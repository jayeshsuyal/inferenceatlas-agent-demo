# AI Spend Review Packet

Private engine, public proof.

- scenario: `ai_spend_budget_overrun`
- packet_id: `ia-spend-review-ai_spend_budget_overrun-v0`
- content_hash: `sha256:47f8ff3775dec3c56988f5d73cb0bf05692ef38e417a307f836cbb6a37c26f6d`
- verdict_class: finance_procurement_review_required
- live spend approved: False
- provider winner selected: False
- savings guaranteed: False

## Review Posture

Do not approve spend changes, vendor switches, or savings claims until Finance and Procurement review invoice, usage, and contract evidence.

## Required Evidence

- vendor invoices for the budget period — owner: Finance; unblocks: baseline spend confirmation
- per-team usage metrics with workload labels — owner: AI Platform / Engineering; unblocks: usage ownership and workload fit review
- contract terms, minimums, credits, and renewal dates — owner: Procurement; unblocks: renegotiation or vendor-change review
- budget owner approval for any cap, shift, or expansion — owner: Finance; unblocks: human decision on spend controls

## Blocked Claims

- AI spend changes are approved. Reason: The packet has no invoice-backed Finance approval.
- Provider-switch savings are already proven. Reason: Savings require invoice, usage, contract, latency, and quality evidence.
- A provider decision is already selected. Reason: Procurement has not reviewed contract terms or operational risk.
- The team can expand live model or tool spend. Reason: Budget owner approval and spend cap proof are missing.

## Reviewers

- Finance: budget baseline, invoice evidence, owner approval (required_before_spend_change)
- Procurement: contract terms, vendor risk, renegotiation path (required_before_vendor_change)
- AI Platform / Engineering: usage metrics, workload fit, quality and latency constraints (required_before_model_class_shift)

## Next Human Action

Attach invoice, usage, and contract evidence, then run a Finance and Procurement review before any spend control or vendor-change decision.
