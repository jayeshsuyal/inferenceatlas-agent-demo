# DecisionPacket: Support Triage Agent Access

## Verdict

Do not approve production tool access yet.

Approve a scoped validation review before any production permission grant.

## Approval Posture

- production access: blocked
- validation review: allowed
- read access: candidate_after_scope_review
- write access: blocked_until_rollback_and_off_switch_proof
- compliance claims: blocked_until_named_reviewer_evidence

## Source Status

- user prompt: provided
- live vendor evidence: not_fetched_in_offline_mode
- workspace policy: missing
- tool auth state: not_connected_in_offline_mode
- reviewer confirmation: missing
- deterministic packet: generated

## Requested Capability

- GitHub: read issues from named repositories; read labels and linked incident references (medium, dry_run_only)
- Slack: summarize named incident channels (high, dry_run_only)
- Jira: propose draft tickets (high, dry_run_only)

## Tool Access Plan

- **github**
  - requested: read issues from named repositories; read labels and linked incident references
  - demo allowance: dry-run read-scope plan only
  - blocked actions: issue edits, repo configuration changes, workflow dispatch
  - required proof: repository allowlist, permission level, audit log owner
- **jira**
  - requested: propose draft tickets
  - demo allowance: draft ticket proposal only; no production creation
  - blocked actions: ticket creation, status changes, assignment changes
  - required proof: project scope, draft-only mode, rollback/off-switch plan
- **slack**
  - requested: summarize named incident channels
  - demo allowance: dry-run named-channel summary plan only
  - blocked actions: posting messages, DM access, workspace-wide history
  - required proof: channel allowlist, retention terms, customer-data boundary

## Tool Scope

- github: read [issues, labels, linked incident references] | write [none] | blocked [issue mutation, repo configuration changes]
- jira: read [named project metadata] | write [draft ticket proposal only] | blocked [ticket creation in production, status changes, assignment changes]
- slack: read [named incident channels only] | write [none] | blocked [posting messages, DM access, workspace-wide history]

## Data Scope

May include:

- customer incident context
- engineering bug reports
- linked incident references
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

## Reviewer Action Items

- **Security/Legal**: action: Confirm allowed data scope, retention, and logging terms; blocks: Slack channel summarization and customer incident context access
- **Engineering**: action: Provide repository/project allowlists, permission boundaries, audit logs, and off-switch proof; blocks: GitHub/Jira tool connection and any write-action pilot
- **Support Ops**: action: Validate triage workflow fit, escalation rules, and human handoff owner; blocks: support operations pilot
- **Procurement/Finance**: action: Review paid seats or vendor spend only if live integrations move beyond dry-run; blocks: paid production rollout

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

Should this support triage agent get GitHub, Slack, Jira access? It will read issues from named repositories; read labels and linked incident references; summarize named incident channels; propose draft tickets. Requested environment: validation_only. Current approval path: manual_security_engineering_support_ops_review.
