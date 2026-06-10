# Sponsor Value Receipts

Private engine, public proof.

Sponsors provide proof signals. IA converts them into packet authority.

Each receipt explains what a sponsor or downstream system contributed, what stayed blocked, and why the IA Packet remains the authority.

## Summary

- scenario: `support_triage_agent`
- receipt_set_id: `ia-sponsor-value-receipts-support_triage_agent-73bf95f7f89d3d99-public-v0`
- packet_id: `ia-agent-access-support-triage-v0`
- graph_id: `ia-proof-graph-support_triage_agent-4f619498deec8dd7-public-v0`
- providers: tavily, composio, openclaw, nebius, portkey
- proof nodes: 80
- proof edges: 141

## Safety

- packet remains authority: True
- all require human review: True
- all non-approving: True
- all non-granting: True
- all non-executing: True
- all non-mutating: True
- all preserve verdict: True

## Receipts

| Provider | Role | Contribution | Stayed Blocked | Proof Nodes |
| --- | --- | --- | --- | --- |
| tavily | Evidence search and freshness layer | Turns missing proof into query plans, source candidates, freshness labels, and reviewer-owned evidence slots. | No proof debt is reduced and no access is approved from search output alone. | 20 |
| composio | Tool permission blast-radius layer | Projects connector actions into blocked write/admin scopes before any tool executes. | Write-like and admin-like actions stay blocked before execution. | 21 |
| openclaw | Runtime trace and blocked-action layer | Shows the checkpoint timeline, attempted actions, policy decisions, and blocked outcomes. | Attempted writes remain blocked and runtime traces cannot replace human review. | 21 |
| nebius | Reviewer synthesis layer | Drafts reviewer-facing summaries from locked packet facts while preserving verdict and safety state. | Narration cannot edit verdicts, blocked claims, safety state, or approval posture. | 9 |
| portkey | Downstream guardrail consumer | Consumes IA packet truth as a guardrail verdict before model or spend movement. | IA does not push policy, call Portkey APIs, mutate Portkey state, or approve spend. | 3 |

## Authority Boundary

Provider proof can inform review, but IA Packet identity, decision lock, verdict, and next human action remain authoritative.
