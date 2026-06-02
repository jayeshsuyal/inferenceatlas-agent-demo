"""Tool layer for the public InferenceAtlas agent demo."""

from __future__ import annotations

import json
from typing import Any

from .config import COMPOSIO_DRY_RUN, TAVILY_API_KEY


def tavily_search(query: str, max_results: int = 3) -> str:
    """Search for live context. Falls back cleanly when no Tavily key is set."""
    if not TAVILY_API_KEY:
        return "[tavily_search skipped] TAVILY_API_KEY is not set."
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(query=query, max_results=max_results, search_depth="advanced")
        items = results.get("results", [])
        if not items:
            return "No results found."
        return "\n\n".join(
            f"{item.get('title', 'Untitled')} - {item.get('url', '')}\n{str(item.get('content', ''))[:400]}"
            for item in items
        )
    except Exception as exc:  # pragma: no cover - external service boundary
        return f"[tavily_search error] {exc}"


def build_decision_packet(decision: str, requested_tools: list[str] | None = None) -> str:
    """Build a conservative public-demo DecisionPacket."""
    tools = requested_tools or ["GitHub", "Slack", "Jira"]
    packet = {
        "decision": decision,
        "current_read": (
            "The agent may be useful, but access should stay blocked until scope, "
            "retention, reviewer ownership, and rollback proof are attached."
        ),
        "requested_capability": [f"Use {tool} within explicitly allowed scopes." for tool in tools],
        "blocked_claims": [
            "No production tool-access approval without a named Security reviewer.",
            "No customer-data safety claim without data-retention and logging proof.",
            "No write-action permission without rollback/off-switch proof.",
            "No autonomous dispatch in the public demo path.",
        ],
        "missing_proof": [
            "tool permission scope",
            "data retention terms",
            "Security / Legal reviewer owner",
            "audit logging plan",
            "rollback/off-switch plan",
        ],
        "reviewer_owners": [
            "Security / Legal",
            "Engineering",
            "Support Ops",
            "Procurement / Finance if paid actions are enabled",
        ],
        "next_human_validation": (
            "Ask Security / Legal to confirm allowed data scope and retention terms "
            "before enabling any tool connection."
        ),
        "guardrails": {
            "does_not_approve": True,
            "external_dispatch_performed": False,
            "state_mutated": False,
            "human_confirmation_required": True,
        },
    }
    return json.dumps(packet, indent=2)


def composio_dry_run(action_name: str, params: dict[str, Any] | None = None) -> str:
    """Prepare, but do not execute, an integration action by default."""
    payload = {
        "action_name": action_name,
        "params": params or {},
        "dry_run": COMPOSIO_DRY_RUN,
        "guardrail": "No external action is dispatched unless dry-run is explicitly disabled.",
    }
    if COMPOSIO_DRY_RUN:
        return json.dumps(payload, indent=2)
    try:
        from composio_openai import ComposioToolSet

        toolset = ComposioToolSet()
        result = toolset.execute_action(action=action_name, params=params or {})
        return json.dumps(result, indent=2)
    except Exception as exc:  # pragma: no cover - external service boundary
        return f"[composio_action error] action={action_name} error={exc}"


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Search for current evidence or context relevant to an agent-access decision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_decision_packet",
            "description": "Build a conservative DecisionPacket for human review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string"},
                    "requested_tools": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["decision"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composio_dry_run",
            "description": "Prepare an integration action as a dry-run packet artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["action_name"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "tavily_search": tavily_search,
    "build_decision_packet": build_decision_packet,
    "composio_dry_run": composio_dry_run,
}

