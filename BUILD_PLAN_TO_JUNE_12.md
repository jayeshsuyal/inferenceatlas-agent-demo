# Build Plan To June 12

Status: public judge harness execution memo
Owners: founder + CTO
Target deadline: June 12, 2026, 23:59 PT

## One-Line Thesis

InferenceAtlas is the pre-permission DecisionPacket layer for AI agents: before an agent gets tools, data, spend, or production access, IA shows what can move, what stays blocked, whether the agent is eligible for this class of access, what proof is missing, who must review, and what validation comes next.

## Why This Repo Exists

The full InferenceAtlas v1 product remains private. This public repo is the redacted judge harness for the agent-access wedge.

The public harness should prove the product contract without exposing proprietary implementation code, private customer context, secrets, internal prompts, or the full v1 source tree.

Judges should be able to verify:

- the product thesis
- the agent-access DecisionPacket contract
- the Agent Access Decision Brief for fast go/no-go review
- deterministic sample outputs
- safety boundaries
- sponsor integration shape
- a working no-key demo path
- a live-mode path for Nebius, Tavily, Composio, and OpenClaw when keys are available

The public repo is not meant to be a code dump. It is meant to be a clean proof surface for a larger private system.

## What Judges Can Verify Today

Current public surface:

- README thesis for pre-commit proof packets
- sample DecisionPacket in `examples/sample_decision_packet.md`
- generated DecisionPacket artifacts under `examples/generated/`
- generated Agent Access Decision Brief artifacts under `examples/generated/`
- no-key demo transcript in `examples/generated/demo_transcript.md`
- Python agent package scaffold under `agent/`
- deterministic packet builder in `agent/packet.py`
- offline packet renderers in `agent/renderers.py`
- product-grade packet fields for source status, approval posture, tool access plan, and reviewer action items
- reviewer-grade access brief with go/no-go, risk register, reviewer gates, and runtime permission boundary
- CTO handoff docs in `docs/CTO_HANDOFF.md`, `docs/ARCHITECTURE.md`, and `docs/LIVE_INTEGRATION_CONTRACT.md`
- AI judge manifest in `AI_JUDGE_MANIFEST.json`
- safety contract in `docs/SAFETY_CONTRACT.md`
- Nebius/Tavily/Composio/OpenClaw integration direction
- explicit conservative safety stance: no autonomous approval, no production mutation, no real dispatch by default

Current top risk after the offline demo landed:

- add live sponsor evidence/tool planning and a short demo video without weakening the no-key safety path.

## What We Are Building By June 12

| Workstream | Outcome | Status |
| --- | --- | --- |
| Offline deterministic demo | `python3 -m agent.demo` generates a complete DecisionPacket with no API keys | Shipped |
| DecisionPacket schema | JSON schema for required packet fields and safety sections | Shipped |
| Markdown + JSON examples | Inspectable packet artifacts for judge and AI review | Shipped |
| V1 capability passport | Redacted map from private v1 capability families to public proof artifacts | Shipped |
| Safety contract | Enforced no-approval, no-dispatch, no-mutation defaults | Shipped |
| Judge review guide | Five-minute public review path with commands, artifacts, and private boundary | Shipped |
| Public conformance contract | Runnable public proof contract for packet and decision brief artifacts | Shipped |
| Agent Trust Receipt | One public control-plane artifact joining scenarios, proof debt, permission envelope, reviewer routing, sponsor runtime plan, and safety state | Shipped |
| Public policy gate | Policy-as-code gate that blocks critical/admin/prod-write access and allows lower-risk validation only with gates | Shipped |
| Dry-run sponsor adapters | Composio/Tavily/Nebius/OpenClaw adapter contracts with no keys, no writes, and no approval authority | Shipped |
| Static Review Room HTML | Serverless visual artifact generated from the Review Room JSON | Shipped |
| Review Room walkthrough | 60-90 second talk track plus checked-in screenshot for skim review and demo recording | Shipped |
| One-command judge harness | `python3 -m agent.judge` regenerates artifacts, validates contract/gate/adapters, and prints the artifact checklist | Shipped |
| Design partner brief | One-workflow CTO/platform-owner trial path with outputs, success criteria, and safety boundaries | Shipped |
| Design partner trial kit | Public fillable request template and support-triage sample for one-workflow trials | Shipped |
| README top-of-fold reframe | First screen says public agent-access review harness, private engine/public proof, judge command, contract status, and dry-run safety | Shipped |
| Tavily evidence mode | Optional live evidence notes with source URLs and freshness status | Planned |
| Agent Access Decision Brief | Concise go/no-go review artifact derived from the packet | Shipped |
| Composio dry-run access plan | Scoped GitHub/Slack/Jira tool-access plan with dry-run default | Shipped |
| CTO build handoff | Stable module map, transitional live scaffolding, and integration contract | Shipped |
| Nebius live narration | Optional live model path for reviewer-ready packet narration | Planned |
| OpenClaw runtime path | Optional runtime harness for agent loop and step recording | Planned |
| CI and tests | GitHub Actions verifies demo, packet shape, and safety defaults | Shipped |
| Demo transcript | Checked-in full judge path covering demo, scenarios, contract, gate, adapters, Trust Receipt, Review Room, walkthrough, and tests | Shipped |
| Short video/GIF | 60-90 second walkthrough for human reviewers | Planned |

## Definition Of Done

By June 12, the repo is judge-ready when all of the following are true:

- `python3 -m agent.demo` works without keys.
- README behavior matches actual behavior.
- README first screen frames the repo as a public agent-access review harness, not just a hackathon demo.
- A judge can understand the product in under five minutes.
- The main demo produces a DecisionPacket for GitHub/Slack/Jira agent access.
- The main demo produces an Agent Access Decision Brief that a judge can skim quickly.
- Packet output includes requested capability, tool/data scope, missing proof, blocked claims, reviewer owners, next validation, and safety footer.
- DecisionPacket examples exist in Markdown and JSON.
- Decision Brief examples exist in Markdown and JSON and distinguish pre-permission review from runtime permission prompts.
- Packet JSON validates against a checked-in schema.
- Decision Brief JSON validates against a checked-in schema.
- Trust Receipt and Review Room artifacts exist in Markdown and JSON.
- Static Review Room HTML exists and is generated from the same public review data.
- Review Room walkthrough and screenshot exist for skim review and demo recording.
- Trust Receipt covers blast-radius diff, permission envelope, proof debt ledger, reviewer routing, sponsor runtime plan, safety state, and private boundary.
- Public policy gate evaluates all scenarios and blocks `admin_code_fix_bot`.
- Sponsor adapters run without keys and report `would_execute=false`.
- One-command judge harness prints the scenario matrix, public contract status, sponsor adapter safety, and artifact checklist.
- Design Partner Brief explains the one-afternoon CTO/platform-owner trial without asking for secrets, writes, approvals, or private v1 source.
- Design Partner Trial Kit includes a public request template and sample with tool scope, data scope, proof debt, reviewer routing, safety defaults, and expected outputs.
- Composio is dry-run by default.
- No external write, approval, dispatch, or mutation happens in the default path.
- Unsupported compliance, readiness, savings, quality, latency, or access claims remain blocked.
- GitHub Actions is green.
- The repo clearly explains how private v1 capabilities are represented without exposing private code.
- The CTO can identify stable modules, transitional scaffolding, live integration contracts, and safety invariants without reverse-engineering the repo.

## Public Review Path

If a judge or AI reviewer opens this repo early, this is the intended review order:

1. `README.md`
2. `docs/JUDGE_REVIEW_GUIDE.md`
3. `python3 -m agent.judge`
4. `docs/DESIGN_PARTNER_BRIEF.md`
5. `docs/DESIGN_PARTNER_TRIAL_KIT.md`
6. `examples/requests/design_partner_trial.yml`
7. `examples/requests/support_triage_trial.yml`
8. `examples/generated/trust_receipt.md`
9. `examples/generated/review_room.md`
10. `examples/generated/review_room.html`
11. `docs/REVIEW_ROOM_WALKTHROUGH.md`
12. `examples/generated/review_room.desktop.jpg`
13. `policy/agent_access.yml`
14. `agent/adapters/`
15. `BUILD_PLAN_TO_JUNE_12.md`
16. `examples/generated/demo_transcript.md`
17. `examples/generated/support_triage_agent.decision_brief.md`
18. `examples/generated/support_triage_agent.packet.md`
19. `examples/generated/support_triage_agent.packet.json`
20. `examples/generated/support_triage_agent.trace.md`
21. `examples/sample_decision_packet.md`
22. `docs/CONTRACT.md`
23. `docs/V1_CAPABILITY_PASSPORT.md`
24. `docs/SAFETY_CONTRACT.md`
25. `python3 -m agent.demo`

The final repo should make this path obvious from the first screen.

## CTO Build Path

If the CTO opens the repo to continue implementation, this is the intended build order:

1. `docs/CTO_HANDOFF.md`
2. `docs/ARCHITECTURE.md`
3. `docs/LIVE_INTEGRATION_CONTRACT.md`
4. `agent/demo.py`
5. `agent/packet.py`
6. `agent/decision_brief.py`
7. `agent/runtime.py`
8. `agent/tools.py`
9. `tests/`

The CTO path should make three things obvious:

- what is stable and should be preserved
- what is transitional and needs refactor before the live demo
- how live sponsor integrations can enrich the packet flow without granting access or committing secrets

## Demo Scenario

Primary scenario:

```text
Should this support triage agent get GitHub, Slack, and Jira access?

It will read GitHub issues, summarize Slack incident channels, and create Jira draft tickets.
It may touch customer incident context, engineering bug reports, and support escalations.
```

Expected packet behavior:

- identify requested tools and data scope
- separate read access from write access
- block production access until reviewer ownership and proof exist
- explain that runtime permission prompts answer specific action approval while IA answers access-class eligibility and proof requirements
- require Security/Legal review for retention, logging, and customer data exposure
- require Engineering review for permission boundaries, rollback, and audit logs
- require Support Ops review for workflow fit and escalation ownership
- keep Composio actions dry-run by default
- produce one concrete next validation step

## Private V1 Capability Passport

The public harness should show the breadth of private v1 through redacted artifacts, contracts, and examples rather than full source.

| Private v1 capability family | Public proof artifact |
| --- | --- |
| Ask IA decision coach | Offline prompt-to-packet transcript |
| WorkloadProfile | Redacted sample JSON with source/provenance fields |
| FactPack | Deterministic evidence sample with assumptions and missing values |
| DecisionPacket | Markdown + JSON packet examples and schema |
| Agent Access Decision Brief | Markdown + JSON go/no-go artifact and schema |
| CTO build handoff | Stable module map, architecture, and live integration contract |
| ArtifactProjection | Same packet projected into judge packet, memo, and review handoff |
| Approval Watch / Evidence Watch | Evidence intake preview against an existing packet |
| Governance | Reviewer-owner map and proof-debt checklist |
| Living Document | Buyer-ready memo generated from the same packet |
| Route Evidence / audit trail | Redacted review queue and audit trail sample |
| TCO/tokenization/provider lanes | Redacted examples showing blocked claims when proof is incomplete |

The principle: private engine, public proof.

## Sponsor Integration Plan

Sponsor integrations should be part of the product behavior, not decorative API calls.

### Nebius

Use Nebius as the optional live inference layer for packet narration, reviewer-ready language, and final packet synthesis.

Offline mode must not depend on Nebius. Nebius enriches the packet; it does not own deterministic truth.

### Tavily

Use Tavily for live evidence notes: current vendor/security/context search, source URLs, and freshness status.

Tavily results should enter the packet as evidence notes, not as unverified final truth.

### Composio

Use Composio to model scoped tool-access requests for GitHub, Slack, and Jira.

Default behavior is dry-run. The public demo must not create tickets, post messages, change repos, or mutate external state.

### OpenClaw

Use OpenClaw as the optional runtime harness for the agent loop, step recording, tool use, and live-mode execution.

Offline deterministic mode remains the fallback path so judging does not depend on keys or network behavior.

## Safety Contract

InferenceAtlas prepares proof packets. Humans approve decisions.

IA does not:

- approve agent access
- grant tool permissions
- dispatch Slack/Jira/GitHub actions by default
- mutate production state
- certify compliance
- guarantee savings
- claim quality lift without eval evidence
- claim latency or capacity readiness without measurement
- claim procurement/security/legal approval without named review evidence

Default demo posture:

- dry-run external actions
- explicit blocked claims
- visible missing proof
- reviewer owners named separately from final approval
- next validation before production access

## CTO Operating Notes

Engineering priority order:

1. Make the no-key offline demo true.
2. Lock the DecisionPacket and Decision Brief schemas.
3. Add Markdown and JSON examples.
4. Add safety contract docs and tests.
5. Add V1 capability passport artifacts.
6. Add CTO handoff docs and integration contracts.
7. Add optional sponsor live paths.
8. Add CI and judge transcript.
9. Record the short demo.

Scope discipline:

- Do not broaden into a generic chatbot.
- Do not build a dashboard tour.
- Do not imply autonomous approval.
- Do not expose private v1 source.
- Do not overclaim compliance, savings, latency, quality, or procurement readiness.
- Do not make sponsor integrations decorative.

The first winning surface is one clear loop:

```text
messy agent-access request
-> WorkloadProfile-style context
-> FactPack-style evidence and missing proof
-> DecisionPacket
-> Agent Access Decision Brief
-> blocked claims
-> reviewer owners
-> next human validation
```

## Build Cadence

### Phase 1: Repo credibility

- fix offline no-key demo
- link this build plan from README
- make current behavior honest
- add first packet schema draft
- add basic tests

### Phase 2: Public proof artifacts

- add packet Markdown and JSON examples
- add decision brief Markdown and JSON examples
- add demo transcript
- add V1 capability passport
- add safety contract
- add CTO handoff and live integration contract
- add redacted private-v1-derived sample artifacts

### Phase 3: Sponsor depth

- add Tavily evidence notes
- add Nebius live narration path
- add Composio dry-run tool-access plan
- add OpenClaw runtime path
- document offline vs live behavior clearly

### Phase 4: Judge polish

- add GitHub Actions
- add `AI_JUDGE_MANIFEST.json`
- add screenshot or GIF
- add 60-90 second video link
- tag a release before the deadline

## Final Standard

The repo should make one thing obvious:

Most agent demos show an agent taking action. InferenceAtlas shows the missing review layer before action: the proof packet a company needs before giving agents tools, data, spend, or production access.

That is the product we are proving by June 12.
