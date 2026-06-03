# Packet Diff

Private engine, public proof.

The same packet engine relaxes for low-risk read-only access, routes proof debt for medium/high risk, and blocks critical admin/prod-write access.

## Scenario Spread

| Scenario | Movement | Policy Gate | Scoped Validation | Production | Missing Proof |
| --- | --- | --- | --- | --- | --- |
| support_triage_agent | routes_to_proof_owner_scoped_validation | VALIDATION_ALLOWED_WITH_GATES | True | False | 5 |
| read_only_analytics_agent | relaxes_to_read_only_validation | VALIDATION_ALLOWED_WITH_GATES | True | False | 3 |
| admin_code_fix_bot | hardens_to_blocked_before_validation | BLOCKED | False | False | 2 |

## Load-Bearing Field Diff

| Field | support_triage_agent | read_only_analytics_agent | admin_code_fix_bot | Differs |
| --- | --- | --- | --- | --- |
| approval_posture.validation_review | allowed | allowed | blocked_until_security_review | True |
| approval_posture.write_access | blocked_until_rollback_and_off_switch_proof | not_requested | blocked_due_to_admin_and_production_mutation | True |
| go_no_go.scoped_validation_review | True | True | False | True |
| go_no_go.production_access | False | False | False | False |
| policy_gate.decision | VALIDATION_ALLOWED_WITH_GATES | VALIDATION_ALLOWED_WITH_GATES | BLOCKED | True |
| requested_capability.highest_risk | high | low | critical | True |
| requested_capability.systems | GitHub, Slack, Jira | BigQuery, Looker | GitHub | True |
| missing_proof.count | 5 | 3 | 2 | True |
| blocked_claims.count | 4 | 2 | 4 | True |
| reviewer_owners | Security/Legal, Engineering, Support Ops, Procurement/Finance | Data/Analytics, Engineering | Security/Engineering, Engineering Leadership, Security/Legal | True |
| next_validation.action | Run a scoped dry-run pilot review with named repositories, channels, and Jira project. | Run a read-only analytics validation with named datasets, dashboards, and aggregate-only metrics. | Reject production write/admin access until the request is rewritten without admin scopes and with rollback proof. | True |

## Why These Fields Matter

- approval_posture.validation_review: Shows whether the request can even enter scoped validation.
- approval_posture.write_access: Separates no-write, proof-blocked write, and admin/prod-write rejection.
- go_no_go.scoped_validation_review: Shows the human-review lane the packet enables.
- go_no_go.production_access: Production remains blocked across the public harness.
- policy_gate.decision: Shows the policy-as-code result over the same packet.
- requested_capability.highest_risk: Proves risk shape changes across read-only, proof-routed, and critical requests.
- requested_capability.systems: Shows the access envelope that drives reviewer routing.
- missing_proof.count: Shows proof debt changes with request risk and scope.
- blocked_claims.count: Shows unsupported approval, safety, or readiness claims stay visible.
- reviewer_owners: Shows the packet routes work to different owners by risk shape.
- next_validation.action: Shows the smallest safe next human step for each request.

## Summary

- differing load-bearing fields: 10 of 11
- has relaxed read-only lane: True
- has proof-routed lane: True
- has blocked critical lane: True
- all production access blocked: True
- all external writes blocked: True

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- requires human review: True
