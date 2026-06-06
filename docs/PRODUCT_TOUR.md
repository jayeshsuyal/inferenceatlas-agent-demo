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

## Lane Matrix

| Lane | Scenario fixtures | Generated artifacts |
| --- | --- | --- |
| Agent access review | `support_triage_agent` · `read_only_analytics_agent` · `admin_code_fix_bot` | DecisionPacket, access brief, Trust Receipt, Proof Health, Sponsor Proof Trace |
| AI spend review | `examples/requests/ai_spend_budget_overrun.yml` | spend packet, Finance Evidence Receipt, Procurement Review Memo, Sponsor Proof Trace |
| Supply-chain / CI review | `examples/requests/miasma_pre_permission_packet.yml` | DecisionPacket, proof debt, reviewer routing, Sponsor Proof Trace |
| MCP / tool blast-radius review | `examples/requests/mcp_tool_blast_radius.yml` | DecisionPacket, proof debt, reviewer routing, local verification hash |

## Five-Minute Product Trial

Run this path from a clean checkout:

```bash
bash scripts/run.sh
python3 -m agent.judge
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.outcome_memo
python3 -m agent.proof_health
python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write
python3 -m agent.sponsor_readiness
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.review_room
python3 -m agent.verify_artifacts
python3 -m unittest discover -s tests
```

Or use the installed commands:

```bash
pip install -e .
ia-judge
ia-skills
ia-packet-diff
ia-receipts
ia-outcome-memo
ia-proof-health
ia-spend examples/requests/ai_spend_budget_overrun.yml
ia-sponsor-readiness
ia-subscribers --json
ia-downstream-gate --all
ia-trial examples/requests/support_triage_trial.yml
ia-trial-outcome-memo examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
ia-review-room
ia-verify-artifacts
```

In five minutes, a reviewer should see:

- a judge harness that works without keys
- a Packet Workbench where a reviewer can choose a lane, generate a packet, copy a review brief, and view the local verification hash
- an Agent Skills registry showing 16 stable public review skills with commands, artifacts, dependencies, and safety boundaries
- a role-level trial request converted into a report, packet, access brief, meeting-ready outcome memo, sponsor evidence replay, and live evidence rehearsal
- a Packet Diff proving low, medium/high, and critical requests move differently
- an Evidence Receipt Ledger attaching tool scope, proof debt, reviewer routes, and cost/procurement controls without weakening the packet lock
- a Downstream Gate decision showing gateways, CI, spend controls, review queues, and observability consume the packet instead of raw agent intent
- a Packet Outcome Memo converting the support-triage packet into a human decision
- an AI Spend Review packet showing Finance/Procurement review before spend caps, vendor switches, or savings claims move
- a sponsor live-readiness report showing where Nebius, Tavily, Composio, and OpenClaw add proof without approval power
- a Trust Receipt and Review Room that summarize blast radius, proof debt, reviewer routing, sponsor proof, and safety state
- a Proof Health report that shows Packet Drift, stale assumptions, expired reviewer gates, and the next human health check
- an Artifact Integrity Gate proving deterministic proof artifacts match generator output, static review assets are valid, and no unexpected generated file is checked in
- three risk postures: low-risk read-only, medium/high-risk proof-routed, and critical/admin blocked fast
- safety defaults that keep approvals, grants, writes, and production mutation off

## Product Surfaces

| Surface | What it proves |
| --- | --- |
| `/workbench` | A reviewer can choose a lane and registered fixture, generate a packet, copy a review brief, export the result, and view a local hash without paste input or live writes. |
| `/api/workbench/generate` | The Workbench operates on existing deterministic packet builders and does not call private v1. |
| `bash scripts/run.sh` | One no-key public command for the default review path. |
| `python3 -m agent.judge` | One command assembles the public product trial path, artifact checklist, safety checks, and design-partner trial summary. |
| `docs/AGENT_SKILLS.md` | The public capability registry maps each agent review skill to proof, command, artifact, dependency, tier, and safety boundary. |
| `docs/PRODUCT_QUALITY_AUDIT.md` | The public proof surface has a premium spine and guardrails for fast iteration. |
| `examples/generated/packet_diff.md` | The packet engine relaxes, routes, and blocks across materially different risk levels. |
| `examples/generated/support_triage_agent.evidence_receipts.md` | Tool scope, missing proof, reviewer routes, and cost/procurement controls attach as receipts without approving access. |
| `examples/generated/support_triage_agent.outcome_memo.md` | The packet becomes a human decision: what can move, what stays blocked, who owns proof debt, and when to refresh. |
| `examples/requests/ai_spend_budget_overrun.yml` | A public role-level spend request fixture for Finance, Procurement, and AI Platform review. |
| `python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write` | A budget-overrun question becomes a Finance/Procurement review packet without approving spend, selecting a provider, or guaranteeing savings. |
| `docs/case_studies/MIASMA_PRE_PERMISSION_PACKET.md` | A public attack-vector case study framed as pre-permission proof, not detection or prevention. |
| `python3 -m agent.trial examples/requests/miasma_pre_permission_packet.yml --json` | A Miasma-inspired request fixture becomes a non-approving access review with reviewer routing and blocked claims. |
| `examples/requests/mcp_tool_blast_radius.yml` | A connector/tool blast-radius request becomes a non-approving packet with dry-run scope and named reviewers. |
| `python3 -m agent.verify_artifacts` | Regenerates deterministic artifacts into a temp directory and fails if outputs are stale, static assets are invalid, or extra generated files are checked in. |
| `python3 -m agent.sponsor_readiness` | Shows which sponsor tools are contract-ready for live enrichment and where their output appears without approving access. |
| `python3 -m agent.trial examples/requests/support_triage_trial.yml` | A role-level request becomes a trial report, DecisionPacket, and Agent Access Decision Brief. |
| `python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml` | The trial request becomes a meeting-ready decision: can-move scope, blocked scope, proof owners, and reviewer routes. |
| `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml` | Sponsor proof slots attach to the trial decision while approvals, grants, writes, and production mutation stay locked. |
| `python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial` | Sanitized sponsor outputs rehearse Tavily sources, Composio permission diffs, Nebius narration, and OpenClaw traces without changing the locked decision. |
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
| Agent Skills registry | Public capability claims are structured as registry entries with commands, artifacts, dependencies, and allowlisted safety boundaries. |
| Packet Diff | The three scenarios produce different load-bearing fields while production access and writes stay blocked. |
| Evidence Receipt Ledger | Receipt IDs attach to the Packet Authority Snapshot while each receipt remains context-only and human-reviewed. |
| Packet Outcome Memo | The selected packet becomes a CTO/security/design-partner decision surface without granting access. |
| Artifact Integrity Gate | Deterministic proof artifacts must remain byte-equal to the current generator output; static review assets must be present; generated inventory must not contain extras. |
| Public trial request files | The trial runner derives a report, packet, access brief, outcome memo, sponsor evidence replay, and live evidence rehearsal from the request file. |
| Public AI spend request file | The spend runner derives a Finance/Procurement review packet, evidence receipt, and procurement memo while preserving non-approval safety defaults. |
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
- packet diff before reviewers assume all scenarios are hardcoded alike
- outcome memo before a meeting ends without a decision
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
examples/generated/support_triage_trial.outcome_memo.md
examples/evidence/support_triage_trial/
examples/generated/support_triage_trial.evidence_replay.md
```

If the report, outcome memo, and evidence replay make risk, proof debt, reviewer ownership, sponsor proof, and the meeting decision clearer than their current process, the product is doing its job.

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
