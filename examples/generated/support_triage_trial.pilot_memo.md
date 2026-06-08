# Pilot Memo

Private engine, public proof.

This memo packages one packet reference, sponsor proof roles, reviewer routing, blocked claims, and missing proof into a buyer-carried pilot artifact.

## Packet Reference

- memo_id: `ia-pilot-memo-support_triage_trial-91a71df3479c999e-public-v0`
- packet_id: `ia-agent-access-support-triage-v0`
- revision_id: `rev_88d8eb01dcc88177`
- content_hash: `sha256:88d8eb01dcc8817774770a07bd4859fdac699eb4dc3f802c059777555a3c235c`
- packet artifact: `examples/generated/support_triage_trial.packet.json`

## Decision

- verdict class: scoped_validation_only
- next human action: Run a scoped dry-run pilot review with named repositories, channels, and Jira project.
- safety anchor: IA did not approve. The next human action is named above.

## Sponsor Contributions

| Provider | Verb | Role | Proof Type | Human Review | Can Change Decision |
| --- | --- | --- | --- | --- | --- |
| tavily | finds | discovery | evidence_candidate_plan | True | False |
| composio | simulates | simulation | permission_diff | True | False |
| nebius | narrates | narration | locked_field_narration | True | False |
| openclaw | traces | observation | runtime_trace_plan | True | False |

## Reviewer Routing

| Owner | Decision Needed | Blocks | Required Before |
| --- | --- | --- | --- |
| Security/Legal | Confirm allowed data scope, retention, and logging terms | Slack channel summarization and customer incident context access | scoped_validation_or_permission_expansion |
| Engineering | Provide repository/project allowlists, permission boundaries, audit logs, and off-switch proof | GitHub/Jira tool connection and any write-action pilot | scoped_validation_or_permission_expansion |
| Support Ops | Validate triage workflow fit, escalation rules, and human handoff owner | support operations pilot | scoped_validation_or_permission_expansion |
| Procurement/Finance | Review paid seats or vendor spend only if live integrations move beyond dry-run | paid production rollout | scoped_validation_or_permission_expansion |

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

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- requires human review: True

## Export Variants

- copy review brief: `examples/generated/support_triage_trial.copy_review_brief.md`
- export pilot memo: `examples/generated/support_triage_trial.pilot_memo.json`, `examples/generated/support_triage_trial.pilot_memo.md`
