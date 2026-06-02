# DecisionPacket: Support Triage Agent Access

## Verdict

Do not approve production access yet; allow read-only validation review.

Approve a scoped read-only validation review after data owner scope confirmation.

## Approval Posture

- production access: blocked
- validation review: allowed
- read access: allowed_after_data_owner_scope_review
- write access: not_requested
- compliance claims: blocked_until_data_owner_review

## Source Status

- user prompt: provided
- live vendor evidence: not_fetched_in_offline_mode
- workspace policy: missing
- tool auth state: not_connected_in_offline_mode
- reviewer confirmation: missing
- deterministic packet: generated

## Requested Capability

- BigQuery: read aggregate product usage tables (low, dry_run_only)
- Looker: read dashboards and saved explores (low, dry_run_only)

## Tool Access Plan

- **bigquery**
  - requested: read aggregate product usage tables
  - demo allowance: read-only validation plan only
  - blocked actions: writes, exports, permission changes
  - required proof: dataset/resource allowlist, data owner approval, read-only credential proof
- **looker**
  - requested: read dashboards and saved explores
  - demo allowance: read-only validation plan only
  - blocked actions: writes, exports, permission changes
  - required proof: dataset/resource allowlist, data owner approval, read-only credential proof

## Tool Scope

- bigquery: read [datasets.read, jobs.create_read_only_query] | write [none] | blocked [permission changes, data export, workspace-wide access]
- looker: read [dashboards.read, explores.read] | write [none] | blocked [permission changes, data export, workspace-wide access]

## Data Scope

May include:

- aggregate product usage metrics
- internal business metrics

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

- **Production access is broadly approved.**: reason: Only a read-only validation review can move before data owner scope confirmation.
- **The agent may export rows or mutate dashboards.**: reason: The request is read-only and does not include export, write, or dashboard mutation proof.

## Missing Proof

- **BigQuery read-only allowlist and credential proof**: owner: Data/Engineering; unblocks: read-only validation review
- **Looker read-only allowlist and credential proof**: owner: Data/Engineering; unblocks: read-only validation review
- **Data owner confirmation that requested metrics are aggregate and non-customer-specific**: owner: Data/Analytics; unblocks: read-only analytics validation

## Reviewer Owners

- **Data/Analytics**: review area: aggregate metric scope, dashboard allowlist, read-only credentials; current state: required_before_validation
- **Engineering**: review area: read-only credential boundary and audit log owner; current state: required_before_access

## Reviewer Action Items

- **Data/Analytics**: action: Confirm metrics are aggregate, allowlisted, and non-customer-specific; blocks: read-only analytics validation
- **Engineering**: action: Provide read-only credential proof and audit log owner; blocks: warehouse/dashboard connection

## Next Human Validation

Action: Run a read-only analytics validation with named datasets, dashboards, and aggregate-only metrics.

Owner: Data/Analytics + Engineering

Success criteria:

- dataset and dashboard allowlist approved
- read-only credentials verified
- no row export or dashboard mutation allowed
- audit log owner named

## Safety State

- Approval granted: False
- External writes enabled: False
- Composio dry-run: True
- Packet state mutation: False
- Requires human approval: True
- Public demo posture: review_packet_only

## Raw Prompt

Should this read-only analytics agent get BigQuery and Looker access? It will read aggregate product usage tables, inspect saved dashboards, and summarize internal business metrics. It must not export rows, change dashboards, or touch customer incident context.
