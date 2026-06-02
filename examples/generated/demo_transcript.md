# Demo Transcript

Command:

```bash
python3 -m agent.demo
```

Mode:

```text
offline_deterministic
```

This no-key path is the default judge-safe run. It does not call live vendors, does not grant access, and does not mutate external state.

## Terminal Output

```text
========================================================================
InferenceAtlas Agent Demo - Offline DecisionPacket
Mode: offline_deterministic | external writes: disabled | Composio: dry-run
========================================================================

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

## Blocked Claims

- Production tool access is approved.
- Customer-data handling is safe.
- The agent may create or mutate Jira/GitHub/Slack state.
- The workflow is compliance-ready.

## Missing Proof

- GitHub repository allowlist and permission level
- Slack channel allowlist, retention policy, and customer-data boundary
- Jira project scope, draft-only mode, and rollback/off-switch plan
- Support escalation workflow and human handoff owner
- Audit log shape for tool calls, evidence intake, and reviewer decisions

## Reviewer Owners

- Security/Legal
- Engineering
- Support Ops
- Procurement/Finance

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

Generated artifacts:
- examples/generated/support_triage_agent.packet.md
- examples/generated/support_triage_agent.packet.json
- examples/generated/support_triage_agent.trace.json
- examples/generated/support_triage_agent.trace.md
```

## What Judges Should Notice

- The demo works without API keys.
- The output is not a generic agent chat response; it is a structured DecisionPacket.
- Production access remains blocked.
- Write actions remain disabled by default.
- Composio is dry-run by default.
- Missing proof is visible instead of hidden.
- Reviewer owners are named before access is approved.
- The next step is validation, not autonomous execution.

## Generated Artifacts

| Artifact | Path |
| --- | --- |
| Markdown packet | `examples/generated/support_triage_agent.packet.md` |
| JSON packet | `examples/generated/support_triage_agent.packet.json` |
| Markdown trace | `examples/generated/support_triage_agent.trace.md` |
| JSON trace | `examples/generated/support_triage_agent.trace.json` |

## Verification

Run:

```bash
python3 -m unittest discover -s tests
```

The tests verify the required packet shape, blocked claims, safety defaults, generated JSON artifact, and no-key demo command.
