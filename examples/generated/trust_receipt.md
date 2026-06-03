# Trust Receipt: Agent Access Review

Pre-permission control plane for AI agent tool, data, spend, and production access.

Receipt ID: `ia-agent-trust-receipt-public-v0`

Receipt hash: `569026c1b19d1b7d`

Private engine, public proof.

## Scenario Blast-Radius Diff

| Scenario | Risk | Validation | Production | Systems |
| --- | --- | --- | --- | --- |
| support_triage_agent | high | True | False | GitHub, Slack, Jira |
| read_only_analytics_agent | low | True | False | BigQuery, Looker |
| admin_code_fix_bot | critical | False | False | GitHub |

## Permission Envelope

Allowed for validation:

- support_triage_agent: GitHub read-scope review against an approved repository allowlist
- support_triage_agent: Slack named-channel summarization review after retention and customer-data scope are approved
- support_triage_agent: Jira draft ticket proposal review with no production ticket creation
- read_only_analytics_agent: bigquery: read-only validation plan only
- read_only_analytics_agent: looker: read-only validation plan only
- admin_code_fix_bot: No validation run until critical reviewer gates are satisfied.

Dry-run only:

- support_triage_agent: github -> dry-run read-scope plan only
- support_triage_agent: slack -> dry-run named-channel summary plan only
- support_triage_agent: jira -> draft ticket proposal only; no production creation
- read_only_analytics_agent: bigquery -> read-only validation plan only
- read_only_analytics_agent: looker -> read-only validation plan only
- admin_code_fix_bot: github -> blocked; admin/write actions require Security and Engineering approval

Blocked in validation:

- support_triage_agent: github: issue edits
- support_triage_agent: github: repo configuration changes
- support_triage_agent: github: workflow dispatch
- support_triage_agent: jira: ticket creation
- support_triage_agent: jira: status changes
- support_triage_agent: jira: assignment changes
- support_triage_agent: slack: posting messages
- support_triage_agent: slack: DM access
- support_triage_agent: slack: workspace-wide history
- read_only_analytics_agent: bigquery: writes
- read_only_analytics_agent: bigquery: exports
- read_only_analytics_agent: bigquery: permission changes
- read_only_analytics_agent: looker: writes
- read_only_analytics_agent: looker: exports
- read_only_analytics_agent: looker: permission changes
- admin_code_fix_bot: github: admin scope
- admin_code_fix_bot: github: production repository mutation
- admin_code_fix_bot: github: workflow dispatch
- admin_code_fix_bot: github: permission changes

Blocked before production:

- production access grant
- external write actions
- workspace-wide Slack access
- customer-data safety or compliance claims without named reviewer evidence
- automated permission expansion without a new packet
- scope expansion without a new packet
- compliance or safety claims without named reviewer evidence

Never allowed in the public demo:

- production access grant
- external writes
- tool permission expansion without a new packet
- compliance, safety, readiness, or savings claims without named proof
- live sponsor action without explicit non-default enablement

## Proof Debt Ledger

- support_triage_agent: GitHub repository allowlist and permission level | owner: Engineering | unblocks: read-only repository evidence review
- support_triage_agent: Slack channel allowlist, retention policy, and customer-data boundary | owner: Security/Legal | unblocks: incident-channel summarization review
- support_triage_agent: Jira project scope, draft-only mode, and rollback/off-switch plan | owner: Engineering | unblocks: draft ticket validation
- support_triage_agent: Support escalation workflow and human handoff owner | owner: Support Ops | unblocks: triage workflow fit review
- support_triage_agent: Audit log shape for tool calls, evidence intake, and reviewer decisions | owner: Security/Engineering | unblocks: reviewable pilot packet
- read_only_analytics_agent: BigQuery read-only allowlist and credential proof | owner: Data/Engineering | unblocks: read-only validation review
- read_only_analytics_agent: Looker read-only allowlist and credential proof | owner: Data/Engineering | unblocks: read-only validation review
- read_only_analytics_agent: Data owner confirmation that requested metrics are aggregate and non-customer-specific | owner: Data/Analytics | unblocks: read-only analytics validation
- admin_code_fix_bot: GitHub admin scope removal or explicit break-glass approval | owner: Security/Engineering | unblocks: admin access rejection review
- admin_code_fix_bot: Audit log shape for tool calls, evidence intake, and reviewer decisions | owner: Security/Engineering | unblocks: reviewable pilot packet

## Reviewer Routing

- **Security/Legal**: 2 gates across support_triage_agent, admin_code_fix_bot
- **Engineering**: 2 gates across support_triage_agent, read_only_analytics_agent
- **Support Ops**: 1 gate across support_triage_agent
- **Procurement/Finance**: 1 gate across support_triage_agent
- **Data/Analytics**: 1 gate across read_only_analytics_agent
- **Security/Engineering**: 1 gate across admin_code_fix_bot
- **Engineering Leadership**: 1 gate across admin_code_fix_bot

## Sponsor Runtime Plan

- **composio**: tool access planner and dry-run action surface; default: dry_run_only; guardrail: must not execute writes or grant tool permissions by default
- **tavily**: evidence candidate source for current security, vendor, and policy context; default: evidence_notes_only; guardrail: must not turn search results into approval or production readiness
- **nebius**: optional inference layer for reviewer-ready narration; default: deterministic_fallback_without_key; guardrail: must not own verdicts, blocked claims, or safety state
- **openclaw**: optional runtime trace harness for agent steps; default: trace_only; guardrail: must not hide blocked attempts or bypass human approval

## Public Contract Status

- contract: agent_access_public.v0
- status: ok

## Policy Gate Status

- policy: policy/agent_access.yml
- policy version: agent_access_public_policy.v0

- support_triage_agent: VALIDATION_ALLOWED_WITH_GATES (allow_scoped_validation_when_safe, require_open_proof_debt)
- read_only_analytics_agent: VALIDATION_ALLOWED_WITH_GATES (allow_scoped_validation_when_safe, require_open_proof_debt)
- admin_code_fix_bot: BLOCKED (deny_critical_risk_validation, require_open_proof_debt)

## Safety State

- approval granted: False
- production access granted: False
- external writes enabled: False
- Composio dry-run: True
- packet state mutation: False
- requires human approval: True
- all scenarios production blocked: True

## Design Partner Signal

Pilot shape: one workflow, three representative agents, dry-run review, no production writes

What a partner validates:

- whether access requests become reviewable faster
- whether proof debt is routed to the right owners
- whether dry-run envelopes match security expectations
- whether sponsor/runtime/evidence traces help reviewers without approving access

## Private Boundary

- public repo role: redacted judge harness and public proof surface
- private source exposed: False
- principle: Private engine, public proof.
