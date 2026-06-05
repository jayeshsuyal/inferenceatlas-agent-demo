"""Deterministic Evidence Receipt Ledger v0.

Receipts attach proof context to a DecisionPacket without approving access,
granting permissions, reducing proof debt automatically, or changing the
packet decision lock.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .packet_authority import (
    build_packet_authority_snapshot,
    derive_decision_lock,
    stable_sha256,
)


EVIDENCE_RECEIPT_LEDGER_SCHEMA_VERSION = "evidence_receipt_ledger.v0"
RECEIPT_GENERATOR = "inferenceatlas-agent-demo"
DEFAULT_SCENARIO = "support_triage_agent"


@dataclass(frozen=True)
class EvidenceReceipt:
    receipt_id: str
    receipt_type: str
    packet_id: str
    scenario: str
    owner: str
    source: str
    status: str
    attaches_to: str
    claim: str
    evidence_summary: str
    unblocks: str
    review_required_by: str
    safety_boundary: dict[str, bool]
    controls: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "receipt_type": self.receipt_type,
            "packet_id": self.packet_id,
            "scenario": self.scenario,
            "owner": self.owner,
            "source": self.source,
            "status": self.status,
            "attaches_to": self.attaches_to,
            "claim": self.claim,
            "evidence_summary": self.evidence_summary,
            "unblocks": self.unblocks,
            "review_required_by": self.review_required_by,
            "safety_boundary": dict(self.safety_boundary),
            "controls": [dict(item) for item in self.controls],
        }


def _receipt_id(packet_id: str, receipt_type: str, owner: str, claim: str) -> str:
    seed = {
        "packet_id": packet_id,
        "receipt_type": receipt_type,
        "owner": owner,
        "claim": claim,
    }
    return f"er_{stable_sha256(seed)[:16]}"


def _safe_boundary() -> dict[str, bool]:
    return {
        "approves_access": False,
        "grants_permissions": False,
        "enables_production_access": False,
        "executes_external_writes": False,
        "mutates_packet_state": False,
        "reduces_proof_debt_automatically": False,
        "requires_human_review": True,
    }


def _build_receipt(
    *,
    packet_id: str,
    scenario: str,
    receipt_type: str,
    owner: str,
    source: str,
    status: str,
    attaches_to: str,
    claim: str,
    evidence_summary: str,
    unblocks: str,
    review_required_by: str,
    controls: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    receipt = EvidenceReceipt(
        receipt_id=_receipt_id(packet_id, receipt_type, owner, claim),
        receipt_type=receipt_type,
        packet_id=packet_id,
        scenario=scenario,
        owner=owner,
        source=source,
        status=status,
        attaches_to=attaches_to,
        claim=claim,
        evidence_summary=evidence_summary,
        unblocks=unblocks,
        review_required_by=review_required_by,
        safety_boundary=_safe_boundary(),
        controls=controls,
    )
    return receipt.to_dict()


def _tool_scope_receipts(packet: dict[str, Any], scenario_name: str) -> list[dict[str, Any]]:
    receipts = []
    for tool_name, plan in packet["tool_access_plan"].items():
        receipts.append(
            _build_receipt(
                packet_id=packet["packet_id"],
                scenario=scenario_name,
                receipt_type="tool_scope_receipt",
                owner="Engineering",
                source=f"packet.tool_access_plan.{tool_name}",
                status="needs_named_owner_review",
                attaches_to=f"tool_access_plan.{tool_name}",
                claim=f"{tool_name} stays within validation allowance until required proof is reviewed.",
                evidence_summary=(
                    f"Requested={plan['requested']}; validation={plan['demo_allowance']}; "
                    f"blocked={', '.join(plan['blocked_actions'])}."
                ),
                unblocks=f"{tool_name} validation boundary review",
                review_required_by="Engineering",
                controls=(
                    {"control": "dry_run_default", "value": "external writes disabled"},
                    {"control": "blocked_actions", "value": ", ".join(plan["blocked_actions"])},
                    {"control": "required_proof", "value": ", ".join(plan["required_proof"])},
                ),
            )
        )
    return receipts


def _missing_proof_receipts(packet: dict[str, Any], scenario_name: str) -> list[dict[str, Any]]:
    receipts = []
    for proof in packet["missing_proof"]:
        receipts.append(
            _build_receipt(
                packet_id=packet["packet_id"],
                scenario=scenario_name,
                receipt_type="proof_debt_receipt",
                owner=proof["owner"],
                source="packet.missing_proof",
                status="missing_human_confirmation",
                attaches_to="missing_proof",
                claim=proof["item"],
                evidence_summary="Proof is named and owner-routed; it is not accepted yet.",
                unblocks=proof["unblocks"],
                review_required_by=proof["owner"],
                controls=(
                    {"control": "human_review_required", "value": "true"},
                    {"control": "auto_reduce_proof_debt", "value": "false"},
                ),
            )
        )
    return receipts


def _finance_receipt(packet: dict[str, Any], scenario_name: str) -> dict[str, Any]:
    requested_systems = ", ".join(packet["tool_access_plan"])
    return _build_receipt(
        packet_id=packet["packet_id"],
        scenario=scenario_name,
        receipt_type="cost_procurement_receipt",
        owner="Procurement/Finance",
        source="public_cost_control_contract",
        status="budget_owner_review_required",
        attaches_to="approval_posture.production_access",
        claim="Tool, model, token, and vendor spend must stay capped until a budget owner signs the pilot envelope.",
        evidence_summary=(
            f"Requested systems: {requested_systems}. Public default is no live spend, no paid-seat grant, "
            "and no production access until budget owner review."
        ),
        unblocks="paid tool/vendor spend review if live actions or seats are enabled",
        review_required_by="Procurement/Finance",
        controls=(
            {"control": "budget_owner_required", "value": "true"},
            {"control": "token_or_tool_spend_cap_required", "value": "true"},
            {"control": "paid_seat_or_vendor_change_requires_review", "value": "true"},
            {"control": "default_public_live_spend", "value": "false"},
        ),
    )


def _reviewer_receipts(packet: dict[str, Any], scenario_name: str) -> list[dict[str, Any]]:
    receipts = []
    for reviewer in packet["reviewer_owners"]:
        receipts.append(
            _build_receipt(
                packet_id=packet["packet_id"],
                scenario=scenario_name,
                receipt_type="reviewer_route_receipt",
                owner=reviewer["owner"],
                source="packet.reviewer_owners",
                status=reviewer["current_state"],
                attaches_to="reviewer_owners",
                claim=f"{reviewer['owner']} owns review for {reviewer['review_area']}.",
                evidence_summary="Reviewer route is explicit; approval is not inferred.",
                unblocks=reviewer["review_area"],
                review_required_by=reviewer["owner"],
                controls=(
                    {"control": "approval_inferred", "value": "false"},
                    {"control": "named_owner_required", "value": "true"},
                ),
            )
        )
    return receipts


def build_evidence_receipts(packet: dict[str, Any], scenario_name: str = DEFAULT_SCENARIO) -> list[dict[str, Any]]:
    """Build deterministic receipts that attach to a packet without changing its lock."""
    return [
        *_tool_scope_receipts(packet, scenario_name),
        *_missing_proof_receipts(packet, scenario_name),
        _finance_receipt(packet, scenario_name),
        *_reviewer_receipts(packet, scenario_name),
    ]


def build_evidence_receipt_ledger(
    packet: dict[str, Any],
    scenario_name: str = DEFAULT_SCENARIO,
    *,
    include_snapshot: bool = True,
) -> dict[str, Any]:
    """Build the ledger consumed by Packet Authority Snapshot v0."""
    lock_before = derive_decision_lock(packet)
    receipts = build_evidence_receipts(packet, scenario_name)
    receipt_ids = [receipt["receipt_id"] for receipt in receipts]
    accepted_evidence = [
        {
            "receipt_id": receipt["receipt_id"],
            "receipt_type": receipt["receipt_type"],
            "status": receipt["status"],
        }
        for receipt in receipts
    ]
    snapshot = (
        build_packet_authority_snapshot(
            packet,
            evidence_receipt_ids=receipt_ids,
            accepted_evidence=accepted_evidence,
            decision_lock_before=lock_before,
        )
        if include_snapshot
        else None
    )
    lock_after = snapshot["decision_lock_after"] if snapshot else lock_before
    if lock_before != lock_after:
        raise ValueError(f"evidence receipts changed packet decision lock: {lock_before} -> {lock_after}")

    safety = {
        "receipt_count": len(receipts),
        "all_require_human_review": all(
            receipt["safety_boundary"]["requires_human_review"] for receipt in receipts
        ),
        "all_non_approving": all(not receipt["safety_boundary"]["approves_access"] for receipt in receipts),
        "all_non_granting": all(not receipt["safety_boundary"]["grants_permissions"] for receipt in receipts),
        "all_non_executing": all(not receipt["safety_boundary"]["executes_external_writes"] for receipt in receipts),
        "all_non_mutating": all(not receipt["safety_boundary"]["mutates_packet_state"] for receipt in receipts),
        "all_non_auto_reducing": all(
            not receipt["safety_boundary"]["reduces_proof_debt_automatically"] for receipt in receipts
        ),
        "decision_lock_preserved": lock_before == lock_after,
    }

    return {
        "schema_version": EVIDENCE_RECEIPT_LEDGER_SCHEMA_VERSION,
        "ledger_id": f"{packet['packet_id']}:evidence_receipts:v0",
        "generated_by": RECEIPT_GENERATOR,
        "mode": str(packet.get("mode", "offline_deterministic")),
        "scenario": scenario_name,
        "packet_id": packet["packet_id"],
        "decision_lock_before": lock_before,
        "decision_lock_after": lock_after,
        "snapshot_id": snapshot["snapshot_id"] if snapshot else None,
        "snapshot_revision_id": snapshot["revision_id"] if snapshot else None,
        "snapshot_content_hash": snapshot["content_hash"] if snapshot else None,
        "receipt_ids": receipt_ids,
        "accepted_evidence": accepted_evidence,
        "summary": {
            "receipt_count": len(receipts),
            "tool_scope_receipts": sum(receipt["receipt_type"] == "tool_scope_receipt" for receipt in receipts),
            "proof_debt_receipts": sum(receipt["receipt_type"] == "proof_debt_receipt" for receipt in receipts),
            "reviewer_route_receipts": sum(receipt["receipt_type"] == "reviewer_route_receipt" for receipt in receipts),
            "cost_procurement_receipts": sum(
                receipt["receipt_type"] == "cost_procurement_receipt" for receipt in receipts
            ),
        },
        "safety": safety,
        "receipts": receipts,
        "finance_procurement": {
            "owner": "Procurement/Finance",
            "receipt_type": "cost_procurement_receipt",
            "spend_claim": "No live model/tool/vendor spend is approved by the public receipt ledger.",
            "budget_owner_required": True,
            "token_or_tool_spend_cap_required": True,
            "approval_granted": False,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def ledger_has_failures(ledger: dict[str, Any]) -> bool:
    safety = ledger["safety"]
    return (
        ledger["decision_lock_before"] != ledger["decision_lock_after"]
        or not safety["decision_lock_preserved"]
        or not safety["all_require_human_review"]
        or not safety["all_non_approving"]
        or not safety["all_non_granting"]
        or not safety["all_non_executing"]
        or not safety["all_non_mutating"]
        or not safety["all_non_auto_reducing"]
        or ledger["finance_procurement"]["approval_granted"]
        or ledger["private_boundary"]["private_source_exposed"]
    )


def ledger_to_pretty_json(ledger: dict[str, Any]) -> str:
    return json.dumps(ledger, indent=2, sort_keys=True)


def render_ledger_markdown(ledger: dict[str, Any]) -> str:
    summary = ledger["summary"]
    safety = ledger["safety"]
    finance = ledger["finance_procurement"]
    lines = [
        "# Evidence Receipt Ledger",
        "",
        "Private engine, public proof.",
        "",
        "Receipts attach proof context to a packet without changing the packet decision lock.",
        "",
        f"- scenario: `{ledger['scenario']}`",
        f"- packet_id: `{ledger['packet_id']}`",
        f"- decision lock: {ledger['decision_lock_before']} -> {ledger['decision_lock_after']}",
        f"- snapshot revision: `{ledger['snapshot_revision_id']}`",
        f"- receipts: {summary['receipt_count']}",
        f"- tool scope receipts: {summary['tool_scope_receipts']}",
        f"- proof debt receipts: {summary['proof_debt_receipts']}",
        f"- reviewer route receipts: {summary['reviewer_route_receipts']}",
        f"- cost/procurement receipts: {summary['cost_procurement_receipts']}",
        "",
        "## Safety",
        "",
        f"- decision lock preserved: {safety['decision_lock_preserved']}",
        f"- all require human review: {safety['all_require_human_review']}",
        f"- all non-approving: {safety['all_non_approving']}",
        f"- all non-granting: {safety['all_non_granting']}",
        f"- all non-executing: {safety['all_non_executing']}",
        f"- all non-mutating: {safety['all_non_mutating']}",
        f"- all non-auto-reducing: {safety['all_non_auto_reducing']}",
        "",
        "## Finance / Procurement",
        "",
        f"- owner: {finance['owner']}",
        f"- spend claim: {finance['spend_claim']}",
        f"- budget owner required: {finance['budget_owner_required']}",
        f"- token/tool spend cap required: {finance['token_or_tool_spend_cap_required']}",
        f"- approval granted: {finance['approval_granted']}",
        "",
        "## Receipt Types",
        "",
        "| Receipt Type | Owner | Status | Can Approve | Requires Human Review |",
        "| --- | --- | --- | --- | --- |",
    ]
    for receipt in ledger["receipts"]:
        safety_boundary = receipt["safety_boundary"]
        lines.append(
            "| {receipt_type} | {owner} | {status} | {approve} | {review} |".format(
                receipt_type=receipt["receipt_type"],
                owner=receipt["owner"],
                status=receipt["status"],
                approve=safety_boundary["approves_access"],
                review=safety_boundary["requires_human_review"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_evidence_receipt_artifacts(output_dir: Path | None = None) -> list[Path]:
    """Write receipt ledger Markdown/JSON artifacts for every registered scenario."""
    from .scenarios import GENERATED_DIR, SCENARIOS, build_scenario_packet

    if output_dir is None:
        output_dir = GENERATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario_name in SCENARIOS:
        packet = build_scenario_packet(scenario_name)
        ledger = build_evidence_receipt_ledger(packet, scenario_name)
        ledger_md = output_dir / f"{scenario_name}.evidence_receipts.md"
        ledger_json = output_dir / f"{scenario_name}.evidence_receipts.json"
        ledger_md.write_text(render_ledger_markdown(ledger), encoding="utf-8")
        ledger_json.write_text(ledger_to_pretty_json(ledger) + "\n", encoding="utf-8")
        written.extend([ledger_md, ledger_json])
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
        prog="python -m agent.evidence_receipts",
        description="Generate deterministic Evidence Receipt Ledger v0 artifacts.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=_scenario_names())
    parser.add_argument("--all", action="store_true", help="Write evidence receipt ledgers for all scenarios.")
    parser.add_argument("--json", action="store_true", help="Print the selected ledger as JSON.")
    parser.add_argument("--no-write", action="store_true", help="Skip writing artifacts for the selected ledger.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for --all or selected writes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.all:
        from .scenarios import ROOT_DIR

        for path in write_evidence_receipt_artifacts(args.output_dir):
            print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
        return 0

    packet = _scenario_packet(args.scenario)
    ledger = build_evidence_receipt_ledger(packet, args.scenario)
    if not args.no_write:
        from .scenarios import GENERATED_DIR, ROOT_DIR

        output_dir = args.output_dir or GENERATED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"{args.scenario}.evidence_receipts.md"
        json_path = output_dir / f"{args.scenario}.evidence_receipts.json"
        md_path.write_text(render_ledger_markdown(ledger), encoding="utf-8")
        json_path.write_text(ledger_to_pretty_json(ledger) + "\n", encoding="utf-8")
        if not args.json:
            for path in (md_path, json_path):
                print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)

    if args.json:
        print(ledger_to_pretty_json(ledger))
    elif args.no_write:
        print(render_ledger_markdown(ledger))
    return 1 if ledger_has_failures(ledger) else 0


if __name__ == "__main__":
    sys.exit(main())
