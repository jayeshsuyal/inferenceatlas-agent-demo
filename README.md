# InferenceAtlas — Public Agent-Access Review Harness

Private engine, public proof.

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

![tests](https://img.shields.io/badge/tests-passing-brightgreen)
![CI](https://img.shields.io/badge/CI-smoke%20green-brightgreen)
![public contract](https://img.shields.io/badge/public%20contract-v0-blue)
![safety](https://img.shields.io/badge/safety-dry--run%20default-purple)

InferenceAtlas is a public, no-key review harness for the private InferenceAtlas v1 product. Before an AI agent receives tools, data, spend, or production permissions, IA prepares the Trust Receipt, DecisionPacket, Packet Diff, Evidence Receipt Ledger, Packet Outcome Memo, Design Partner Outcome Memo, Sponsor Evidence Replay, access brief, policy-gate result, Proof Health report, proof debt, reviewer routing, cost controls, and next validation plan humans need to review.

This repo is the Hack the High Seas public proof surface. It is not a private v1 code dump.

Start with the product tour: [Product Tour](docs/PRODUCT_TOUR.md). For the capability map, read [Agent Skills](docs/AGENT_SKILLS.md).

Then run the full public judge path:

```bash
python3 -m agent.judge
```

Run the design-partner trial sample:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
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
python3 -m agent.skills
python3 -m agent.packet_diff
python3 -m agent.evidence_receipts
python3 -m agent.packet_authority
python3 -m agent.verification --all
python3 -m agent.subscribers --json
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

For the PR-grade local safety gate, run:

```bash
bash scripts/pr_smoke.sh
```

Or use the installed command set:

```bash
pip install -e .
ia-judge
ia-review --list
ia-skills
ia-packet-diff
ia-receipts
ia-snapshot
ia-verify --all
ia-subscribers --json
ia-outcome-memo
ia-contract --all
ia-gate --all
ia-adapters --all
ia-sponsor-readiness
ia-trust
ia-review-room
ia-proof-health
ia-trial examples/requests/support_triage_trial.yml
ia-trial-outcome-memo examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
ia-verify-artifacts
```

The fastest artifact to skim is the generated Trust Receipt:

```text
examples/generated/trust_receipt.md
```

The fastest capability map is:

```text
docs/AGENT_SKILLS.md
```

The fastest proof that the packet bends across risk levels is:

```text
examples/generated/packet_diff.md
```

The fastest human decision artifact is:

```text
examples/generated/support_triage_agent.outcome_memo.md
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

The fastest design-partner meeting-decision artifact is:

```text
examples/generated/support_triage_trial.outcome_memo.md
```

The fastest proof that sponsor tools attach evidence without taking over the decision is:

```text
examples/generated/support_triage_trial.evidence_replay.md
```

The fastest proof that redacted sponsor outputs can be rehearsed safely is:

```bash
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
```

The fastest proof that deterministic proof artifacts are fresh, static review assets are valid, and no unexpected generated file is checked in is:

```bash
python3 -m agent.verify_artifacts
```

Start here for the public execution plan: [Build Plan To June 12](BUILD_PLAN_TO_JUNE_12.md).

For AI judges and fast repo review, see [AI Judge Manifest](AI_JUDGE_MANIFEST.json), [Agent Reviewer Instructions](AGENTS.md), [Agentic Review Expected Output](docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md), [Product Tour](docs/PRODUCT_TOUR.md), [Agent Skills](docs/AGENT_SKILLS.md), [Product Quality Audit](docs/PRODUCT_QUALITY_AUDIT.md), [Judge Review Guide](docs/JUDGE_REVIEW_GUIDE.md), [Design Partner Brief](docs/DESIGN_PARTNER_BRIEF.md), [Public Conformance Contract](docs/CONTRACT.md), [Safety Contract](docs/SAFETY_CONTRACT.md), and [V1 Capability Passport](docs/V1_CAPABILITY_PASSPORT.md).

For CTO/build handoff, start with [CTO Handoff](docs/CTO_HANDOFF.md), then [Architecture](docs/ARCHITECTURE.md), then [Live Integration Contract](docs/LIVE_INTEGRATION_CONTRACT.md).

Before an agent gets tool access, data access, spend, or production permissions, IA creates a DecisionPacket, Agent Access Decision Brief, Trust Receipt, Packet Diff, Evidence Receipt Ledger, Packet Outcome Memo, Design Partner Outcome Memo, Sponsor Evidence Replay, and Proof Health report showing:

- source status
- scenario blast-radius diff
- approval posture
- access eligibility go/no-go
- agent skills registry
- risk-level packet diff
- packet outcome memo
- design-partner outcome memo
- sponsor evidence replay
- artifact integrity status
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

IA does not auto-approve, dispatch, or mutate state. It prepares the proof packet, evidence receipts, access brief, Trust Receipt, Packet Diff, Packet Outcome Memo, and Proof Health report humans review.

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
-> IA compares packet outcomes across risk levels.
-> IA converts the selected packet into a human outcome memo.
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
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
python3 -m agent.trial examples/requests/support_triage_trial.yml --write
```

Or use the installed command:

```bash
ia-trial examples/requests/support_triage_trial.yml
ia-trial-outcome-memo examples/requests/support_triage_trial.yml
ia-trial-evidence-replay examples/requests/support_triage_trial.yml
```

The runner writes a design-partner trial report plus derived packet, brief, outcome memo, and sponsor evidence replay artifacts under `examples/generated/`.

To exercise the live sponsor path, add Nebius/Tavily/Composio keys and run:

```bash
IA_LIVE_MODE=1 python3 -m agent.demo
```

## Mind runtime (state-transition engine)

The Mind runtime treats **DecisionPacket state** as the primary artifact: `Mind(t+1) = F(Mind(t))`. Chat is optional; the process can advance without user input.

```bash
python3 -m agent.mind init
python3 -m agent.mind step
python3 -m agent.mind run          # continuous loop (Ctrl-C to stop)
python3 -m agent.mind e2e          # offline validation for all 3 scenarios
python3 -m agent.mind project      # write examples/mind_runtime/
```

State persists under `state/mind/` (gitignored). The cortex (LLM) may append `evidence_notes` only; verdict and `safety_state` stay locked. Run `python -m agent.mind run` in one terminal and `python -m web` in another to see live mind ticks in the UI.

## Hackathon web harness (what this branch adds)

The public repo remains an **agent-access review harness**; the web UI now also supports a **unified cost + evidence chat** for live demos. Summary of what landed vs `main`:

| Area | What you get |
| --- | --- |
| **Unified chat** | One prompt merges Skills, GitHub repo digests, Google Drive files, and local uploads with labeled sections and an honest **Context used** manifest. |
| **Thinking logs** | `POST /api/chat/stream` streams orchestration steps (SSE) before the final reply. |
| **Skills** | `/` slash picker + skill chips; harness facts stay authoritative for access review. |
| **GitHub** | OAuth popup, searchable repo picker, attach/index (README + tree + files), status badges on chips. |
| **Google Drive** | OAuth popup, tabbed picker (docs / images / video), attach/index, token refresh on 401. |
| **Connectors** | Registry UI (GitHub, Drive, Nebius/Tavily/Composio keys via session popup); demo sign-in when host OAuth apps are unset. |
| **Cost engine (Option A)** | Cost questions call **InferenceAtlas-v1** over HTTP (`POST /api/v1/plan/llm`) when `INFERENCEATLAS_V1_URL` is set; otherwise deterministic **catalog fallback** from the static CSV. LLM is slot-filler only — no Tavily/`compare_providers` for prices when the ENGINE block is present. |
| **v1 health** | Sidebar pill **v1 engine: connected / unreachable / not set** from `GET /api/health`. |

See [V1 API Gateway](docs/V1_API_GATEWAY.md) for the thin-gateway contract. The v1 product API itself lives in [InferenceAtlas-v1](https://github.com/jayeshsuyal/InferenceAtlas-v1) (run locally; this repo does not vendor that engine).

### Web UI quick start

```bash
cd inferenceatlas-agent-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[live,web]"
cp .env.example .env
# LLM: NEBIUS_API_KEY or OPENAI_API_KEY
# Optional connectors (host OAuth apps, not user secrets in .env):
#   GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET
#   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET
#   WEB_PUBLIC_URL=http://127.0.0.1:8080
# Optional v1 cost engine:
#   INFERENCEATLAS_V1_URL=http://127.0.0.1:8000
python3 -m web
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). Use **+** for Skills & Connectors, attach GitHub repos and Drive files as chips, then ask cost or access questions.

### Run InferenceAtlas-v1 for full `rank_configs`

In a **second terminal** (sibling clone of InferenceAtlas-v1):

```bash
cd InferenceAtlas-v1
python3 -m venv venv && source venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
pip install "fastapi>=0.100" "uvicorn[standard]>=0.23"
uvicorn inference_atlas.api_server:app --host 127.0.0.1 --port 8000
```

Set `INFERENCEATLAS_V1_URL=http://127.0.0.1:8000` in this demo’s `.env` and restart `python3 -m web`. Sidebar **v1 engine: connected** means `plan_llm` is live.

### New / extended HTTP APIs

| Endpoint | Purpose |
| --- | --- |
| `GET /api/connectors` | Connector registry for UI |
| `POST /api/connectors/connect` | Start OAuth popup flow |
| `GET /api/connectors/github/repos` | List/search repos |
| `POST /api/connectors/github/attach` | Index repo digest for chat |
| `GET /api/connectors/drive/files` | List/search Drive files |
| `POST /api/connectors/drive/attach` | Index Drive file for chat |
| `POST /api/chat/stream` | SSE chat with thinking logs |
| `GET /api/health` | LLM/Tavily/Composio + `inferenceatlas_v1` status |

### New Python modules

```text
agent/chat_orchestrator.py   # unified context + tool vs engine routing
agent/cost_plan.py           # v1 gateway + ENGINE block formatting
agent/v1_client.py           # HTTP client for /api/v1/plan/llm
agent/workload_parse.py      # tokens/month + cost-question detection
agent/catalog_token_fallback.py
agent/github_repo.py
agent/google_drive_files.py
agent/connector_oauth.py
agent/connector_runtime.py
agent/ui_connectors.py
docs/V1_API_GATEWAY.md
```

## Interactive Paths

### Web UI (custom questions)

```bash
python3 -m web
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) to chat with the agent, use example prompts, or type your own requests. The sidebar shows **Mind state** (tick, tensions), connector/v1 status pills, and can advance ticks; chat also queues observations on `support_triage_agent`.

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
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
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
examples/generated/support_triage_trial.outcome_memo.md
examples/generated/support_triage_trial.outcome_memo.json
examples/evidence/support_triage_trial/
examples/generated/support_triage_trial.evidence_replay.md
examples/generated/support_triage_trial.evidence_replay.json
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
