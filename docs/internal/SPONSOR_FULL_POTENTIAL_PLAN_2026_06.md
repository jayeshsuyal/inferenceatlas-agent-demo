# Sponsor Full Potential Plan - June 2026

Internal tracker. This is the sponsor-depth plan for the public agent-demo lane.
It is intentionally proof-first: sponsor tools deepen evidence, provenance, review
clarity, and downstream gating. They do not approve, write, dispatch, mutate,
reduce proof debt automatically, approve spend, select providers, or override
the IA Packet.

## Locked Principle

Sponsor potential at IA altitude is proof depth, not action depth.

| IA-altitude sponsor potential | Action-altitude sponsor potential |
| --- | --- |
| Stronger proof | More autonomous action |
| Harder evidence claims | More side effects |
| Verifiable provenance | Faster execution |
| What sponsors should be seen doing in IA | What generic agent demos usually show |

Magic means unexpected proof depth, not unexpected action complexity.

The judge-facing loop should read as:

```text
IA Packet -> sponsor proof collection -> decision lock stays unchanged -> downstream previews -> human review artifact
```

One local IA API call may orchestrate multiple sponsor proof steps, but every
sponsor is allowed to contribute proof only.

## Current Shipped State

As of PR #107, the public harness has the safe proof spine:

| Surface | Shipped |
| --- | --- |
| Sponsor order | Tavily -> Composio -> OpenClaw -> Nebius |
| SponsorProofTrace | Locked-order trace with access and spend evidence blocks |
| SponsorProofCollector | One run object that wraps trace, packet advisor, Portkey preview, Nebius synthesis, and ledger |
| Tavily | Live evidence path plus fallback, source URLs, freshness labels, query/source quality summary |
| Composio | Dry-run GitHub/Slack/Jira permission diff, permission review matrix, blocked-write/risk summary |
| OpenClaw | Runtime trace contract, trace timeline, blocked action events, trace quality summary |
| Nebius | Packet-grounded narration, evidence synthesis, source-bound role briefs |
| Portkey | Dry-run adapter, BYO Guardrails webhook, live probe, no mutation by default |
| Safety | No sponsor approval, no permission grants, no external writes, no packet mutation |
| Validation | Focused sponsor tests, full pytest, artifact integrity, PR smoke, GitHub smoke |

The important #107 shift:

> Sponsor tools now visibly deepen the proof packet without changing packet authority.

## Tier Map

### Tavily

| Tier | Status | Plan | Why it matters | Time |
| --- | --- | --- | --- | --- |
| Today / shipped | Shipped | Live evidence candidates with source URLs, freshness labels, query/source quality summary | Shows Tavily can contribute cited evidence without reducing proof debt | Done |
| Tier 1 | Next | Multi-query live evidence per packet, source diversity scoring, domain trust tier | Makes the packet feel alive and verifiable | 1 PR |
| Tier 2 | Later | Cross-source corroboration, lane-specific search windows, stronger freshness windows | Turns sources into claim-support signals | 1-2 weeks |
| Tier 3 | Vision | Real-time citation streaming during demo | Partnership-grade proof experience | Later |

Tier 1 acceptance:

- Query plan fans out from packet missing proof and blocked claims.
- Results retain URL, title, snippet, score, freshness, domain, source type.
- Diversity score is deterministic from returned URLs/domains.
- No Tavily result can approve, reduce proof debt, or unlock movement.

Magical demo beat:

> Run the packet live and show current Tavily sources attached to the proof run with freshness and domain diversity.

### Nebius

| Tier | Status | Plan | Why it matters | Time |
| --- | --- | --- | --- | --- |
| Today / shipped | Shipped | Packet-grounded narration, evidence synthesis, source-bound role briefs | Same packet can be explained to reviewers without letting an LLM own the verdict | Done |
| Tier 1 | Next | Multi-persona synthesis for CFO, Security, CTO, and Legal using only packet fields and Tavily source IDs | Shows one IA Packet serving multiple buyer languages | 1 PR |
| Tier 2 | Later | Confidence/freshness tags per claim, stronger source-count annotations | Makes hallucination prevention more visible | 1-2 weeks |
| Tier 3 | Vision | Multi-model corroboration and disagreement flagging | Product-grade model governance | Later |

Tier 1 acceptance:

- Four role outputs: CFO, Security, CTO, Legal.
- Each role output cites only allowed Tavily source IDs.
- Each role output keeps the same next human action and safety anchor.
- Tests reject new URLs, invented source IDs, approval language, and proof-debt reduction claims.

Magical demo beat:

> Click or ask for CFO view, then Security view, and watch the same packet become two different stakeholder briefs without changing the verdict.

### Composio

| Tier | Status | Plan | Why it matters | Time |
| --- | --- | --- | --- | --- |
| Today / shipped | Shipped | Dry-run permission diffs, execute-action previews, review matrix, blocked-write summary | Shows what would stay blocked before any tool action | Done |
| Tier 1 | Next | Blast radius object for GitHub/Slack/Jira from requested scopes and optional read-only metadata | Makes risk visible and visceral | 1 PR |
| Tier 2 | Later | Scope minimization recommendations and per-tool risk scoring from metadata | Converts blast radius into least-privilege recommendations | 1-2 weeks |
| Tier 3 | Vision | Live OAuth sandbox flow against test accounts | Partnership-grade demo | Later |

Tier 1 acceptance:

- Blast radius object names tool, accessible object category, requested scope, blocked write categories, and owner.
- Optional read-only metadata fetches are explicitly opt-in and never execute actions.
- Composio remains dry-run by default.
- No Composio output can grant scopes, approve access, write to tools, or reduce proof debt.

Magical demo beat:

> Show the agent request, then show exactly which repos/channels/issues would be in blast radius if the scope were granted.

### OpenClaw

| Tier | Status | Plan | Why it matters | Time |
| --- | --- | --- | --- | --- |
| Today / shipped | Shipped | Trace contract, timeline, blocked action events, trace quality summary | Shows policy checkpoints before runtime movement | Done |
| Tier 1 | Next | More explicit step-by-step trace timeline artifact with attempted vs permitted state | Operator-grade visibility | 1 PR |
| Tier 2 | High leverage | With-IA vs without-IA comparison | The most visceral value proof | 1-2 weeks |
| Tier 3 | Vision | Forensic audit export, recurring pattern detection | Enterprise audit surface | Later |

Tier 1 acceptance:

- Timeline includes step order, attempted action, policy decision, blocked/permitted state, and packet field observed.
- All attempted write-like actions remain `would_execute=false`.
- Timeline can be rendered in markdown/JSON without UI dependency.

Magical demo beat:

> Show the same agent flow as a trace: attempted action, IA policy decision, blocked event, next human review.

### Portkey

| Tier | Status | Plan | Why it matters | Time |
| --- | --- | --- | --- | --- |
| Today / shipped | Shipped | Dry-run Portkey adapter, BYO Guardrails webhook, live probe, read-only events | Shows Portkey can ask IA before a model/spend movement proceeds | Done |
| Tier 1 | Next | Guardrail proof loop summary with latency, packet reference, verdict, and policy preview | Makes Portkey integration feel production-shaped without live mutation | 1 PR |
| Tier 2 | Later | Same request with/without IA gate; spend packet tied to budget guardrail | Connects access and spend lanes | 1-2 weeks |
| Tier 3 | Vision | Multi-region webhook, verdict caching, partnership integration | Partnership-grade | Later |

Tier 1 acceptance:

- Probe records elapsed time and verdict.
- Response includes packet id, revision, hash, safety state, and next human action.
- POST is auth-gated and no-token behavior fails safe.
- No Portkey API writes happen by default.

Magical demo beat:

> Portkey calls IA, IA returns a verdict with packet reference and latency, and the packet remains the source of truth.

## PR Sequence

This is the safe sequence after #107:

| PR | Slice | Sponsors | Scope | Non-goals |
| --- | --- | --- | --- | --- |
| #107 | Sponsor proof quality | Tavily, Composio, OpenClaw, Nebius | Add proof-quality summaries and invariants | No UI creep, no live writes |
| #108 | Live proof intelligence | Tavily, Nebius | Multi-query evidence and multi-persona source-bound synthesis | No new approvals, no source invention |
| #109 | Blast radius and trace depth | Composio, OpenClaw | Blast radius object and richer trace artifact | No OAuth sandbox, no writes |
| #110 | Guardrail proof loop | Portkey | Latency/verdict/packet-reference proof loop | No Portkey config mutation |
| #111 | Demo surface polish | All | Expose only the strongest proof beats in the browser | No dashboard sprawl |

## Tier 1 Win Condition

If Tier 1 lands across all sponsors, the demo should prove:

1. Tavily brings live, source-backed evidence into the packet.
2. Nebius turns the same packet into role-specific reviewer language without changing the verdict.
3. Composio shows permission blast radius before any tool action.
4. OpenClaw records attempted vs blocked runtime movement.
5. Portkey asks IA before a model/spend movement proceeds.

The short claim:

> IA turns sponsor tools into proof contributors for one packet downstream systems can trust.

## Magical Filter

Before shipping any idea, it should hit at least 3 of 5:

| Criterion | Meaning |
| --- | --- |
| Live data a judge can verify | Current URL, timestamp, policy, or returned evidence |
| Fast enough to feel real | Local proof loop should feel immediate; live calls should degrade gracefully |
| Visible failure mode | Reviewer sees what would stay blocked without pretending IA took action |
| Sponsor feature used seriously | Not a token mention; the sponsor has a clear architecture role |
| One-sentence explanation | A judge understands it in 5 seconds |

## Safety Lines

Never claim:

- IA can take any random natural-language request and fully orchestrate all live sponsors today.
- IA approves access, spend, vendors, or production movement.
- Sponsors reduce proof debt automatically.
- Composio executes tool actions in the public default path.
- Portkey config is mutated by default.
- Nebius can invent sources or decide the verdict.
- Tavily sources prove a claim without human review.
- OpenClaw executed runtime writes in the public fallback path.

Safe claim:

> IA turns supported agent, spend, and tool-access requests into packet-backed proof runs, keeps the decision locked, collects sponsor proof safely, previews downstream gates, and gives humans the review artifact.

## Post-Hackathon 30-Day Track

| Window | Focus |
| --- | --- |
| June 9-10 | Finish and merge #107, then start #108 only if the branch stays clean |
| June 11-14 | Rehearse, record, stabilize, and avoid feature sprawl |
| June 15-21 | Tier 1 sponsor depth across Tavily, Nebius, Composio, OpenClaw, Portkey |
| June 22-July 5 | Highest-leverage Tier 2: OpenClaw with/without IA and Nebius confidence/source scoring |
| July 6-12 | Re-record v2 demo for design partners and investor/buyer conversations |

## Current Next Move

Merge #107 after CI stays green. Then start #108 as a narrow backend artifact PR:

```text
PR #108: Tavily + Nebius live proof intelligence
- Tavily: multi-query source diversity and freshness summary
- Nebius: CFO/Security/CTO/Legal source-bound role synthesis
- Collector: one compact live proof intelligence summary
- Tests: no invented source IDs, no new URLs, no approval language, no proof-debt reduction
- Non-goals: no UI redesign, no writes, no approval, no mutation
```
