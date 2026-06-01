#!/bin/bash
# bench-up.sh — bring up the docker stack, then deploy the LXD CPE once the
# orchestrator has created the bridges. Invoked by the systemd unit (ExecStart).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"

docker compose -f "$COMPOSE_FILE" up -d

# rdk-cpe.sh itself waits for cpe-rtr / lan-cpe before importing/starting.
ENABLE_WIFI="${ENABLE_WIFI:-0}" "$SCRIPT_DIR/rdk-cpe.sh" up
