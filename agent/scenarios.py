"""Scenario registry and generated artifact helpers."""

from __future__ import annotations

from pathlib import Path

from .access_request import AccessRequest
from .decision_brief import build_agent_access_decision_brief, brief_to_pretty_json
from .packet import (
    ADMIN_CODE_FIX_REQUEST,
    READ_ONLY_ANALYTICS_REQUEST,
    SUPPORT_TRIAGE_REQUEST,
    build_decision_packet,
    packet_to_pretty_json,
)
from .renderers import render_decision_brief_markdown, render_packet_markdown


ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT_DIR / "examples" / "generated"

SCENARIOS: dict[str, AccessRequest] = {
    "support_triage_agent": SUPPORT_TRIAGE_REQUEST,
    "read_only_analytics_agent": READ_ONLY_ANALYTICS_REQUEST,
    "admin_code_fix_bot": ADMIN_CODE_FIX_REQUEST,
}


def build_scenario_packet(scenario_name: str) -> dict:
    """Build a DecisionPacket for a named scenario."""
    return build_decision_packet(SCENARIOS[scenario_name])


def build_scenario_brief(scenario_name: str) -> dict:
    """Build an Agent Access Decision Brief for a named scenario."""
    return build_agent_access_decision_brief(build_scenario_packet(scenario_name))


def write_scenario_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Write packet and brief Markdown/JSON artifacts for every registered scenario."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        brief = build_agent_access_decision_brief(packet)

        packet_md = output_dir / f"{scenario_name}.packet.md"
        packet_json = output_dir / f"{scenario_name}.packet.json"
        brief_md = output_dir / f"{scenario_name}.decision_brief.md"
        brief_json = output_dir / f"{scenario_name}.decision_brief.json"

        packet_md.write_text(render_packet_markdown(packet), encoding="utf-8")
        packet_json.write_text(packet_to_pretty_json(packet) + "\n", encoding="utf-8")
        brief_md.write_text(render_decision_brief_markdown(brief), encoding="utf-8")
        brief_json.write_text(brief_to_pretty_json(brief) + "\n", encoding="utf-8")
        written.extend([packet_md, packet_json, brief_md, brief_json])
    return written


def main() -> None:
    """Regenerate scenario packet and brief artifacts."""
    for path in write_scenario_artifacts():
        print(path.relative_to(ROOT_DIR))


if __name__ == "__main__":
    main()
