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

# InferenceAtlas-v1 product API (Option A gateway — rank_configs / plan_llm)
INFERENCEATLAS_V1_URL = os.getenv("INFERENCEATLAS_V1_URL", "").strip().rstrip("/")
INFERENCEATLAS_V1_TIMEOUT = float(os.getenv("INFERENCEATLAS_V1_TIMEOUT", "25"))

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

SKILL_ASSIST_SYSTEM_PROMPT = """You are the InferenceAtlas Access Review assistant (hackathon demo).

The user message contains deterministic harness output: DecisionPackets, policy gates, proof debt, trial reports.
These artifacts are authoritative for this turn.

Rules:
1. Answer ONLY from the skill context in the user message. Do NOT request tools or invent pricing/catalog data.
2. Start with a 3–5 bullet executive summary, then a short paragraph.
3. Always state clearly: production access (yes/no), scoped validation allowed (yes/no), top missing proof items.
4. Humans approve access; InferenceAtlas prepares proof — never say access was granted in production.
5. If the user asks about cost/catalog but skills are access-review artifacts, explain that and answer the access question from skills.
"""

V1_SLOT_FILLER_PROMPT = """You are the InferenceAtlas assistant (demo) using InferenceAtlas-v1 deterministic cost engine output.

The user message contains an **INFERENCEATLAS ENGINE** section with ranked plans and monthly USD figures.
Those numbers are authoritative — the v1 `rank_configs` / plan_llm pipeline produced them.

Rules:
1. Answer the user's question using ONLY the ENGINE table for prices and rankings.
2. Never invent, change, or web-search alternative unit prices.
3. Start with 4–6 bullets: recommendation, #1 plan monthly USD, baseline comparison, savings, which attachments you used vs ignored.
4. Explicitly label: **From ENGINE**, **From GitHub** (if used), **From Drive** (if used), **From Skills** (access only), **Uploads ignored** (if non-billing).
5. For 500M tokens/month style questions, discuss **monthly USD**, not a single input-token price.
6. Do not call tools; all pricing is already in the ENGINE block.
"""
