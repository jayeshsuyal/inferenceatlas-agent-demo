"""Read-only verification artifacts for Packet Authority Snapshot v0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .packet_authority import (
    DEFAULT_SCENARIO,
    build_packet_authority_snapshot,
    derive_decision_lock,
)


PACKET_VERIFICATION_SCHEMA_VERSION = "packet_verification.v0"


def _bool_safety(packet: dict[str, Any], key: str) -> bool:
    return bool(packet.get("safety_state", {}).get(key))


def _production_access(packet: dict[str, Any]) -> bool:
    posture = str(packet.get("approval_posture", {}).get("production_access", "")).lower()
    return posture not in {"", "blocked"} or _bool_safety(packet, "approval_granted")


def _external_writes(packet: dict[str, Any]) -> bool:
    return _bool_safety(packet, "external_writes_enabled")


def _permission_grants(packet: dict[str, Any]) -> bool:
    return _bool_safety(packet, "approval_granted")


def _scoped_validation(packet: dict[str, Any]) -> bool:
    return packet.get("approval_posture", {}).get("validation_review") == "allowed"


def build_verification_artifact(
    packet: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the read-only verification JSON a downstream consumer can inspect."""
    if snapshot is None:
        snapshot = build_packet_authority_snapshot(packet)

    lock_state = derive_decision_lock(packet)
    if lock_state != snapshot["decision_lock_after"]:
        raise ValueError("packet lock state does not match snapshot lock state")

    return {
        "schema_version": PACKET_VERIFICATION_SCHEMA_VERSION,
        "verification_status": "valid_review_required",
        "packet_id": snapshot["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "revision_id": snapshot["revision_id"],
        "content_hash": snapshot["content_hash"],
        "decision_lock": snapshot["decision_lock_after"],
        "production_access": _production_access(packet),
        "external_writes": _external_writes(packet),
        "permission_grants": _permission_grants(packet),
        "approval_granted": _bool_safety(packet, "approval_granted"),
        "scoped_validation": _scoped_validation(packet),
        "blocked_claims": packet.get("blocked_claims", []),
        "missing_proof": packet.get("missing_proof", []),
        "reviewer_owners": packet.get("reviewer_owners", []),
        "next_human_action": snapshot["next_human_action"],
        "safety_invariants": snapshot["safety_invariants"],
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def verification_has_failures(artifact: dict[str, Any]) -> bool:
    """Return True when the public demo verification would unsafe-pass."""
    return (
        artifact["verification_status"] != "valid_review_required"
        or artifact["production_access"]
        or artifact["external_writes"]
        or artifact["permission_grants"]
        or artifact["approval_granted"]
        or artifact["private_boundary"]["private_source_exposed"]
    )


def verification_to_pretty_json(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact, indent=2, sort_keys=True)


def render_verification_summary(artifact: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Packet Verification",
            "",
            "Private engine, public proof.",
            "",
            f"- status: {artifact['verification_status']}",
            f"- packet_id: `{artifact['packet_id']}`",
            f"- revision_id: `{artifact['revision_id']}`",
            f"- content_hash: `{artifact['content_hash']}`",
            f"- decision_lock: {artifact['decision_lock']}",
            f"- scoped_validation: {artifact['scoped_validation']}",
            f"- production_access: {artifact['production_access']}",
            f"- external_writes: {artifact['external_writes']}",
            f"- permission_grants: {artifact['permission_grants']}",
            f"- next_human_action: {artifact['next_human_action']}",
            "",
        ]
    )


def write_verification_artifacts(output_dir: Path | None = None) -> list[Path]:
    """Write verification JSON artifacts for every registered scenario."""
    from .scenarios import GENERATED_DIR, SCENARIOS, build_scenario_packet

    if output_dir is None:
        output_dir = GENERATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        snapshot = build_packet_authority_snapshot(packet)
        artifact = build_verification_artifact(packet, snapshot=snapshot)
        path = output_dir / f"{scenario_name}.verification.json"
        path.write_text(verification_to_pretty_json(artifact) + "\n", encoding="utf-8")
        written.append(path)
    return written


def _scenario_packet(scenario_or_packet_id: str) -> tuple[str, dict[str, Any]]:
    from .scenarios import SCENARIOS, build_scenario_packet

    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        if scenario_or_packet_id in {scenario_name, packet["packet_id"]}:
            return scenario_name, packet
    raise ValueError(f"unknown scenario or packet_id: {scenario_or_packet_id}")


def _scenario_names() -> list[str]:
    from .scenarios import SCENARIOS

    return list(SCENARIOS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.verification",
        description="Verify a public Packet Authority Snapshot v0 state.",
    )
    parser.add_argument(
        "scenario_or_packet_id",
        nargs="?",
        default=DEFAULT_SCENARIO,
        help="Scenario name or packet_id to verify.",
    )
    parser.add_argument("--all", action="store_true", help="Verify all scenarios.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable verification JSON.")
    parser.add_argument("--write", action="store_true", help="Write verification artifacts for all scenarios.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for --write.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.write:
        from .scenarios import ROOT_DIR

        for path in write_verification_artifacts(args.output_dir):
            print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
        return 0

    if args.all:
        artifacts = []
        for scenario_name in _scenario_names():
            _, packet = _scenario_packet(scenario_name)
            artifacts.append(build_verification_artifact(packet))
        if args.json:
            print(json.dumps({"results": artifacts}, indent=2, sort_keys=True))
        else:
            for artifact in artifacts:
                print(render_verification_summary(artifact))
        return 1 if any(verification_has_failures(artifact) for artifact in artifacts) else 0

    _, packet = _scenario_packet(args.scenario_or_packet_id)
    artifact = build_verification_artifact(packet)
    if args.json:
        print(verification_to_pretty_json(artifact))
    else:
        print(render_verification_summary(artifact))
    return 1 if verification_has_failures(artifact) else 0


if __name__ == "__main__":
    sys.exit(main())
