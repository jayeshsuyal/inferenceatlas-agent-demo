"""Canonical Packet Authority Snapshot v0.

The DecisionPacket remains the source packet. This module gives each packet a
stable identity, content hash, revision, and decision-lock record so downstream
readers can verify the packet without owning the packet engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKET_AUTHORITY_SNAPSHOT_SCHEMA_VERSION = "packet_authority_snapshot.v0"
SNAPSHOT_GENERATOR = "inferenceatlas-agent-demo"
DEFAULT_SCENARIO = "support_triage_agent"

_LOCK_STRENGTH = {
    "approval_granted": 0,
    "read_only_validation": 1,
    "scoped_validation_only": 1,
    "blocked": 2,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def stable_sha256(value: Any) -> str:
    """Return a deterministic sha256 digest for JSON-serializable payloads."""
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "allowed", "approved"}
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value) if value is not None else False


def derive_decision_lock(packet: dict[str, Any]) -> str:
    """Map a DecisionPacket into the compact lock state used by verification."""
    safety = packet.get("safety_state", {})
    posture = packet.get("approval_posture", {})

    if _truthy(safety.get("approval_granted")):
        return "approval_granted"

    production_posture = str(posture.get("production_access", "")).lower()
    if production_posture and production_posture != "blocked":
        return "approval_granted"

    if posture.get("validation_review") != "allowed":
        return "blocked"

    if posture.get("write_access") == "not_requested":
        return "read_only_validation"

    return "scoped_validation_only"


def assert_decision_lock_not_weakened(before: str, after: str) -> None:
    """Fail closed when evidence or a caller tries to loosen the lock state."""
    if before not in _LOCK_STRENGTH:
        raise ValueError(f"unknown decision_lock_before: {before}")
    if after not in _LOCK_STRENGTH:
        raise ValueError(f"unknown decision_lock_after: {after}")
    if _LOCK_STRENGTH[after] < _LOCK_STRENGTH[before]:
        raise ValueError(f"decision lock weakened: {before} -> {after}")


def _safety_invariants(packet: dict[str, Any]) -> tuple[str, ...]:
    safety = packet.get("safety_state", {})
    posture = packet.get("approval_posture", {})
    return (
        f"approval_granted={bool(safety.get('approval_granted'))}",
        f"production_access={posture.get('production_access', 'unknown')}",
        f"external_writes_enabled={bool(safety.get('external_writes_enabled'))}",
        f"packet_state_mutation={bool(safety.get('packet_state_mutation'))}",
        f"requires_human_approval={bool(safety.get('requires_human_approval'))}",
    )


def _locked_fields() -> tuple[str, ...]:
    return (
        "decision.verdict",
        "approval_posture.production_access",
        "approval_posture.validation_review",
        "approval_posture.write_access",
        "safety_state.approval_granted",
        "safety_state.external_writes_enabled",
        "safety_state.requires_human_approval",
    )


@dataclass(frozen=True)
class PacketAuthoritySnapshot:
    schema_version: str
    snapshot_id: str
    packet_id: str
    revision_id: str
    content_hash: str
    decision_lock_before: str
    decision_lock_after: str
    evidence_receipt_ids: tuple[str, ...]
    accepted_evidence: tuple[dict[str, str], ...]
    rejected_evidence: tuple[dict[str, str], ...]
    locked_fields: tuple[str, ...]
    next_human_action: str
    safety_invariants: tuple[str, ...]
    generated_by: str
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "packet_id": self.packet_id,
            "revision_id": self.revision_id,
            "content_hash": self.content_hash,
            "decision_lock_before": self.decision_lock_before,
            "decision_lock_after": self.decision_lock_after,
            "evidence_receipt_ids": list(self.evidence_receipt_ids),
            "accepted_evidence": [dict(item) for item in self.accepted_evidence],
            "rejected_evidence": [dict(item) for item in self.rejected_evidence],
            "locked_fields": list(self.locked_fields),
            "next_human_action": self.next_human_action,
            "safety_invariants": list(self.safety_invariants),
            "generated_by": self.generated_by,
            "mode": self.mode,
        }


def _normalize_evidence(items: tuple[dict[str, str], ...] | list[dict[str, str]] | None) -> tuple[dict[str, str], ...]:
    return tuple(dict(item) for item in (items or ()))


def build_packet_authority_snapshot(
    packet: dict[str, Any],
    *,
    evidence_receipt_ids: tuple[str, ...] | list[str] | None = None,
    accepted_evidence: tuple[dict[str, str], ...] | list[dict[str, str]] | None = None,
    rejected_evidence: tuple[dict[str, str], ...] | list[dict[str, str]] | None = None,
    decision_lock_before: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic authority snapshot from a DecisionPacket."""
    receipt_ids = tuple(evidence_receipt_ids or ())
    accepted = _normalize_evidence(accepted_evidence)
    rejected = _normalize_evidence(rejected_evidence)
    lock_after = derive_decision_lock(packet)
    lock_before = decision_lock_before or lock_after
    assert_decision_lock_not_weakened(lock_before, lock_after)

    source_payload = {
        "packet": packet,
        "evidence_receipt_ids": list(receipt_ids),
        "accepted_evidence": [dict(item) for item in accepted],
        "rejected_evidence": [dict(item) for item in rejected],
        "decision_lock_before": lock_before,
        "decision_lock_after": lock_after,
    }
    digest = stable_sha256(source_payload)
    revision_id = f"rev_{digest[:16]}"
    packet_id = str(packet["packet_id"])

    snapshot = PacketAuthoritySnapshot(
        schema_version=PACKET_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
        snapshot_id=f"{packet_id}:{revision_id}",
        packet_id=packet_id,
        revision_id=revision_id,
        content_hash=f"sha256:{digest}",
        decision_lock_before=lock_before,
        decision_lock_after=lock_after,
        evidence_receipt_ids=receipt_ids,
        accepted_evidence=accepted,
        rejected_evidence=rejected,
        locked_fields=_locked_fields(),
        next_human_action=str(packet.get("next_validation", {}).get("action", "human review required")),
        safety_invariants=_safety_invariants(packet),
        generated_by=SNAPSHOT_GENERATOR,
        mode=str(packet.get("mode", "offline_deterministic")),
    )
    return snapshot.to_dict()


def snapshot_to_pretty_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True)


def render_snapshot_summary(snapshot: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Packet Authority Snapshot",
            "",
            "Private engine, public proof.",
            "",
            f"- packet_id: `{snapshot['packet_id']}`",
            f"- revision_id: `{snapshot['revision_id']}`",
            f"- content_hash: `{snapshot['content_hash']}`",
            f"- decision_lock_before: {snapshot['decision_lock_before']}",
            f"- decision_lock_after: {snapshot['decision_lock_after']}",
            f"- evidence_receipts: {len(snapshot['evidence_receipt_ids'])}",
            f"- next_human_action: {snapshot['next_human_action']}",
            "",
        ]
    )


def write_packet_authority_artifacts(output_dir: Path | None = None) -> list[Path]:
    """Write snapshot JSON artifacts for every registered scenario."""
    from .scenarios import GENERATED_DIR, SCENARIOS, build_scenario_packet

    if output_dir is None:
        output_dir = GENERATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        snapshot = build_packet_authority_snapshot(packet)
        path = output_dir / f"{scenario_name}.snapshot.json"
        path.write_text(snapshot_to_pretty_json(snapshot) + "\n", encoding="utf-8")
        written.append(path)
    return written


def _scenario_packet(scenario_name: str) -> dict[str, Any]:
    from .scenarios import SCENARIOS, build_scenario_packet

    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    return build_scenario_packet(scenario_name)


def _scenario_names() -> list[str]:
    from .scenarios import SCENARIOS

    return list(SCENARIOS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.packet_authority",
        description="Build Packet Authority Snapshot v0 artifacts.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=_scenario_names())
    parser.add_argument("--all", action="store_true", help="Write snapshots for all scenarios.")
    parser.add_argument("--json", action="store_true", help="Print the selected snapshot as JSON.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for --all.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.all:
        from .scenarios import ROOT_DIR

        for path in write_packet_authority_artifacts(args.output_dir):
            print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
        return 0

    snapshot = build_packet_authority_snapshot(_scenario_packet(args.scenario))
    if args.json:
        print(snapshot_to_pretty_json(snapshot))
    else:
        print(render_snapshot_summary(snapshot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
