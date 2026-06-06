# Agentic Review Expected Output

Status: public AI reviewer checklist
Purpose: give automated repo reviewers exact pass signals for the no-key public proof surface

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

Private engine, public proof.

## Default Review Command

Run the no-key judge path first, then verify the checked-in proof artifacts:

```bash
bash scripts/run.sh
bash scripts/pr_smoke.sh
python3 -m agent.judge --no-write
python3 -m agent.skills
python3 -m agent.evidence_receipts --no-write
python3 -m agent.packet_authority
python3 -m agent.verification --all
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml --no-write
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.verify_artifacts
```

Expected human-readable signals across that two-command path:

- PR smoke gate reports `InferenceAtlas PR smoke gate passed.`
- mode is `offline_deterministic`
- live keys required is `False`
- external writes enabled is `False`
- approval granted is `False`
- private source exposed is `False`
- scenario matrix includes `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- Packet Diff reports relaxed read-only, proof-routed, and blocked critical lanes
- Evidence Receipt Ledger reports receipt-backed proof context, unchanged decision lock, and budget owner review required
- Packet Authority Snapshot reports a sha256 content hash, stable revision, and unchanged decision lock
- Packet Verification reports production access, external writes, permission grants, and approval granted are all `false`
- Packet Outcome Memo reports `scoped_validation_only` for `support_triage_agent`
- Design Partner Outcome Memo reports `scoped_validation_only` for `support_triage_trial`
- Sponsor Evidence Replay reports sponsors cannot change the trial decision
- Sponsor Proof Trace reports Tavily -> Composio -> OpenClaw -> Nebius in locked order with unchanged decision lock
- Live Evidence Rehearsal reports sanitized evidence is attached and the decision remains locked
- AI Spend Review reports Finance/Procurement review required, with no spend approval, provider selection, or savings guarantee
- Agent Skills reports `17 / 17 stable skills available`
- Artifact Integrity Gate reports `60 generated artifacts verified`, `0 stale`, `2 static assets valid`, and `0 unexpected checked-in`
- `admin_code_fix_bot` is `BLOCKED`
- public contract status is `ok`
- sponsor adapters show `would_execute=False` and `can_approve_access=False`
- Proof Health status is `drifting`
- artifact checklist entries are `OK`

## Machine-Readable Review

For a strict parser, run both JSON surfaces:

```bash
bash scripts/run.sh --json
python3 -m agent.judge --no-write --json
python3 -m agent.skills --json
python3 -m agent.evidence_receipts --no-write --json
python3 -m agent.packet_authority --json
python3 -m agent.verification --all --json
python3 -m agent.downstream_gate --all --json
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml --no-write --json
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --json
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial --json
python3 -m agent.sponsor_proof_trace examples/requests/support_triage_trial.yml --no-write --json
python3 -m agent.spend --no-write --json
python3 -m agent.verify_artifacts --json
```

Expected judge JSON pass signals:

- `mode` is `offline_deterministic`
- `public_contract.status` is `ok`
- every `scenario_matrix` item has `production_access` set to `false`
- every `scenario_matrix` item has `approval_granted` set to `false`
- `policy_gate.admin_code_fix_bot.decision` is `BLOCKED`
- `access_speed_layer.all_routes_immediate` is `true`
- `design_partner_trial.production_access` is `false`
- `design_partner_trial.approves_access` is `false`
- `design_partner_trial.grants_permissions` is `false`
- `design_partner_trial.executes_external_writes` is `false`
- `design_partner_outcome_memo.decision_code` is `scoped_validation_only`
- `design_partner_outcome_memo.production_access` is `false`
- `design_partner_outcome_memo.permission_grants` is `false`
- `design_partner_outcome_memo.external_writes` is `false`
- `design_partner_outcome_memo.approves_access` is `false`
- `design_partner_evidence_replay.can_sponsor_change_decision` is `false`
- `design_partner_evidence_replay.all_non_executing` is `true`
- `design_partner_evidence_replay.all_non_approving` is `true`
- `design_partner_evidence_replay.all_non_granting` is `true`
- `design_partner_evidence_replay.all_non_mutating` is `true`
- `summary.sanitized_evidence_attached` is `true` when `--evidence-dir examples/evidence/support_triage_trial` is used
- `live_evidence_rehearsal.decision_locked` is `true` when `--evidence-dir examples/evidence/support_triage_trial` is used
- `proof_health.overall_status` is `drifting`
- `proof_health.human_review_required` is `true`
- `proof_health.approves_access` is `false`
- `proof_health.grants_permissions` is `false`
- `proof_health.executes_external_writes` is `false`
- `sponsor_proof_trace.decision_lock_unchanged` is `true`
- `sponsor_proof_trace.all_non_executing` is `true`
- `sponsor_proof_trace.approves_access` is `false`
- `sponsor_proof_trace.approves_spend` is `false`
- `sponsor_proof_trace.selects_provider` is `false`
- `sponsor_proof_trace.guarantees_savings` is `false`
- `packet_diff.has_relaxed_read_only_lane` is `true`
- `packet_diff.has_proof_routed_lane` is `true`
- `packet_diff.has_blocked_critical_lane` is `true`
- Evidence Receipt Ledger JSON has `decision_lock_after` unchanged, `all_non_approving` set to `true`, and `budget_owner_required` set to `true`
- Packet Authority Snapshot JSON has `decision_lock_after` set to `scoped_validation_only` for the support-triage packet
- every Packet Verification result has `production_access`, `external_writes`, `permission_grants`, and `approval_granted` set to `false`
- `packet_outcome_memo.decision_code` is `scoped_validation_only`
- `packet_outcome_memo.production_access` is `false`
- `safety.all_adapters_non_executing` is `true`
- `safety.all_adapters_non_approving` is `true`
- `private_boundary.private_source_exposed` is `false`

Expected artifact verifier JSON pass signals:

- `status` is `ok`
- `summary.generated_artifacts_verified` is `60`
- `summary.stale_artifacts` is `0`
- `summary.unexpected_checked_in_artifacts` is `0`
- `summary.missing_static_assets` is `0`

Expected skills JSON pass signals:

- `schema_version` is `agent_skills_registry.v0`
- `summary.registered_skills` is `17`
- `summary.stable_skills` is `17`
- `summary.available_stable_skills` is `17`
- `private_boundary.private_source_exposed` is `false`

## Full Command Set

An agentic reviewer can use this complete no-key path:

```bash
bash scripts/run.sh
bash scripts/pr_smoke.sh
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.evidence_receipts
python3 -m agent.packet_authority
python3 -m agent.verification --all
python3 -m agent.outcome_memo
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.verify_artifacts
python3 -m unittest discover -s tests
```

Expected pass signals:

- the demo runs without API keys
- Agent Skills maps public capabilities to commands, artifacts, dependencies, and safety boundaries
- public contract reports all scenarios as `OK`
- Packet Diff proves the three public scenarios differ in load-bearing fields
- Evidence Receipt Ledger attaches tool-scope, proof-debt, reviewer-route, and cost/procurement receipts without changing the lock
- Packet Authority Snapshot gives the support-triage packet a deterministic content hash and revision
- Packet Verification stays read-only and never claims approval
- Packet Outcome Memo turns the support-triage packet into a can-move, stays-blocked, proof-owner decision
- Design Partner Outcome Memo turns the trial request into a meeting-ready can-move, stays-blocked, proof-owner decision
- Sponsor Evidence Replay attaches sponsor proof slots to the same trial decision without changing safety state
- Sponsor Proof Trace records access and spend evidence blocks without changing the decision lock
- Live Evidence Rehearsal attaches sanitized sponsor outputs while rejecting secret-shaped or write-shaped inputs
- Artifact Integrity Gate proves deterministic proof artifacts are fresh, static review assets are valid, and no unexpected generated file is checked in
- policy gate blocks critical/admin/prod-write scope
- sponsor adapters remain dry-run, non-executing, and non-approving
- Trust Receipt, Review Room, Proof Health, and trial report artifacts exist
- unit tests pass in the current public suite

## What To Inspect After Commands Pass

Inspect these in order:

1. `AI_JUDGE_MANIFEST.json`
2. `docs/PRODUCT_TOUR.md`
3. `docs/AGENT_SKILLS.md`
4. `docs/PRODUCT_QUALITY_AUDIT.md`
5. `examples/generated/packet_diff.md`
6. `examples/generated/support_triage_agent.evidence_receipts.md`
7. `examples/generated/support_triage_agent.snapshot.json`
8. `examples/generated/support_triage_agent.verification.json`
9. `examples/generated/support_triage_agent.outcome_memo.md`
10. `examples/generated/review_room.html`
11. `examples/generated/trust_receipt.md`
12. `examples/generated/support_triage_agent.proof_health.md`
13. `examples/generated/support_triage_trial_report.md`
14. `examples/generated/support_triage_trial.outcome_memo.md`
15. `examples/generated/support_triage_trial.evidence_replay.md`
16. `examples/evidence/support_triage_trial/`
17. `docs/CONTRACT.md`
18. `docs/SAFETY_CONTRACT.md`

## Failure Signals

Treat these as review failures:

- any command requires secrets in the default path
- production access becomes `true`
- approval granted becomes `true`
- sponsor adapters can execute writes by default
- sponsor adapters can approve access
- Packet Diff no longer shows all three risk lanes
- Evidence Receipt Ledger weakens the packet lock, skips human review, or claims budget approval
- Packet Authority Snapshot content hash or revision is nondeterministic
- Packet Verification claims production access, external writes, permission grants, or approval
- Agent Skills registry drifts from `agent/skills.py` or reports fewer than 16 stable available skills
- Packet Outcome Memo approves access, grants permissions, or enables writes
- Design Partner Outcome Memo approves access, grants permissions, or enables writes
- Sponsor Evidence Replay lets a sponsor change the decision, approve access, grant permissions, execute writes, or mutate production
- Sponsor Proof Trace changes sponsor order, unlocks a decision, approves access, approves spend, selects a provider, or guarantees savings
- Live Evidence Rehearsal accepts evidence containing secrets, approval flags, grant flags, write flags, or production mutation flags
- AI Spend Review approves spend, selects a provider, guarantees savings, or executes external writes
- Artifact Integrity Gate reports stale, missing, invalid, or unexpected generated artifacts
- Proof Health approves, grants, writes, or mutates production
- `admin_code_fix_bot` is not blocked
- public contract status is not `ok`
- checked artifacts are missing
- private source exposure is `true`

## Review Conclusion

If the commands pass and the failure signals are absent, the public repo proves a safe review harness:

```text
agent request
-> agent skills registry
-> proof packet
-> evidence receipt ledger
-> packet authority snapshot
-> packet verification
-> downstream gate decisions
-> access brief
-> trust receipt
-> packet diff
-> outcome memo
-> design-partner outcome memo
-> sponsor evidence replay
-> live evidence rehearsal
-> proof health
-> artifact integrity gate
-> human review
```

It does not prove autonomous approval. It proves the pre-permission review surface a human approval process can inspect.
