# DecisionPacket: Support Triage Agent Access

## Verdict

Do not approve production tool access yet.

Approve a scoped validation review before any production permission grant.

## Requested Capability

- GitHub: read issues for bug reports and incident context (medium, dry_run_only)
- Slack: summarize incident channels (high, dry_run_only)
- Jira: create draft tickets (high, dry_run_only)

## Tool Scope

- github: read [issues, labels, linked incident references] | write [none] | blocked [issue mutation, repo configuration changes]
- jira: read [named project metadata] | write [draft ticket proposal only] | blocked [ticket creation in production, status changes, assignment changes]
- slack: read [named incident channels only] | write [none] | blocked [posting messages, DM access, workspace-wide history]

## Data Scope

May include:

- customer incident context
- engineering bug reports
- support escalation notes
- internal incident channel summaries

Must define before access:

- retention period
- logging policy
- allowed channel and repository list
- customer data handling boundary
- reviewer-owned deletion and rollback process

## Evidence Notes

- **offline harness**: status: deterministic; note: No live vendor, policy, or workspace evidence was fetched in offline mode.
- **safety contract**: status: enforced_by_default; note: The public demo path prepares review packets and does not grant access.

## Blocked Claims

- **Production tool access is approved.**: reason: No named Security/Legal reviewer and no tool scope proof.
- **Customer-data handling is safe.**: reason: Retention, logging, deletion, and channel/repository boundaries are not proven.
- **The agent may create or mutate Jira/GitHub/Slack state.**: reason: Write actions require rollback/off-switch proof and explicit human approval.
- **The workflow is compliance-ready.**: reason: Compliance approval cannot be inferred from an agent request or demo transcript.

## Missing Proof

- **GitHub repository allowlist and permission level**: owner: Engineering; unblocks: read-only repository evidence review
- **Slack channel allowlist, retention policy, and customer-data boundary**: owner: Security/Legal; unblocks: incident-channel summarization review
- **Jira project scope, draft-only mode, and rollback/off-switch plan**: owner: Engineering; unblocks: draft ticket validation
- **Support escalation workflow and human handoff owner**: owner: Support Ops; unblocks: triage workflow fit review
- **Audit log shape for tool calls, evidence intake, and reviewer decisions**: owner: Security/Engineering; unblocks: reviewable pilot packet

## Reviewer Owners

- **Security/Legal**: review area: customer-data exposure, retention, logging, policy boundary; current state: required_before_access
- **Engineering**: review area: permission boundaries, rollback, off-switch, audit logs; current state: required_before_write_actions
- **Support Ops**: review area: workflow fit, escalation rules, human handoff; current state: required_before_pilot
- **Procurement/Finance**: review area: paid tool/vendor spend if live actions or seats are enabled; current state: conditional

## Next Human Validation

Action: Run a scoped dry-run pilot review with named repositories, channels, and Jira project.

Owner: Security/Legal + Engineering

Success criteria:

- approved data and tool scope
- audit log reviewed
- write actions remain draft-only
- rollback/off-switch owner named

## Safety State

- Approval granted: False
- External writes enabled: False
- Composio dry-run: True
- Packet state mutation: False
- Requires human approval: True
- Public demo posture: review_packet_only

## Raw Prompt

Should this support triage agent get GitHub, Slack, and Jira access? It will read GitHub issues, summarize Slack incident channels, and create Jira draft tickets. It may touch customer incident context, engineering bug reports, and support escalations.
