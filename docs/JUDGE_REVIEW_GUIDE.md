# Judge Review Guide

Status: public reviewer entrypoint
Purpose: make the repo reviewable in five minutes without exposing private v1 source

## Five-Minute Path

If you are reviewing quickly, use this order:

1. Run the no-key demo.
2. Inspect the generated decision brief.
3. Inspect the scenario matrix.
4. Validate the public conformance contract.
5. Check the safety defaults and tests.

```bash
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.trust
python3 -m unittest discover -s tests
```

The default path is deterministic and works without API keys.

If you are using an AI reviewer or coding agent, also read `AGENTS.md`.

## What To Inspect

| Question | Public artifact |
| --- | --- |
| What does the product do? | `README.md` |
| What is the highest-signal product artifact? | `examples/generated/trust_receipt.md` |
| What should a judge skim as one room? | `examples/generated/review_room.md` |
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
- the Trust Receipt gives a public audit-style control-plane artifact without exposing private v1

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
-> no-key demo
-> Trust Receipt
-> Review Room
-> generated decision brief
-> generated packet
-> scenario CLI
-> public conformance contract
-> tests and CI
-> private boundary docs
```

That chain shows a product contract without turning the public repo into a v1 code dump.
