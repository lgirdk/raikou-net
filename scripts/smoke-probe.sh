#!/usr/bin/env bash
# scripts/smoke-probe.sh — raikou-net smoke probe.
#
# Runs INSIDE the Vagrant VM after the stack is up. Emits a numbered, per-step
# PASS/FAIL transcript and a final RESULT line, then exits 0 iff all four
# checks pass. Fail-fast: stops at the first failing check.
#   1. every service in the chosen compose file has a running container
#   2. the orchestrator's /var/log/orchestrator.log has no ERROR/CRITICAL/Traceback
#   3. the CPE container has a DHCP v4 address on its WAN-side (cpe-rtr) iface
#   4. the LAN container has a DHCP v4 address on its LAN-side iface
#
# Interface names are read from examples/prplos/config.json via jq.
#
# Args: none. Env:
#   COMPOSE_FILE  default docker-compose.ghcr.yaml
#   COMPOSE_DIR   default /vagrant  (examples/prplos's contents are rsynced here)
#   POLL_INTERVAL default 5
#   POLL_TIMEOUT  default 90

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.ghcr.yaml}"
COMPOSE_DIR="${COMPOSE_DIR:-/vagrant}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
POLL_TIMEOUT="${POLL_TIMEOUT:-90}"

cd "$COMPOSE_DIR"

TOTAL=4
STEP_NO=0

info() { echo "[smoke] $*"; }
rule() { echo "[smoke] ----------------------------------------"; }

# PASS line for the current step.
pass_step() { printf '[smoke] STEP %d/%d  %-30s PASS\n' "$STEP_NO" "$TOTAL" "$1"; }

# FAIL line + verdict for the current step, then exit non-zero.
fail_step() {
  local name="$1" reason="${2:-}"
  printf '[smoke] STEP %d/%d  %-30s FAIL\n' "$STEP_NO" "$TOTAL" "$name"
  if [ -n "$reason" ]; then echo "[smoke]   reason: $reason"; fi
  rule
  echo "[smoke] RESULT: FAIL at step $STEP_NO/$TOTAL ($name)"
  echo "[smoke] (remaining checks skipped)"
  exit 1
}

# Poll a predicate quietly until it passes or POLL_TIMEOUT elapses. Returns 0/1.
poll_check() {
  local deadline=$(( SECONDS + POLL_TIMEOUT ))
  while (( SECONDS < deadline )); do
    if "$@"; then return 0; fi
    sleep "$POLL_INTERVAL"
  done
  return 1
}

# Run a numbered polled step: bump counter, poll, print PASS or fail-exit.
step() {
  local name="$1"; shift
  STEP_NO=$((STEP_NO + 1))
  if poll_check "$@"; then
    pass_step "$name"
  else
    fail_step "$name" "timed out after ${POLL_TIMEOUT}s"
  fi
}

# Need jq to read config.json.
command -v jq >/dev/null 2>&1 || {
  info "jq missing; installing"
  sudo apt-get update -qq && sudo apt-get install -y -qq jq
}

# ----- 1. All compose services have a running container -----
check_services_running() {
  local expected running missing
  expected=$(docker compose -f "$COMPOSE_FILE" config --services | sort)
  running=$(docker compose -f "$COMPOSE_FILE" ps --status running --services 2>/dev/null | sort)
  missing=$(comm -23 <(echo "$expected") <(echo "$running"))
  [ -z "$missing" ]
}
step "all services running" check_services_running

# ----- 2. Orchestrator error scan -----
# grep exits 2 when the file is missing; require the file first (poll retries
# until orchestrator is up), then scan it.
check_orchestrator_log() {
  docker exec orchestrator test -f /var/log/orchestrator.log 2>/dev/null || return 1
  ! docker exec orchestrator \
      grep -E 'ERROR|CRITICAL|Traceback' /var/log/orchestrator.log >/dev/null 2>&1
}
step "orchestrator log clean" check_orchestrator_log

# ----- 3. CPE has a DHCP v4 IP on its WAN-side (cpe-rtr) interface -----
# Selected by bridge (cpe-rtr), not by name: resolves to eth1 in the prplos
# config and survives reordering of the cpe interface list.
STEP_NO=$((STEP_NO + 1))
cpe_iface=$(jq -r '.container.cpe[] | select(.bridge == "cpe-rtr") | .iface' config.json | head -1)
{ [ -n "$cpe_iface" ] && [ "$cpe_iface" != "null" ]; } \
  || fail_step "cpe cpe-rtr dhcp v4" "could not read cpe-rtr iface from config.json"
check_cpe_ip() {
  local ip
  ip=$(docker exec cpe ip -4 -br addr show "$cpe_iface" 2>/dev/null | awk '{print $3}')
  [ -n "$ip" ]
}
if poll_check check_cpe_ip; then
  pass_step "cpe $cpe_iface dhcp v4"
else
  fail_step "cpe $cpe_iface dhcp v4" "no v4 address after ${POLL_TIMEOUT}s"
fi

# ----- 4. LAN gets a DHCP v4 IP on its LAN-side interface -----
# The LAN container doesn't auto-request a lease; kick off ISC dhclient first
# (the lan image always ships isc-dhclient), then poll. A non-zero dhclient
# exit is tolerated — the address poll is the real gate.
STEP_NO=$((STEP_NO + 1))
lan_iface=$(jq -r '.container.lan[0].iface' config.json)
{ [ -n "$lan_iface" ] && [ "$lan_iface" != "null" ]; } \
  || fail_step "lan dhcp v4" "could not read lan iface from config.json"
info "triggering dhclient on lan $lan_iface"
docker exec lan dhclient -v "$lan_iface" || true
check_lan_ip() {
  local ip
  ip=$(docker exec lan ip -4 -br addr show "$lan_iface" 2>/dev/null | awk '{print $3}')
  [ -n "$ip" ]
}
if poll_check check_lan_ip; then
  pass_step "lan $lan_iface dhcp v4"
else
  fail_step "lan $lan_iface dhcp v4" "no v4 address after ${POLL_TIMEOUT}s"
fi

rule
echo "[smoke] RESULT: PASS  (4/4 passed)"
