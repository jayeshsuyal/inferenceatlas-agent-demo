# Live Integration Contract

Status: CTO implementation contract
Purpose: define how Nebius, Tavily, Composio, and OpenClaw can enter the demo without weakening the offline judge path

## Default Rule

Offline deterministic mode is the source of judge safety:

```bash
python3 -m agent.demo
```

Live sponsor mode is optional:

```bash
IA_LIVE_MODE=1 python3 -m agent.demo
```

If keys are missing, live mode should fail clearly. If live mode is disabled, the default path must not call vendor APIs.

## Provider Contracts

| Provider | Input | Allowed output | Must not |
| --- | --- | --- | --- |
| Nebius | Prompt, packet, evidence notes | Reviewer-ready narration or packet explanation | Decide truth, approve access, or override blocked claims |
| Tavily | Search queries derived from missing proof or vendor/security context | Evidence notes with URLs, freshness status, and uncertainty | Treat web results as compliance approval |
| Composio | Tool access plan for GitHub, Slack, and Jira | Dry-run action plan, required scopes, blocked write actions | Create tickets, post Slack messages, mutate repos, or expand permissions by default |
| OpenClaw | Agent loop, tool-call sequence, runtime steps | Trace entries and live-mode execution metadata | Hide blocked steps or bypass packet safety state |

## Artifact Requirements

Every live integration should leave evidence in at least one checked artifact:

| Integration | Artifact target |
| --- | --- |
| Nebius | packet narration field or demo transcript note |
| Tavily | `evidence_notes`, `source_status`, trace step |
| Composio | `tool_access_plan`, access envelope, trace step |
| OpenClaw | `examples/generated/support_triage_agent.trace.json` and Markdown trace |
| Proof Health | `examples/generated/support_triage_agent.proof_health.json` and Markdown lifecycle report |

Generated artifacts must still parse as JSON and pass tests after live fields are added.

## Adapter Output Shape

The public dry-run contracts live in `agent/adapters/` and can be inspected with:

```bash
python3 -m agent.adapters --all
python3 -m agent.adapters --all --json
python3 -m agent.sponsor_readiness
```

They must stay no-key, non-executing, and blocked from approving access.

The Sponsor Live Readiness report shows the CTO where each sponsor can add live proof and which artifact should change:

| Provider | Live proof role | Default public boundary |
| --- | --- | --- |
| Nebius | Reviewer-ready narration over locked packet fields. | Cannot change verdict, safety state, or blocked claims. |
| Tavily | Source-backed evidence notes with URLs and freshness. | Cannot reduce proof debt without human review. |
| Composio | Dry-run permission diff for requested actions. | Cannot grant permissions or execute writes by default. |
| OpenClaw | Runtime trace entries for attempted and blocked steps. | Cannot bypass packet safety state. |

The first live proof slice is Tavily source collection, explicitly opt-in and no-write:

```bash
python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write --live-tavily --json
```

The run embeds Tavily source candidates in the SponsorProofTrace/SponsorProofCollector output. Source candidates remain review inputs; they do not approve access or reduce proof debt automatically.

The first Composio slice is a dry-run permission diff, also explicitly opt-in and no-write:

```bash
python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write --composio-dry-run --json
```

The run embeds a Composio-shaped execute-action preview for GitHub, Slack, and Jira. The preview records allowed validation scope, blocked write actions, and required proof. It does not call Composio `execute`, grant permissions, or mutate connected accounts.

Use this shape for new integration outputs before merging them into the packet:

```json
{
  "provider": "tavily",
  "status": "live_fetched",
  "purpose": "security context for Slack incident-channel summarization",
  "summary": "Evidence note written in reviewer-safe language.",
  "source_urls": ["https://example.com/source"],
  "freshness": "fetched_at_runtime",
  "safety_impact": "none",
  "blocked_from_approving_access": true
}
```

For Composio, keep the dry-run flag explicit:

```json
{
  "provider": "composio",
  "status": "dry_run_planned",
  "tool": "jira",
  "requested_action": "draft ticket proposal",
  "would_execute": false,
  "blocked_actions": ["ticket creation", "status changes", "assignment changes"],
  "required_proof": ["project scope", "draft-only mode", "rollback/off-switch plan"]
}
```

## Environment Variables

| Variable | Required for | Default |
| --- | --- | --- |
| `IA_LIVE_MODE` | Live sponsor path | unset / false |
| `NEBIUS_API_KEY` | Nebius narration/runtime | empty |
| `NEBIUS_BASE_URL` | Nebius OpenAI-compatible endpoint | `https://api.studio.nebius.com/v1/` |
| `NEBIUS_MODEL` | Nebius model | configured in `.env.example` |
| `TAVILY_API_KEY` | Tavily evidence search | empty |
| `COMPOSIO_API_KEY` | Composio dry-run planning | empty |
| `COMPOSIO_DRY_RUN` | Composio write safety | `1` |
| `PORTKEY_GUARDRAIL_TOKEN` | Portkey BYO Guardrail webhook auth | empty |
| `PORTKEY_REHEARSAL_TOKEN` | Rehearsal-only Portkey probe marker | empty |
| `WEB_PUBLIC_URL` | Public callback/base URL for OAuth and live dashboard setup | `http://127.0.0.1:8080` |
| `AGENT_MAX_STEPS` | Runtime loop limit | `6` in `.env.example` |

Never commit `.env`, keys, tokens, live customer data, or private workspace IDs.

For a live Portkey dashboard demo, the public URL must be reachable by Portkey and must terminate at the same IA server that has `PORTKEY_GUARDRAIL_TOKEN` configured. Portkey should call `/api/portkey/guardrail` with `Authorization: Bearer <same token>`. This is packet consumption only: IA does not call Portkey Admin APIs, push policies, mutate Portkey state, or approve access.

## Live Mode Acceptance Checks

Before recording a live demo, verify:

- no-key `python3 -m agent.demo` still works
- `python3 -m unittest discover -s tests` passes
- generated packet JSON parses
- generated decision brief JSON parses
- generated Proof Health JSON parses
- production access is still blocked
- Composio write actions are dry-run or explicitly blocked
- live evidence appears as evidence, not approval
- Proof Health reports drift and reviewer refresh work without approving access
- trace shows any live or blocked tool step honestly

## Implementation Order

1. Add a Tavily evidence adapter that returns structured notes.
2. Merge those notes into `evidence_notes` while preserving blocked claims.
3. Add Nebius narration as a projection over the packet.
4. Add explicit Composio dry-run planners for GitHub, Slack, and Jira.
5. Add OpenClaw trace capture for live steps.
6. Expand schemas and tests only after the shape is stable.

## Non-Negotiables

- packet state remains the source of truth
- decision brief is derived from the packet
- Proof Health is derived from the packet and brief
- runtime prompts do not replace access eligibility review
- live integrations do not auto-approve access
- no external writes in the default public path
- no private v1 source or secrets in this repository
