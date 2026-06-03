#!/bin/bash
# rdk-cpe.sh — deploy ("up") or tear down ("down") a single RDK-generic CPE as an
# LXD container, attaching eth0/eth1 to the raikou-net orchestrator's Linux bridges.
#
# Distilled from gen/vcpe.sh + gen/gen-util.sh for the single-CPE prplos bench.
# Dropped vs. the original: suffix/vlan_map, host bridge creation, VLAN-translation
# farm, lxdbr1, hashing and LXD-certificate helpers.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- configuration (env-overridable) ----
CPE_NAME="${CPE_NAME:-rdk-cpe}"
WAN_BRIDGE="${WAN_BRIDGE:-cpe-rtr}"
LAN_BRIDGE="${LAN_BRIDGE:-lan-cpe}"
ENABLE_WIFI="${ENABLE_WIFI:-0}"
CUST_ID="${CUST_ID:-8}"
PROFILE_TEMPLATE="${PROFILE_TEMPLATE:-$SCRIPT_DIR/profiles/vcpe.yaml}"
RDK_IMAGE="${RDK_IMAGE:-}"   # explicit path wins; else newest images/*.tar.bz2 (resolved in cmd_up)
IMAGE_ALIAS="${IMAGE_ALIAS:-$CPE_NAME}"
PROFILE_NAME="$CPE_NAME"
NVRAM_VOL="${NVRAM_VOL:-vcpe-nvram}"

# default MACs (base values from gen/vcpe.sh, single CPE / no suffix)
ETH0_MAC="00:16:3e:20:79:68"
ETH1_MAC="00:16:3e:16:5f:7c"

log() { echo "[rdk-cpe] $*"; }
die() { echo "[rdk-cpe][ERROR] $*" >&2; exit 1; }

check_lxd() {
    command -v lxc >/dev/null 2>&1 || die "lxc not found; is LXD installed?"
    lxc list >/dev/null 2>&1 || die "cannot talk to the LXD daemon"
}

wait_for_bridges() {
    local b timeout=60 elapsed
    for b in "$WAN_BRIDGE" "$LAN_BRIDGE"; do
        elapsed=0
        until ip link show "$b" >/dev/null 2>&1; do
            [ "$elapsed" -ge "$timeout" ] && \
                die "bridge $b not present after ${timeout}s (is the docker stack up?)"
            sleep 2; elapsed=$((elapsed + 2))
        done
        log "bridge $b present"
    done
}

setup_wifi() {
    [ "$ENABLE_WIFI" = "1" ] || return 0
    log "setting up virtual wlan radios (mac80211_hwsim)"
    if [ "$(ls -1d /sys/class/ieee80211/phy* 2>/dev/null | wc -l)" -lt 4 ]; then
        sudo modprobe -r mac80211_hwsim 2>/dev/null || true
        sudo modprobe mac80211_hwsim radios=4
        sleep 1
    fi
    local i
    for i in 0 1 2 3; do
        if ip link show "wlan$i" >/dev/null 2>&1; then
            sudo ip link set "wlan$i" down 2>/dev/null || true
            sudo ip link set "wlan$i" name "virt-wlan$i" 2>/dev/null || true
            sudo ip link set "virt-wlan$i" up 2>/dev/null || true
        fi
    done
}

cmd_up() {
    check_lxd
    # Resolve the rootfs: an explicit RDK_IMAGE wins; otherwise pick the newest
    # *.tar.bz2 under images/ (the filename varies by tag, e.g. qemux86 vs bpi).
    if [ -z "$RDK_IMAGE" ]; then
        RDK_IMAGE="$(ls -t "$SCRIPT_DIR"/images/*.tar.bz2 2>/dev/null | head -n1)"
    fi
    [ -n "$RDK_IMAGE" ] && [ -f "$RDK_IMAGE" ] || \
        die "no RDK rootfs (*.tar.bz2) found in $SCRIPT_DIR/images (set RDK_IMAGE to override)"
    log "using rootfs $RDK_IMAGE"
    wait_for_bridges
    setup_wifi

    # nvram volume
    lxc storage volume show default "$NVRAM_VOL" >/dev/null 2>&1 || \
        lxc storage volume create default "$NVRAM_VOL" size=4MiB

    # import image (always refresh the alias). The RDK *.lxc.tar.bz2 is a UNIFIED
    # LXD image: it already embeds its own metadata.yaml + rootfs/, so it must be
    # imported with a SINGLE argument. Importing it split (metadata + rootfs) makes
    # LXD treat the whole blob as the rootfs, nesting the real filesystem under
    # /rootfs/ inside the container — which breaks `exec /sbin/init` at start.
    lxc image delete "$IMAGE_ALIAS" 2>/dev/null || true
    lxc image import "$RDK_IMAGE" --alias "$IMAGE_ALIAS" || die "lxc image import failed"

    # profile from template
    lxc profile create "$PROFILE_NAME" 2>/dev/null || true
    lxc profile edit "$PROFILE_NAME" < "$PROFILE_TEMPLATE" || die "lxc profile edit failed"

    # strip template's default wlan devices (re-added below only if WiFi enabled)
    local i
    for i in 0 1 2 3; do
        lxc profile device remove "$PROFILE_NAME" "wlan${i}" >/dev/null 2>&1 || true
    done

    # WAN (eth0) + LAN (eth1) bridged nics, attached to the orchestrator bridges
    lxc profile device add "$PROFILE_NAME" eth0 nic \
        nictype=bridged parent="$WAN_BRIDGE" hwaddr="$ETH0_MAC" name=eth0
    lxc profile device add "$PROFILE_NAME" eth1 nic \
        nictype=bridged parent="$LAN_BRIDGE" hwaddr="$ETH1_MAC" name=eth1

    # nvram disk (replace template's hardcoded source)
    lxc profile device remove "$PROFILE_NAME" nvram >/dev/null 2>&1 || true
    lxc profile device add "$PROFILE_NAME" nvram disk \
        pool=default source="$NVRAM_VOL" path=/data/rdkb_nvram

    # optional wlan nics
    if [ "$ENABLE_WIFI" = "1" ]; then
        for i in 0 1 2 3; do
            lxc profile device add "$PROFILE_NAME" "wlan${i}" nic \
                nictype=physical parent="virt-wlan${i}" name="wlan${i}" >/dev/null 2>&1 || true
        done
    fi

    # create + configure + start
    lxc init "$IMAGE_ALIAS" "$CPE_NAME" -p "$PROFILE_NAME" || die "lxc init failed"
    lxc config set "$CPE_NAME" environment.CREATION_DATE="$(date +"%Y-%m-%d_%H:%M:%S")"
    lxc config set "$CPE_NAME" environment.SERIAL_NUMBER="$(echo "${ETH0_MAC//:/}" | tr '[:lower:]' '[:upper:]')"
    lxc config set "$CPE_NAME" environment.HARDWARE_VERSION="1.0"
    lxc start "$CPE_NAME" || die "lxc start failed"
    log "started $CPE_NAME (eth0->$WAN_BRIDGE, eth1->$LAN_BRIDGE)"

    # optional customer-id provisioning
    if [ -n "$CUST_ID" ]; then
        sleep 5
        lxc exec "$CPE_NAME" -- /usr/bin/set_customerID_pp "$CUST_ID" 2>/dev/null || \
            log "set_customerID_pp not run (binary missing or container not ready yet)"
    fi
}

cmd_down() {
    check_lxd
    lxc delete "$CPE_NAME" -f 2>/dev/null || true
    lxc profile delete "$PROFILE_NAME" 2>/dev/null || true
    lxc storage volume delete default "$NVRAM_VOL" 2>/dev/null || true
    lxc image delete "$IMAGE_ALIAS" 2>/dev/null || true
    if [ "$ENABLE_WIFI" = "1" ]; then
        sudo modprobe -r mac80211_hwsim 2>/dev/null || true
    fi
    log "cleaned up $CPE_NAME"
}

case "${1:-}" in
    up)   cmd_up ;;
    down) cmd_down ;;
    *)    echo "Usage: $0 {up|down}" >&2; exit 1 ;;
esac
