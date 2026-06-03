# Agent Access Decision Brief: Read-Only Analytics Agent

## Decision

Question: Should the read-only analytics agent get BigQuery and Looker access?

Verdict: Do not grant production access.

Recommended next step: Approve a scoped validation review only.

Reason: The request is constrained enough for validation, but production access still requires reviewer proof.

## Go / No-Go

- production access: False
- scoped validation review: True
- external writes: False
- Composio dry-run: True
- next validation: Run a read-only analytics validation with named datasets, dashboards, and aggregate-only metrics.

## Runtime Permission Boundary

- Runtime permission prompts answer: Can the agent perform this specific action now?
- InferenceAtlas answers: Should this agent be eligible for this class of access at all, and what proof is required first?
- Why this is different: Runtime prompts are last-mile execution checks. The Decision Brief is the pre-permission governance review that decides eligibility, missing proof, and reviewer gates before runtime tools are granted.

## Access Eligibility

- **BigQuery**
  - requested: read aggregate product usage tables
  - eligibility: candidate_for_scoped_validation_review
  - validation allowance: read-only validation plan only
  - production status: blocked
  - required proof: dataset/resource allowlist, data owner approval, read-only credential proof
- **Looker**
  - requested: read dashboards and saved explores
  - eligibility: candidate_for_scoped_validation_review
  - validation allowance: read-only validation plan only
  - production status: blocked
  - required proof: dataset/resource allowlist, data owner approval, read-only credential proof

## Access Envelope

Allowed for validation:

- bigquery: read-only validation plan only
- looker: read-only validation plan only

Blocked in validation:

- bigquery: writes
- bigquery: exports
- bigquery: permission changes
- looker: writes
- looker: exports
- looker: permission changes

Blocked before production:

- production access grant
- external write actions
- scope expansion without a new packet
- compliance or safety claims without named reviewer evidence

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

- **Data/Analytics**
  - gate: Confirm metrics are aggregate, allowlisted, and non-customer-specific
  - blocks: read-only analytics validation
  - required before: production_access
- **Engineering**
  - gate: Provide read-only credential proof and audit log owner
  - blocks: warehouse/dashboard connection
  - required before: production_access

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

- Derived from packet: ia-agent-access-read-only-analytics-v0
- Mode: offline_deterministic
