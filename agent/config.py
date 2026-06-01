"""
Agent configuration — reads from environment variables.

Required env vars:
    NEBIUS_API_KEY      : Nebius Studio API key
    TAVILY_API_KEY      : Tavily search API key
    COMPOSIO_API_KEY    : Composio API key

Optional:
    NEBIUS_BASE_URL     : defaults to Nebius OpenAI-compatible endpoint
    NEBIUS_MODEL        : model to use (default: meta-llama/Meta-Llama-3.1-70B-Instruct-fast)
    AGENT_MAX_STEPS     : max tool-call iterations (default: 10)
"""

import os

NEBIUS_BASE_URL = os.getenv(
    "NEBIUS_BASE_URL",
    "https://api.studio.nebius.com/v1/",
)
NEBIUS_MODEL = os.getenv(
    "NEBIUS_MODEL",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-fast",
)
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")

AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "10"))

SYSTEM_PROMPT = """You are the InferenceAtlas Intelligence Agent — an expert in AI infrastructure cost optimization.

Your job is to help users understand, compare, and reduce their AI inference spend across providers (OpenAI, Anthropic, Mistral, Groq, Together, Fireworks, Deepgram, Cohere, Nebius, and more).

You have access to:
- tavily_search          : search the web for current AI provider pricing, news, and benchmarks
- get_catalog_summary    : retrieve the InferenceAtlas internal pricing catalog summary
- compare_providers      : compare cost across providers for a given workload spec
- export_report          : export a cost comparison report via Composio (Google Sheets / Notion / email)
- composio_action        : run any Composio action by name (GitHub, Slack, HubSpot, etc.)

Workflow for cost questions:
1. Use tavily_search to get current pricing data if you need live info
2. Use get_catalog_summary / compare_providers for catalog-grounded analysis
3. Always ground your numbers — quote sources, provider names, and when prices were last verified
4. Offer to export a report if the user needs a deliverable

Never invent pricing numbers. If you're uncertain, search first.
"""
