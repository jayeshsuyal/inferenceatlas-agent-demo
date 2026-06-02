"""CLI entry point for the public InferenceAtlas agent demo."""

from __future__ import annotations

import sys

from .agent import InferenceAtlasAgent


def main() -> None:
    agent = InferenceAtlasAgent()
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(agent.run(prompt))
        return

    print("InferenceAtlas Agent Demo")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if prompt.lower() in {"exit", "quit", "q"}:
            print("Bye.")
            return
        if not prompt:
            continue
        print("Agent:")
        print(agent.chat(prompt))
        print()


if __name__ == "__main__":
    main()

