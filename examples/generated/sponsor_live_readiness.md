# Sponsor Live Readiness

Private engine, public proof.

Sponsor tools enrich proof; they do not approve access.

## Summary

- scenario: `support_triage_agent`
- provider count: 4
- all contracts ready: True
- default path requires keys: False
- all non-executing: True
- all non-approving: True
- all non-granting: True
- all non-mutating: True
- human review required: True

## Provider Readiness

| Provider | Live Value | Proof Pack | Default Safety |
| --- | --- | --- | --- |
| composio | Dry-run permission diff for GitHub, Slack, and Jira actions. | permission_diff | execute=False; approve=False; grant=False; mutate=False |
| tavily | Source-backed evidence notes with URL and freshness fields. | evidence_candidate_plan | execute=False; approve=False; grant=False; mutate=False |
| nebius | Reviewer-ready narration over locked packet fields. | locked_field_narration | execute=False; approve=False; grant=False; mutate=False |
| openclaw | Runtime trace plan for attempted steps, policy decisions, and blocked outcomes. | runtime_trace_plan | execute=False; approve=False; grant=False; mutate=False |

## CTO Next Steps

- composio: Keep Composio dry-run by default; emit action plans without granting permissions or writing.
- tavily: Fetch evidence candidates for missing proof; require human review before proof debt changes.
- nebius: Connect Nebius only as a narration layer; keep verdict, blocked claims, and safety state locked.
- openclaw: Record the live agent loop as trace evidence; do not let runtime checks replace pre-permission review.

## Default Public Boundary

- works without keys: True
- live calls made: False
- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- requires human review: True

Sponsor tools are proof contributors, not approval authorities.
