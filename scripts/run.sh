#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"

export COMPOSIO_DRY_RUN="${COMPOSIO_DRY_RUN:-1}"
export IA_LIVE_MODE="${IA_LIVE_MODE:-}"

exec "$PYTHON_BIN" -m agent.judge --no-write "$@"
