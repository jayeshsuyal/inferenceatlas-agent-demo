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
- all fallback available: True
- all dry-run available: True
- all live-capable: True
- any live enabled: False

## Provider Readiness

| Provider | Live Value | Proof Pack | Default Safety |
| --- | --- | --- | --- |
| tavily | Source-backed evidence notes with URL and freshness fields. | evidence_candidate_plan | execute=False; approve=False; grant=False; mutate=False |
| composio | Dry-run permission diff for GitHub, Slack, and Jira actions. | permission_diff | execute=False; approve=False; grant=False; mutate=False |
| openclaw | Runtime trace plan for attempted steps, policy decisions, and blocked outcomes. | runtime_trace_plan | execute=False; approve=False; grant=False; mutate=False |
| nebius | Reviewer-ready narration over locked packet fields. | locked_field_narration | execute=False; approve=False; grant=False; mutate=False |

## Readiness Matrix

| Provider | Fallback | Dry Run | Live Capable | Live Enabled | Disabled Reason | Demo Mode |
| --- | --- | --- | --- | --- | --- | --- |
| tavily | True | True | True | False | env_not_inspected_public_default | fallback_evidence_candidates |
| composio | True | True | True | False | env_not_inspected_public_default | dry_run_permission_diff |
| openclaw | True | True | True | False | env_not_inspected_public_default | fallback_runtime_trace |
| nebius | True | True | True | False | env_not_inspected_public_default | fallback_narration |

## CTO Next Steps

- tavily: Fetch evidence candidates for missing proof; require human review before proof debt changes.
- composio: Keep Composio dry-run by default; emit action plans without granting permissions or writing.
- openclaw: Record the live agent loop as trace evidence; do not let runtime checks replace pre-permission review.
- nebius: Connect Nebius only as a narration layer; keep verdict, blocked claims, and safety state locked.

## Default Public Boundary

- works without keys: True
- live calls made: False
- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- requires human review: True

Sponsor tools are proof contributors, not approval authorities.
