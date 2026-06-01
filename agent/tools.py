"""
Tool definitions for the InferenceAtlas agent.

Tavily  → live search
Composio → external integrations (export, Slack, GitHub, Sheets, ...)
Native  → catalog-grounded pricing tools backed by InferenceAtlas data
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Tavily search
# ---------------------------------------------------------------------------

def tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web for current AI pricing or provider news."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        results = client.search(query=query, max_results=max_results, search_depth="advanced")
        items = results.get("results", [])
        if not items:
            return "No results found."
        lines = []
        for r in items:
            lines.append(f"**{r.get('title', 'Untitled')}** — {r.get('url', '')}\n{r.get('content', '')[:400]}")
        return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"[tavily_search error] {e}"


# ---------------------------------------------------------------------------
# Native InferenceAtlas catalog tools
# ---------------------------------------------------------------------------

def _load_catalog() -> list[dict]:
    """Load the internal pricing catalog."""
    import csv
    catalog_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "master_ai_pricing_dataset_16_providers.csv"
    )
    catalog_path = os.path.normpath(catalog_path)
    if not os.path.exists(catalog_path):
        return []
    with open(catalog_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_catalog_summary() -> str:
    """Return a high-level summary of the InferenceAtlas pricing catalog."""
    rows = _load_catalog()
    if not rows:
        return "Catalog not available."
    providers = {r.get("provider", "") for r in rows}
    workload_types = {r.get("workload_type", r.get("type", "")) for r in rows}
    return (
        f"InferenceAtlas Catalog: {len(rows)} entries across "
        f"{len(providers)} providers ({', '.join(sorted(providers))}) and "
        f"{len(workload_types)} workload types ({', '.join(sorted(workload_types))})."
    )


def compare_providers(workload_type: str, model_size: str = "", top_n: int = 5) -> str:
    """
    Compare providers for a given workload type and optional model size filter.
    Returns the top_n cheapest options from the catalog.
    """
    rows = _load_catalog()
    if not rows:
        return "Catalog not available."

    filtered = [
        r for r in rows
        if workload_type.lower() in r.get("workload_type", r.get("type", "")).lower()
    ]
    if model_size:
        filtered = [
            r for r in filtered
            if model_size.lower() in r.get("model", r.get("model_name", "")).lower()
        ]
    if not filtered:
        return f"No catalog entries found for workload_type='{workload_type}' model_size='{model_size}'."

    # Sort by a numeric price field — try common column names
    price_col = None
    for col in ["price_per_1m_tokens", "price_per_token", "cost_per_1k", "price", "input_cost_per_token"]:
        if col in (filtered[0] or {}):
            price_col = col
            break

    if price_col:
        try:
            filtered.sort(key=lambda r: float(r.get(price_col, 9999) or 9999))
        except ValueError:
            pass

    top = filtered[:top_n]
    lines = [f"Top {len(top)} options for '{workload_type}':"]
    for r in top:
        provider = r.get("provider", "?")
        model = r.get("model", r.get("model_name", "?"))
        price = r.get(price_col, "?") if price_col else "see catalog"
        lines.append(f"  • {provider} / {model} — {price_col or 'price'}: {price}")
    return "\n".join(lines)


def export_report(content: str, destination: str = "google_sheets") -> str:
    """
    Export a cost report via Composio to Google Sheets, Notion, or email.
    destination: 'google_sheets' | 'notion' | 'email'
    """
    return composio_action(
        action_name=f"GOOGLESHEETS_CREATE_SPREADSHEET" if destination == "google_sheets" else destination.upper() + "_CREATE",
        params={"title": "InferenceAtlas Cost Report", "content": content},
    )


def composio_action(action_name: str, params: dict | None = None) -> str:
    """Run any Composio action by name with the given params dict."""
    try:
        from composio_openai import ComposioToolSet
        toolset = ComposioToolSet(api_key=os.environ.get("COMPOSIO_API_KEY"))
        result = toolset.execute_action(
            action=action_name,
            params=params or {},
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"[composio_action error] action={action_name} error={e}"


# ---------------------------------------------------------------------------
# OpenAI-schema tool definitions (passed to the LLM)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": (
                "Search the web for current AI provider pricing, provider news, benchmarks, "
                "or any other live information needed to answer the user's question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {"type": "integer", "description": "Max results to return (default 5).", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_catalog_summary",
            "description": "Get a summary of the InferenceAtlas internal pricing catalog (providers, workload types, entry count).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_providers",
            "description": "Compare AI providers by cost for a given workload type from the InferenceAtlas catalog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workload_type": {"type": "string", "description": "e.g. 'llm', 'speech_to_text', 'embedding'"},
                    "model_size": {"type": "string", "description": "Optional filter, e.g. '70b', '7b'"},
                    "top_n": {"type": "integer", "description": "How many top results to return (default 5)"},
                },
                "required": ["workload_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": "Export a cost analysis report to Google Sheets, Notion, or email via Composio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The report content to export."},
                    "destination": {
                        "type": "string",
                        "enum": ["google_sheets", "notion", "email"],
                        "description": "Where to export the report.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composio_action",
            "description": "Run any Composio action by its exact action name (e.g. GITHUB_CREATE_ISSUE, SLACK_SEND_MESSAGE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string", "description": "Composio action name in SCREAMING_SNAKE format."},
                    "params": {"type": "object", "description": "Parameters to pass to the action."},
                },
                "required": ["action_name"],
            },
        },
    },
]


TOOL_DISPATCH: dict[str, Any] = {
    "tavily_search": tavily_search,
    "get_catalog_summary": get_catalog_summary,
    "compare_providers": compare_providers,
    "export_report": export_report,
    "composio_action": composio_action,
}
