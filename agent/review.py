"""CLI for reviewing deterministic agent-access scenarios."""

from __future__ import annotations

import argparse
import sys

from .decision_brief import brief_to_pretty_json
from .packet import packet_to_pretty_json
from .renderers import render_decision_brief_markdown, render_packet_markdown
from .scenarios import SCENARIOS, build_scenario_brief, build_scenario_packet


def _scenario_choices() -> list[str]:
    return list(SCENARIOS)


def render_review(scenario_name: str, *, artifact: str = "brief", output_format: str = "markdown") -> str:
    """Render a scenario packet or brief for CLI output."""
    if artifact == "packet":
        packet = build_scenario_packet(scenario_name)
        if output_format == "json":
            return packet_to_pretty_json(packet)
        return render_packet_markdown(packet)

    brief = build_scenario_brief(scenario_name)
    if output_format == "json":
        return brief_to_pretty_json(brief)
    return render_decision_brief_markdown(brief)


def list_scenarios() -> str:
    """Return a human-readable list of registered scenarios."""
    lines = ["Available scenarios:"]
    for scenario_name, request in SCENARIOS.items():
        lines.append(f"- {scenario_name}: {request.purpose}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.review",
        description="Render deterministic InferenceAtlas access-review packets and briefs.",
    )
    parser.add_argument(
        "--scenario",
        choices=_scenario_choices(),
        default="support_triage_agent",
        help="Registered scenario to review.",
    )
    parser.add_argument(
        "--artifact",
        choices=("brief", "packet"),
        default="brief",
        help="Artifact to render.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        print(list_scenarios())
        return 0

    print(render_review(args.scenario, artifact=args.artifact, output_format=args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
