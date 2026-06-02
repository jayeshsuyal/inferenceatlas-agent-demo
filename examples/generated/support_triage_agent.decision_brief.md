# Agent Access Decision Brief: Support Triage Agent

## Decision

Question: Should the support triage agent get GitHub, Slack, and Jira access?

Verdict: Do not grant production access.

Recommended next step: Approve a scoped validation review only.

Reason: The request touches sensitive support, engineering, and incident systems without named reviewer proof.

## Go / No-Go

- production access: False
- scoped validation review: True
- external writes: False
- Composio dry-run: True
- next validation: Run a scoped dry-run pilot review with named repositories, channels, and Jira project.

## Runtime Permission Boundary

- Runtime permission prompts answer: Can the agent perform this specific action now?
- InferenceAtlas answers: Should this agent be eligible for this class of access at all, and what proof is required first?
- Why this is different: Runtime prompts are last-mile execution checks. The Decision Brief is the pre-permission governance review that decides eligibility, missing proof, and reviewer gates before runtime tools are granted.

## Access Eligibility

- **GitHub**
  - requested: read issues for bug reports and incident context
  - eligibility: candidate_for_scoped_validation_review
  - validation allowance: dry-run read-scope plan only
  - production status: blocked
  - required proof: repository allowlist, permission level, audit log owner
- **Slack**
  - requested: summarize incident channels
  - eligibility: candidate_for_scoped_validation_review
  - validation allowance: dry-run named-channel summary plan only
  - production status: blocked
  - required proof: channel allowlist, retention terms, customer-data boundary
- **Jira**
  - requested: create draft tickets
  - eligibility: candidate_for_scoped_validation_review
  - validation allowance: draft ticket proposal only; no production creation
  - production status: blocked
  - required proof: project scope, draft-only mode, rollback/off-switch plan

## Access Envelope

Allowed for validation:

- GitHub read-scope review against an approved repository allowlist
- Slack named-channel summarization review after retention and customer-data scope are approved
- Jira draft ticket proposal review with no production ticket creation

Blocked in validation:

- github: issue edits
- github: repo configuration changes
- github: workflow dispatch
- jira: ticket creation
- jira: status changes
- jira: assignment changes
- slack: posting messages
- slack: DM access
- slack: workspace-wide history

Blocked before production:

- production access grant
- external write actions
- workspace-wide Slack access
- customer-data safety or compliance claims without named reviewer evidence
- automated permission expansion without a new packet

## Risk Register

- **excessive agency**
  - why it matters: The agent is asking for multiple operational systems at once.
  - mitigation: Split read and write paths, keep validation scoped, and require a new packet before expansion.
- **sensitive information exposure**
  - why it matters: Slack incidents, support escalations, and bug reports may contain customer context.
  - mitigation: Require retention, logging, deletion, and channel/repository boundaries before access.
- **prompt injection via tool content**
  - why it matters: Issues, tickets, and incident messages can contain instructions that should not become policy.
  - mitigation: Treat tool content as evidence, not authority; preserve source status and reviewer gates.
- **unauthorized write actions**
  - why it matters: Jira, GitHub, or Slack mutations can affect customers, incidents, and engineering operations.
  - mitigation: Keep Composio dry-run by default and block write actions until rollback and off-switch proof exists.
- **missing audit trail**
  - why it matters: Reviewers need to know what evidence was used, what was blocked, and who approved scope changes.
  - mitigation: Require audit log shape for tool calls, evidence intake, reviewer decisions, and future packet updates.

## Reviewer Gates

- **Security/Legal**
  - gate: Confirm allowed data scope, retention, and logging terms
  - blocks: Slack channel summarization and customer incident context access
  - required before: production_access
- **Engineering**
  - gate: Provide repository/project allowlists, permission boundaries, audit logs, and off-switch proof
  - blocks: GitHub/Jira tool connection and any write-action pilot
  - required before: production_access
- **Support Ops**
  - gate: Validate triage workflow fit, escalation rules, and human handoff owner
  - blocks: support operations pilot
  - required before: production_access
- **Procurement/Finance**
  - gate: Review paid seats or vendor spend only if live integrations move beyond dry-run
  - blocks: paid production rollout
  - required before: paid_rollout

## Sponsor Readiness

- nebius: Optional live narration layer for reviewer-ready packet language; offline truth remains deterministic.
- tavily: Optional live evidence notes with source URLs and freshness status; search results do not auto-approve access.
- composio: Scoped GitHub/Slack/Jira tool planning remains dry-run by default.
- openclaw: Optional live runtime trace should preserve the same blocked-access contract.

## Safety State

- Approval granted: False
- External writes enabled: False
- Composio dry-run: True
- Packet state mutation: False
- Requires human approval: True
- Public demo posture: review_packet_only

## Source Packet

- Derived from packet: ia-agent-access-support-triage-v0
- Mode: offline_deterministic
