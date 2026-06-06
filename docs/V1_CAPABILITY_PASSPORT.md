# V1 Capability Passport

Status: public redacted capability map
Purpose: show private InferenceAtlas v1 breadth without exposing proprietary source code

## Summary

The full InferenceAtlas v1 product remains private. This public repo is a judge-verifiable harness for the agent-access wedge.

The public harness demonstrates the v1 product contract through schemas, deterministic examples, generated artifacts, tests, CI, and redacted docs.

It also gives the CTO a buildable public structure through handoff docs, architecture notes, and live integration contracts.

The principle is:

```text
private engine, public proof
```

## Product Spine

Private v1 is organized around the same object spine this public harness exposes:

```text
messy decision request
-> request profile
-> evidence pack
-> DecisionPacket
-> artifact projection
-> Agent Access Decision Brief
-> review surface
```

The public demo focuses on one high-stakes review moment:

```text
Should this support triage agent get GitHub, Slack, and Jira access?
```

The public output is a DecisionPacket plus an Agent Access Decision Brief. The packet shows source status, approval posture, requested capability, tool access plan, tool scope, data scope, evidence notes, blocked claims, missing proof, reviewer owners, reviewer action items, next validation, and safety state. The brief gives reviewers the fast go/no-go: access eligibility, runtime permission boundary, risk register, reviewer gates, sponsor readiness, and safety state.

## Capability Map

| Product capability family | Public proof artifact | What the artifact proves | What remains private |
| --- | --- | --- | --- |
| Decision review coach | `python3 -m agent.demo` and `examples/generated/support_triage_agent.packet.md` | A messy agent-access request becomes a reviewable packet instead of an auto-approval. | Full private orchestration, production prompts, UI state, and session logic. |
| Request profiling | `agent/packet.py` packet fields for raw prompt, source status, requested capability, tool scope, and data scope | The user request is preserved and normalized before recommendation language appears. | Full extraction stack, private field enrichment, and production session context. |
| Evidence packing | `source_status`, `evidence_notes`, `missing_proof`, and `blocked_claims` in generated JSON | Evidence, assumptions, and missing truths stay separate from recommendation prose. | Full deterministic evidence engines, provider/catalog internals, and private fixtures. |
| DecisionPacket | `schemas/decision_packet.schema.json` and generated packet JSON | The recommendation object has a stable shape that AI and human reviewers can inspect. | Full private packet builders, historical packet state, and production routing contracts. |
| Agent Access Decision Brief | `schemas/agent_access_decision_brief.schema.json` and generated brief JSON/Markdown | A packet can become a skim-ready access eligibility decision without exposing private review logic. | Private review surfaces, account-specific approval maps, and production eligibility scoring. |
| Agent Trust Gateway | `examples/generated/trust_receipt.md`, `examples/generated/review_room.md`, `examples/generated/review_room.html`, and `docs/REVIEW_ROOM_WALKTHROUGH.md` | Scenario spread, permission envelope, proof debt, reviewer routing, sponsor runtime plan, safety state, and private boundary are joined into one public control-plane artifact, serverless visual room, and demo talk track. | Private control-plane implementation, production routing, customer-specific policy, and account state. |
| Packet lifecycle health | `python3 -m agent.proof_health` and `examples/generated/support_triage_agent.proof_health.md` | Packet Drift, stale assumptions, expired reviewer gates, and the next human health check are visible before access expands. | Private lifecycle automation, customer-specific refresh cadence, and production review state. |
| Public policy gate | `policy/agent_access.yml` and `python3 -m agent.gate --all` | A policy-as-code gate blocks critical/admin/prod-write access and allows lower-risk validation only with visible gates. | Private policy compiler, customer-specific policies, reviewer queue state, and production enforcement integrations. |
| Sponsor adapter contracts | `agent/adapters/` and `python3 -m agent.adapters --all` | Nebius, Tavily, Composio, and OpenClaw enter as dry-run/evidence/narration/trace contracts that cannot approve access or execute writes. | Live keys, private account state, live sponsor traces, and production adapter implementations. |
| Tool access planning | `tool_access_plan` in generated packet JSON and Markdown | Dry-run allowances are separated from blocked write actions for GitHub, Slack, and Jira. | Live Composio account state, private workspace configuration, and production tool grants. |
| Artifact projection | Markdown, JSON, and trace artifacts under `examples/generated/` | The same packet can be projected into multiple review surfaces without changing the underlying safety state. | Private UI projections, durable document rendering, and production surface handoff code. |
| Approval and evidence boundary | `docs/SAFETY_CONTRACT.md` and packet safety fields | Evidence review is separated from approval; new evidence cannot silently grant access. | Private evidence intake UI, reviewer queue, audit trail, and production review state. |
| Governance | `reviewer_owners`, `reviewer_action_items`, and `next_validation` packet sections | Proof debt becomes owner-routed review work instead of vague "ask someone" copy. | Full governance workflows, buyer-specific approval maps, and private reviewer state. |
| Durable review memo | Markdown packet artifact and future memo projection | The packet can become a durable leadership/reviewer artifact. | Private document product surface and production document state. |
| Review trace and audit trail | `examples/generated/support_triage_agent.trace.md` and `.json` | The review path is inspectable step by step. | Private event stores, audit logs, review decisions, and queue implementation. |
| TCO / tokenization / provider lanes | Blocked-claim discipline in the public packet | Unsupported savings, readiness, quality, latency, or compliance claims remain blocked without proof. | Private pricing catalogs, tokenization calibrations, route intelligence, and provider validation engines. |
| Sponsor runtime path | `IA_LIVE_MODE=1 python3 -m agent.demo` hook and manifest sponsor map | Sponsor integrations have a planned place in the packet flow, while the default path remains no-key and judge-safe. | CTO-held keys, live execution traces, private integration setup, and any non-public account context. |
| Engineering handoff | `docs/CTO_HANDOFF.md`, `docs/ARCHITECTURE.md`, and `docs/LIVE_INTEGRATION_CONTRACT.md` | The public branch is structured enough for live sponsor work without exposing private v1 source. | Private implementation details, production secrets, customer workspaces, and full internal operating cadence. |

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
| Judge review guide | `docs/JUDGE_REVIEW_GUIDE.md` |
| Design partner brief | `docs/DESIGN_PARTNER_BRIEF.md` |
| Design partner trial kit | `docs/DESIGN_PARTNER_TRIAL_KIT.md` |
| Trial request template | `examples/requests/design_partner_trial.yml` |
| Support triage trial sample | `examples/requests/support_triage_trial.yml` |
| Build plan | `BUILD_PLAN_TO_JUNE_12.md` |
| Public conformance contract | `docs/CONTRACT.md` |
| One-command public harness | `bash scripts/run.sh` |
| Direct judge harness | `python3 -m agent.judge` |
| Trust Receipt | `examples/generated/trust_receipt.md` |
| Review Room | `examples/generated/review_room.md` |
| Static Review Room HTML | `examples/generated/review_room.html` |
| Proof Health | `examples/generated/support_triage_agent.proof_health.md` |
| Review Room walkthrough | `docs/REVIEW_ROOM_WALKTHROUGH.md` |
| Review Room screenshot | `examples/generated/review_room.desktop.jpg` |
| Public policy gate | `policy/agent_access.yml` |
| Sponsor adapters | `agent/adapters/` |
| Safety contract | `docs/SAFETY_CONTRACT.md` |
| CTO handoff | `docs/CTO_HANDOFF.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Live integration contract | `docs/LIVE_INTEGRATION_CONTRACT.md` |
| Packet schema | `schemas/decision_packet.schema.json` |
| Decision Brief schema | `schemas/agent_access_decision_brief.schema.json` |
| Packet Markdown | `examples/generated/support_triage_agent.packet.md` |
| Packet JSON | `examples/generated/support_triage_agent.packet.json` |
| Decision Brief Markdown | `examples/generated/support_triage_agent.decision_brief.md` |
| Decision Brief JSON | `examples/generated/support_triage_agent.decision_brief.json` |
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
- runtime permission checks stay separate from pre-permission access eligibility

These defaults are represented in the generated packet and decision brief, then verified by tests.

## What This Means For Reviewers

If a reviewer sees only this public repo, they should still be able to answer:

1. What is the product?
2. What exact decision does the demo review?
3. What packet does IA produce?
4. What quick access decision brief should a reviewer skim first?
5. What claims stay blocked?
6. Who must review?
7. What validation comes next?
8. How is the private v1 product represented without exposing source?

That is the review bar for this public harness.
