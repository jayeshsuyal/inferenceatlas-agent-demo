"""Project Mind state to packet/brief artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from agent.decision_brief import build_agent_access_decision_brief, brief_to_pretty_json
from agent.public_contract import validate_public_review_artifacts
from agent.renderers import render_decision_brief_markdown, render_packet_markdown
from agent.scenarios import ROOT_DIR

from .model import Mind


MIND_RUNTIME_DIR = ROOT_DIR / "examples" / "mind_runtime"


def project_mind(mind: Mind, output_dir: Path = MIND_RUNTIME_DIR) -> Tuple[List[Path], List[str]]:
    """Write packet/brief projections and return paths + contract errors."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario = mind.scenario
    packet = mind.packet
    brief = build_agent_access_decision_brief(packet)
    errors = validate_public_review_artifacts(packet, brief)

    paths = []
    packet_json = output_dir / f"{scenario}.packet.json"
    packet_md = output_dir / f"{scenario}.packet.md"
    brief_json = output_dir / f"{scenario}.decision_brief.json"
    brief_md = output_dir / f"{scenario}.decision_brief.md"
    mind_json = output_dir / f"{scenario}.mind.json"

    packet_json.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet_md.write_text(render_packet_markdown(packet), encoding="utf-8")
    brief_json.write_text(brief_to_pretty_json(brief) + "\n", encoding="utf-8")
    brief_md.write_text(render_decision_brief_markdown(brief), encoding="utf-8")
    mind_json.write_text(json.dumps(mind.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    paths.extend([packet_json, packet_md, brief_json, brief_md, mind_json])
    return paths, errors
