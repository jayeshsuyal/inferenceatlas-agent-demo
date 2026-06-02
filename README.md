# InferenceAtlas Agent Demo

Hack the High Seas public demo repo.

InferenceAtlas is a pre-commit proof-packet layer for AI agents and AI infrastructure decisions.

Before an agent gets tool access, data access, spend, or production permissions, IA creates a DecisionPacket showing:

- requested capability
- tool and data scope
- missing proof
- blocked claims
- reviewer owners
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
python -m venv .venv
source .venv/bin/activate
pip install -r agent/requirements.txt
cp .env.example .env
python -m agent.demo
```

The demo runs without keys using deterministic local packet generation. Add Nebius/Tavily/Composio keys to exercise the agentic path.

## Example

See:

```text
examples/sample_decision_packet.md
```

## Safety Contract

This public demo is intentionally conservative:

- no autonomous approval
- no real dispatch by default
- no packet state mutation
- no fake compliance/savings/readiness claims
- Composio actions are dry-run unless explicitly changed

Humans approve decisions. IA prepares the proof.

## Roadmap Before June 12

- tighten the agent-access DecisionPacket examples
- add optional live Tavily evidence notes
- add a short demo video
- add a polished screenshot/sample output

This repo is a public hackathon wrapper. The private InferenceAtlas v1 product codebase is not exposed here.

