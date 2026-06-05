# Evidence Receipt Ledger

Private engine, public proof.

Receipts attach proof context to a packet without changing the packet decision lock.

- scenario: `admin_code_fix_bot`
- packet_id: `ia-agent-access-admin-code-fix-bot-v0`
- decision lock: blocked -> blocked
- snapshot revision: `rev_7dd2645ee8bfe352`
- receipts: 7
- tool scope receipts: 1
- proof debt receipts: 2
- reviewer route receipts: 3
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
| proof_debt_receipt | Security/Engineering | missing_human_confirmation | False | True |
| proof_debt_receipt | Security/Engineering | missing_human_confirmation | False | True |
| cost_procurement_receipt | Procurement/Finance | budget_owner_review_required | False | True |
| reviewer_route_receipt | Security/Engineering | required_before_validation | False | True |
| reviewer_route_receipt | Engineering Leadership | required_before_any_write_path | False | True |
| reviewer_route_receipt | Security/Legal | required_before_access | False | True |
