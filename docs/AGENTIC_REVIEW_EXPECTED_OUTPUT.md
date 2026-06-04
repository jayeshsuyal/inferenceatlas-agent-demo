# Agentic Review Expected Output

Status: public AI reviewer checklist
Purpose: give automated repo reviewers exact pass signals for the no-key public proof surface

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

Private engine, public proof.

## Default Review Command

Run the no-key judge path first, then verify the checked-in proof artifacts:

```bash
python3 -m agent.judge --no-write
python3 -m agent.skills
python3 -m agent.verify_artifacts
```

Expected human-readable signals across that two-command path:

- mode is `offline_deterministic`
- live keys required is `False`
- external writes enabled is `False`
- approval granted is `False`
- private source exposed is `False`
- scenario matrix includes `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- Packet Diff reports relaxed read-only, proof-routed, and blocked critical lanes
- Packet Outcome Memo reports `scoped_validation_only` for `support_triage_agent`
- Agent Skills reports `12 / 12 stable skills available`
- Artifact Integrity Gate reports `33 generated artifacts verified`, `0 stale`, `2 static assets valid`, and `0 unexpected checked-in`
- `admin_code_fix_bot` is `BLOCKED`
- public contract status is `ok`
- sponsor adapters show `would_execute=False` and `can_approve_access=False`
- Proof Health status is `drifting`
- artifact checklist entries are `OK`

## Machine-Readable Review

For a strict parser, run both JSON surfaces:

```bash
python3 -m agent.judge --no-write --json
python3 -m agent.skills --json
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
- `proof_health.overall_status` is `drifting`
- `proof_health.human_review_required` is `true`
- `proof_health.approves_access` is `false`
- `proof_health.grants_permissions` is `false`
- `proof_health.executes_external_writes` is `false`
- `packet_diff.has_relaxed_read_only_lane` is `true`
- `packet_diff.has_proof_routed_lane` is `true`
- `packet_diff.has_blocked_critical_lane` is `true`
- `packet_outcome_memo.decision_code` is `scoped_validation_only`
- `packet_outcome_memo.production_access` is `false`
- `safety.all_adapters_non_executing` is `true`
- `safety.all_adapters_non_approving` is `true`
- `private_boundary.private_source_exposed` is `false`

Expected artifact verifier JSON pass signals:

- `status` is `ok`
- `summary.generated_artifacts_verified` is `33`
- `summary.stale_artifacts` is `0`
- `summary.unexpected_checked_in_artifacts` is `0`
- `summary.missing_static_assets` is `0`

Expected skills JSON pass signals:

- `schema_version` is `agent_skills_registry.v0`
- `summary.registered_skills` is `12`
- `summary.stable_skills` is `12`
- `summary.available_stable_skills` is `12`
- `private_boundary.private_source_exposed` is `false`

## Full Command Set

An agentic reviewer can use this complete no-key path:

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.outcome_memo
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.verify_artifacts
python3 -m unittest discover -s tests
```

Expected pass signals:

- the demo runs without API keys
- Agent Skills maps public capabilities to commands, artifacts, dependencies, and safety boundaries
- public contract reports all scenarios as `OK`
- Packet Diff proves the three public scenarios differ in load-bearing fields
- Packet Outcome Memo turns the support-triage packet into a can-move, stays-blocked, proof-owner decision
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
6. `examples/generated/support_triage_agent.outcome_memo.md`
7. `examples/generated/review_room.html`
8. `examples/generated/trust_receipt.md`
9. `examples/generated/support_triage_agent.proof_health.md`
10. `examples/generated/support_triage_trial_report.md`
11. `docs/CONTRACT.md`
12. `docs/SAFETY_CONTRACT.md`

## Failure Signals

Treat these as review failures:

- any command requires secrets in the default path
- production access becomes `true`
- approval granted becomes `true`
- sponsor adapters can execute writes by default
- sponsor adapters can approve access
- Packet Diff no longer shows all three risk lanes
- Agent Skills registry drifts from `agent/skills.py` or reports fewer than 12 stable available skills
- Packet Outcome Memo approves access, grants permissions, or enables writes
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
-> access brief
-> trust receipt
-> packet diff
-> outcome memo
-> proof health
-> artifact integrity gate
-> human review
```

It does not prove autonomous approval. It proves the pre-permission review surface a human approval process can inspect.
