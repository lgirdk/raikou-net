#!/bin/bash
# bench-down.sh — tear the CPE down first, then the docker stack. Invoked by the
# systemd unit (ExecStop). Tolerates partial state.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"

ENABLE_WIFI="${ENABLE_WIFI:-0}" "$SCRIPT_DIR/rdk-cpe.sh" down || true
docker compose -f "$COMPOSE_FILE" down
