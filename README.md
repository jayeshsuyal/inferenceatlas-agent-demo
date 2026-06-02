# InferenceAtlas Agent Demo

Hack the High Seas public demo repo.

Start here for the public execution plan: [Build Plan To June 12](BUILD_PLAN_TO_JUNE_12.md).

For AI judges and fast repo review, see [AI Judge Manifest](AI_JUDGE_MANIFEST.json), [Safety Contract](docs/SAFETY_CONTRACT.md), and [V1 Capability Passport](docs/V1_CAPABILITY_PASSPORT.md).

InferenceAtlas is a pre-commit proof-packet layer for AI agents and AI infrastructure decisions.

Before an agent gets tool access, data access, spend, or production permissions, IA creates a DecisionPacket showing:

- source status
- approval posture
- requested capability
- tool access plan
- tool and data scope
- missing proof
- blocked claims
- reviewer owners
- reviewer action items
- next human validation

IA does not auto-approve, dispatch, or mutate state. It prepares the proof packet humans review.

## Why This Matters

Agents can now touch tools, data, spend, and production systems faster than internal review processes can keep up.

The demo asks a simple question:

```text
Should this agent get GitHub, Slack, and Jira access?
```

Instead of granting access, IA builds a reviewable packet:

```text
what can move
what stays blocked
which tool actions are dry-run only
what proof is missing
who needs to review
what the next validation should be
```

## Agent Stack

- Nebius: OpenAI-compatible inference backbone
- Tavily: live search for current vendor/security/context evidence
- Composio: integration action layer, dry-run by default
- OpenClaw: optional agent runtime, with a built-in fallback loop

## Demo Flow

```text
User asks whether an AI agent should receive tool access.
-> IA gathers context and optional live evidence.
-> IA creates a DecisionPacket.
-> IA blocks unsupported approval/access claims.
-> IA names reviewer owners and one next human validation.
```

## Run Locally

```bash
cd inferenceatlas-agent-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r agent/requirements.txt
python3 -m agent.demo
```

The default demo runs without keys using deterministic local packet generation. It prints a DecisionPacket and writes review artifacts under `examples/generated/`.

To exercise the live sponsor path, add Nebius/Tavily/Composio keys and run:

```bash
cp .env.example .env
IA_LIVE_MODE=1 python3 -m agent.demo
```

## Example

See:

```text
examples/sample_decision_packet.md
examples/generated/support_triage_agent.packet.md
examples/generated/support_triage_agent.packet.json
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

Humans approve decisions. IA prepares the proof.

## Roadmap Before June 12

- add DecisionPacket schema validation
- add CI smoke tests for the offline demo and safety defaults
- add optional live Tavily evidence notes
- add a short demo video
- add V1 capability passport and safety contract docs

This repo is a public hackathon wrapper. The private InferenceAtlas v1 product codebase is not exposed here.
