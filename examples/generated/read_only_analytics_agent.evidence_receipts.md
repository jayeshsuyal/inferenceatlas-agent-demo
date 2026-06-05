# Evidence Receipt Ledger

Private engine, public proof.

Receipts attach proof context to a packet without changing the packet decision lock.

- scenario: `read_only_analytics_agent`
- packet_id: `ia-agent-access-read-only-analytics-v0`
- decision lock: read_only_validation -> read_only_validation
- snapshot revision: `rev_325dd666c69fa24e`
- receipts: 8
- tool scope receipts: 2
- proof debt receipts: 3
- reviewer route receipts: 2
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
| proof_debt_receipt | Data/Engineering | missing_human_confirmation | False | True |
| proof_debt_receipt | Data/Engineering | missing_human_confirmation | False | True |
| proof_debt_receipt | Data/Analytics | missing_human_confirmation | False | True |
| cost_procurement_receipt | Procurement/Finance | budget_owner_review_required | False | True |
| reviewer_route_receipt | Data/Analytics | required_before_validation | False | True |
| reviewer_route_receipt | Engineering | required_before_access | False | True |
