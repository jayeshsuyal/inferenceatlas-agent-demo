"""
InferenceAtlas Intelligence Agent

Agentic component powered by:
  - Nebius      : LLM inference backbone (OpenAI-compatible)
  - Tavily      : live web search for pricing intelligence
  - Composio    : tool integrations (sheets, GitHub, notifications, etc.)
  - OpenClaw    : agent runtime / tool-calling orchestration loop
"""

from .agent import InferenceAtlasAgent

__all__ = ["InferenceAtlasAgent"]
