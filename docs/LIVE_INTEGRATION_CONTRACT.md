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

Generated artifacts must still parse as JSON and pass tests after live fields are added.

## Adapter Output Shape

The public dry-run contracts live in `agent/adapters/` and can be inspected with:

```bash
python3 -m agent.adapters --all
python3 -m agent.adapters --all --json
```

They must stay no-key, non-executing, and blocked from approving access.

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
| `AGENT_MAX_STEPS` | Runtime loop limit | `6` in `.env.example` |

Never commit `.env`, keys, tokens, live customer data, or private workspace IDs.

## Live Mode Acceptance Checks

Before recording a live demo, verify:

- no-key `python3 -m agent.demo` still works
- `python3 -m unittest discover -s tests` passes
- generated packet JSON parses
- generated decision brief JSON parses
- production access is still blocked
- Composio write actions are dry-run or explicitly blocked
- live evidence appears as evidence, not approval
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
- runtime prompts do not replace access eligibility review
- live integrations do not auto-approve access
- no external writes in the default public path
- no private v1 source or secrets in this repository
