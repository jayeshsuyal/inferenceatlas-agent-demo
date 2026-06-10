# Command Reference

Status: public command reference
Purpose: keep the README one-run simple while preserving the full reviewer and CTO command surface

Private engine, public proof.

## Default Public Run

```bash
bash scripts/run.sh
```

This runs the judge harness in no-write mode. It requires no API keys and keeps live integrations disabled by default.

## PR Safety Gate

```bash
bash scripts/pr_smoke.sh
```

This is the local mirror of the public PR smoke gate: schema parsing, JSON command surfaces, walkthrough smoke, artifact integrity, unit tests, and tracked secret-shaped token guard.
For the full served reviewer smoke inside this gate, install the web extra first:

```bash
pip install -e ".[web]"
```

## Demo Rehearsal Gate

```bash
python3 scripts/demo_rehearsal.py
python3 scripts/demo_rehearsal.py --json
```

This checks the recording-critical path: no-key review preflight, four Ask IA prompts, Portkey dry-run gate, Sponsor Proof Run safety locks, and artifact integrity. It does not use live keys or enable writes.

## Optional Keyed Sponsor Rehearsal

```bash
python3 -m web
python3 scripts/keyed_sponsor_rehearsal.py --base-url http://127.0.0.1:8080
python3 scripts/keyed_sponsor_rehearsal.py --base-url http://127.0.0.1:8080 --json
```

This requires local sponsor keys. It verifies Nebius returns live read-only reviewer narration, Tavily returns live evidence, Composio remains dry-run/no-execute, Portkey remains dry-run/no-mutation, the IA Packet decision lock stays unchanged, and the local run ledger records the proof run. It prints status and counts only, never secret values.

## Optional Portkey BYO Guardrail Probe

```bash
PORTKEY_GUARDRAIL_TOKEN="local-demo-token" python3 -m web
PORTKEY_GUARDRAIL_TOKEN="local-demo-token" \
  python3 scripts/portkey_guardrail_probe.py \
  --base-url http://127.0.0.1:8080 \
  --json
```

This sends a Portkey-shaped `beforeRequestHook` payload to IA, verifies the packet-backed boolean `verdict`, checks the read-only safety boundary, and confirms the local guardrail event was recorded. It does not call Portkey APIs, push policies, transform requests, execute writes, or print the shared token.

For a real Portkey account demo, configure the Portkey BYO Guardrails webhook URL to point at the public IA URL ending in `/api/portkey/guardrail`, set the webhook header to `Authorization: Bearer <same token>`, and pass metadata such as `{"ia_fixture":"ai_spend_budget_overrun","ia_requested_mode":"model_request"}`. Portkey documents webhook metadata and the required boolean `verdict` response here: `https://portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails`.

## Portkey Guardrail Proof Loop

```bash
python3 -m agent.portkey_guardrail_proof_loop \
  --fixture ai_spend_budget_overrun \
  --requested-mode model_request
```

This renders the read-only proof loop a reviewer expects after a Portkey guardrail call: webhook shape, packet reference, verdict, latency, policy preview, auth boundary, and safety invariants. It writes nothing and makes no Portkey API calls.

## Full Sponsor ProofGraph

```bash
python3 -m agent.proof_graph --include-all-sponsors --json
```

This renders the complete packet-bound proof graph in one command: Tavily evidence candidates, Composio dry-run blast radius, OpenClaw runtime trace, Nebius reviewer synthesis, and the Portkey downstream guardrail consumer. The preset is equivalent to the explicit sponsor/downstream flags and remains non-approving, non-mutating, no-write, and no-live-call by default.

## Sponsor Value Receipts

```bash
python3 -m agent.sponsor_value_receipts --no-write
python3 -m agent.sponsor_value_receipts --no-write --json
```

This renders one receipt per sponsor/downstream tool: Tavily, Composio, OpenClaw, Nebius, and Portkey. Each receipt shows the proof contribution, what stayed blocked, and the safety boundary that keeps IA as the packet authority.

## Optional Max Rehearsal Stress

```bash
IA_SPONSOR_PROOF_RUN_LEDGER_DIR="$(mktemp -d)" \
LLM_PROVIDER=nebius COMPOSIO_DRY_RUN=1 \
uvicorn web.app:app --host 127.0.0.1 --port 8110

python3 scripts/max_rehearsal_stress.py \
  --base-url http://127.0.0.1:8110 \
  --keyed-runs 20 \
  --concurrency 3 \
  --json \
  --output-doc docs/internal/STRESS_TEST_RESULTS_2026_06_09.md
```

This is the local-only pre-recording stress gate. It repeats keyed live-read sponsor rehearsals, mixes fallback runs, pressures packet/chat/Portkey/ledger APIs, checks adversarial fail-closed inputs, and verifies four zero counters: no writes, no approvals, no packet mutations, and no secret-shaped output.

## Full Public Python Commands

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.evidence_receipts
python3 -m agent.packet_authority
python3 -m agent.proof_graph --include-all-sponsors --json
python3 -m agent.verification --all
python3 -m agent.subscribers --json
python3 -m agent.downstream_gate --all
python3 -m agent.packet_advisor --fixture ai_spend_budget_overrun --subscriber portkey_model_spend_gate --question "Can Portkey allow this spend?" --json
python3 -m agent.portkey_adapter --fixture ai_spend_budget_overrun --mode dry-run --json
python3 -m agent.portkey_guardrail_proof_loop --fixture ai_spend_budget_overrun --requested-mode model_request --json
python3 -m agent.outcome_memo
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.sponsor_readiness
python3 -m agent.sponsor_value_receipts --no-write
python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml
python3 -m agent.sponsor_proof_trace examples/requests/support_triage_trial.yml
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.verify_artifacts
python3 scripts/demo_rehearsal.py
python3 -m unittest discover -s tests
```

## Installed Command Set

```bash
pip install -e ".[web]"
ia-judge
ia-review --list
ia-skills
ia-packet-diff
ia-receipts
ia-snapshot
ia-verify --all
ia-subscribers --json
ia-downstream-gate --all
ia-packet-advisor --fixture ai_spend_budget_overrun --subscriber portkey_model_spend_gate --question "Can Portkey allow this spend?" --json
ia-portkey-adapter --fixture ai_spend_budget_overrun --mode dry-run --json
ia-outcome-memo
ia-contract --all
ia-gate --all
ia-adapters --all
ia-sponsor-readiness
ia-sponsor-value-receipts --no-write
ia-sponsor-proof-collector examples/requests/support_triage_trial.yml
ia-sponsor-proof-trace examples/requests/support_triage_trial.yml
ia-trust
ia-review-room
ia-proof-health
ia-spend examples/requests/ai_spend_budget_overrun.yml
ia-trial examples/requests/support_triage_trial.yml
ia-trial-outcome-memo examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
ia-verify-artifacts
```

## Safety Defaults

- The default public run does not require keys.
- Composio remains dry-run unless explicitly configured outside the public path.
- Sponsor tools contribute proof only; they do not approve, grant, write, spend, or mutate production.
- Use `bash scripts/pr_smoke.sh` before opening or merging product changes.
