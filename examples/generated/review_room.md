# InferenceAtlas Agent Access Review Room

Before an AI agent gets access, issue the Trust Receipt.

Trust Receipt hash: `6b5caa082cc32f27`

## Copy-Paste Review Commands

```bash
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m unittest discover -s tests
```

## Product Loop

- messy agent-access request
- deterministic rules engine
- scenario blast-radius diff
- DecisionPacket
- Agent Access Decision Brief
- Trust Receipt
- static Review Room HTML
- public policy gate
- dry-run sponsor adapter contracts
- public contract validation
- optional sponsor/runtime/evidence enrichment

## Scenario Matrix

| Scenario | Risk | Validation | Production | Systems |
| --- | --- | --- | --- | --- |
| support_triage_agent | high | True | False | GitHub, Slack, Jira |
| read_only_analytics_agent | low | True | False | BigQuery, Looker |
| admin_code_fix_bot | critical | False | False | GitHub |

## Proof Debt Summary

- open items: 10
- owners: Data/Analytics, Data/Engineering, Engineering, Security/Engineering, Security/Legal, Support Ops

## Reviewer Routing Summary

- Security/Legal: 2 gates across 2 scenarios
- Engineering: 2 gates across 2 scenarios
- Support Ops: 1 gate across 1 scenario
- Procurement/Finance: 1 gate across 1 scenario
- Data/Analytics: 1 gate across 1 scenario
- Security/Engineering: 1 gate across 1 scenario
- Engineering Leadership: 1 gate across 1 scenario

## First Artifacts To Inspect

- examples/generated/trust_receipt.md
- examples/generated/review_room.md
- examples/generated/review_room.html
- policy/agent_access.yml
- agent/adapters/
- examples/generated/support_triage_agent.decision_brief.md
- examples/generated/admin_code_fix_bot.packet.json
- docs/CONTRACT.md

## Policy Gate Status

- support_triage_agent: VALIDATION_ALLOWED_WITH_GATES
- read_only_analytics_agent: VALIDATION_ALLOWED_WITH_GATES
- admin_code_fix_bot: BLOCKED

## Sponsor Adapter Status

- composio: dry_run_planned; would_execute=False
- tavily: evidence_candidates_planned; would_execute=False
- nebius: deterministic_narration_fallback; would_execute=False
- openclaw: trace_contract_planned; would_execute=False

## Safety State

- approval_granted: False
- production_access_granted: False
- external_writes_enabled: False
- composio_dry_run: True
- packet_state_mutation: False
- requires_human_approval: True
- all_scenarios_production_blocked: True

## Private Boundary

- private source exposed: False
- principle: Private engine, public proof.
