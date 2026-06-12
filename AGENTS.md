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
bash scripts/run.sh
bash scripts/pr_smoke.sh
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.evidence_receipts
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
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.verify_artifacts
python3 -m unittest discover -s tests
```

Expected result:

- the PR smoke gate completes with no keys, no live mode, no secret-shaped tracked tokens, and no default writes
- the judge harness prints the scenario matrix, public contract status, sponsor adapter safety, and artifact checklist
- the demo runs without keys
- the scenario list shows `support_triage_agent`, `read_only_analytics_agent`, and `admin_code_fix_bot`
- the Agent Skills registry reports `17 / 17 stable skills available`
- Packet Diff shows relaxed read-only, proof-routed scoped validation, and blocked critical lanes
- Evidence Receipt Ledger attaches tool scope, proof debt, reviewer routes, and cost/procurement controls without changing the packet lock
- Packet Outcome Memo converts the support-triage packet into a scoped-validation human decision
- the public contract reports all scenarios as `OK`
- the policy gate blocks `admin_code_fix_bot` and allows lower-risk validation only with gates
- sponsor adapters report dry-run contracts and `would_execute=False`
- sponsor live readiness reports all contracts ready, all non-executing, and all non-approving
- the Trust Receipt, Review Room, and static Review Room HTML artifacts are generated
- the Proof Health report shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- the design-partner trial runner converts a role-level request into a report, packet, and access brief
- the Design Partner Outcome Memo converts the trial request into a meeting-ready can-move/stays-blocked decision
- the Sponsor Evidence Replay attaches Tavily, Composio, Nebius, and OpenClaw proof slots without changing the decision
- Live Evidence Rehearsal accepts sanitized sponsor outputs while keeping approvals, grants, writes, and decision changes blocked
- the Product Quality Audit names the premium spine and safety guardrails
- Artifact Integrity Gate reports deterministic proof artifacts as fresh, static review assets as valid, and no unexpected generated file as checked in
- the Review Room walkthrough and screenshot are available for visual skim review
- tests pass

## Inspect These First

1. `AI_JUDGE_MANIFEST.json`
2. `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`
3. `docs/PRODUCT_TOUR.md`
4. `docs/AGENT_SKILLS.md`
5. `docs/PRODUCT_QUALITY_AUDIT.md`
6. `docs/JUDGE_REVIEW_GUIDE.md`
7. `docs/DESIGN_PARTNER_BRIEF.md`
8. `docs/DESIGN_PARTNER_TRIAL_KIT.md`
9. `examples/requests/design_partner_trial.yml`
10. `examples/requests/support_triage_trial.yml`
11. `examples/generated/support_triage_trial_report.md`
12. `examples/generated/support_triage_trial.outcome_memo.md`
13. `examples/generated/support_triage_trial.evidence_replay.md`
14. `examples/evidence/support_triage_trial/`
15. `examples/generated/trust_receipt.md`
16. `examples/generated/packet_diff.md`
17. `examples/generated/support_triage_agent.evidence_receipts.md`
18. `examples/generated/support_triage_agent.outcome_memo.md`
19. `examples/generated/sponsor_live_readiness.md`
20. `examples/generated/review_room.md`
21. `examples/generated/review_room.html`
22. `examples/generated/support_triage_agent.proof_health.md`
23. `docs/REVIEW_ROOM_WALKTHROUGH.md`
24. `examples/generated/review_room.desktop.jpg`
25. `policy/agent_access.yml`
26. `agent/adapters/`
27. `examples/generated/support_triage_agent.decision_brief.md`
28. `examples/generated/support_triage_agent.packet.md`
29. `examples/generated/admin_code_fix_bot.packet.json`
30. `docs/CONTRACT.md`
31. `docs/SAFETY_CONTRACT.md`
32. `docs/V1_CAPABILITY_PASSPORT.md`

## What To Judge

Evaluate the public product contract:

- Does `bash scripts/run.sh` summarize the full safe review path in one no-key command?
- Does `python3 -m agent.judge` remain available as the direct judge harness?
- Does `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md` give exact pass/fail signals for automated review?
- Does `docs/PRODUCT_TOUR.md` explain the product trial path and what is fixed versus derived?
- Does `docs/AGENT_SKILLS.md` map public agent skills to commands, artifacts, dependencies, and safety boundaries?
- Does `docs/PRODUCT_QUALITY_AUDIT.md` keep the public product spine coherent under fast iteration?
- Does the repo turn a messy agent-access request into a reviewable DecisionPacket?
- Does `examples/generated/packet_diff.md` prove the packet bends across low, medium/high, and critical access?
- Does `python3 -m agent.evidence_receipts` attach receipts without approving access or weakening the decision lock?
- Does `examples/generated/support_triage_agent.outcome_memo.md` turn the packet into a clear human decision?
- Does `python3 -m agent.verify_artifacts` prove deterministic proof artifacts are fresh and no unexpected generated file is checked in?
- Does the decision brief give a fast go/no-go surface?
- Does the Trust Receipt summarize the permission envelope, proof debt, reviewer routing, and safety state?
- Does Proof Health show packet drift, stale assumptions, expired reviewer gates, and the next human refresh action?
- Does the public policy gate block critical/admin/prod-write access?
- Do sponsor adapters stay dry-run and blocked from approving access?
- Does Sponsor Live Readiness show where Nebius, Tavily, Composio, and OpenClaw add proof without approval power?
- Do low, medium/high, and critical scenarios produce materially different review postures?
- Does `docs/DESIGN_PARTNER_BRIEF.md` make the one-workflow trial path concrete without asking for secrets?
- Do `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/*.yml` give a concrete trial input surface without exposing secrets?
- Does `python3 -m agent.trial examples/requests/support_triage_trial.yml` produce a trial report without approving, granting, or writing?
- Does `python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml` turn the trial into a meeting decision without approving, granting, or writing?
- Does `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml` attach sponsor proof without approving, granting, writing, or changing the decision?
- Does `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial` rehearse redacted sponsor evidence without changing the decision?
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
