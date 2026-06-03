# InferenceAtlas Agent Access Review Room

Before an AI agent gets access, issue the Trust Receipt.

Trust Receipt hash: `43367e239140041e`

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
- walkthrough-ready visual review
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
- docs/REVIEW_ROOM_WALKTHROUGH.md
- examples/generated/review_room.desktop.jpg
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

## Sponsor Proof Pack

Sponsor tools enrich proof packets; they do not approve agents.

- **composio** (permission_diff): Shows the exact requested tool actions, validation-only allowances, blocked actions, and proof required before any tool grant. Visible output: tool-by-tool permission diff and dry-run invocation plan. Contributions: 6; human review required: True; cannot: approve access, grant permissions, execute writes, reduce proof debt automatically.
- **tavily** (evidence_candidate_plan): Turns missing proof into reviewer-safe evidence queries with freshness and source placeholders. Visible output: evidence query plan with owners, source URL slots, and freshness state. Contributions: 10; human review required: True; cannot: approve access, grant permissions, declare compliance, reduce proof debt automatically.
- **nebius** (locked_field_narration): Projects deterministic packet truth into reviewer-ready language while keeping safety-critical fields locked. Visible output: narration contract with editable language fields and locked verdict fields. Contributions: 9; human review required: True; cannot: approve access, grant permissions, change verdict, change safety state.
- **openclaw** (runtime_trace_plan): Shows how attempted agent steps would be traced with policy decisions before any live action. Visible output: runtime trace contract for blocked and dry-run steps. Contributions: 9; human review required: True; cannot: approve access, grant permissions, execute runtime steps, hide blocked attempts.

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
