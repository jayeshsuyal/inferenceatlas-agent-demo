"""Public demo entry point for the hackathon judge harness."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.decision_brief import build_agent_access_decision_brief, brief_to_pretty_json
from agent.packet import (
    DEFAULT_AGENT_ACCESS_PROMPT,
    build_support_triage_decision_packet,
    build_support_triage_trace,
    packet_to_pretty_json,
)
from agent.renderers import render_decision_brief_markdown, render_packet_markdown, render_trace_markdown


ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT_DIR / "examples" / "generated"


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _write_offline_artifacts(packet: dict, trace: list[dict[str, str]], brief: dict) -> list[Path]:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    packet_md = GENERATED_DIR / "support_triage_agent.packet.md"
    packet_json = GENERATED_DIR / "support_triage_agent.packet.json"
    trace_json = GENERATED_DIR / "support_triage_agent.trace.json"
    trace_md = GENERATED_DIR / "support_triage_agent.trace.md"
    brief_md = GENERATED_DIR / "support_triage_agent.decision_brief.md"
    brief_json = GENERATED_DIR / "support_triage_agent.decision_brief.json"

    packet_md.write_text(render_packet_markdown(packet), encoding="utf-8")
    packet_json.write_text(packet_to_pretty_json(packet) + "\n", encoding="utf-8")
    trace_json.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    trace_md.write_text(render_trace_markdown(trace), encoding="utf-8")
    brief_md.write_text(render_decision_brief_markdown(brief), encoding="utf-8")
    brief_json.write_text(brief_to_pretty_json(brief) + "\n", encoding="utf-8")

    return [packet_md, packet_json, trace_json, trace_md, brief_md, brief_json]


def _run_offline_demo() -> None:
    packet = build_support_triage_decision_packet(DEFAULT_AGENT_ACCESS_PROMPT)
    trace = build_support_triage_trace()
    brief = build_agent_access_decision_brief(packet)
    written = _write_offline_artifacts(packet, trace, brief)

    print("=" * 72)
    print("InferenceAtlas Agent Demo - Offline DecisionPacket")
    print("Mode: offline_deterministic | external writes: disabled | Composio: dry-run")
    print("=" * 72)
    print()
    print(render_packet_markdown(packet))
    print("Decision brief:")
    print(f"- {brief['decision']['verdict']}")
    print(f"- Runtime boundary: {brief['runtime_permission_boundary']['inferenceatlas_decision_brief_answers']}")
    print()
    print("Generated artifacts:")
    for path in written:
        print(f"- {path.relative_to(ROOT_DIR)}")


def _run_live_demo() -> None:
    missing = [v for v in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "COMPOSIO_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"Missing env vars for live mode: {', '.join(missing)}")
        print("Run without IA_LIVE_MODE for the deterministic no-key judge demo.")
        sys.exit(1)

    from agent import InferenceAtlasAgent

    agent = InferenceAtlasAgent()

    print("=" * 72)
    print("InferenceAtlas Agent Demo - Live Sponsor Mode")
    print("Nebius + Tavily + Composio + OpenClaw path")
    print("Safety: review packet only; keep external writes dry-run by default")
    print("=" * 72)
    print()
    print(f"User: {DEFAULT_AGENT_ACCESS_PROMPT}")
    print("Agent: ", end="", flush=True)
    for chunk in agent.stream_chat(DEFAULT_AGENT_ACCESS_PROMPT):
        print(chunk, end="", flush=True)
    print()


def main():
    if _env_enabled("IA_LIVE_MODE"):
        _run_live_demo()
        return
    _run_offline_demo()


if __name__ == "__main__":
    main()
