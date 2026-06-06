# Artifact Map

Status: public artifact map
Purpose: keep the README short while giving reviewers a fast path into every proof surface

Private engine, public proof.

## Fastest Artifacts To Skim

| Reviewer question | Artifact |
| --- | --- |
| What is the highest-signal proof object? | `examples/generated/trust_receipt.md` |
| What capabilities exist? | `docs/AGENT_SKILLS.md` |
| Does the packet bend across risk levels? | `examples/generated/packet_diff.md` |
| What human decision comes out? | `examples/generated/support_triage_agent.outcome_memo.md` |
| Where do sponsor tools attach proof? | `examples/generated/support_triage_trial.sponsor_proof_trace.md` |
| Can sponsor evidence attach without changing the decision? | `examples/generated/support_triage_trial.evidence_replay.md` |
| What is the static visual room? | `examples/generated/review_room.html` |
| What is the lifecycle/drift signal? | `examples/generated/support_triage_agent.proof_health.md` |
| What should Finance and Procurement review? | `examples/generated/ai_spend_budget_overrun.spend_packet.md` |
| What is the guided walkthrough? | `docs/REVIEW_ROOM_WALKTHROUGH.md` |
| What is the design-partner trial output? | `examples/generated/support_triage_trial_report.md` |
| What is the design-partner meeting memo? | `examples/generated/support_triage_trial.outcome_memo.md` |
| What proves artifact freshness? | `python3 -m agent.verify_artifacts` |

## Source Docs

- [Product Tour](PRODUCT_TOUR.md)
- [Judge Review Guide](JUDGE_REVIEW_GUIDE.md)
- [Agentic Review Expected Output](AGENTIC_REVIEW_EXPECTED_OUTPUT.md)
- [Product Quality Audit](PRODUCT_QUALITY_AUDIT.md)
- [Public Conformance Contract](CONTRACT.md)
- [Safety Contract](SAFETY_CONTRACT.md)
- [V1 Capability Passport](V1_CAPABILITY_PASSPORT.md)

## Safety Boundary

The artifacts are proof surfaces. They do not approve access, grant permissions, execute external writes, approve spend, select providers, or guarantee savings.
