"""
CLI entry point for the InferenceAtlas agent.

Run:
    python -m agent.cli "Which provider is cheapest for 70B LLM inference?"

Or interactive REPL:
    python -m agent.cli
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.WARNING)

from .agent import InferenceAtlasAgent
from .config import COMPOSIO_API_KEY, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, TAVILY_API_KEY


def _warn_missing() -> None:
    if not LLM_API_KEY:
        print("Missing LLM API key. Set NEBIUS_API_KEY or OPENAI_API_KEY in .env")
        sys.exit(1)
    optional = []
    if not TAVILY_API_KEY:
        optional.append("TAVILY_API_KEY")
    if not COMPOSIO_API_KEY:
        optional.append("COMPOSIO_API_KEY")
    if optional:
        print(f"[warn] Optional env vars not set: {', '.join(optional)}")
        print("       Live search / Composio exports will be skipped.\n")


def main() -> None:
    _warn_missing()

    agent = InferenceAtlasAgent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Query: {query}\n")
        print("Agent: ", end="", flush=True)
        for chunk in agent.stream(query):
            print(chunk, end="", flush=True)
        print()
        return

    print("InferenceAtlas Intelligence Agent")
    print(f"LLM: {LLM_PROVIDER} ({LLM_MODEL}) · Tavily · Composio · OpenClaw")
    print("Type 'exit' or Ctrl-C to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Bye.")
            break

        print("Agent: ", end="", flush=True)
        for chunk in agent.stream_chat(user_input):
            print(chunk, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    main()
