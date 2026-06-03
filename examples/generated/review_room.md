# InferenceAtlas Agent Access Review Room

Before an AI agent gets access, issue the Trust Receipt.

Trust Receipt hash: `ed67331633c85a94`

## Copy-Paste Review Commands

```bash
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.trust
python3 -m unittest discover -s tests
```

## Product Loop

- messy agent-access request
- deterministic rules engine
- scenario blast-radius diff
- DecisionPacket
- Agent Access Decision Brief
- Trust Receipt
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
- examples/generated/support_triage_agent.decision_brief.md
- examples/generated/admin_code_fix_bot.packet.json
- docs/CONTRACT.md

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
