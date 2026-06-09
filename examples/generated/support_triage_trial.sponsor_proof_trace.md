# Sponsor Proof Trace

Private engine, public proof.

Sponsor tools collect proof in locked order. They do not approve, grant, write, spend, or mutate production.

## Trace Identity

- trace_id: `ia-sponsor-proof-trace-support_triage_trial-6e7de66f3aa9a1e7-public-v0`
- packet_id: `ia-agent-access-support-triage-v0`
- revision_id: `rev_965302783cee8688`
- content_hash: `sha256:6e7de66f3aa9a1e7c0ac2e0637acfc42110a1d4bb31376415c44066c302572a6`
- scenario: `support_triage_agent`
- lane: `both`

## Decision Lock

- verdict: Do not approve production tool access yet.
- production access: False
- permission grants: False
- external writes: False
- approval granted: False
- spend approved: False
- provider winner selected: False
- savings guaranteed: False
- sponsors can change decision: False
- decision lock unchanged: True

## Sponsor Steps

| Order | Sponsor | Verb | Live Key Used | Fallback | Would Execute | Can Approve |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | tavily | searched | False | True | False | False |
| 2 | composio | planned | False | True | False | False |
| 3 | openclaw | traced | False | True | False | False |
| 4 | nebius | narrated | False | True | False | False |

## Step Summaries

- tavily searched: 5 evidence candidate slots planned; no proof debt reduced.
- composio planned: 3 dry-run permission plans built; no tool write executed.
- openclaw traced: 3 runtime checkpoints traced; 9 blocked action events preserved.
- nebius narrated: Reviewer narration prepared from locked packet fields. IA does not approve this request. Human review is required before any access, spend, or production movement. Verdict and safety state unchanged.

## Sponsor Proof Quality

- Tavily queries planned: 5
- Tavily source URLs: 0
- Composio blocked writes: 9
- Composio highest risk: high
- OpenClaw checkpoints: 3
- OpenClaw blocked events: 9
- OpenClaw attempted actions: 9
- Nebius locked fields: 4
- blast radius max risk: critical
- blast radius write/admin blocked: True
- packet remains authority: True
- sponsors can approve or write: False

## Blast Radius

- tools reviewed: 3
- blocked actions: 9
- write-like actions: 5
- admin-like actions: 4
- max risk level: critical
- all write/admin blocked: True
- would execute: False

## Access Evidence

- requested tools: github, slack, jira
- blocked actions: 9
- missing proof: 5
- reviewer owners: Security/Legal, Engineering, Support Ops, Procurement/Finance

## Spend Evidence

- spend packet: `ia-spend-review-ai_spend_budget_overrun-v0`
- requested budget period: 2026_Q1
- invoice evidence refs: 2
- blocked dollar claims: 4
- approves spend: False
- selects provider: False
- guarantees savings: False

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
- approves spend: False
- selects provider: False
- guarantees savings: False
- requires human review: True

## Source Artifacts

- request: `examples/requests/support_triage_trial.yml`
- packet: `examples/generated/support_triage_trial.packet.json`
- sponsor_readiness: `examples/generated/sponsor_live_readiness.json`
- sponsor_evidence_replay: `examples/generated/support_triage_trial.evidence_replay.json`
- spend_packet: `examples/generated/ai_spend_budget_overrun.spend_packet.json`
