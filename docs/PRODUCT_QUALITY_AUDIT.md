# Product Quality Audit

Status: public product-quality guardrail
Purpose: keep the public proof surface premium, coherent, safe, and reviewable while the repo moves quickly

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

Private engine, public proof.

## Product Quality Thesis

The public harness should feel like a product, not a pile of demo artifacts.

That means each surface must earn its place in the review path. It should either help a judge decide what IA does, help a CTO build safely, help a design partner trial one workflow, or prove the safety boundary without requiring secrets.

The product spine is simple:

```text
agent-access question
-> Agent Skills registry
-> DecisionPacket
-> Packet Diff
-> Agent Access Decision Brief
-> Trust Receipt
-> Packet Outcome Memo
-> Artifact Integrity Gate
-> Review Room
-> Proof Health
-> Sponsor Live Readiness
-> Design Partner Trial Runner
-> human review
```

The public repo should keep that spine visible at every review depth.

## Premium Spine

A reviewer should be able to follow this order without needing private source code, live tokens, or a meeting:

1. `README.md`
2. `docs/PRODUCT_TOUR.md`
3. `docs/AGENT_SKILLS.md`
4. `docs/PRODUCT_QUALITY_AUDIT.md`
5. `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`
6. `python3 -m agent.judge`
7. `examples/generated/packet_diff.md`
8. `examples/generated/support_triage_agent.outcome_memo.md`
9. `python3 -m agent.verify_artifacts`
10. `examples/generated/review_room.html`
11. `examples/generated/trust_receipt.md`
12. `examples/generated/support_triage_agent.proof_health.md`
13. `examples/generated/sponsor_live_readiness.md`
14. `docs/DESIGN_PARTNER_BRIEF.md`
15. `docs/DESIGN_PARTNER_TRIAL_KIT.md`
16. `examples/generated/support_triage_trial_report.md`

This order is the product-quality baseline. It gives a skim reviewer a clear story, gives an agentic reviewer a command path, gives a CTO a build path, and gives a design partner a trial path.

## Load-Bearing Surfaces

| Surface | Product job | Quality bar |
| --- | --- | --- |
| Agent Skills registry | Show the public capability map before reviewers inspect individual artifacts. | Must be generated from `agent/skills.py`, preserve safe categories, and keep every skill backed by commands, artifacts, dependencies, and allowlisted safety boundaries. |
| DecisionPacket | Show the access request, risk posture, proof debt, blocked claims, reviewer owners, and safety state. | Must remain deterministic, schema-backed, and non-approving. |
| Packet Diff | Show how the same engine relaxes, routes, or blocks across risk levels. | Must compare load-bearing fields and preserve blocked production/write invariants. |
| Agent Access Decision Brief | Compress the packet into a fast go/no-go review surface. | Must make scoped validation, production access, missing proof, and next validation obvious. |
| Trust Receipt | Give the fastest audit-style summary. | Must join permission envelope, proof debt, reviewer routing, sponsor proof, and safety state. |
| Packet Outcome Memo | Convert the packet into a human decision. | Must name what can move, what stays blocked, proof owners, reviewer routes, and refresh timing without approving access. |
| Artifact Integrity Gate | Prove deterministic proof artifacts are fresh and generated inventory is clean. | Must regenerate deterministic artifacts, validate static review assets, and fail when outputs drift or unexpected generated files are checked in. |
| Review Room | Put the review into one static room. | Must work without a server, scripts, secrets, or external assets. |
| Proof Health | Show whether a packet is current enough to keep using. | Must show drift, stale assumptions, expired reviewer gates, and the next human refresh action without approving access. |
| Sponsor Live Readiness | Show where Nebius, Tavily, Composio, and OpenClaw can add live proof. | Must keep every provider non-executing, non-approving, non-granting, and non-mutating by default. |
| Design Partner Trial Runner | Turn one role-level request into a report, packet, and access brief. | Must stay no-key, no-write, and scoped to one workflow. |
| Agentic Review Expected Output | Tell an automated reviewer exactly what should pass or fail. | Must give machine-readable checks and failure signals. |

## What Stays Premium

- The first screen stays product-first: private engine, public proof.
- The default path stays one command: `python3 -m agent.judge`.
- The review path stays no-key and deterministic.
- Sponsor tools contribute proof, not approval authority.
- Composio remains dry-run by default.
- The rule is simple: production access stays blocked in the public harness.
- External writes stay disabled in the public harness.
- Human approval remains required.
- Every new public artifact must clarify reviewer decision, design-partner trial, or CTO build path.
- Packet-adjacent artifacts must derive from the packet, brief, policy gate, Proof Health, or sponsor readiness.

## What Not To Add

- No landing-page drift in this repo lane.
- No extra artifact that only repeats the README or packet prose.
- No live write path as a default reviewer experience.
- No sponsor tool deciding the verdict.
- No private prompts, secrets, customer context, account-specific grants, or private v1 source code.
- No broad platform rollout story before the one-workflow design-partner trial path is solid.

## Quality Bar

Before a PR claims the product surface is stronger, it should preserve these signals:

- `python3 -m agent.judge --no-write` passes.
- `python3 -m agent.judge --no-write --json` remains machine-readable.
- `python3 -m unittest discover -s tests` passes.
- `python3 -m py_compile agent/*.py agent/adapters/*.py web/*.py` passes.
- `python3 -m json.tool AI_JUDGE_MANIFEST.json` passes.
- `python3 -m agent.skills --json` passes.
- `python3 -m agent.verify_artifacts` passes.
- The artifact checklist includes the review surfaces a judge should skim.
- The public boundary tests stay clean.
- The Review Room, Trust Receipt, Packet Diff, Packet Outcome Memo, Proof Health, Sponsor Live Readiness, and trial report remain generated public artifacts.

## Product Spine Check

Use this as the quick premium-quality review:

| Question | Pass signal |
| --- | --- |
| Can a judge understand the product in under one minute? | README, Product Tour, and this audit point to the same spine. |
| Can a reviewer see the capability map? | `docs/AGENT_SKILLS.md` maps 12 stable public skills to commands, artifacts, dependencies, and safety boundaries. |
| Can an agentic reviewer run it without help? | `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md` and `python3 -m agent.judge --no-write --json` give exact pass signals. |
| Can a reviewer see that the packet is not one hardcoded shape? | `examples/generated/packet_diff.md` compares load-bearing fields across the three public scenarios. |
| Can the packet become a meeting decision? | `examples/generated/support_triage_agent.outcome_memo.md` names can-move scope, blocked scope, proof owners, and refresh timing. |
| Can a reviewer trust the public proof inventory is fresh? | `python3 -m agent.verify_artifacts` byte-compares regenerated outputs against `examples/generated/`, validates static review assets, and fails on unexpected generated files. |
| Can a CTO build on it safely? | `docs/CTO_HANDOFF.md`, `docs/ARCHITECTURE.md`, and `docs/LIVE_INTEGRATION_CONTRACT.md` preserve dry-run and human-review defaults. |
| Can a design partner trial it? | `docs/DESIGN_PARTNER_TRIAL_KIT.md`, request samples, and the trial runner convert one workflow into public outputs. |
| Can sponsor tools help without taking over? | Sponsor Live Readiness shows proof contribution while keeping execution, approval, grants, and mutation off. |

## Next Product Move

The next premium product move should be a Design Partner Outcome Memo for a real trial request.

The public Packet Outcome Memo now proves the shape. The design-partner-specific version should convert a real trial request into the decision a CTO, Security lead, or AI platform owner wants after a trial:

```text
Move this agent into scoped validation.
Keep these capabilities blocked.
Assign this proof debt to these owners.
Refresh the packet on this date.
```

That is the product moment: a faster, clearer, safer human decision before an agent receives access.
