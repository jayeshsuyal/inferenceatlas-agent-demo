# CTO Handoff

Status: build handoff for live sponsor path
Audience: CTO / engineering owner
Default safety posture: no-key offline demo stays green while live integrations are added

## Start Here

Run the current proof surface:

```bash
python3 -m agent.demo
python3 -m agent.skills
python3 -m agent.evidence_receipts --no-write
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.sponsor_readiness
python3 -m unittest discover -s tests
```

Expected result:

- the demo runs without API keys
- Agent Skills reports the public capability map without exposing private source
- Evidence Receipt Ledger attaches proof, reviewer, and cost/procurement receipts without weakening the packet lock
- Design Partner Outcome Memo turns the trial request into a meeting-ready decision without approving access
- Sponsor Evidence Replay attaches sponsor proof slots without changing the decision, granting permissions, or writing
- Live Evidence Rehearsal accepts sanitized Tavily, Composio, Nebius, and OpenClaw outputs while preserving the same locked decision
- sponsor live readiness shows where Nebius, Tavily, Composio, and OpenClaw can add proof without approval power
- packet, trace, decision brief, and Proof Health artifacts regenerate under `examples/generated/`
- production access remains blocked
- external writes remain disabled
- Composio remains dry-run by default

## What Is Stable

These pieces are safe to build on:

| Area | Path | Build role |
| --- | --- | --- |
| Offline judge harness | `agent/demo.py` | Entry point for no-key and live-mode demo paths. Keep this command stable. |
| Agent Skills registry | `agent/skills.py` | Canonical public capability map. Add new public skills here before adding docs or CLI projections. |
| DecisionPacket source | `agent/packet.py` | Canonical structured review object. Live integrations should enrich this shape, not bypass it. |
| Evidence Receipt Ledger | `agent/evidence_receipts.py` | Receipt-backed proof, reviewer, and cost/procurement controls. Receipts can add context but cannot approve access or weaken packet locks. |
| Packet Diff projection | `agent/packet_diff.py` | Scenario comparison surface proving low, medium/high, and critical requests produce different load-bearing fields. |
| Packet Outcome Memo projection | `agent/outcome_memo.py` | Meeting-ready human decision derived from packet, brief, policy gate, Proof Health, and sponsor readiness. |
| Design Partner Outcome Memo projection | `agent/trial_outcome_memo.py` | Trial-request meeting decision derived from the public trial bundle. Keep it no-key, non-approving, and tied to the same packet/brief spine. |
| Sponsor Evidence Replay projection | `agent/trial_evidence_replay.py` | Dry-run sponsor proof replay derived from the public trial bundle and outcome memo. It can ingest sanitized evidence from `examples/evidence/support_triage_trial` while keeping sponsors as proof contributors, not decision owners. |
| Sponsor Proof Trace | `agent/sponsor_proof_trace.py` | Canonical locked-order trace for Tavily, Composio, OpenClaw, and Nebius proof collection. This is the safe runtime object for live sponsor wiring. |
| Sanitized evidence fixtures | `examples/evidence/support_triage_trial/` | Redacted provider-output shape for CTO-held Tavily, Composio, Nebius, and OpenClaw results. Replace with redacted local files only; never commit secrets. |
| Decision brief projection | `agent/decision_brief.py` | Skim-ready access decision derived from the packet. Do not make this an independent truth source. |
| Proof Health projection | `agent/proof_health.py` | Lifecycle report for Packet Drift, stale assumptions, expired reviewer gates, and next human health check. Keep it non-approving. |
| AI Spend Review projection | `agent/spend.py` | Finance/Procurement review packet for AI budget shock. Keep it non-approving, provider-neutral, and evidence-first. |
| ChatAnswer contract | `agent/chat_answer.py` | Structured answer metadata for high-stakes web replies. Keep it packet-backed, source-labeled, and non-approving. |
| Renderers | `agent/renderers.py` | Markdown projections for packet, trace, and brief. Add new surfaces here. |
| Schemas | `schemas/` | Public contracts for generated JSON artifacts. Update tests with any schema change. |
| Generated proof | `examples/generated/` | Checked-in artifacts judges and AI reviewers can inspect. Regenerate after behavior changes. |
| Sponsor readiness | `agent/sponsor_readiness.py` | CTO-facing map for live sponsor value, visible artifacts, and safety boundaries. |
| Safety tests | `tests/` | Guardrails for no-key execution, blocked access, dry-run defaults, and artifact shape. |
| CI smoke | `.github/workflows/smoke.yml` | GitHub Actions proof that the public harness is runnable and safe by default. |

## What Is Transitional

The files below are useful live-mode scaffolding, but still reflect the older cost-optimization agent surface:

| Path | Current state | Recommended action |
| --- | --- | --- |
| `agent/config.py` | System prompt and tool descriptions still reference AI cost optimization. | Refactor prompt toward agent-access review before recording the live demo. |
| `agent/tools.py` | Tavily and Composio wrappers exist, but Composio has a generic action helper. | Add explicit dry-run access-planning helpers before any live action path. |
| `agent/runtime.py` | Nebius/OpenClaw runtime wrapper exists. | Keep it optional; live mode should enrich packet/trace artifacts and preserve offline fallback. |
| `agent/agent.py` and `agent/cli.py` | Generic chat wrapper exists. | Useful for live narration, but the judge demo should stay packet-first. |

## Product Spine

The public branch should keep one clear object spine:

```text
messy agent-access request
-> Agent Skills registry
-> source status
-> evidence notes and missing proof
-> DecisionPacket
-> Packet Diff
-> Evidence Receipt Ledger
-> Agent Access Decision Brief
-> Packet Outcome Memo
-> Design Partner Outcome Memo
-> Sponsor Evidence Replay
-> Live Evidence Rehearsal
-> Proof Health
-> AI Spend Review
-> trace
-> Markdown/JSON artifacts
```

Live integrations should attach to the spine as structured evidence or scoped tool-access plans. They should not replace the packet with a free-form chat answer.

## Live Build Order

1. Keep `python3 -m agent.demo` green without keys.
2. Run `python3 -m agent.sponsor_readiness --inspect-env` locally to confirm which sponsor keys are configured without printing values.
3. Add Tavily evidence notes as structured packet entries.
4. Add Nebius narration that summarizes the existing packet without changing safety defaults.
5. Add Composio dry-run access planning for GitHub, Slack, and Jira.
6. Add OpenClaw step recording into the trace artifact.
7. Preserve Proof Health as a lifecycle projection; live evidence may refresh drift inputs but cannot auto-approve access.
8. Update generated artifacts and tests after each step.
9. Record the live walkthrough only after offline and live paths both preserve the safety contract.

## Integration Rules

Every live integration should answer four questions before code lands:

| Question | Required answer |
| --- | --- |
| What packet fields can this integration enrich? | Name exact fields, for example `evidence_notes`, `tool_access_plan`, or `source_status`. |
| What can it never change? | Safety defaults, blocked claims, and production approval state. |
| What artifact proves it ran? | JSON field, Markdown section, trace step, or test assertion. |
| What happens without keys? | The offline deterministic path still works and generated artifacts still parse. |

## Safety Invariants

Do not merge live-mode work unless these remain true:

- `approval_granted` is `false`
- `external_writes_enabled` is `false`
- `composio_dry_run` is `true`
- production access remains blocked
- live evidence cannot auto-approve access
- runtime tool prompts do not replace pre-permission eligibility review
- no secrets, tokens, private customer data, or private v1 source are committed

## Local Runbook

Use this sequence before pushing:

```bash
python3 -m json.tool AI_JUDGE_MANIFEST.json >/tmp/manifest_check.json
python3 -m json.tool schemas/decision_packet.schema.json >/tmp/decision_packet_schema_check.json
python3 -m json.tool schemas/agent_access_decision_brief.schema.json >/tmp/decision_brief_schema_check.json
python3 -m py_compile agent/*.py
env NEBIUS_API_KEY= TAVILY_API_KEY= COMPOSIO_API_KEY= IA_LIVE_MODE= python3 -m agent.demo >/tmp/inferenceatlas_demo.txt
python3 -m agent.sponsor_readiness --no-write
python3 -m agent.sponsor_proof_trace examples/requests/support_triage_trial.yml --no-write --json >/tmp/sponsor_proof_trace_check.json
python3 -m agent.evidence_receipts --no-write --json >/tmp/evidence_receipts_check.json
python3 -m json.tool examples/generated/support_triage_agent.packet.json >/tmp/packet_check.json
python3 -m json.tool examples/generated/support_triage_agent.trace.json >/tmp/trace_check.json
python3 -m json.tool examples/generated/support_triage_agent.decision_brief.json >/tmp/brief_check.json
python3 -m agent.proof_health --no-write
python3 -m json.tool examples/generated/support_triage_agent.proof_health.json >/tmp/proof_health_check.json
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml --no-write --json >/tmp/trial_outcome_memo_check.json
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --json >/tmp/trial_evidence_replay_check.json
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial --json >/tmp/live_evidence_rehearsal_check.json
python3 -m unittest discover -s tests
```

## CTO Definition Of Done

The repo is ready for the CTO to build on when:

- there is a single documented object spine
- stable and transitional modules are clearly separated
- sponsor integrations have explicit contracts
- generated artifacts are reproducible
- tests protect the safety posture
- the live-mode path can be built without weakening the default offline demo
