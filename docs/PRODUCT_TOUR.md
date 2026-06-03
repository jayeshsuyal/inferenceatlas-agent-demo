# Product Tour

Status: public product evaluation path
Purpose: show judges, CTOs, Security leads, AI platform owners, and design partners how to evaluate InferenceAtlas as a product, not a one-off demo

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

Private engine, public proof.

## The Product Bet

AI agents are moving toward tools, data, spend, and production systems faster than internal approval paths can adapt.

InferenceAtlas is the pre-permission review layer. Before an agent gets access, it produces the proof packet a human approval process needs:

- what the agent is asking to touch
- what can move into scoped validation
- what stays blocked
- what proof is missing
- who owns each reviewer gate
- what the smallest safe validation step is
- whether sponsor/runtime/evidence layers remain dry-run and non-approving

The product moment is not an autonomous yes. The product moment is a faster, clearer, safer human review.

## Five-Minute Product Trial

Run this path from a clean checkout:

```bash
python3 -m agent.judge
python3 -m agent.proof_health
python3 -m agent.sponsor_readiness
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.review_room
python3 -m unittest discover -s tests
```

Or use the installed commands:

```bash
pip install -e .
ia-judge
ia-proof-health
ia-sponsor-readiness
ia-trial examples/requests/support_triage_trial.yml
ia-review-room
```

In five minutes, a reviewer should see:

- a judge harness that works without keys
- a role-level trial request converted into a report, packet, and access brief
- a sponsor live-readiness report showing where Nebius, Tavily, Composio, and OpenClaw add proof without approval power
- a Trust Receipt and Review Room that summarize blast radius, proof debt, reviewer routing, sponsor proof, and safety state
- a Proof Health report that shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- three risk postures: low-risk read-only, medium/high-risk proof-routed, and critical/admin blocked fast
- safety defaults that keep approvals, grants, writes, and production mutation off

## Product Surfaces

| Surface | What it proves |
| --- | --- |
| `python3 -m agent.judge` | One command assembles the public product trial path, artifact checklist, safety checks, and design-partner trial summary. |
| `python3 -m agent.sponsor_readiness` | Shows which sponsor tools are contract-ready for live enrichment and where their output appears without approving access. |
| `python3 -m agent.trial examples/requests/support_triage_trial.yml` | A role-level request becomes a trial report, DecisionPacket, and Agent Access Decision Brief. |
| `examples/generated/trust_receipt.md` | A skim-ready receipt joins scenario spread, permission envelope, proof debt, reviewer routing, sponsor proof, and safety state. |
| `examples/generated/review_room.html` | A static visual review room works without a web app, scripts, secrets, or external assets. |
| `examples/generated/support_triage_agent.proof_health.md` | Proof Health shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check before access expands. |
| `docs/CONTRACT.md` | The public proof contract is written down and validated by tests. |
| `policy/agent_access.yml` | Critical/admin/prod-write access is blocked by policy before validation. |

## What Is Fixed Versus Derived

This public repo is intentionally a redacted product harness. It includes fixed public fixtures so judges can reproduce the review path, and derived outputs so they can verify that the harness is not just prose.

| Fixed public fixture | Derived product behavior |
| --- | --- |
| Three public scenarios | Verdict, proof debt, reviewer routing, access-speed lane, and safety state are derived from structured request inputs. |
| Public trial request files | The trial runner derives a report, packet, and access brief from the request file. |
| Public lifecycle checkpoints | The Proof Health report derives packet drift status, stale assumptions, expired reviewer gates, and human refresh action from the existing packet and brief. |
| Sponsor readiness contracts | The readiness report derives provider value, visible outputs, CTO next steps, and safety boundaries from the adapter contracts. |
| Conservative safety defaults | The outputs preserve blocked approvals, blocked grants, blocked writes, dry-run sponsor posture, and human approval requirement. |
| Sponsor adapter contracts | Sponsor outputs enrich evidence, narration, permission diff, and runtime trace planning without approval power. |
| Public artifact paths | `python3 -m agent.judge` regenerates the public artifacts and checks that they exist. |

The important line is simple:

```text
fixed fixtures make review reproducible; derived outputs make the product claim testable
```

## Why This Is Not A Normal Agent Demo

Most agent demos optimize for action. InferenceAtlas optimizes for the missing gate before action.

Instead of showing an agent posting, changing, spending, deploying, or mutating, the public harness shows:

- the requested access envelope
- blocked claims before they become false confidence
- proof debt before it becomes shadow approval
- reviewer ownership before access moves
- dry-run sponsor participation before live integrations
- packet drift before stale access becomes hidden approval
- a safe next validation step before production access

That is the product stance: agent access should be reviewable before it is executable.

## Design Partner Shape

A strong first design partner brings one real agent-access workflow:

- one agent
- one business owner
- one set of requested tools
- one set of data classes
- one current approval path
- one Security, Engineering, Ops, Legal, or Finance reviewer who owns the risk

They should fill a role-level request shape, not upload secrets:

```text
examples/requests/design_partner_trial.yml
```

Then they compare the public trial output against their current approval path:

```text
examples/generated/support_triage_trial_report.md
examples/generated/support_triage_trial.packet.md
examples/generated/support_triage_trial.decision_brief.md
```

If the report makes risk, proof debt, and reviewer ownership clearer than their current process, the product is doing its job.

## Safety Boundary

This public harness does not approve access.

It does not:

- grant permissions
- execute external writes
- mutate production
- request secrets
- fetch customer data
- expose private prompts
- expose private v1 source code
- let sponsor integrations change the verdict

It does:

- produce a proof packet
- show packet drift and stale assumptions
- make missing proof visible
- route reviewers
- block unsupported claims
- preserve dry-run sponsor posture
- name the next human validation step

Private engine, public proof.
