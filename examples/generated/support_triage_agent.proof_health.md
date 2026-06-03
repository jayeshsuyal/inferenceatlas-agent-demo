# Proof Health: support_triage_agent

Private engine, public proof.

Agent-access proof packets age; InferenceAtlas makes drift visible before access moves.

A DecisionPacket is not permanent approval. It ages as tool scope, data boundaries, reviewer gates, and evidence freshness drift.

## Verdict

- scenario: `support_triage_agent`
- status: drifting
- score: 67
- next human health check: day_30_security_engineering_review
- source packet artifact: `examples/generated/support_triage_agent.packet.json`
- source brief artifact: `examples/generated/support_triage_agent.decision_brief.json`

## Packet Drift Timeline

| Checkpoint | Status | Score | Open Proof | Human Action |
| --- | --- | --- | --- | --- |
| day_0 | current | 84 | 5 | Run scoped validation review only. |
| day_30 | drifting | 67 | 5 | Refresh reviewer gates before any broader validation. |
| day_60 | stale | 42 | 5 | Issue a new packet or rerun the trial request. |

## Drifted Facts

- Slack channel allowlist may have changed since intake.
- Jira project scope needs confirmation before draft-ticket validation.
- Audit-log expectations may no longer match the runtime plan.
- Support escalation workflow owner needs reconfirmation.

## Stale Assumptions

- Incident-channel retention terms still match the original request.
- Repository allowlist still reflects the current support workflow.
- Customer-data boundary proof remains unchanged.
- Rollback and off-switch ownership is still named.

## Expired Reviewer Gates

- Security/Legal data-boundary review has not been refreshed within 30 days.
- Engineering allowlist review expired.
- Support Ops workflow-fit review expired.

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- requires human review: True

Proof Health does not approve access. It keeps packet drift visible so a human can decide whether the request is still reviewable.
