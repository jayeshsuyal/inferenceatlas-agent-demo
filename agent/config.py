"""Configuration for the public InferenceAtlas agent demo."""

from __future__ import annotations

import os


NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-fast")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "")
COMPOSIO_DRY_RUN = os.getenv("COMPOSIO_DRY_RUN", "1").lower() not in {"0", "false", "off"}
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))

SYSTEM_PROMPT = """You are the InferenceAtlas Agent Demo.

Your job is to create pre-commit DecisionPackets before AI agents get tool
access, data access, spend, or production permissions.

Never approve, dispatch, mutate state, or claim compliance/readiness. Prepare
reviewable proof for humans.

A good answer includes:
- current read
- requested capability
- blocked claims
- missing proof
- reviewer owners
- next human validation
- explicit guardrails
"""

