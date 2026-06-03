"""One-command offline judge harness for the public proof surface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters import ADAPTER_NAMES, build_all_adapter_results
from .contract import validate_all
from .gate import evaluate_all
from .packet import build_support_triage_trace
from .proof_health import build_proof_health_report, write_proof_health_artifacts
from .renderers import render_trace_markdown
from .review_room import write_review_room_html
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, write_scenario_artifacts
from .trust import build_trust_receipt, write_trust_artifacts
from .trial import DEFAULT_TRIAL_REQUEST, build_trial_report, write_trial_artifacts


JUDGE_HARNESS_VERSION = "agent_judge_harness.v0"

JUDGE_COMMANDS = [
    "python3 -m agent.judge",
    "python3 -m agent.demo",
    "python3 -m agent.review --list",
    "python3 -m agent.contract --all",
    "python3 -m agent.gate --all",
    "python3 -m agent.adapters --all",
    "python3 -m agent.trust",
    "python3 -m agent.review_room",
    "python3 -m agent.proof_health",
    "python3 -m agent.trial examples/requests/support_triage_trial.yml",
    "python3 -m unittest discover -s tests",
]

PRIMARY_ARTIFACTS = [
    "docs/PRODUCT_TOUR.md",
    "examples/generated/demo_transcript.md",
    "examples/generated/trust_receipt.md",
    "examples/generated/review_room.md",
    "examples/generated/review_room.html",
    "examples/generated/support_triage_agent.proof_health.md",
    "examples/generated/support_triage_agent.proof_health.json",
    "docs/REVIEW_ROOM_WALKTHROUGH.md",
    "docs/DESIGN_PARTNER_BRIEF.md",
    "docs/DESIGN_PARTNER_TRIAL_KIT.md",
    "examples/requests/design_partner_trial.yml",
    "examples/requests/support_triage_trial.yml",
    "examples/generated/support_triage_trial_report.md",
    "examples/generated/support_triage_trial_report.json",
    "examples/generated/support_triage_trial.packet.json",
    "examples/generated/support_triage_trial.decision_brief.json",
    "examples/generated/review_room.desktop.jpg",
    "policy/agent_access.yml",
    "agent/adapters/",
    "examples/generated/support_triage_agent.decision_brief.md",
    "examples/generated/support_triage_agent.packet.md",
    "examples/generated/admin_code_fix_bot.packet.json",
    "docs/CONTRACT.md",
    "docs/SAFETY_CONTRACT.md",
    "docs/V1_CAPABILITY_PASSPORT.md",
]


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _write_support_trace(output_dir: Path = GENERATED_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = build_support_triage_trace()
    trace_json = output_dir / "support_triage_agent.trace.json"
    trace_md = output_dir / "support_triage_agent.trace.md"
    trace_json.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    trace_md.write_text(render_trace_markdown(trace), encoding="utf-8")
    return [trace_json, trace_md]


def write_judge_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Regenerate the offline public artifacts a judge should inspect."""
    written = []
    written.extend(write_scenario_artifacts(output_dir))
    written.extend(_write_support_trace(output_dir))
    written.extend(write_trust_artifacts(output_dir))
    written.append(write_review_room_html(output_dir))
    written.extend(write_proof_health_artifacts(output_dir=output_dir))
    written.extend(write_trial_artifacts(DEFAULT_TRIAL_REQUEST, output_dir))
    return written


def _adapter_summary() -> dict[str, dict[str, Any]]:
    scenario_results = {
        scenario_name: build_all_adapter_results(scenario_name)
        for scenario_name in SCENARIOS
    }
    summary: dict[str, dict[str, Any]] = {}
    for provider in ADAPTER_NAMES:
        provider_results = [scenario_results[scenario_name][provider] for scenario_name in SCENARIOS]
        summary[provider] = {
            "statuses": sorted({result["status"] for result in provider_results}),
            "proof_pack_types": sorted({result["proof_pack"]["proof_type"] for result in provider_results}),
            "human_review_required": all(result["human_review_required"] for result in provider_results),
            "would_execute": any(result["would_execute"] for result in provider_results),
            "can_approve_access": any(result["can_approve_access"] for result in provider_results),
            "can_grant_permissions": any(result["can_grant_permissions"] for result in provider_results),
            "can_mutate_external_state": any(result["can_mutate_external_state"] for result in provider_results),
        }
    return summary


def _artifact_status(paths: list[str]) -> list[dict[str, Any]]:
    statuses = []
    for item in paths:
        path = ROOT_DIR / item
        statuses.append(
            {
                "path": item,
                "exists": path.exists(),
                "kind": "directory" if path.is_dir() else "file",
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return statuses


def build_judge_report(*, write_artifacts: bool = True) -> dict[str, Any]:
    """Build a machine-readable judge report for the offline public harness."""
    written_paths = write_judge_artifacts() if write_artifacts else []
    contract_results = validate_all(generated_dir=GENERATED_DIR)
    gate_results = evaluate_all()
    adapter_summary = _adapter_summary()
    trust_receipt = build_trust_receipt()
    trial_report = build_trial_report(DEFAULT_TRIAL_REQUEST)
    proof_health = build_proof_health_report()

    return {
        "schema_version": JUDGE_HARNESS_VERSION,
        "mode": "offline_deterministic",
        "generated_by": "inferenceatlas-agent-demo",
        "commands": JUDGE_COMMANDS,
        "written_artifacts": [_relative(path) for path in written_paths],
        "scenario_matrix": [
            {
                "scenario": scenario_name,
                "policy_gate_decision": gate_results[scenario_name]["decision"],
                "production_access": gate_results[scenario_name]["safety_state"]["production_access"],
                "scoped_validation_review": gate_results[scenario_name]["safety_state"]["scoped_validation_review"],
                "composio_dry_run": gate_results[scenario_name]["safety_state"]["composio_dry_run"],
                "approval_granted": gate_results[scenario_name]["safety_state"]["approval_granted"],
            }
            for scenario_name in SCENARIOS
        ],
        "access_speed_layer": trust_receipt["access_speed_layer"],
        "design_partner_trial": {
            "request_path": trial_report["request_path"],
            "request_readiness": trial_report["request_readiness"],
            "access_speed_lane": trial_report["access_speed_lane"]["lane"],
            "production_access": trial_report["decision_brief_summary"]["production_access"],
            "scoped_validation_review": trial_report["decision_brief_summary"]["scoped_validation_review"],
            "validation_errors": trial_report["validation"]["errors"],
            "approves_access": trial_report["safety"]["public_runner_approves_access"],
            "grants_permissions": trial_report["safety"]["public_runner_grants_permissions"],
            "executes_external_writes": trial_report["safety"]["public_runner_executes_external_writes"],
        },
        "proof_health": {
            "scenario": proof_health["scenario"],
            "overall_status": proof_health["overall_status"],
            "overall_score": proof_health["overall_score"],
            "next_human_health_check": proof_health["next_human_health_check"],
            "current_checkpoints": proof_health["proof_health_summary"]["current_checkpoints"],
            "drifting_checkpoints": proof_health["proof_health_summary"]["drifting_checkpoints"],
            "stale_checkpoints": proof_health["proof_health_summary"]["stale_checkpoints"],
            "human_review_required": proof_health["proof_health_summary"]["human_review_required"],
            "approves_access": proof_health["safety_boundary"]["approves_access"],
            "grants_permissions": proof_health["safety_boundary"]["grants_permissions"],
            "executes_external_writes": proof_health["safety_boundary"]["executes_external_writes"],
            "mutates_production": proof_health["safety_boundary"]["mutates_production"],
        },
        "public_contract": {
            "status": "ok" if all(errors == [] for errors in contract_results.values()) else "fail",
            "results": contract_results,
        },
        "policy_gate": {
            scenario_name: {
                "decision": result["decision"],
                "reason": result["reason"],
                "triggered_rule_ids": [rule["rule_id"] for rule in result["triggered_rules"]],
            }
            for scenario_name, result in gate_results.items()
        },
        "sponsor_adapters": adapter_summary,
        "safety": {
            "approves_access": False,
            "grants_permissions": False,
            "external_writes_default": False,
            "composio_dry_run_default": True,
            "packet_state_mutation_default": False,
            "requires_human_approval": True,
            "all_adapters_non_executing": all(not item["would_execute"] for item in adapter_summary.values()),
            "all_adapters_non_approving": all(not item["can_approve_access"] for item in adapter_summary.values()),
        },
        "artifact_checklist": _artifact_status(PRIMARY_ARTIFACTS),
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def report_has_failures(report: dict[str, Any]) -> bool:
    """Return whether the judge report violates the public review contract."""
    return (
        report["public_contract"]["status"] != "ok"
        or not all(item["exists"] for item in report["artifact_checklist"])
        or not report["safety"]["all_adapters_non_executing"]
        or not report["safety"]["all_adapters_non_approving"]
        or any(item["production_access"] for item in report["scenario_matrix"])
        or any(item["approval_granted"] for item in report["scenario_matrix"])
        or not report["access_speed_layer"]["all_routes_immediate"]
        or any(item["production_access"] for item in report["access_speed_layer"]["routes"])
        or bool(report["design_partner_trial"]["validation_errors"])
        or report["design_partner_trial"]["production_access"]
        or report["design_partner_trial"]["approves_access"]
        or report["design_partner_trial"]["grants_permissions"]
        or report["design_partner_trial"]["executes_external_writes"]
        or not report["proof_health"]["human_review_required"]
        or report["proof_health"]["approves_access"]
        or report["proof_health"]["grants_permissions"]
        or report["proof_health"]["executes_external_writes"]
        or report["proof_health"]["mutates_production"]
    )


def _status(value: bool) -> str:
    return "OK" if value else "MISSING"


def render_judge_report_markdown(report: dict[str, Any]) -> str:
    """Render the judge report as compact human-readable Markdown."""
    lines = [
        "# InferenceAtlas Judge Harness",
        "",
        f"- mode: {report['mode']}",
        "- live keys required: False",
        "- external writes enabled: False",
        "- approval granted: False",
        "- private source exposed: False",
        "",
        "Private engine, public proof.",
        "",
        "## Command",
        "",
        "```bash",
        "python3 -m agent.judge",
        "```",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Policy Gate | Scoped Validation | Production |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["scenario_matrix"]:
        lines.append(
            "| {scenario} | {gate} | {validation} | {production} |".format(
                scenario=item["scenario"],
                gate=item["policy_gate_decision"],
                validation=item["scoped_validation_review"],
                production=item["production_access"],
            )
        )

    speed_layer = report["access_speed_layer"]
    lines.extend(
        [
            "",
            "## Access Speed Layer",
            "",
            speed_layer["headline"],
            "",
            f"- Decision time: {speed_layer['decision_time']}",
            f"- auto-generated packet: {speed_layer['packet_generated_automatically']}",
            f"- fast lane routes: {speed_layer['fast_lane_count']}",
            f"- proof-routed routes: {speed_layer['proof_routed_count']}",
            f"- blocked-fast routes: {speed_layer['blocked_fast_count']}",
            "",
            "| Scenario | Lane | Decision Time | Production |",
            "| --- | --- | --- | --- |",
        ]
    )
    for route in speed_layer["routes"]:
        lines.append(
            "| {scenario} | {lane} | {decision_time} | {production} |".format(
                scenario=route["scenario"],
                lane=route["lane"],
                decision_time=route["decision_time"],
                production=route["production_access"],
            )
        )

    trial = report["design_partner_trial"]
    lines.extend(
        [
            "",
            "## Design Partner Trial Runner",
            "",
            f"- request: `{trial['request_path']}`",
            f"- readiness: {trial['request_readiness']}",
            f"- access speed lane: {trial['access_speed_lane']}",
            f"- scoped validation review: {trial['scoped_validation_review']}",
            f"- production access: {trial['production_access']}",
            f"- approves access: {trial['approves_access']}",
            f"- grants permissions: {trial['grants_permissions']}",
            f"- executes external writes: {trial['executes_external_writes']}",
        ]
    )

    lines.extend(
        [
            "",
            "## Proof Health",
            "",
            "Packet lifecycle status for the primary support-triage packet.",
            "",
            f"- scenario: `{report['proof_health']['scenario']}`",
            f"- status: {report['proof_health']['overall_status']}",
            f"- score: {report['proof_health']['overall_score']}",
            f"- next human health check: {report['proof_health']['next_human_health_check']}",
            f"- human review required: {report['proof_health']['human_review_required']}",
            f"- approves access: {report['proof_health']['approves_access']}",
            f"- grants permissions: {report['proof_health']['grants_permissions']}",
            "",
            "## Public Contract",
            "",
            f"- status: {report['public_contract']['status']}",
        ]
    )
    for scenario_name, errors in report["public_contract"]["results"].items():
        lines.append(f"- {scenario_name}: {'OK' if not errors else 'FAIL'}")

    lines.extend(["", "## Sponsor Adapter Safety", ""])
    for provider, summary in report["sponsor_adapters"].items():
        lines.append(
            "- {provider}: statuses={statuses}; proof={proof}; human_review_required={review}; would_execute={would_execute}; can_approve_access={can_approve}".format(
                provider=provider,
                statuses=", ".join(summary["statuses"]),
                proof=", ".join(summary["proof_pack_types"]),
                review=summary["human_review_required"],
                would_execute=summary["would_execute"],
                can_approve=summary["can_approve_access"],
            )
        )

    lines.extend(["", "## Artifact Checklist", ""])
    for item in report["artifact_checklist"]:
        lines.append(f"- [{_status(item['exists'])}] `{item['path']}`")

    lines.extend(
        [
            "",
            "## Next Human Review",
            "",
            "1. Read `docs/PRODUCT_TOUR.md`.",
            "2. Skim `examples/generated/review_room.html`.",
            "3. Read `examples/generated/trust_receipt.md`.",
            "4. Read `examples/generated/support_triage_agent.proof_health.md`.",
            "5. Read `docs/DESIGN_PARTNER_BRIEF.md` for the one-workflow trial path.",
            "6. Open `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml`.",
            "7. Run `python3 -m agent.trial examples/requests/support_triage_trial.yml`.",
            "8. Use `docs/REVIEW_ROOM_WALKTHROUGH.md` for the demo talk track.",
            "9. Confirm `admin_code_fix_bot` remains blocked before validation.",
            "10. Confirm sponsor adapters stay dry-run and non-approving.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.judge",
        description="Run the no-key InferenceAtlas judge harness and print the review checklist.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the judge report as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip regenerating artifacts before building the report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_judge_report(write_artifacts=not args.no_write)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_judge_report_markdown(report))

    return 1 if report_has_failures(report) else 0


if __name__ == "__main__":
    sys.exit(main())
