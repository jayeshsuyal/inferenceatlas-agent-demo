# Evidence Receipt Ledger

Private engine, public proof.

Receipts attach proof context to a packet without changing the packet decision lock.

- scenario: `support_triage_agent`
- packet_id: `ia-agent-access-support-triage-v0`
- decision lock: scoped_validation_only -> scoped_validation_only
- snapshot revision: `rev_965302783cee8688`
- receipts: 13
- tool scope receipts: 3
- proof debt receipts: 5
- reviewer route receipts: 4
- cost/procurement receipts: 1

## Safety

- decision lock preserved: True
- all require human review: True
- all non-approving: True
- all non-granting: True
- all non-executing: True
- all non-mutating: True
- all non-auto-reducing: True

## Finance / Procurement

- owner: Procurement/Finance
- spend claim: No live model/tool/vendor spend is approved by the public receipt ledger.
- budget owner required: True
- token/tool spend cap required: True
- approval granted: False

## Receipt Types

| Receipt Type | Owner | Status | Can Approve | Requires Human Review |
| --- | --- | --- | --- | --- |
| tool_scope_receipt | Engineering | needs_named_owner_review | False | True |
| tool_scope_receipt | Engineering | needs_named_owner_review | False | True |
| tool_scope_receipt | Engineering | needs_named_owner_review | False | True |
| proof_debt_receipt | Engineering | missing_human_confirmation | False | True |
| proof_debt_receipt | Security/Legal | missing_human_confirmation | False | True |
| proof_debt_receipt | Engineering | missing_human_confirmation | False | True |
| proof_debt_receipt | Support Ops | missing_human_confirmation | False | True |
| proof_debt_receipt | Security/Engineering | missing_human_confirmation | False | True |
| cost_procurement_receipt | Procurement/Finance | budget_owner_review_required | False | True |
| reviewer_route_receipt | Security/Legal | required_before_access | False | True |
| reviewer_route_receipt | Engineering | required_before_write_actions | False | True |
| reviewer_route_receipt | Support Ops | required_before_pilot | False | True |
| reviewer_route_receipt | Procurement/Finance | conditional | False | True |
