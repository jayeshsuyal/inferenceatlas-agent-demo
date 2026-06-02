# V1 Capability Passport

Status: public redacted capability map
Purpose: show private InferenceAtlas v1 breadth without exposing proprietary source code

## Summary

The full InferenceAtlas v1 product remains private. This public repo is a judge-verifiable harness for the agent-access wedge.

The public harness demonstrates the v1 product contract through schemas, deterministic examples, generated artifacts, tests, CI, and redacted docs.

The principle is:

```text
private engine, public proof
```

## Product Spine

Private v1 is organized around the same object spine this public harness exposes:

```text
messy decision request
-> WorkloadProfile
-> FactPack
-> DecisionPacket
-> ArtifactProjection
-> review surface
```

The public demo focuses on one high-stakes review moment:

```text
Should this support triage agent get GitHub, Slack, and Jira access?
```

The public output is a DecisionPacket that shows source status, approval posture, requested capability, tool access plan, tool scope, data scope, evidence notes, blocked claims, missing proof, reviewer owners, reviewer action items, next validation, and safety state.

## Capability Map

| Private v1 capability family | Public proof artifact | What the artifact proves | What remains private |
| --- | --- | --- | --- |
| Ask IA decision coach | `python3 -m agent.demo` and `examples/generated/support_triage_agent.packet.md` | A messy agent-access request becomes a reviewable packet instead of an auto-approval. | Full private Ask IA orchestration, production prompts, UI state, and session logic. |
| WorkloadProfile | `agent/packet.py` packet fields for raw prompt, source status, requested capability, tool scope, and data scope | The user request is preserved and normalized before recommendation language appears. | Full workload extraction stack, private field enrichment, and production session context. |
| FactPack | `source_status`, `evidence_notes`, `missing_proof`, and `blocked_claims` in generated JSON | Evidence, assumptions, and missing truths stay separate from recommendation prose. | Full deterministic evidence engines, provider/catalog internals, and private fixtures. |
| DecisionPacket | `schemas/decision_packet.schema.json` and generated packet JSON | The recommendation object has a stable shape that AI and human reviewers can inspect. | Full private packet builders, historical packet state, and production routing contracts. |
| Tool access planning | `tool_access_plan` in generated packet JSON and Markdown | Dry-run allowances are separated from blocked write actions for GitHub, Slack, and Jira. | Live Composio account state, private workspace configuration, and production tool grants. |
| ArtifactProjection | Markdown, JSON, and trace artifacts under `examples/generated/` | The same packet can be projected into multiple review surfaces without changing the underlying safety state. | Private UI projections, Living Document renderer, and production surface handoff code. |
| Approval Watch / Evidence Watch | `docs/SAFETY_CONTRACT.md` and packet safety fields | Evidence review is separated from approval; new evidence cannot silently grant access. | Private evidence intake UI, reviewer queue, audit trail, and production review state. |
| Governance | `reviewer_owners`, `reviewer_action_items`, and `next_validation` packet sections | Proof debt becomes owner-routed review work instead of vague "ask someone" copy. | Full governance workflows, buyer-specific approval maps, and private reviewer state. |
| Living Document | Markdown packet artifact and future memo projection | The packet can become a durable leadership/reviewer artifact. | Private Living Document product surface and production document state. |
| Route Evidence / audit trail | `examples/generated/support_triage_agent.trace.md` and `.json` | The review path is inspectable step by step. | Private event stores, audit logs, review decisions, and queue implementation. |
| TCO / tokenization / provider lanes | Blocked-claim discipline in the public packet | Unsupported savings, readiness, quality, latency, or compliance claims remain blocked without proof. | Private pricing catalogs, tokenization calibrations, route intelligence, and provider validation engines. |
| Sponsor runtime path | `IA_LIVE_MODE=1 python3 -m agent.demo` hook and manifest sponsor map | Sponsor integrations have a planned place in the packet flow, while the default path remains no-key and judge-safe. | CTO-held keys, live execution traces, private integration setup, and any non-public account context. |

## Current Public Proof Surface

Judges can verify the current harness without secrets:

```bash
python3 -m agent.demo
python3 -m unittest discover -s tests
```

Public files to inspect:

| Proof | Path |
| --- | --- |
| AI-readable manifest | `AI_JUDGE_MANIFEST.json` |
| Build plan | `BUILD_PLAN_TO_JUNE_12.md` |
| Safety contract | `docs/SAFETY_CONTRACT.md` |
| Packet schema | `schemas/decision_packet.schema.json` |
| Packet Markdown | `examples/generated/support_triage_agent.packet.md` |
| Packet JSON | `examples/generated/support_triage_agent.packet.json` |
| Decision trace Markdown | `examples/generated/support_triage_agent.trace.md` |
| Decision trace JSON | `examples/generated/support_triage_agent.trace.json` |
| Tests | `tests/test_decision_packet.py` |
| CI workflow | `.github/workflows/smoke.yml` |

## Redaction Boundary

This public repo intentionally does not expose:

- private InferenceAtlas v1 source code
- customer data
- production secrets
- private prompts
- private catalog internals
- private reviewer queues or audit stores
- live sponsor tokens
- production deployment configuration

The public repo should expose enough proof for a judge to understand and verify the product contract, but not enough to reconstruct proprietary v1 implementation details.

## Safety Boundary

The public harness must preserve these defaults:

- no autonomous approval
- no permission grant
- no external writes
- no production state mutation
- no packet state mutation
- Composio dry-run by default
- human approval required
- unsupported claims remain blocked

These defaults are represented in the generated packet and verified by tests.

## What This Means For Reviewers

If a reviewer sees only this public repo, they should still be able to answer:

1. What is the product?
2. What exact decision does the demo review?
3. What packet does IA produce?
4. What claims stay blocked?
5. Who must review?
6. What validation comes next?
7. How is the private v1 product represented without exposing source?

That is the review bar for this public harness.
