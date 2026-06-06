# Design Partner Brief

Status: public design-partner trial brief
Purpose: show how a CTO, Security lead, or AI platform owner can evaluate InferenceAtlas on one real agent-access workflow without secrets, writes, approvals, or private v1 source exposure

Private engine, public proof.

## Trial Thesis

InferenceAtlas should be evaluated before an agent receives tools, data, spend, or production permissions.

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

The design-partner question is:

```text
Can IA turn one messy agent-access request into a reviewable Trust Receipt, DecisionPacket, access brief, Design Partner Outcome Memo, Sponsor Evidence Replay, Proof Health report, policy-gate result, and next validation plan that Security, Engineering, Legal, Ops, and Finance can actually act on?
```

The public repo proves the contract. A design partner validates the workflow on real internal access requests.

For the fillable request shape, use `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml`.

## Best-Fit Design Partner

The strongest trial partner is a team that is about to give an AI agent access to internal tools or sensitive operating data.

Good first workflows:

- support or incident triage agent requesting GitHub, Slack, Jira, ticketing, or customer-context access
- analytics agent requesting read-only warehouse, dashboard, or metric access
- code-fix or deployment assistant requesting repo, CI, production, admin, or rollback-adjacent access

The first trial should use one workflow, not every agent in the company.

## One-Afternoon Trial

Use this sequence for a first CTO or platform-owner evaluation:

1. Run the public judge harness:

```bash
bash scripts/run.sh
python3 -m agent.judge
```

2. Skim the high-signal artifacts:

```text
examples/generated/trust_receipt.md
examples/generated/packet_diff.md
examples/generated/support_triage_agent.outcome_memo.md
examples/generated/sponsor_live_readiness.md
examples/generated/review_room.html
examples/generated/support_triage_agent.proof_health.md
examples/generated/support_triage_trial_report.md
examples/generated/support_triage_trial.outcome_memo.md
examples/evidence/support_triage_trial/
examples/generated/support_triage_trial.evidence_replay.md
examples/generated/support_triage_agent.decision_brief.md
policy/agent_access.yml
docs/REVIEW_ROOM_WALKTHROUGH.md
```

3. Open the public request kit:

```text
docs/DESIGN_PARTNER_TRIAL_KIT.md
examples/requests/design_partner_trial.yml
examples/requests/support_triage_trial.yml
```

4. Run the public trial sample:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
```

5. Pick one real internal agent-access workflow and map it into the same review questions:

- What tools does the agent want?
- What data classes can it touch?
- What actions are read-only, draft-only, write-capable, admin, or production-adjacent?
- What proof is missing?
- Which reviewer owners must sign off?
- What validation can happen before production access?

6. Compare IA output against the current internal approval path:

- Does the Trust Receipt make blast radius visible faster?
- Does Packet Diff prove lower-risk and critical requests move differently?
- Does the Packet Outcome Memo make the meeting decision obvious?
- Does the Design Partner Outcome Memo make the trial decision obvious?
- Does Sponsor Evidence Replay show where Tavily, Composio, Nebius, and OpenClaw proof attaches without taking over?
- Does Live Evidence Rehearsal accept sanitized sponsor outputs without changing the decision?
- Does the access brief give a clearer go/no-go?
- Does the policy gate block the right class of access?
- Does reviewer routing remove ambiguity?
- Does proof debt become concrete owner work?
- Does Proof Health show when stale assumptions and reviewer gates need refresh?
- Does the sponsor adapter plan stay dry-run and non-approving?
- Does Sponsor Live Readiness show where live proof can appear without requiring a live write?

## Trial Outputs

A successful trial should produce:

- one Trust Receipt for the selected workflow
- one DecisionPacket with tool scope, data scope, missing proof, blocked claims, reviewers, and safety state
- one Agent Access Decision Brief for fast review
- one Packet Diff showing how the review posture changes across risk levels
- one Packet Outcome Memo naming what can move, what stays blocked, proof owners, and refresh timing
- one Design Partner Outcome Memo turning the trial request into can-move scope, blocked scope, proof owners, and reviewer routes
- one Sponsor Evidence Replay showing where sponsor proof attaches to proof owners while the decision stays locked
- one Live Evidence Rehearsal showing redacted provider outputs can attach safely
- one Proof Health report showing Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- one Design Partner Trial Report that shows request readiness, access-speed lane, proof debt, and safety boundary
- one policy-gate result explaining what can move and what stays blocked
- one dry-run tool-access plan for the relevant integration layer
- one sponsor live-readiness report showing which live proof hooks are ready and still non-approving
- one next human validation step

The output is not an approval. It is the proof packet a human approval process can review.

## Success Criteria

The trial is working if the partner can answer these questions faster than their current process:

- Should this agent be eligible for this class of access?
- What must stay blocked before validation?
- Which proof is missing?
- Which team owns each review item?
- What is the smallest safe validation step?
- Which claims are unsupported and should not be repeated?
- Which external actions remain dry-run?

The trial is not successful because the answer is always yes. It is successful when risky access gets slowed down for the right reasons and low-risk validation can move with visible gates.

## Non-Negotiable Safety Boundary

The public harness and first design-partner trial should not ask for:

- production credentials
- live sponsor tokens
- customer data in this public repo
- private prompts
- private v1 source code
- account-specific permission grants
- write-enabled Composio actions
- autonomous approval authority

Default posture:

- no access approval
- no permission grant
- no external write
- no production mutation
- no packet state mutation
- Composio dry-run by default
- human approval remains required

## What The CTO Can Build On

The current public branch gives a builder enough structure to extend a live trial safely:

| Need | Public surface |
| --- | --- |
| One-command review path | `bash scripts/run.sh` |
| Direct judge harness | `python3 -m agent.judge` |
| Trial meeting decision | `python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml` |
| Trial sponsor proof replay | `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml` |
| Trial live evidence rehearsal | `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial` |
| Product contract | `docs/CONTRACT.md` |
| Safety contract | `docs/SAFETY_CONTRACT.md` |
| Live integration boundary | `docs/LIVE_INTEGRATION_CONTRACT.md` |
| Sponsor adapter shape | `agent/adapters/` and `python3 -m agent.adapters --all` |
| Policy gate | `policy/agent_access.yml` and `python3 -m agent.gate --all` |
| CTO implementation map | `docs/CTO_HANDOFF.md` and `docs/ARCHITECTURE.md` |
| Demo talk track | `docs/REVIEW_ROOM_WALKTHROUGH.md` |

The CTO can add live Nebius, Tavily, Composio, or OpenClaw enrichment without changing the safety authority: deterministic packet, policy gate, blocked claims, proof debt, and human approval remain the review spine.

## Design Partner Ask

Bring one real agent-access request and one reviewer who owns the risk.

Do not start with a broad platform rollout. Start with a single agent where the current approval path is slow, ambiguous, or too informal for the access being requested.

Use the public template for the first pass:

```text
examples/requests/design_partner_trial.yml
```

The strongest first partner meeting ends with this decision:

```text
Move this agent into scoped validation, keep these capabilities blocked, and assign this proof debt to named owners.
```

That is the product moment.
