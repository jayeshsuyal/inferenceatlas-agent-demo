"""
CLI entry point for the InferenceAtlas agent.

Run:
    python -m agent.cli "Which provider is cheapest for 70B LLM inference?"

Or interactive REPL:
    python -m agent.cli
"""

import sys
import logging

logging.basicConfig(level=logging.WARNING)

from .agent import InferenceAtlasAgent


def _check_env() -> list[str]:
    import os
    missing = []
    for var in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY"):
        if not os.environ.get(var):
            missing.append(var)
    return missing


def main() -> None:
    missing = _check_env()
    if missing:
        print(f"[warn] Missing env vars: {', '.join(missing)}")
        print("       Set them before running the agent for full functionality.\n")

    agent = InferenceAtlasAgent()

    if len(sys.argv) > 1:
        # Single-turn from CLI arg
        query = " ".join(sys.argv[1:])
        print(f"Query: {query}\n")
        print("Agent: ", end="", flush=True)
        for chunk in agent.stream(query):
            print(chunk, end="", flush=True)
        print()
        return

    # Interactive REPL
    print("InferenceAtlas Intelligence Agent")
    print("Tech stack: Nebius (inference) · Tavily (search) · Composio (tools) · OpenClaw (runtime)")
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
