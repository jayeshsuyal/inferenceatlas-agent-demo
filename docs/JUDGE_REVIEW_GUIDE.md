# Judge Review Guide

Status: public reviewer entrypoint
Purpose: make the repo reviewable in five minutes without exposing private v1 source

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

## Five-Minute Path

If you are reviewing quickly, use this order:

1. Read the Product Tour.
2. Read the Agent Skills registry.
3. Read the Product Quality Audit.
4. Run the one-command judge harness.
5. Inspect the generated Packet Diff.
6. Inspect the generated Packet Outcome Memo.
7. Run the no-key demo if you want the full packet output.
8. Inspect the generated Proof Health report.
9. Inspect the generated Design Partner Outcome Memo.
10. Inspect the generated Sponsor Evidence Replay.
11. Inspect the generated decision brief.
12. Inspect the scenario matrix.
13. Validate the public conformance contract.
14. Check the safety defaults and tests.

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.outcome_memo
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.sponsor_readiness
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.verify_artifacts
python3 -m unittest discover -s tests
```

The default path is deterministic and works without API keys.

If you are using an AI reviewer or coding agent, also read `AGENTS.md`.

For exact automated pass/fail signals, read `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`.

## What To Inspect

| Question | Public artifact |
| --- | --- |
| What does the product do? | `docs/PRODUCT_TOUR.md` and `README.md` |
| What public agent skills are available? | `docs/AGENT_SKILLS.md` and `python3 -m agent.skills --json` |
| What keeps the product surface premium? | `docs/PRODUCT_QUALITY_AUDIT.md` |
| What is the one-command judge path? | `python3 -m agent.judge` |
| What should an automated reviewer treat as pass/fail? | `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md` |
| Does the packet bend across risk? | `python3 -m agent.packet_diff` and `examples/generated/packet_diff.md` |
| What decision should a human leave with? | `python3 -m agent.outcome_memo` and `examples/generated/support_triage_agent.outcome_memo.md` |
| Are the checked-in artifacts fresh? | `python3 -m agent.verify_artifacts` |
| How would a CTO trial this with one real workflow? | `docs/DESIGN_PARTNER_BRIEF.md` |
| What request shape would a design partner fill? | `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml` |
| What happens when a role-level trial request is run? | `python3 -m agent.trial examples/requests/support_triage_trial.yml` and `examples/generated/support_triage_trial_report.md` |
| What meeting decision comes out of that trial? | `python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml` and `examples/generated/support_triage_trial.outcome_memo.md` |
| Where do sponsor proof slots attach to that decision? | `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml` and `examples/generated/support_triage_trial.evidence_replay.md` |
| What is the highest-signal product artifact? | `examples/generated/trust_receipt.md` |
| What should a judge skim as one room? | `examples/generated/review_room.md` |
| What visual artifact works without a server? | `examples/generated/review_room.html` |
| Does the packet lifecycle show drift before stale access? | `python3 -m agent.proof_health` and `examples/generated/support_triage_agent.proof_health.md` |
| What should a reviewer use for the demo talk track? | `docs/REVIEW_ROOM_WALKTHROUGH.md` and `examples/generated/review_room.desktop.jpg` |
| What policy gate is enforced? | `policy/agent_access.yml` and `python3 -m agent.gate --all` |
| How do sponsor integrations enter safely? | `python3 -m agent.adapters --all` |
| Are sponsor tools ready to add live proof safely? | `python3 -m agent.sponsor_readiness` and `examples/generated/sponsor_live_readiness.md` |
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
- Agent Skills maps public capabilities to commands, artifacts, dependencies, and safety boundaries
- low-risk, medium-risk, and critical-risk scenarios produce materially different review postures
- Packet Diff shows relaxed read-only, proof-routed scoped validation, and blocked critical lanes
- Packet Outcome Memo turns the packet into can-move, stays-blocked, proof-owner, and refresh decisions
- the Artifact Integrity Gate proves deterministic proof artifacts match generator output, static review assets are valid, and no unexpected generated file is checked in
- the public policy gate blocks critical/admin/prod-write access
- sponsor integrations enter as dry-run contracts, not live writes or approvals
- Sponsor Live Readiness shows where Nebius, Tavily, Composio, and OpenClaw add proof without becoming approval authorities
- the Trust Receipt gives a public audit-style control-plane artifact without exposing private v1
- the Proof Health report shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- the Design Partner Brief turns the demo into a one-workflow CTO/platform-owner trial path without asking for secrets
- the Design Partner Trial Kit and trial runner give that trial a concrete public input and output path without adding live writes or private source exposure
- the Design Partner Outcome Memo turns that trial output into a can-move, stays-blocked, proof-owner meeting decision
- Sponsor Evidence Replay shows where sponsor proof attaches without letting sponsors approve, grant, write, mutate, or change the verdict
- the Product Quality Audit keeps the public proof surface aligned around the same premium spine during fast iteration

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
-> Agent Skills
-> Product Quality Audit
-> Agentic Review Expected Output
-> one-command judge harness
-> Packet Diff
-> Packet Outcome Memo
-> Artifact Integrity Gate
-> Design Partner Brief
-> Design Partner Trial Kit
-> Design Partner Trial Runner
-> Design Partner Outcome Memo
-> Sponsor Evidence Replay
-> no-key demo
-> Trust Receipt
-> Review Room
-> static Review Room HTML
-> Proof Health
-> Review Room walkthrough and screenshot
-> public policy gate
-> dry-run sponsor adapter contracts
-> sponsor live readiness
-> generated decision brief
-> generated packet
-> scenario CLI
-> public conformance contract
-> tests and CI
-> private boundary docs
```

That chain shows a product contract without turning the public repo into a v1 code dump.
