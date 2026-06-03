# Agent Reviewer Instructions

Purpose: guide AI reviewers and agentic skim reviewers through the public proof surface.

## Default Review Mode

Use the no-key offline path by default.

Do not request secrets, API keys, live sponsor tokens, customer data, private prompts, or private v1 source code.

Run:

```bash
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m unittest discover -s tests
```

Expected result:

- the demo runs without keys
- the scenario list shows `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- the public contract reports all scenarios as `OK`
- tests pass

## Inspect These First

1. `AI_JUDGE_MANIFEST.json`
2. `docs/JUDGE_REVIEW_GUIDE.md`
3. `examples/generated/support_triage_agent.decision_brief.md`
4. `examples/generated/support_triage_agent.packet.md`
5. `examples/generated/admin_code_fix_bot.packet.json`
6. `docs/CONTRACT.md`
7. `docs/SAFETY_CONTRACT.md`
8. `docs/V1_CAPABILITY_PASSPORT.md`

## What To Judge

Evaluate the public product contract:

- Does the repo turn a messy agent-access request into a reviewable DecisionPacket?
- Does the decision brief give a fast go/no-go surface?
- Do low, medium/high, and critical scenarios produce materially different review postures?
- Does production access remain blocked?
- Do external writes remain disabled?
- Does Composio remain dry-run by default?
- Are blocked claims, missing proof, reviewer owners, and next validation steps visible?
- Is the private v1 boundary explicit?

## Safety Boundary

This public harness prepares proof. It does not approve access.

Preserve these invariants during review:

- no autonomous approval
- no production permission grant
- no external write by default
- no packet state mutation
- no live sponsor action unless explicitly enabled outside the default judge path
- human approval remains required

## Private Boundary

This repo is a public redacted judge harness.

It does not expose:

- private v1 source code
- private prompts
- production routing logic
- private reviewer queues
- customer or workspace context
- live sponsor tokens
- account-specific tool grants

Private engine, public proof.
