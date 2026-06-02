# Sample DecisionPacket

## Decision

Should the support triage agent get GitHub, Slack, and Jira access?

## Current Read

The agent may be useful for incident triage, but tool access should stay blocked until scope, data retention, and reviewer ownership are proven.

## Requested Capability

Allow a support triage agent to:

- read GitHub issues for bug reports
- summarize Slack incident channels
- create Jira draft tickets

## Blocked Claims

- No production tool-access approval without a named Security reviewer.
- No customer-data safety claim without data-retention and logging proof.
- No write-action permission without rollback/off-switch proof.
- No autonomous dispatch to Slack, Jira, or GitHub in the demo path.

## Missing Proof

- GitHub repository scope and permission level
- Slack channel scope and retention terms
- Jira project scope and write limits
- Security/Legal reviewer owner
- audit logging plan
- rollback/off-switch plan

## Reviewer Owners

- Security / Legal: data scope, retention, policy review
- Engineering: permission boundaries, rollback, audit logs
- Support Ops: workflow fit and escalation ownership
- Procurement / Finance: tool/vendor spend if paid actions are enabled

## Next Human Validation

Ask Security / Legal to confirm the allowed data scope and retention terms before enabling any tool connection.

## Guardrails

- IA prepares this packet for review.
- IA does not approve access.
- IA does not dispatch external actions.
- IA does not mutate production state.

