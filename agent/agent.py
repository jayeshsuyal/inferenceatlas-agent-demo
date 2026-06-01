"""
InferenceAtlasAgent — the main agent class.

Usage:
    from agent import InferenceAtlasAgent

    agent = InferenceAtlasAgent()

    # Single-turn
    print(agent.run("Which providers offer the cheapest LLM inference for a 70B model?"))

    # Multi-turn (maintains history)
    agent.chat("I'm spending $4k/month on OpenAI GPT-4.")
    agent.chat("What's the cheapest equivalent?")
    agent.chat("Export a comparison to Google Sheets.")

    # Streaming
    for chunk in agent.stream("Compare top 5 LLM providers by cost per million tokens"):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import logging
from typing import Generator

from . import runtime

logger = logging.getLogger("inference_atlas.agent")


class InferenceAtlasAgent:
    """
    Stateful InferenceAtlas Intelligence Agent.

    Maintains conversation history across .chat() calls so the agent can
    reference prior context (e.g., workload specs mentioned earlier).
    """

    def __init__(self) -> None:
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, user_message: str) -> str:
        """Single-turn: send a message, get a full response string back."""
        messages = [{"role": "user", "content": user_message}]
        return runtime.run(messages)

    def chat(self, user_message: str) -> str:
        """
        Multi-turn: maintains history.
        Call repeatedly to build a conversation.
        """
        self._history.append({"role": "user", "content": user_message})
        response = runtime.run(self._history)
        self._history.append({"role": "assistant", "content": response})
        return response

    def stream(self, user_message: str) -> Generator[str, None, None]:
        """Single-turn streaming — yields response text chunks as they arrive."""
        messages = [{"role": "user", "content": user_message}]
        yield from runtime.stream(messages)

    def stream_chat(self, user_message: str) -> Generator[str, None, None]:
        """Multi-turn streaming — maintains history, yields chunks."""
        self._history.append({"role": "user", "content": user_message})
        collected = []
        for chunk in runtime.stream(self._history):
            collected.append(chunk)
            yield chunk
        self._history.append({"role": "assistant", "content": "".join(collected)})

    def reset(self) -> None:
        """Clear conversation history."""
        self._history = []

    @property
    def history(self) -> list[dict]:
        return list(self._history)
