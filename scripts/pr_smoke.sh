#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"

export NEBIUS_API_KEY=""
export TAVILY_API_KEY=""
export COMPOSIO_API_KEY=""
export IA_LIVE_MODE=""

run() {
  printf '\n==> %s\n' "$*" >&2
  "$@"
}

json_check() {
  local input_path="$1"
  local output_path="${2:-/tmp/ia_pr_smoke.checked.json}"
  run "$PYTHON_BIN" -m json.tool "$input_path" >"$output_path"
}

command_json_check() {
  local output_path="$1"
  shift
  run "$@" >"$output_path"
  json_check "$output_path" "${output_path}.checked"
}

run_secret_shape_guard() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '\n==> skipping secret-shaped token guard outside git worktree\n'
    return 0
  fi

  local openai_prefix="sk""-proj-"
  local tavily_prefix="tvly""-"
  local google_prefix="GOC""SPX-"
  local composio_prefix="ak""_"
  local nebius_prefix="v1""\\."
  local oauth_secret_assignment="(GITHUB_OAUTH_CLIENT_SECRET|GOOGLE_OAUTH_CLIENT_SECRET)[[:space:]]*=[[:space:]]*[\"']?[[:alnum:]_-]{24,}[\"']?"
  local secret_pattern="(${openai_prefix}[[:alnum:]_-]{20,}|${tavily_prefix}[[:alnum:]_-]{20,}|${google_prefix}[[:alnum:]_-]{10,}|${composio_prefix}[[:alnum:]_-]{20,}|${nebius_prefix}[[:alnum:]_.-]{60,}|BEGIN [A-Z ]*PRIVATE KEY|${oauth_secret_assignment})"
  local secret_hits

  secret_hits="$(git grep -l -E "$secret_pattern" -- . || true)"

  if [ -n "$secret_hits" ]; then
    printf '\nSecret-shaped tokens were found in tracked public files. File names only:\n'
    printf '%s\n' "$secret_hits"
    return 1
  fi

  printf '\n==> secret-shaped token guard passed\n'
}

run "$PYTHON_BIN" -m py_compile agent/*.py agent/adapters/*.py agent/mind/*.py web/*.py

json_check AI_JUDGE_MANIFEST.json /tmp/ia_manifest.checked.json
json_check web/static/skills-registry.json /tmp/ia_skills_registry.checked.json
json_check schemas/decision_packet.schema.json /tmp/ia_decision_packet_schema.checked.json
json_check schemas/agent_access_decision_brief.schema.json /tmp/ia_decision_brief_schema.checked.json
json_check schemas/pilot_memo.schema.json /tmp/ia_pilot_memo_schema.checked.json

command_json_check /tmp/ia_judge.no_write.json "$PYTHON_BIN" -m agent.judge --no-write --json
command_json_check /tmp/ia_skills.json "$PYTHON_BIN" -m agent.skills --json
command_json_check /tmp/ia_packet_diff.no_write.json "$PYTHON_BIN" -m agent.packet_diff --no-write --json
command_json_check /tmp/ia_evidence_receipts.no_write.json "$PYTHON_BIN" -m agent.evidence_receipts --no-write --json
command_json_check /tmp/ia_packet_authority.json "$PYTHON_BIN" -m agent.packet_authority --json
command_json_check /tmp/ia_verification.all.json "$PYTHON_BIN" -m agent.verification --all --json
command_json_check /tmp/ia_subscribers.json "$PYTHON_BIN" -m agent.subscribers --json
command_json_check /tmp/ia_outcome_memo.no_write.json "$PYTHON_BIN" -m agent.outcome_memo --no-write --json
command_json_check /tmp/ia_gate.all.json "$PYTHON_BIN" -m agent.gate --all --json
command_json_check /tmp/ia_adapters.all.json "$PYTHON_BIN" -m agent.adapters --all --json
command_json_check /tmp/ia_sponsor_readiness.no_write.json "$PYTHON_BIN" -m agent.sponsor_readiness --no-write --json
command_json_check /tmp/ia_proof_health.no_write.json "$PYTHON_BIN" -m agent.proof_health --no-write --json
command_json_check /tmp/ia_spend.no_write.json "$PYTHON_BIN" -m agent.spend --no-write --json
command_json_check /tmp/ia_trial.json "$PYTHON_BIN" -m agent.trial examples/requests/support_triage_trial.yml --json
command_json_check /tmp/ia_trial_outcome_memo.no_write.json "$PYTHON_BIN" -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml --no-write --json
command_json_check /tmp/ia_trial_evidence_replay.no_write.json "$PYTHON_BIN" -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --json
command_json_check /tmp/ia_live_evidence_rehearsal.no_write.json "$PYTHON_BIN" -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial --json
command_json_check /tmp/ia_pilot_memo.no_write.json "$PYTHON_BIN" -m agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --json
command_json_check /tmp/ia_verify_artifacts.json "$PYTHON_BIN" -m agent.verify_artifacts --json

run "$PYTHON_BIN" -m agent.judge --no-write
run "$PYTHON_BIN" -m agent.pilot_memo examples/requests/support_triage_trial.yml --no-write --copy
run "$PYTHON_BIN" -m agent.contract --all
run "$PYTHON_BIN" -m agent.spend --no-write
run "$PYTHON_BIN" -m agent.verify_artifacts
run "$PYTHON_BIN" -m unittest discover -s tests
run_secret_shape_guard

printf '\nInferenceAtlas PR smoke gate passed.\n'
