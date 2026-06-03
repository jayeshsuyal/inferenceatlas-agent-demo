"""Proof Health lifecycle projection for public agent-access packets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet


PROOF_HEALTH_SCHEMA_VERSION = "agent_proof_health.v0"
PROOF_HEALTH_ID = "ia-agent-proof-health-public-v0"
DEFAULT_SCENARIO = "support_triage_agent"


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _support_triage_timeline(open_proof_items: int) -> list[dict[str, Any]]:
    return [
        {
            "checkpoint": "day_0",
            "status": "current",
            "score": 84,
            "summary": "Packet is reviewable for scoped validation; production remains blocked.",
            "drifted_facts": [],
            "stale_assumptions": [],
            "expired_reviewer_gates": [],
            "open_proof_items": open_proof_items,
            "human_action": "Run scoped validation review only.",
        },
        {
            "checkpoint": "day_30",
            "status": "drifting",
            "score": 67,
            "summary": "Tool scope and data-boundary assumptions need reviewer refresh before validation expands.",
            "drifted_facts": [
                "Slack channel allowlist may have changed since intake.",
                "Jira project scope needs confirmation before draft-ticket validation.",
            ],
            "stale_assumptions": [
                "Incident-channel retention terms still match the original request.",
                "Repository allowlist still reflects the current support workflow.",
            ],
            "expired_reviewer_gates": [
                "Security/Legal data-boundary review has not been refreshed within 30 days.",
            ],
            "open_proof_items": open_proof_items,
            "human_action": "Refresh reviewer gates before any broader validation.",
        },
        {
            "checkpoint": "day_60",
            "status": "stale",
            "score": 42,
            "summary": "Packet should not be reused without a new proof review.",
            "drifted_facts": [
                "Audit-log expectations may no longer match the runtime plan.",
                "Support escalation workflow owner needs reconfirmation.",
            ],
            "stale_assumptions": [
                "Customer-data boundary proof remains unchanged.",
                "Rollback and off-switch ownership is still named.",
            ],
            "expired_reviewer_gates": [
                "Engineering allowlist review expired.",
                "Support Ops workflow-fit review expired.",
            ],
            "open_proof_items": open_proof_items,
            "human_action": "Issue a new packet or rerun the trial request.",
        },
    ]


def build_proof_health_report(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    """Build a deterministic public lifecycle report for a scenario packet."""
    if scenario_name not in SCENARIOS:
        raise KeyError(f"unknown scenario: {scenario_name}")

    packet = build_scenario_packet(scenario_name)
    brief = build_scenario_brief(scenario_name)
    missing_proof = packet.get("missing_proof", [])
    timeline = _support_triage_timeline(len(missing_proof))

    return {
        "schema_version": PROOF_HEALTH_SCHEMA_VERSION,
        "proof_health_id": PROOF_HEALTH_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "scenario": scenario_name,
        "source_packet_artifact": f"examples/generated/{scenario_name}.packet.json",
        "source_brief_artifact": f"examples/generated/{scenario_name}.decision_brief.json",
        "headline": "Agent-access proof packets age; InferenceAtlas makes drift visible before access moves.",
        "overall_status": "drifting",
        "overall_score": 67,
        "next_human_health_check": "day_30_security_engineering_review",
        "proof_health_summary": {
            "current_checkpoints": sum(1 for item in timeline if item["status"] == "current"),
            "drifting_checkpoints": sum(1 for item in timeline if item["status"] == "drifting"),
            "stale_checkpoints": sum(1 for item in timeline if item["status"] == "stale"),
            "open_proof_items": len(missing_proof),
            "human_review_required": True,
        },
        "source_review_state": {
            "decision": brief["decision"]["verdict"],
            "production_access": brief["go_no_go"]["production_access"],
            "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
            "external_writes": brief["go_no_go"]["external_writes"],
            "composio_dry_run": brief["go_no_go"]["composio_dry_run"],
        },
        "health_timeline": timeline,
        "packet_lifecycle": ["created", "reviewable", "drifting", "stale_without_refresh"],
        "packet_drift_signals": [
            "tool scope changed",
            "data boundary changed",
            "reviewer gate expired",
            "proof item still open",
        ],
        "safety_boundary": {
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_production": False,
            "requires_human_review": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def _flatten(items: list[dict[str, Any]], key: str) -> list[str]:
    flattened: list[str] = []
    for item in items:
        for value in item[key]:
            if value not in flattened:
                flattened.append(value)
    return flattened


def _render_bullets(values: list[str]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {value}" for value in values]


def render_proof_health_markdown(report: dict[str, Any]) -> str:
    """Render a Proof Health report as skim-ready Markdown."""
    lines = [
        f"# Proof Health: {report['scenario']}",
        "",
        "Private engine, public proof.",
        "",
        report["headline"],
        "",
        "A DecisionPacket is not permanent approval. It ages as tool scope, data boundaries, reviewer gates, and evidence freshness drift.",
        "",
        "## Verdict",
        "",
        f"- scenario: `{report['scenario']}`",
        f"- status: {report['overall_status']}",
        f"- score: {report['overall_score']}",
        f"- next human health check: {report['next_human_health_check']}",
        f"- source packet artifact: `{report['source_packet_artifact']}`",
        f"- source brief artifact: `{report['source_brief_artifact']}`",
        "",
        "## Packet Drift Timeline",
        "",
        "| Checkpoint | Status | Score | Open Proof | Human Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in report["health_timeline"]:
        lines.append(
            "| {checkpoint} | {status} | {score} | {open_proof} | {action} |".format(
                checkpoint=item["checkpoint"],
                status=item["status"],
                score=item["score"],
                open_proof=item["open_proof_items"],
                action=item["human_action"],
            )
        )

    timeline = report["health_timeline"]
    lines.extend(
        [
            "",
            "## Drifted Facts",
            "",
            *_render_bullets(_flatten(timeline, "drifted_facts")),
            "",
            "## Stale Assumptions",
            "",
            *_render_bullets(_flatten(timeline, "stale_assumptions")),
            "",
            "## Expired Reviewer Gates",
            "",
            *_render_bullets(_flatten(timeline, "expired_reviewer_gates")),
            "",
            "## Safety Boundary",
            "",
            f"- approves access: {report['safety_boundary']['approves_access']}",
            f"- grants permissions: {report['safety_boundary']['grants_permissions']}",
            f"- executes external writes: {report['safety_boundary']['executes_external_writes']}",
            f"- mutates production: {report['safety_boundary']['mutates_production']}",
            f"- requires human review: {report['safety_boundary']['requires_human_review']}",
            "",
            "Proof Health does not approve access. It keeps packet drift visible so a human can decide whether the request is still reviewable.",
            "",
        ]
    )
    return "\n".join(lines)


def write_proof_health_artifacts(
    scenario_name: str = DEFAULT_SCENARIO,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write Proof Health Markdown and JSON artifacts for a scenario."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_proof_health_report(scenario_name)
    proof_health_json = output_dir / f"{scenario_name}.proof_health.json"
    proof_health_md = output_dir / f"{scenario_name}.proof_health.md"

    proof_health_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proof_health_md.write_text(render_proof_health_markdown(report), encoding="utf-8")
    return [proof_health_json, proof_health_md]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.proof_health",
        description="Generate the public InferenceAtlas Proof Health lifecycle artifact.",
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default=DEFAULT_SCENARIO,
        help="Scenario to project into a Proof Health report.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where Proof Health artifacts should be written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the Proof Health report as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing artifacts and print only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_proof_health_report(args.scenario)

    if not args.no_write:
        written = write_proof_health_artifacts(args.scenario, args.output_dir)
        for path in written:
            print(_relative(path))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.no_write:
        print(render_proof_health_markdown(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
