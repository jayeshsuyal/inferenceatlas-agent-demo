#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"
HOST="${IA_REVIEW_HOST:-127.0.0.1}"
PORT="${IA_REVIEW_PORT:-8080}"
FIXTURE="${IA_REVIEW_FIXTURE:-mcp_tool_blast_radius}"
OPEN_BROWSER=1
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: bash scripts/review_60.sh [--port 8080] [--host 127.0.0.1] [--fixture mcp_tool_blast_radius] [--no-open] [--dry-run]

Runs the 60-second public review path:
  judge smoke -> local web server -> IA Packet autorun URL
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --host)
      HOST="${2:?--host requires a value}"
      shift 2
      ;;
    --fixture)
      FIXTURE="${2:?--fixture requires a value}"
      shift 2
      ;;
    --no-open)
      OPEN_BROWSER=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASE_URL="http://${HOST}:${PORT}"
PACKET_URL="${BASE_URL}/packet?fixture=${FIXTURE}&autorun=1"

fail() {
  printf '\nreview_60 failed: %s\n' "$*" >&2
  exit 1
}

check_python() {
  "$PYTHON_BIN" - <<'PY' || exit 1
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9+ required. Current: " + sys.version.split()[0])
PY
}

check_fixture() {
  "$PYTHON_BIN" - "$FIXTURE" <<'PY' || exit 1
import sys
from agent.workbench import build_workbench_result

fixture_id = sys.argv[1]
result = build_workbench_result(fixture_id)
decision = result["decision"]
local = result["local_verification"]

assert decision["production_access"] is False
assert decision["permission_grants"] is False
assert decision["external_writes"] is False
assert decision["approval_granted"] is False
assert local["calls_v1"] is False
assert local["read_only"] is True
PY
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

wait_for_packet_api() {
  local attempts=40
  local i
  for i in $(seq 1 "$attempts"); do
    if "$PYTHON_BIN" - "$BASE_URL" "$FIXTURE" <<'PY' >/dev/null 2>&1
import json
import sys
import urllib.request
import urllib.parse

base_url = sys.argv[1]
fixture = urllib.parse.quote(sys.argv[2])
with urllib.request.urlopen(base_url + "/api/ia-packet?fixture=" + fixture, timeout=1.0) as response:
    payload = json.loads(response.read().decode("utf-8"))
if payload.get("schema_version") != "ia_packet_detail.v0":
    raise SystemExit(1)
PY
    then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

print_banner() {
  local status="$1"
  cat <<EOF

[ok] ${status}  (no keys required - dry-run by default - no v1 calls)
[ok] IA Packet autorun: ${PACKET_URL}

What you will see in 60 seconds:
  1. Agent/tool request structured into a public fixture
  2. IA Packet - verdict, blocked claims, missing proof
  3. Sponsor Proof Trace - Tavily -> Composio -> OpenClaw -> Nebius
  4. Downstream trust - gateways, CI, spend, review, observability
  5. Export artifact - copy IA Packet brief or open Workbench

Press Ctrl+C when done.
EOF
}

check_python
check_fixture

export COMPOSIO_DRY_RUN="${COMPOSIO_DRY_RUN:-1}"
export IA_LIVE_MODE=""

if [ "$DRY_RUN" = "1" ]; then
  print_banner "Review path preflight passed"
  exit 0
fi

if port_in_use; then
  fail "port ${PORT} is already in use. Stop the existing process or rerun with --port <free-port>."
fi

"$PYTHON_BIN" -m agent.judge --no-write --json >/tmp/ia_review_60_judge.json

SERVER_LOG="${TMPDIR:-/tmp}/ia_review_60_web_${PORT}.log"
"$PYTHON_BIN" -m uvicorn web.app:app --host "$HOST" --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID="$!"

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if ! wait_for_packet_api; then
  tail -40 "$SERVER_LOG" >&2 || true
  fail "web server did not become ready at ${BASE_URL}. See ${SERVER_LOG}."
fi

print_banner "Backend ready"

if [ "$OPEN_BROWSER" = "1" ] && command -v open >/dev/null 2>&1; then
  open "$PACKET_URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
