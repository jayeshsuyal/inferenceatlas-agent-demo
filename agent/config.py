"""
Agent configuration — reads from environment variables (see .env.example).

LLM (one required):
    NEBIUS_API_KEY      : Nebius Studio (OpenAI-compatible)
    OPENAI_API_KEY      : fallback when Nebius is unset

Optional:
    NEBIUS_BASE_URL / OPENAI_BASE_URL / LLM_BASE_URL
    NEBIUS_MODEL / OPENAI_MODEL / LLM_MODEL
    TAVILY_API_KEY      : live web search (skipped if unset)
    COMPOSIO_API_KEY    : integrations (skipped if unset)
    AGENT_MAX_STEPS     : max tool-call iterations (default: 10)
"""

from __future__ import annotations

import os

from ._env import load_dotenv

load_dotenv()

NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "").strip()
COMPOSIO_DRY_RUN = os.environ.get("COMPOSIO_DRY_RUN", "1").strip() not in ("0", "false", "False")

AGENT_MAX_STEPS = max(8, int(os.getenv("AGENT_MAX_STEPS", "10")))

_LLM_PREFER = os.getenv("LLM_PROVIDER", "").strip().lower()


def _use_openai() -> None:
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
    LLM_API_KEY = OPENAI_API_KEY
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    LLM_PROVIDER = "openai"


def _use_nebius() -> None:
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
    LLM_API_KEY = NEBIUS_API_KEY
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/"),
    )
    LLM_MODEL = os.getenv(
        "LLM_MODEL",
        os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
    )
    LLM_PROVIDER = "nebius"


if _LLM_PREFER == "openai" and OPENAI_API_KEY:
    _use_openai()
elif _LLM_PREFER == "nebius" and NEBIUS_API_KEY:
    _use_nebius()
elif NEBIUS_API_KEY:
    _use_nebius()
elif OPENAI_API_KEY:
    _use_openai()
else:
    LLM_API_KEY = ""
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    LLM_PROVIDER = "none"

# Back-compat aliases used by runtime
NEBIUS_BASE_URL = LLM_BASE_URL
NEBIUS_MODEL = LLM_MODEL

SYSTEM_PROMPT = """You are the InferenceAtlas Intelligence Agent — an expert in AI infrastructure cost optimization.

Your job is to help users understand, compare, and reduce their AI inference spend across providers (OpenAI, Anthropic, Mistral, Groq, Together, Fireworks, Deepgram, Cohere, Nebius, and more).

You have access to:
- tavily_search          : search the web for current AI provider pricing, news, and benchmarks
- get_catalog_summary    : retrieve the InferenceAtlas internal pricing catalog summary
- compare_providers      : compare cost across providers for a given workload spec
- export_report          : export a cost comparison report via Composio (Google Sheets / Notion / email)
- composio_action        : run any Composio action by name (GitHub, Slack, HubSpot, etc.)

Workflow:
1. If the user asks what InferenceAtlas tracks or wants a catalog overview → call get_catalog_summary first.
2. For cost comparisons or cheapest-model questions → call compare_providers (and tavily_search if live pricing is needed).
3. Always ground answers in tool results — never invent pricing numbers.
4. Offer export_report only when the user wants a deliverable.

Never reply with "provide more details" when a tool can answer the question. Use tools proactively.
"""
