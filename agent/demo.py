"""Run the public hackathon demo."""

from __future__ import annotations

from .agent import InferenceAtlasAgent


DEMO_PROMPT = (
    "Should our support triage agent get GitHub issues, Slack incident channels, "
    "and Jira ticket creation access?"
)


def main() -> None:
    agent = InferenceAtlasAgent()
    print("InferenceAtlas Agent Demo")
    print("Nebius + Tavily + Composio + optional OpenClaw-style tool loop")
    print("=" * 72)
    print(f"User: {DEMO_PROMPT}\n")
    print("Agent DecisionPacket:")
    print(agent.run(DEMO_PROMPT))


if __name__ == "__main__":
    main()

