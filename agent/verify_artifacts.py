"""Artifact integrity gate for checked-in public proof artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .judge import write_judge_artifacts
from .scenarios import GENERATED_DIR, ROOT_DIR


VERIFY_ARTIFACTS_SCHEMA_VERSION = "artifact_integrity_report.v0"


@dataclass(frozen=True)
class ArtifactFamily:
    name: str
    files: tuple[str, ...]


GENERATED_ARTIFACT_FAMILIES = (
    ArtifactFamily(
        "Packet artifacts",
        (
            "support_triage_agent.packet.md",
            "support_triage_agent.packet.json",
            "read_only_analytics_agent.packet.md",
            "read_only_analytics_agent.packet.json",
            "admin_code_fix_bot.packet.md",
            "admin_code_fix_bot.packet.json",
        ),
    ),
    ArtifactFamily(
        "Decision briefs",
        (
            "support_triage_agent.decision_brief.md",
            "support_triage_agent.decision_brief.json",
            "read_only_analytics_agent.decision_brief.md",
            "read_only_analytics_agent.decision_brief.json",
            "admin_code_fix_bot.decision_brief.md",
            "admin_code_fix_bot.decision_brief.json",
        ),
    ),
    ArtifactFamily(
        "Traces",
        (
            "support_triage_agent.trace.md",
            "support_triage_agent.trace.json",
        ),
    ),
    ArtifactFamily(
        "Trust Receipt",
        (
            "trust_receipt.md",
            "trust_receipt.json",
        ),
    ),
    ArtifactFamily(
        "Packet Diff",
        (
            "packet_diff.md",
            "packet_diff.json",
        ),
    ),
    ArtifactFamily(
        "Outcome Memo",
        (
            "support_triage_agent.outcome_memo.md",
            "support_triage_agent.outcome_memo.json",
        ),
    ),
    ArtifactFamily(
        "Review Room",
        (
            "review_room.md",
            "review_room.json",
            "review_room.html",
        ),
    ),
    ArtifactFamily(
        "Proof Health",
        (
            "support_triage_agent.proof_health.md",
            "support_triage_agent.proof_health.json",
        ),
    ),
    ArtifactFamily(
        "Sponsor Readiness",
        (
            "sponsor_live_readiness.md",
            "sponsor_live_readiness.json",
        ),
    ),
    ArtifactFamily(
        "Design Partner Trial",
        (
            "support_triage_trial_report.md",
            "support_triage_trial_report.json",
            "support_triage_trial.packet.md",
            "support_triage_trial.packet.json",
            "support_triage_trial.decision_brief.md",
            "support_triage_trial.decision_brief.json",
        ),
    ),
    ArtifactFamily(
        "Design Partner Outcome Memo",
        (
            "support_triage_trial.outcome_memo.md",
            "support_triage_trial.outcome_memo.json",
        ),
    ),
    ArtifactFamily(
        "Sponsor Evidence Replay",
        (
            "support_triage_trial.evidence_replay.md",
            "support_triage_trial.evidence_replay.json",
        ),
    ),
)

STATIC_REVIEW_ASSETS = (
    "demo_transcript.md",
    "review_room.desktop.jpg",
)

REGENERATION_COMMAND = "python3 -m agent.judge"


def _public_path(file_name: str) -> str:
    return f"examples/generated/{file_name}"


def _expected_file_names() -> set[str]:
    return {file_name for family in GENERATED_ARTIFACT_FAMILIES for file_name in family.files}


def _static_file_names() -> set[str]:
    return set(STATIC_REVIEW_ASSETS)


def _first_difference(expected: bytes, actual: bytes) -> dict[str, Any]:
    expected_text = expected.decode("utf-8", errors="replace").splitlines()
    actual_text = actual.decode("utf-8", errors="replace").splitlines()
    max_len = max(len(expected_text), len(actual_text))
    for index in range(max_len):
        expected_line = expected_text[index] if index < len(expected_text) else "<missing line>"
        actual_line = actual_text[index] if index < len(actual_text) else "<missing line>"
        if expected_line != actual_line:
            return {
                "line": index + 1,
                "expected": expected_line,
                "actual": actual_line,
            }

    max_bytes = max(len(expected), len(actual))
    for index in range(max_bytes):
        expected_byte = expected[index] if index < len(expected) else None
        actual_byte = actual[index] if index < len(actual) else None
        if expected_byte != actual_byte:
            return {
                "byte": index,
                "expected": expected_byte,
                "actual": actual_byte,
            }
    return {"line": 1, "expected": "", "actual": ""}


def _compare_file(actual_dir: Path, expected_dir: Path, file_name: str) -> dict[str, Any]:
    actual_path = actual_dir / file_name
    expected_path = expected_dir / file_name
    public_path = _public_path(file_name)

    if not actual_path.exists():
        return {
            "path": public_path,
            "status": "missing_checked_in",
            "message": f"Checked-in artifact is missing: {public_path}",
        }
    if not expected_path.exists():
        return {
            "path": public_path,
            "status": "missing_regenerated",
            "message": f"Regenerator did not produce: {public_path}",
        }

    actual = actual_path.read_bytes()
    expected = expected_path.read_bytes()
    if actual == expected:
        return {
            "path": public_path,
            "status": "fresh",
            "size_bytes": len(actual),
        }

    return {
        "path": public_path,
        "status": "stale",
        "size_bytes": len(actual),
        "expected_size_bytes": len(expected),
        "first_difference": _first_difference(expected, actual),
    }


def _static_asset_status(actual_dir: Path, file_name: str) -> dict[str, Any]:
    path = actual_dir / file_name
    status = "present"
    message = None
    if not path.exists():
        status = "missing"
        message = f"Static review asset is missing: {_public_path(file_name)}"
    elif not path.is_file():
        status = "invalid"
        message = f"Static review asset is not a file: {_public_path(file_name)}"
    elif path.stat().st_size == 0:
        status = "invalid"
        message = f"Static review asset is empty: {_public_path(file_name)}"
    elif file_name.endswith(".jpg") and not path.read_bytes().startswith(b"\xff\xd8\xff"):
        status = "invalid"
        message = f"Static review asset is not a JPEG file: {_public_path(file_name)}"

    return {
        "path": _public_path(file_name),
        "status": status,
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
        "message": message,
    }


def _family_result(actual_dir: Path, expected_dir: Path, family: ArtifactFamily) -> dict[str, Any]:
    file_results = [_compare_file(actual_dir, expected_dir, file_name) for file_name in family.files]
    failures = [item for item in file_results if item["status"] != "fresh"]
    return {
        "family": family.name,
        "file_count": len(family.files),
        "status": "OK" if not failures else "STALE",
        "files": file_results,
        "stale_count": len(failures),
    }


def verify_artifacts(actual_dir: Path = GENERATED_DIR) -> dict[str, Any]:
    """Regenerate deterministic artifacts into a temp dir and compare them byte-for-byte."""
    actual_dir = actual_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="ia-artifact-verify-") as tmp:
        expected_dir = Path(tmp)
        written = write_judge_artifacts(expected_dir)
        written_names = {path.name for path in written}
        expected_names = _expected_file_names()
        static_names = _static_file_names()
        unexpected_generated = sorted(written_names - expected_names)
        missing_from_regenerator = sorted(expected_names - written_names)
        actual_inventory = list(actual_dir.iterdir()) if actual_dir.exists() and actual_dir.is_dir() else []
        unexpected_checked_in = sorted(
            path.name
            for path in actual_inventory
            if path.is_file() and path.name not in expected_names and path.name not in static_names
        )

        family_results = [
            _family_result(actual_dir, expected_dir, family)
            for family in GENERATED_ARTIFACT_FAMILIES
        ]
        static_assets = [_static_asset_status(actual_dir, file_name) for file_name in STATIC_REVIEW_ASSETS]

    stale_files = [
        file_result
        for family in family_results
        for file_result in family["files"]
        if file_result["status"] != "fresh"
    ]
    missing_static_assets = [asset for asset in static_assets if asset["status"] != "present"]
    total_verified = sum(family["file_count"] for family in family_results)

    return {
        "schema_version": VERIFY_ARTIFACTS_SCHEMA_VERSION,
        "mode": "offline_deterministic",
        "generated_by": "inferenceatlas-agent-demo",
        "actual_dir": str(actual_dir.relative_to(ROOT_DIR) if actual_dir.is_relative_to(ROOT_DIR) else actual_dir),
        "regeneration_command": REGENERATION_COMMAND,
        "status": "ok"
        if not stale_files
        and not missing_static_assets
        and not unexpected_generated
        and not unexpected_checked_in
        and not missing_from_regenerator
        else "fail",
        "summary": {
            "artifact_families": len(family_results),
            "generated_artifacts_verified": total_verified,
            "stale_artifacts": len(stale_files),
            "static_assets_checked": len(static_assets),
            "missing_static_assets": len(missing_static_assets),
            "unexpected_generated_artifacts": len(unexpected_generated),
            "unexpected_checked_in_artifacts": len(unexpected_checked_in),
            "missing_from_regenerator": len(missing_from_regenerator),
        },
        "families": family_results,
        "static_assets": static_assets,
        "unexpected_generated_artifacts": [_public_path(item) for item in unexpected_generated],
        "unexpected_checked_in_artifacts": [_public_path(item) for item in unexpected_checked_in],
        "missing_from_regenerator": [_public_path(item) for item in missing_from_regenerator],
        "failures": {
            "stale_files": stale_files,
            "missing_static_assets": missing_static_assets,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def _format_first_difference(item: dict[str, Any]) -> list[str]:
    diff = item.get("first_difference", {})
    if "line" in diff:
        return [
            f"First difference (line {diff['line']}):",
            f"  - {diff['expected']}",
            f"  + {diff['actual']}",
        ]
    if "byte" in diff:
        return [
            f"First difference (byte {diff['byte']}):",
            f"  - {diff['expected']}",
            f"  + {diff['actual']}",
        ]
    return ["First difference: unavailable"]


def render_verify_report(report: dict[str, Any]) -> str:
    """Render artifact verification as human-readable text."""
    lines = [
        "# Artifact Integrity Gate",
        "",
        "Private engine, public proof.",
        "",
    ]
    for family in report["families"]:
        lines.append(f"{family['family']} ({family['file_count']} files): {family['status']}")

    static_status = "OK" if report["summary"]["missing_static_assets"] == 0 else "FAIL"
    lines.append(f"Static review assets ({report['summary']['static_assets_checked']} files): {static_status}")

    summary = report["summary"]
    lines.extend(
        [
            "",
            "Total: {total} generated artifacts verified - {stale} stale - {static} static assets valid - {unexpected} unexpected checked-in".format(
                total=summary["generated_artifacts_verified"],
                stale=summary["stale_artifacts"],
                static=summary["static_assets_checked"] - summary["missing_static_assets"],
                unexpected=summary["unexpected_checked_in_artifacts"],
            ),
        ]
    )

    stale_files = report["failures"]["stale_files"]
    missing_static_assets = report["failures"]["missing_static_assets"]
    if (
        stale_files
        or missing_static_assets
        or report["unexpected_generated_artifacts"]
        or report["unexpected_checked_in_artifacts"]
        or report["missing_from_regenerator"]
    ):
        lines.extend(["", "## Failures", ""])
        for item in stale_files:
            lines.append(f"x STALE: {item['path']}")
            lines.extend(_format_first_difference(item))
            lines.append("")
        for item in missing_static_assets:
            lines.append(f"x STATIC ASSET {item['status'].upper()}: {item['path']}")
        for item in report["unexpected_generated_artifacts"]:
            lines.append(f"x UNEXPECTED GENERATED ARTIFACT: {item}")
        for item in report["unexpected_checked_in_artifacts"]:
            lines.append(f"x UNEXPECTED CHECKED-IN ARTIFACT: {item}")
        for item in report["missing_from_regenerator"]:
            lines.append(f"x MISSING FROM REGENERATOR: {item}")
        lines.extend(
            [
                "",
                "Regenerate with:",
                f"  {report['regeneration_command']}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.verify_artifacts",
        description="Verify the checked-in public proof inventory.",
    )
    parser.add_argument(
        "--actual-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory containing checked-in generated artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the integrity report as machine-readable JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = verify_artifacts(args.actual_dir)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_verify_report(report))

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
