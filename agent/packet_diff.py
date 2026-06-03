"""Packet Diff projection for public scenario review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .gate import evaluate_all
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_brief, build_scenario_packet


PACKET_DIFF_SCHEMA_VERSION = "agent_packet_diff.v0"
PACKET_DIFF_ID = "ia-agent-packet-diff-public-v0"

RISK_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _highest_risk(packet: dict[str, Any]) -> str:
    risk_levels = [item["risk_level"] for item in packet["requested_capability"]]
    return max(risk_levels, key=lambda level: RISK_RANK[level])


def _value_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _owner_names(packet: dict[str, Any]) -> list[str]:
    return [item["owner"] for item in packet["reviewer_owners"]]


def _capability_systems(packet: dict[str, Any]) -> list[str]:
    return [item["system"] for item in packet["requested_capability"]]


def _scenario_packet_movement(packet: dict[str, Any], brief: dict[str, Any]) -> str:
    highest_risk = _highest_risk(packet)
    if highest_risk == "low" and brief["go_no_go"]["scoped_validation_review"]:
        return "relaxes_to_read_only_validation"
    if highest_risk == "critical" or not brief["go_no_go"]["scoped_validation_review"]:
        return "hardens_to_blocked_before_validation"
    return "routes_to_proof_owner_scoped_validation"


FieldGetter = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], Any]


LOAD_BEARING_FIELDS: list[tuple[str, str, str, FieldGetter]] = [
    (
        "approval_posture.validation_review",
        "Validation review posture",
        "Shows whether the request can even enter scoped validation.",
        lambda packet, brief, gate: packet["approval_posture"]["validation_review"],
    ),
    (
        "approval_posture.write_access",
        "Write access posture",
        "Separates no-write, proof-blocked write, and admin/prod-write rejection.",
        lambda packet, brief, gate: packet["approval_posture"]["write_access"],
    ),
    (
        "go_no_go.scoped_validation_review",
        "Scoped validation go/no-go",
        "Shows the human-review lane the packet enables.",
        lambda packet, brief, gate: brief["go_no_go"]["scoped_validation_review"],
    ),
    (
        "go_no_go.production_access",
        "Production access invariant",
        "Production remains blocked across the public harness.",
        lambda packet, brief, gate: brief["go_no_go"]["production_access"],
    ),
    (
        "policy_gate.decision",
        "Policy gate decision",
        "Shows the policy-as-code result over the same packet.",
        lambda packet, brief, gate: gate["decision"],
    ),
    (
        "requested_capability.highest_risk",
        "Highest requested risk",
        "Proves risk shape changes across read-only, proof-routed, and critical requests.",
        lambda packet, brief, gate: _highest_risk(packet),
    ),
    (
        "requested_capability.systems",
        "Requested systems",
        "Shows the access envelope that drives reviewer routing.",
        lambda packet, brief, gate: _capability_systems(packet),
    ),
    (
        "missing_proof.count",
        "Missing proof count",
        "Shows proof debt changes with request risk and scope.",
        lambda packet, brief, gate: len(packet["missing_proof"]),
    ),
    (
        "blocked_claims.count",
        "Blocked claims count",
        "Shows unsupported approval, safety, or readiness claims stay visible.",
        lambda packet, brief, gate: len(packet["blocked_claims"]),
    ),
    (
        "reviewer_owners",
        "Reviewer owners",
        "Shows the packet routes work to different owners by risk shape.",
        lambda packet, brief, gate: _owner_names(packet),
    ),
    (
        "next_validation.action",
        "Next validation",
        "Shows the smallest safe next human step for each request.",
        lambda packet, brief, gate: packet["next_validation"]["action"],
    ),
]


def build_packet_diff_report() -> dict[str, Any]:
    """Build a deterministic diff across all public scenario packets."""
    packets = {scenario_name: build_scenario_packet(scenario_name) for scenario_name in SCENARIOS}
    briefs = {scenario_name: build_scenario_brief(scenario_name) for scenario_name in SCENARIOS}
    gates = evaluate_all()

    scenario_spread = []
    for scenario_name in SCENARIOS:
        packet = packets[scenario_name]
        brief = briefs[scenario_name]
        gate = gates[scenario_name]
        scenario_spread.append(
            {
                "scenario": scenario_name,
                "source_packet_artifact": f"examples/generated/{scenario_name}.packet.json",
                "source_brief_artifact": f"examples/generated/{scenario_name}.decision_brief.json",
                "highest_risk": _highest_risk(packet),
                "packet_movement": _scenario_packet_movement(packet, brief),
                "policy_gate_decision": gate["decision"],
                "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
                "production_access": brief["go_no_go"]["production_access"],
                "external_writes": brief["go_no_go"]["external_writes"],
                "missing_proof_count": len(packet["missing_proof"]),
                "blocked_claim_count": len(packet["blocked_claims"]),
                "reviewer_owners": _owner_names(packet),
                "next_validation": packet["next_validation"]["action"],
            }
        )

    load_bearing_fields = []
    for path, label, why_it_matters, getter in LOAD_BEARING_FIELDS:
        values = {
            scenario_name: getter(packets[scenario_name], briefs[scenario_name], gates[scenario_name])
            for scenario_name in SCENARIOS
        }
        load_bearing_fields.append(
            {
                "path": path,
                "label": label,
                "why_it_matters": why_it_matters,
                "values": values,
                "differs_across_scenarios": len({_value_key(value) for value in values.values()}) > 1,
            }
        )

    differing_fields = [item for item in load_bearing_fields if item["differs_across_scenarios"]]
    return {
        "schema_version": PACKET_DIFF_SCHEMA_VERSION,
        "packet_diff_id": PACKET_DIFF_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "headline": "The same packet engine relaxes for low-risk read-only access, routes proof debt for medium/high risk, and blocks critical admin/prod-write access.",
        "scenario_order": list(SCENARIOS),
        "scenario_spread": scenario_spread,
        "load_bearing_fields": load_bearing_fields,
        "summary": {
            "scenario_count": len(SCENARIOS),
            "load_bearing_field_count": len(load_bearing_fields),
            "differing_field_count": len(differing_fields),
            "has_relaxed_read_only_lane": any(
                item["packet_movement"] == "relaxes_to_read_only_validation" for item in scenario_spread
            ),
            "has_proof_routed_lane": any(
                item["packet_movement"] == "routes_to_proof_owner_scoped_validation"
                for item in scenario_spread
            ),
            "has_blocked_critical_lane": any(
                item["packet_movement"] == "hardens_to_blocked_before_validation"
                for item in scenario_spread
            ),
            "all_production_access_blocked": all(not item["production_access"] for item in scenario_spread),
            "all_external_writes_blocked": all(not item["external_writes"] for item in scenario_spread),
        },
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


def _render_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


def render_packet_diff_markdown(report: dict[str, Any]) -> str:
    """Render the packet diff report as skim-ready Markdown."""
    lines = [
        "# Packet Diff",
        "",
        "Private engine, public proof.",
        "",
        report["headline"],
        "",
        "## Scenario Spread",
        "",
        "| Scenario | Movement | Policy Gate | Scoped Validation | Production | Missing Proof |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["scenario_spread"]:
        lines.append(
            "| {scenario} | {movement} | {gate} | {validation} | {production} | {missing} |".format(
                scenario=item["scenario"],
                movement=item["packet_movement"],
                gate=item["policy_gate_decision"],
                validation=item["scoped_validation_review"],
                production=item["production_access"],
                missing=item["missing_proof_count"],
            )
        )

    lines.extend(
        [
            "",
            "## Load-Bearing Field Diff",
            "",
            "| Field | support_triage_agent | read_only_analytics_agent | admin_code_fix_bot | Differs |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["load_bearing_fields"]:
        values = item["values"]
        lines.append(
            "| {field} | {support} | {analytics} | {admin} | {differs} |".format(
                field=item["path"],
                support=_render_value(values["support_triage_agent"]),
                analytics=_render_value(values["read_only_analytics_agent"]),
                admin=_render_value(values["admin_code_fix_bot"]),
                differs=item["differs_across_scenarios"],
            )
        )

    lines.extend(
        [
            "",
            "## Why These Fields Matter",
            "",
        ]
    )
    for item in report["load_bearing_fields"]:
        lines.append(f"- {item['path']}: {item['why_it_matters']}")

    summary = report["summary"]
    safety = report["safety_boundary"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- differing load-bearing fields: {summary['differing_field_count']} of {summary['load_bearing_field_count']}",
            f"- has relaxed read-only lane: {summary['has_relaxed_read_only_lane']}",
            f"- has proof-routed lane: {summary['has_proof_routed_lane']}",
            f"- has blocked critical lane: {summary['has_blocked_critical_lane']}",
            f"- all production access blocked: {summary['all_production_access_blocked']}",
            f"- all external writes blocked: {summary['all_external_writes_blocked']}",
            "",
            "## Safety Boundary",
            "",
            f"- approves access: {safety['approves_access']}",
            f"- grants permissions: {safety['grants_permissions']}",
            f"- executes external writes: {safety['executes_external_writes']}",
            f"- mutates production: {safety['mutates_production']}",
            f"- requires human review: {safety['requires_human_review']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_packet_diff_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Write packet diff Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_packet_diff_report()
    packet_diff_json = output_dir / "packet_diff.json"
    packet_diff_md = output_dir / "packet_diff.md"
    packet_diff_json.write_text(_pretty_json(report) + "\n", encoding="utf-8")
    packet_diff_md.write_text(render_packet_diff_markdown(report), encoding="utf-8")
    return [packet_diff_json, packet_diff_md]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.packet_diff",
        description="Generate the public InferenceAtlas packet diff artifact.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where packet diff artifacts should be written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the packet diff as machine-readable JSON.",
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
    report = build_packet_diff_report()

    if not args.no_write:
        for path in write_packet_diff_artifacts(args.output_dir):
            print(_relative(path))

    if args.json:
        print(_pretty_json(report))
    elif args.no_write:
        print(render_packet_diff_markdown(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
