#!/usr/bin/env bash
# scripts/smoke-probe.sh — raikou-net smoke probe.
#
# Runs INSIDE the Vagrant VM after the stack is up. Exits 0 iff:
#   1. every service in the chosen compose file has a running container
#   2. the orchestrator's /var/log/orchestrator.log has no ERROR/CRITICAL/Traceback
#   3. the CPE container has a v4 address on its WAN-side interface
#   4. the LAN container has a v4 address (DHCP-assigned) on its LAN-side iface
#
# Interface names are read from examples/double_hop/config.json (the
# source of truth for the topology) via jq.
#
# Args: none. Env:
#   COMPOSE_FILE  default docker-compose.ghcr.yaml
#   COMPOSE_DIR   default /vagrant/examples/double_hop
#   POLL_INTERVAL default 5
#   POLL_TIMEOUT  default 90

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.ghcr.yaml}"
COMPOSE_DIR="${COMPOSE_DIR:-/vagrant/examples/double_hop}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
POLL_TIMEOUT="${POLL_TIMEOUT:-90}"

cd "$COMPOSE_DIR"

fail() { echo "FAIL: $*" >&2; exit 1; }
info() { echo "[smoke] $*"; }

# Need jq to read config.json
command -v jq >/dev/null 2>&1 || {
  info "jq missing; installing"
  sudo apt-get update -qq && sudo apt-get install -y -qq jq
}

# ----- Helper: poll a predicate until it passes or timeout -----
poll() {
  local what="$1"; shift
  local deadline=$(( SECONDS + POLL_TIMEOUT ))
  while (( SECONDS < deadline )); do
    if "$@"; then info "$what: ok"; return 0; fi
    sleep "$POLL_INTERVAL"
  done
  fail "$what: timed out after ${POLL_TIMEOUT}s"
}

# ----- 1. All compose services have a running container -----
check_services_running() {
  local expected running missing
  expected=$(docker compose -f "$COMPOSE_FILE" config --services | sort)
  running=$(docker compose -f "$COMPOSE_FILE" ps --status running --services 2>/dev/null | sort)
  missing=$(comm -23 <(echo "$expected") <(echo "$running"))
  [ -z "$missing" ]
}
poll "all services running" check_services_running

# ----- 2. Orchestrator error scan -----
# grep exits 2 when the file is missing. Without the explicit `test -f`
# guard, that 2 gets swallowed by `2>&1 >/dev/null` and the leading `!`
# inverts it to truthy — masking a startup failure where the log was
# never even created. So: first require the file to exist (poll keeps
# retrying until orchestrator is up), then grep its contents.
check_orchestrator_log() {
  docker exec orchestrator test -f /var/log/orchestrator.log 2>/dev/null || return 1
  ! docker exec orchestrator \
      grep -E 'ERROR|CRITICAL|Traceback' /var/log/orchestrator.log >/dev/null 2>&1
}
poll "orchestrator log clean" check_orchestrator_log

# ----- 3. CPE has v4 IP on its WAN-side interface -----
# config.json shape (per app/utils.py TypedDicts):
#   { "container": { "cpe": [ {"iface": "...", "bridge": "...", ...}, ... ], ... } }
# Pick the iface attached to the cpe→router bridge (cpe-rtr). Selecting
# by bridge name rather than array index survives reordering of the cpe
# interface list in config.json.
cpe_iface=$(jq -r '.container.cpe[] | select(.bridge == "cpe-rtr") | .iface' config.json | head -1)
[ -n "$cpe_iface" ] && [ "$cpe_iface" != "null" ] || fail "could not read cpe-rtr iface from config.json"

check_cpe_ip() {
  local ip
  ip=$(docker exec cpe ip -4 -br addr show "$cpe_iface" 2>/dev/null | awk '{print $3}')
  [ -n "$ip" ]
}
poll "cpe $cpe_iface has v4 ip" check_cpe_ip

# ----- 4. LAN has v4 IP (DHCP-assigned) on its LAN-side interface -----
lan_iface=$(jq -r '.container.lan[0].iface' config.json)
[ -n "$lan_iface" ] && [ "$lan_iface" != "null" ] || fail "could not read lan iface from config.json"

check_lan_ip() {
  local ip
  ip=$(docker exec lan ip -4 -br addr show "$lan_iface" 2>/dev/null | awk '{print $3}')
  [ -n "$ip" ]
}
poll "lan $lan_iface has dhcp v4 ip" check_lan_ip

info "PASS: all probes succeeded"
