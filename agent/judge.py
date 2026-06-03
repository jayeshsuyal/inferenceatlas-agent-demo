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
from .renderers import render_trace_markdown
from .review_room import write_review_room_html
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, write_scenario_artifacts
from .trust import write_trust_artifacts


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
    "python3 -m unittest discover -s tests",
]

PRIMARY_ARTIFACTS = [
    "examples/generated/demo_transcript.md",
    "examples/generated/trust_receipt.md",
    "examples/generated/review_room.md",
    "examples/generated/review_room.html",
    "docs/REVIEW_ROOM_WALKTHROUGH.md",
    "docs/DESIGN_PARTNER_BRIEF.md",
    "docs/DESIGN_PARTNER_TRIAL_KIT.md",
    "examples/requests/design_partner_trial.yml",
    "examples/requests/support_triage_trial.yml",
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

    lines.extend(
        [
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
            "1. Skim `examples/generated/review_room.html`.",
            "2. Read `examples/generated/trust_receipt.md`.",
            "3. Read `docs/DESIGN_PARTNER_BRIEF.md` for the one-workflow trial path.",
            "4. Open `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml`.",
            "5. Use `docs/REVIEW_ROOM_WALKTHROUGH.md` for the demo talk track.",
            "6. Confirm `admin_code_fix_bot` remains blocked before validation.",
            "7. Confirm sponsor adapters stay dry-run and non-approving.",
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
