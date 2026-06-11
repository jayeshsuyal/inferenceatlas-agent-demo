#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"
HOST="${IA_REVIEWER_SMOKE_HOST:-127.0.0.1}"
PORT="${IA_REVIEWER_SMOKE_PORT:-8097}"
BASE_URL="http://${HOST}:${PORT}"
SERVER_LOG="${TMPDIR:-/tmp}/ia_reviewer_smoke_web_${PORT}.log"
LEDGER_DIR="${TMPDIR:-/tmp}/ia_reviewer_smoke_ledger_${PORT}"

export NEBIUS_API_KEY=""
export OPENAI_API_KEY=""
export TAVILY_API_KEY=""
export COMPOSIO_API_KEY=""
export IA_LIVE_MODE=""
export IA_DISABLE_DOTENV="1"
export IA_SPONSOR_PROOF_RUN_LEDGER_DIR="$LEDGER_DIR"

fail() {
  printf 'Reviewer smoke gate failed: %s\n' "$1" >&2
  exit 1
}

port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  if command -v nc >/dev/null 2>&1; then
    nc -z "$HOST" "$PORT" >/dev/null 2>&1
    return $?
  fi

  return 1
}

wait_for_ready() {
  local attempts="${IA_REVIEWER_SMOKE_READY_ATTEMPTS:-60}"
  local i

  for ((i = 1; i <= attempts; i++)); do
    if "$PYTHON_BIN" - "$BASE_URL" <<'PY' >/dev/null 2>&1
import sys
import urllib.request

base_url = sys.argv[1].rstrip("/")
with urllib.request.urlopen(base_url + "/api/workbench", timeout=1.0) as response:
    if response.status != 200:
        raise SystemExit(1)
PY
    then
      return 0
    fi
    sleep 0.25
  done

  return 1
}

"$PYTHON_BIN" - <<'PY' >/dev/null
import importlib.util
import sys

missing = [name for name in ("fastapi", "uvicorn") if importlib.util.find_spec(name) is None]
if missing:
    print(
        "Missing web smoke dependencies: "
        + ", ".join(missing)
        + ". Install with: python -m pip install -e '.[web]'",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

if port_in_use; then
  fail "port ${PORT} is already in use. Set IA_REVIEWER_SMOKE_PORT to a free port."
fi

rm -rf "$LEDGER_DIR"
mkdir -p "$LEDGER_DIR"

"$PYTHON_BIN" -m uvicorn web.app:app --host "$HOST" --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID="$!"

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if ! wait_for_ready; then
  tail -60 "$SERVER_LOG" >&2 || true
  fail "server did not become ready at ${BASE_URL}. See ${SERVER_LOG}."
fi

"$PYTHON_BIN" scripts/reviewer_smoke.py --base-url "$BASE_URL"
"$PYTHON_BIN" scripts/reviewer_stress_smoke.py --base-url "$BASE_URL" --session-id "reviewer-stress-gate"
"$PYTHON_BIN" scripts/review_run_rehearsal_gate.py --base-url "$BASE_URL" --json

printf '\nReviewer smoke gate passed at %s.\n' "$BASE_URL"
