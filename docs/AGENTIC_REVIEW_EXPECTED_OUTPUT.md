# Agentic Review Expected Output

Status: public AI reviewer checklist
Purpose: give automated repo reviewers exact pass signals for the no-key public proof surface

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

Private engine, public proof.

## Default Review Command

Run the no-key judge path first:

```bash
python3 -m agent.judge --no-write
```

Expected human-readable signals:

- mode is `offline_deterministic`
- live keys required is `False`
- external writes enabled is `False`
- approval granted is `False`
- private source exposed is `False`
- scenario matrix includes `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- `admin_code_fix_bot` is `BLOCKED`
- public contract status is `ok`
- sponsor adapters show `would_execute=False` and `can_approve_access=False`
- Proof Health status is `drifting`
- artifact checklist entries are `OK`

## Machine-Readable Review

For a strict parser, run:

```bash
python3 -m agent.judge --no-write --json
```

Expected JSON pass signals:

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
- `safety.all_adapters_non_executing` is `true`
- `safety.all_adapters_non_approving` is `true`
- `private_boundary.private_source_exposed` is `false`

## Full Command Set

An agentic reviewer can use this complete no-key path:

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m unittest discover -s tests
```

Expected pass signals:

- the demo runs without API keys
- public contract reports all scenarios as `OK`
- policy gate blocks critical/admin/prod-write scope
- sponsor adapters remain dry-run, non-executing, and non-approving
- Trust Receipt, Review Room, Proof Health, and trial report artifacts exist
- unit tests pass; the current public suite contains 120 tests

## What To Inspect After Commands Pass

Inspect these in order:

1. `AI_JUDGE_MANIFEST.json`
2. `docs/PRODUCT_TOUR.md`
3. `examples/generated/review_room.html`
4. `examples/generated/trust_receipt.md`
5. `examples/generated/support_triage_agent.proof_health.md`
6. `examples/generated/support_triage_trial_report.md`
7. `docs/CONTRACT.md`
8. `docs/SAFETY_CONTRACT.md`

## Failure Signals

Treat these as review failures:

- any command requires secrets in the default path
- production access becomes `true`
- approval granted becomes `true`
- sponsor adapters can execute writes by default
- sponsor adapters can approve access
- Proof Health approves, grants, writes, or mutates production
- `admin_code_fix_bot` is not blocked
- public contract status is not `ok`
- checked artifacts are missing
- private source exposure is `true`

## Review Conclusion

If the commands pass and the failure signals are absent, the public repo proves a safe review harness:

```text
agent request
-> proof packet
-> access brief
-> trust receipt
-> proof health
-> human review
```

It does not prove autonomous approval. It proves the pre-permission review surface a human approval process can inspect.
