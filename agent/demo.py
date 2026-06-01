"""
Quick demo script — shows the agent in action for the hackathon judges.

Run:
    NEBIUS_API_KEY=... TAVILY_API_KEY=... COMPOSIO_API_KEY=... python agent/demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import InferenceAtlasAgent


DEMO_QUERIES = [
    "Give me a quick summary of what InferenceAtlas tracks.",
    "Search for the current pricing of Mistral Large and compare it against what's in the InferenceAtlas catalog.",
    "I run 500M tokens/month on GPT-4o. What's the cheapest equivalent model I could switch to without sacrificing quality?",
]


def main():
    missing = [v for v in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        print("Set them and re-run. Exiting.")
        sys.exit(1)

    agent = InferenceAtlasAgent()

    print("=" * 70)
    print("  InferenceAtlas Intelligence Agent — Demo")
    print("  Nebius · Tavily · Composio · OpenClaw")
    print("=" * 70)

    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n[{i}/{len(DEMO_QUERIES)}] User: {query}")
        print("Agent: ", end="", flush=True)
        for chunk in agent.stream_chat(query):
            print(chunk, end="", flush=True)
        print("\n" + "-" * 70)


if __name__ == "__main__":
    main()
