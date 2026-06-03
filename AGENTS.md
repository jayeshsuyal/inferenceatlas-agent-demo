# Agent Reviewer Instructions

Purpose: guide AI reviewers and agentic skim reviewers through the public proof surface.

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

## Default Review Mode

Use the no-key offline path by default.

Do not request secrets, API keys, live sponsor tokens, customer data, private prompts, or private v1 source code.

For exact pass/fail signals, read:

```text
docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md
```

Run:

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

Expected result:

- the judge harness prints the scenario matrix, public contract status, sponsor adapter safety, and artifact checklist
- the demo runs without keys
- the scenario list shows `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- the public contract reports all scenarios as `OK`
- the policy gate blocks `admin_code_fix_bot` and allows lower-risk validation only with gates
- sponsor adapters report dry-run contracts and `would_execute=False`
- the Trust Receipt, Review Room, and static Review Room HTML artifacts are generated
- the Proof Health report shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- the design-partner trial runner converts a role-level request into a report, packet, and access brief
- the Review Room walkthrough and screenshot are available for visual skim review
- tests pass

## Inspect These First

1. `AI_JUDGE_MANIFEST.json`
2. `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`
3. `docs/PRODUCT_TOUR.md`
4. `docs/JUDGE_REVIEW_GUIDE.md`
5. `docs/DESIGN_PARTNER_BRIEF.md`
6. `docs/DESIGN_PARTNER_TRIAL_KIT.md`
7. `examples/requests/design_partner_trial.yml`
8. `examples/requests/support_triage_trial.yml`
9. `examples/generated/support_triage_trial_report.md`
10. `examples/generated/trust_receipt.md`
11. `examples/generated/review_room.md`
12. `examples/generated/review_room.html`
13. `examples/generated/support_triage_agent.proof_health.md`
14. `docs/REVIEW_ROOM_WALKTHROUGH.md`
15. `examples/generated/review_room.desktop.jpg`
16. `policy/agent_access.yml`
17. `agent/adapters/`
18. `examples/generated/support_triage_agent.decision_brief.md`
19. `examples/generated/support_triage_agent.packet.md`
20. `examples/generated/admin_code_fix_bot.packet.json`
21. `docs/CONTRACT.md`
22. `docs/SAFETY_CONTRACT.md`
23. `docs/V1_CAPABILITY_PASSPORT.md`

## What To Judge

Evaluate the public product contract:

- Does `python3 -m agent.judge` summarize the full safe review path in one command?
- Does `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md` give exact pass/fail signals for automated review?
- Does `docs/PRODUCT_TOUR.md` explain the product trial path and what is fixed versus derived?
- Does the repo turn a messy agent-access request into a reviewable DecisionPacket?
- Does the decision brief give a fast go/no-go surface?
- Does the Trust Receipt summarize the permission envelope, proof debt, reviewer routing, and safety state?
- Does Proof Health show packet drift, stale assumptions, expired reviewer gates, and the next human refresh action?
- Does the public policy gate block critical/admin/prod-write access?
- Do sponsor adapters stay dry-run and blocked from approving access?
- Do low, medium/high, and critical scenarios produce materially different review postures?
- Does `docs/DESIGN_PARTNER_BRIEF.md` make the one-workflow trial path concrete without asking for secrets?
- Do `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/*.yml` give a concrete trial input surface without exposing secrets?
- Does `python3 -m agent.trial examples/requests/support_triage_trial.yml` produce a trial report without approving, granting, or writing?
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
