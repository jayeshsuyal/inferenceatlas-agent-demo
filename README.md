# InferenceAtlas — Public Agent-Access Review Harness

Private engine, public proof.

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

![tests](https://img.shields.io/badge/tests-passing-brightgreen)
![CI](https://img.shields.io/badge/CI-smoke%20green-brightgreen)
![public contract](https://img.shields.io/badge/public%20contract-v0-blue)
![safety](https://img.shields.io/badge/safety-dry--run%20default-purple)

InferenceAtlas is a public, no-key review harness for the private InferenceAtlas v1 product. Before an AI agent receives tools, data, spend, or production permissions, IA prepares the Trust Receipt, DecisionPacket, access brief, policy-gate result, Proof Health report, proof debt, reviewer routing, and next validation plan humans need to review.

This repo is the Hack the High Seas public proof surface. It is not a private v1 code dump.

Start with the product tour: [Product Tour](docs/PRODUCT_TOUR.md).

Then run the full public judge path:

```bash
python3 -m agent.judge
```

Run the design-partner trial sample:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
```

Install the public harness commands:

```bash
pip install -e .
ia-judge
```

## Judge Fast Path

If you are reviewing quickly, start with the [Product Tour](docs/PRODUCT_TOUR.md), then use the [Judge Review Guide](docs/JUDGE_REVIEW_GUIDE.md). If you are evaluating product quality under fast iteration, read the [Product Quality Audit](docs/PRODUCT_QUALITY_AUDIT.md). If you are evaluating design-partner fit, read the [Design Partner Brief](docs/DESIGN_PARTNER_BRIEF.md). If you are using an AI reviewer or coding agent, start with [Agent Reviewer Instructions](AGENTS.md) and [Agentic Review Expected Output](docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md).

Then run:

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.sponsor_readiness
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m unittest discover -s tests
```

Or use the installed command set:

```bash
pip install -e .
ia-judge
ia-review --list
ia-contract --all
ia-gate --all
ia-adapters --all
ia-sponsor-readiness
ia-trust
ia-review-room
ia-proof-health
ia-trial examples/requests/support_triage_trial.yml
```

The fastest artifact to skim is the generated Trust Receipt:

```text
examples/generated/trust_receipt.md
```

The fastest sponsor-tool artifact is the Sponsor Live Readiness report:

```text
examples/generated/sponsor_live_readiness.md
```

The fastest visual artifact to skim is the static Review Room:

```text
examples/generated/review_room.html
```

The fastest lifecycle artifact is the generated Proof Health report:

```text
examples/generated/support_triage_agent.proof_health.md
```

The fastest product-quality guardrail is:

```text
docs/PRODUCT_QUALITY_AUDIT.md
```

The fastest walkthrough artifact is:

```text
docs/REVIEW_ROOM_WALKTHROUGH.md
examples/generated/review_room.desktop.jpg
```

The fastest scenario-specific artifact is the generated access brief:

```text
examples/generated/support_triage_agent.decision_brief.md
```

The fastest product-trial artifact is:

```text
examples/generated/support_triage_trial_report.md
```

Start here for the public execution plan: [Build Plan To June 12](BUILD_PLAN_TO_JUNE_12.md).

For AI judges and fast repo review, see [AI Judge Manifest](AI_JUDGE_MANIFEST.json), [Agent Reviewer Instructions](AGENTS.md), [Agentic Review Expected Output](docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md), [Product Tour](docs/PRODUCT_TOUR.md), [Product Quality Audit](docs/PRODUCT_QUALITY_AUDIT.md), [Judge Review Guide](docs/JUDGE_REVIEW_GUIDE.md), [Design Partner Brief](docs/DESIGN_PARTNER_BRIEF.md), [Public Conformance Contract](docs/CONTRACT.md), [Safety Contract](docs/SAFETY_CONTRACT.md), and [V1 Capability Passport](docs/V1_CAPABILITY_PASSPORT.md).

For CTO/build handoff, start with [CTO Handoff](docs/CTO_HANDOFF.md), then [Architecture](docs/ARCHITECTURE.md), then [Live Integration Contract](docs/LIVE_INTEGRATION_CONTRACT.md).

Before an agent gets tool access, data access, spend, or production permissions, IA creates a DecisionPacket, Agent Access Decision Brief, Trust Receipt, and Proof Health report showing:

- source status
- scenario blast-radius diff
- approval posture
- access eligibility go/no-go
- permission envelope
- requested capability
- tool access plan
- tool and data scope
- risk register
- proof debt ledger
- packet drift signals
- missing proof
- blocked claims
- reviewer owners
- reviewer action items
- next human validation
- safety state

IA does not auto-approve, dispatch, or mutate state. It prepares the proof packet, access brief, Trust Receipt, and Proof Health report humans review.

## Why This Matters

Agents can now touch tools, data, spend, and production systems faster than internal review processes can keep up.

The demo asks a simple question:

```text
Should this agent get GitHub, Slack, and Jira access?
```

Instead of granting access, IA builds a reviewable packet and a concise access brief:

```text
what can move
what stays blocked
which tool actions are dry-run only
whether the agent is eligible for this class of access
what proof is missing
who needs to review
what the next validation should be
```

## Access Speed Layer

The packet is generated automatically, so it should speed review instead of creating paperwork. IA routes each access request immediately:

- low-risk read-only requests enter a fast-lane scoped validation path
- medium/high-risk requests keep scoped validation moving while proof debt routes to named owners
- critical/admin/prod-write requests are blocked fast with exact reviewer gates

The visible proof is in `examples/generated/trust_receipt.json`, `examples/generated/review_room.md`, and `examples/generated/review_room.html`.

## Agent Stack

- Nebius: OpenAI-compatible inference backbone
- Tavily: live search for current vendor/security/context evidence
- Composio: integration action layer, dry-run by default
- OpenClaw: optional agent runtime, with a built-in fallback loop

## Sponsor Proof Pack

InferenceAtlas uses sponsor integrations as proof contributors, not approval authorities:

- Tavily: evidence candidate plan with freshness and source slots
- Composio: permission diff for allowed validation actions, blocked actions, and required proof
- Nebius: reviewer-ready narration contract with verdict and safety fields locked
- OpenClaw: runtime trace plan for attempted steps, policy decisions, and blocked outcomes

The Sponsor Live Readiness report shows where live Nebius, Tavily, Composio, and OpenClaw work would appear once keys are supplied by the CTO:

```bash
python3 -m agent.sponsor_readiness
```

Every sponsor path remains dry-run, non-approving, non-mutating, and human-reviewed by default.

## Demo Flow

```text
User asks whether an AI agent should receive tool access.
-> IA gathers context and optional live evidence.
-> IA creates a DecisionPacket and Agent Access Decision Brief.
-> IA blocks unsupported approval/access claims.
-> IA names reviewer owners and one next human validation.
```

## Run Locally

```bash
cd inferenceatlas-agent-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python3 -m agent.demo
```

The default demo runs without keys using deterministic local packet generation. It prints a DecisionPacket and writes review artifacts under `examples/generated/`.

For live sponsor mode or the local web UI, install the optional dependencies:

```bash
pip install -e ".[live,web]"
```

For the one-command judge harness, run:

```bash
python3 -m agent.judge
```

This regenerates the offline public proof artifacts, validates the public contract, evaluates the policy gate, summarizes dry-run sponsor adapters, and prints the artifact checklist.

For the design-partner trial path, read:

```text
docs/DESIGN_PARTNER_BRIEF.md
docs/DESIGN_PARTNER_TRIAL_KIT.md
examples/requests/design_partner_trial.yml
examples/requests/support_triage_trial.yml
```

It defines the one-afternoon CTO/platform-owner evaluation: bring one real agent-access workflow, use the public request template, produce the review packet, compare against the current approval path, and keep secrets, writes, approvals, and private v1 source out of the public repo.

Run the public trial sample:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial examples/requests/support_triage_trial.yml --write
```

Or use the installed command:

```bash
ia-trial examples/requests/support_triage_trial.yml
```

The runner writes a design-partner trial report plus derived packet and brief artifacts under `examples/generated/`.

To exercise the live sponsor path, add Nebius/Tavily/Composio keys and run:

```bash
IA_LIVE_MODE=1 python3 -m agent.demo
```

## Interactive Paths

### Web UI (custom questions)

```bash
python -m web
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) to chat with the agent, use example prompts, or type your own requests. Conversations are multi-turn per browser session.

### CLI

```bash
python -m agent.cli "Compare llm providers for 70B inference"
```

## Scenario Proof

The rules engine now covers three deterministic access-review scenarios:

| Scenario | What it proves |
| --- | --- |
| `support_triage_agent` | Medium/high-risk support workflow gets scoped validation while production access remains blocked. |
| `read_only_analytics_agent` | Read-only aggregate analytics scope gets a lighter validation path and fewer reviewer gates. |
| `admin_code_fix_bot` | Admin/prod-write scope is blocked before validation and escalated to Security/Engineering. |

Regenerate packet and brief artifacts for all scenarios:

```bash
python3 -m agent.judge
python3 -m agent.scenarios
```

Review any scenario directly from the CLI:

```bash
python3 -m agent.review --list
python3 -m agent.review --scenario read_only_analytics_agent
python3 -m agent.review --scenario admin_code_fix_bot --artifact packet --format json
```

Validate the public conformance contract:

```bash
python3 -m agent.contract --all
python3 -m agent.contract --all --generated-dir examples/generated
```

Evaluate scenarios against the public policy gate:

```bash
python3 -m agent.gate --all
python3 -m agent.gate --scenario admin_code_fix_bot
python3 -m agent.gate --scenario admin_code_fix_bot --json
```

Render dry-run sponsor adapter contracts:

```bash
python3 -m agent.adapters --all
python3 -m agent.adapters --provider composio --scenario admin_code_fix_bot --json
python3 -m agent.sponsor_readiness
```

Generate the Agent Trust Receipt and Review Room:

```bash
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.proof_health
```

This writes:

```text
examples/generated/trust_receipt.md
examples/generated/trust_receipt.json
examples/generated/sponsor_live_readiness.md
examples/generated/sponsor_live_readiness.json
examples/generated/review_room.md
examples/generated/review_room.json
examples/generated/review_room.html
examples/generated/support_triage_agent.proof_health.md
examples/generated/support_triage_agent.proof_health.json
```

Run the design-partner trial sample:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial examples/requests/support_triage_trial.yml --write
```

This writes:

```text
examples/generated/support_triage_trial_report.md
examples/generated/support_triage_trial_report.json
examples/generated/support_triage_trial.packet.md
examples/generated/support_triage_trial.packet.json
examples/generated/support_triage_trial.decision_brief.md
examples/generated/support_triage_trial.decision_brief.json
```

Review the 60-90 second walkthrough script and checked-in screenshot:

```text
docs/REVIEW_ROOM_WALKTHROUGH.md
examples/generated/review_room.desktop.jpg
```

## Builder / CTO Path

If you are extending the live sponsor path, use this order:

```text
docs/CTO_HANDOFF.md
docs/ARCHITECTURE.md
docs/LIVE_INTEGRATION_CONTRACT.md
agent/demo.py
agent/packet.py
agent/decision_brief.py
agent/adapters/
tests/
```

The current no-key demo and generated artifacts are the safety baseline. Live Nebius, Tavily, Composio, and OpenClaw work should enrich the packet flow without weakening blocked production access, dry-run Composio, or no-key execution.

## Example

See:

```text
examples/sample_decision_packet.md
examples/generated/support_triage_agent.packet.md
examples/generated/support_triage_agent.packet.json
examples/generated/support_triage_agent.decision_brief.md
examples/generated/support_triage_agent.decision_brief.json
examples/generated/read_only_analytics_agent.packet.md
examples/generated/read_only_analytics_agent.packet.json
examples/generated/read_only_analytics_agent.decision_brief.md
examples/generated/read_only_analytics_agent.decision_brief.json
examples/generated/admin_code_fix_bot.packet.md
examples/generated/admin_code_fix_bot.packet.json
examples/generated/admin_code_fix_bot.decision_brief.md
examples/generated/admin_code_fix_bot.decision_brief.json
examples/generated/trust_receipt.md
examples/generated/trust_receipt.json
examples/generated/sponsor_live_readiness.md
examples/generated/sponsor_live_readiness.json
examples/generated/review_room.md
examples/generated/review_room.json
examples/generated/review_room.html
examples/generated/support_triage_agent.proof_health.md
examples/generated/support_triage_agent.proof_health.json
examples/generated/review_room.desktop.jpg
docs/REVIEW_ROOM_WALKTHROUGH.md
policy/agent_access.yml
examples/generated/support_triage_agent.trace.md
examples/generated/support_triage_agent.trace.json
examples/generated/demo_transcript.md
```

## Safety Contract

See the full [Safety Contract](docs/SAFETY_CONTRACT.md). This public demo is intentionally conservative:

- no autonomous approval
- no real dispatch by default
- no packet state mutation
- no fake compliance/savings/readiness claims
- Composio actions are dry-run unless explicitly changed
- production access is blocked in both the packet and decision brief

Humans approve decisions. IA prepares the proof.

## Roadmap Before June 12

- add live evidence mode without weakening offline safety
- add sponsor integration notes for CTO live setup
- add optional live Tavily evidence notes
- add a short demo video
- add judge polish: release tag and demo recording

This repo is a public hackathon wrapper. The private InferenceAtlas v1 product codebase is not exposed here.
