# Judge Review Guide

Status: public reviewer entrypoint
Purpose: make the repo reviewable in five minutes without exposing private v1 source

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

## Five-Minute Path

If you are reviewing quickly, use this order:

1. Read the Product Tour.
2. Run the one-command judge harness.
3. Run the no-key demo if you want the full packet output.
4. Inspect the generated Proof Health report.
5. Inspect the generated decision brief.
6. Inspect the scenario matrix.
7. Validate the public conformance contract.
8. Check the safety defaults and tests.

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m unittest discover -s tests
```

The default path is deterministic and works without API keys.

If you are using an AI reviewer or coding agent, also read `AGENTS.md`.

For exact automated pass/fail signals, read `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`.

## What To Inspect

| Question | Public artifact |
| --- | --- |
| What does the product do? | `docs/PRODUCT_TOUR.md` and `README.md` |
| What is the one-command judge path? | `python3 -m agent.judge` |
| What should an automated reviewer treat as pass/fail? | `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md` |
| How would a CTO trial this with one real workflow? | `docs/DESIGN_PARTNER_BRIEF.md` |
| What request shape would a design partner fill? | `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml` |
| What happens when a role-level trial request is run? | `python3 -m agent.trial examples/requests/support_triage_trial.yml` and `examples/generated/support_triage_trial_report.md` |
| What is the highest-signal product artifact? | `examples/generated/trust_receipt.md` |
| What should a judge skim as one room? | `examples/generated/review_room.md` |
| What visual artifact works without a server? | `examples/generated/review_room.html` |
| Does the packet lifecycle show drift before stale access? | `python3 -m agent.proof_health` and `examples/generated/support_triage_agent.proof_health.md` |
| What should a reviewer use for the demo talk track? | `docs/REVIEW_ROOM_WALKTHROUGH.md` and `examples/generated/review_room.desktop.jpg` |
| What policy gate is enforced? | `policy/agent_access.yml` and `python3 -m agent.gate --all` |
| How do sponsor integrations enter safely? | `python3 -m agent.adapters --all` |
| What should a reviewer skim first? | `examples/generated/support_triage_agent.decision_brief.md` |
| What complete packet was produced? | `examples/generated/support_triage_agent.packet.md` |
| Does the engine bend across risk levels? | `python3 -m agent.review --list` |
| Is the public proof contract enforced? | `python3 -m agent.contract --all` |
| Are blocked production defaults tested? | `python3 -m unittest discover -s tests` |
| How does this map to private v1? | `docs/V1_CAPABILITY_PASSPORT.md` |
| What is the safety boundary? | `docs/SAFETY_CONTRACT.md` |

## What This Proves

The public harness proves that InferenceAtlas can turn a messy agent-access request into a reviewable pre-permission packet:

- production access stays blocked
- external writes stay disabled
- Composio stays dry-run by default
- missing proof remains visible
- unsupported approval/compliance/readiness claims stay blocked
- reviewer owners and next validation steps are explicit
- low-risk, medium-risk, and critical-risk scenarios produce materially different review postures
- the public policy gate blocks critical/admin/prod-write access
- sponsor integrations enter as dry-run contracts, not live writes or approvals
- the Trust Receipt gives a public audit-style control-plane artifact without exposing private v1
- the Proof Health report shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- the Design Partner Brief turns the demo into a one-workflow CTO/platform-owner trial path without asking for secrets
- the Design Partner Trial Kit and trial runner give that trial a concrete public input and output path without adding live writes or private source exposure

## What This Does Not Expose

This repo is a public proof surface, not the private product source.

It does not expose:

- private v1 source code
- private prompts
- private reviewer queues
- production routing logic
- customer or workspace context
- live sponsor tokens
- account-specific tool grants

Private engine, public proof.

## Review Signal

The strongest review signal is not a single artifact. It is the chain:

```text
README thesis
-> Product Tour
-> Agentic Review Expected Output
-> one-command judge harness
-> Design Partner Brief
-> Design Partner Trial Kit
-> Design Partner Trial Runner
-> no-key demo
-> Trust Receipt
-> Review Room
-> static Review Room HTML
-> Proof Health
-> Review Room walkthrough and screenshot
-> public policy gate
-> dry-run sponsor adapter contracts
-> generated decision brief
-> generated packet
-> scenario CLI
-> public conformance contract
-> tests and CI
-> private boundary docs
```

That chain shows a product contract without turning the public repo into a v1 code dump.
