"""Public AI spend review packet for Finance and Procurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scenarios import GENERATED_DIR, ROOT_DIR


SPEND_REVIEW_SCHEMA_VERSION = "ai_spend_review_packet.v0"
FINANCE_RECEIPT_SCHEMA_VERSION = "finance_evidence_receipt.v0"
PROCUREMENT_MEMO_SCHEMA_VERSION = "procurement_review_memo.v0"
SPEND_SCENARIO_ID = "ai_spend_budget_overrun"

SPEND_REVIEW_QUESTION = (
    "Our team spent the 2026 AI budget in Q1. Should we cap usage, switch model "
    "classes, or renegotiate vendor terms?"
)

_FORBIDDEN_SPEND_CLAIM_PATTERNS = (
    r"approved\s+spend",
    r"spend\s+approved",
    r"guaranteed\s+savings",
    r"will\s+save\s+\$",
    r"saved\s+\$[\d,]+",
    r"\d+%\s+savings?",
    r"final\s+winner",
    r"best\s+provider",
    r"vendor\s+selected",
)


@dataclass(frozen=True)
class SpendReviewRequest:
    """Stable public request for AI spend review."""

    scenario_id: str
    question: str
    environment: str
    requested_decision: str
    data_classes: tuple[str, ...]
    budget_period: str
    spend_signal: str


DEFAULT_SPEND_REQUEST = SpendReviewRequest(
    scenario_id=SPEND_SCENARIO_ID,
    question=SPEND_REVIEW_QUESTION,
    environment="prod",
    requested_decision="spend_review",
    data_classes=(
        "vendor_invoice_evidence",
        "per_team_usage_metrics",
        "contract_terms",
        "budget_owner_attestation",
    ),
    budget_period="2026_Q1",
    spend_signal="budget_exhausted_early",
)


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contains_forbidden_spend_claim(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in _FORBIDDEN_SPEND_CLAIM_PATTERNS)


def build_spend_review_packet(
    request: SpendReviewRequest = DEFAULT_SPEND_REQUEST,
    *,
    mode: str = "offline_deterministic",
) -> dict[str, Any]:
    """Build the public AI spend review packet without approving spend."""
    packet_id = f"ia-spend-review-{request.scenario_id}-v0"
    packet = {
        "schema_version": SPEND_REVIEW_SCHEMA_VERSION,
        "packet_id": packet_id,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": mode,
        "scenario": request.scenario_id,
        "decision": {
            "question": request.question,
            "requested_decision": request.requested_decision,
            "verdict_class": "finance_procurement_review_required",
            "review_posture": (
                "Do not approve spend changes, vendor switches, or savings claims until "
                "Finance and Procurement review invoice, usage, and contract evidence."
            ),
        },
        "spend_posture": {
            "live_spend_approved": False,
            "usage_cap_approved": False,
            "vendor_switch_approved": False,
            "renegotiation_approved": False,
            "savings_guaranteed": False,
            "provider_winner_selected": False,
            "default_public_state": "review_packet_only",
        },
        "requested_finance_decision": {
            "budget_period": request.budget_period,
            "spend_signal": request.spend_signal,
            "decision_options_under_review": [
                "usage cap",
                "model class shift",
                "vendor contract renegotiation",
            ],
        },
        "required_evidence": [
            {
                "evidence": "vendor invoices for the budget period",
                "owner": "Finance",
                "unblocks": "baseline spend confirmation",
            },
            {
                "evidence": "per-team usage metrics with workload labels",
                "owner": "AI Platform / Engineering",
                "unblocks": "usage ownership and workload fit review",
            },
            {
                "evidence": "contract terms, minimums, credits, and renewal dates",
                "owner": "Procurement",
                "unblocks": "renegotiation or vendor-change review",
            },
            {
                "evidence": "budget owner approval for any cap, shift, or expansion",
                "owner": "Finance",
                "unblocks": "human decision on spend controls",
            },
        ],
        "blocked_claims": [
            {
                "claim": "AI spend changes are approved.",
                "reason": "The packet has no invoice-backed Finance approval.",
            },
            {
                "claim": "Provider-switch savings are already proven.",
                "reason": "Savings require invoice, usage, contract, latency, and quality evidence.",
            },
            {
                "claim": "A provider decision is already selected.",
                "reason": "Procurement has not reviewed contract terms or operational risk.",
            },
            {
                "claim": "The team can expand live model or tool spend.",
                "reason": "Budget owner approval and spend cap proof are missing.",
            },
        ],
        "reviewer_owners": [
            {
                "owner": "Finance",
                "review_area": "budget baseline, invoice evidence, owner approval",
                "current_state": "required_before_spend_change",
            },
            {
                "owner": "Procurement",
                "review_area": "contract terms, vendor risk, renegotiation path",
                "current_state": "required_before_vendor_change",
            },
            {
                "owner": "AI Platform / Engineering",
                "review_area": "usage metrics, workload fit, quality and latency constraints",
                "current_state": "required_before_model_class_shift",
            },
        ],
        "next_human_action": {
            "action": (
                "Attach invoice, usage, and contract evidence, then run a Finance and "
                "Procurement review before any spend control or vendor-change decision."
            ),
            "owner": "Finance + Procurement",
            "success_criteria": [
                "invoice baseline confirmed",
                "per-team usage owner mapped",
                "contract terms reviewed",
                "budget owner names the approved next action",
            ],
        },
        "safety_state": {
            "approval_granted": False,
            "spend_approved": False,
            "external_writes_enabled": False,
            "provider_winner_selected": False,
            "savings_guaranteed": False,
            "requires_human_approval": True,
        },
        "private_boundary": {
            "private_v1_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }
    packet["content_hash"] = f"sha256:{_stable_digest(packet)}"
    return packet


def build_finance_evidence_receipt(packet: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Finance evidence receipt for the spend packet."""
    packet = packet or build_spend_review_packet()
    receipt = {
        "schema_version": FINANCE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"{packet['packet_id']}:finance-evidence:v0",
        "packet_id": packet["packet_id"],
        "content_hash": packet["content_hash"],
        "review_owner": "Finance",
        "evidence_required": [
            "vendor invoices for the review period",
            "team-level usage metrics",
            "budget owner attestation",
        ],
        "blocked_until": [
            "budget baseline is confirmed",
            "usage owner is mapped",
            "spend cap or expansion owner is named",
        ],
        "safety_boundary": {
            "approves_spend": False,
            "guarantees_savings": False,
            "selects_provider": False,
            "executes_external_writes": False,
            "requires_human_review": True,
        },
    }
    receipt["content_hash"] = f"sha256:{_stable_digest(receipt)}"
    return receipt


def build_procurement_review_memo(packet: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Procurement review memo for vendor or contract changes."""
    packet = packet or build_spend_review_packet()
    memo = {
        "schema_version": PROCUREMENT_MEMO_SCHEMA_VERSION,
        "memo_id": f"{packet['packet_id']}:procurement-memo:v0",
        "packet_id": packet["packet_id"],
        "packet_content_hash": packet["content_hash"],
        "decision": "review_required",
        "summary": (
            "Procurement can review contract terms and vendor-change paths, but this "
            "memo does not approve a vendor switch or guarantee savings."
        ),
        "required_review": [
            "current contract minimums, credits, renewal dates, and termination terms",
            "security and data-processing obligations for any candidate vendor",
            "quality, latency, support, and migration risk evidence",
            "Finance approval for any cap, expansion, or contract amendment",
        ],
        "blocked_claims": [
            "vendor switch is approved",
            "provider decision is already selected",
            "savings evidence is already complete",
            "live spend may expand",
        ],
        "next_human_action": packet["next_human_action"]["action"],
        "safety_boundary": {
            "approves_spend": False,
            "guarantees_savings": False,
            "selects_provider": False,
            "executes_external_writes": False,
            "requires_human_review": True,
        },
    }
    memo["content_hash"] = f"sha256:{_stable_digest(memo)}"
    return memo


def spend_review_has_forbidden_claims(*surfaces: str) -> bool:
    """Return True if a spend review surface contains a forbidden outcome claim."""
    return any(_contains_forbidden_spend_claim(surface) for surface in surfaces)


def spend_packet_to_pretty_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, indent=2, sort_keys=True)


def render_spend_review_packet_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# AI Spend Review Packet",
        "",
        "Private engine, public proof.",
        "",
        f"- scenario: `{packet['scenario']}`",
        f"- packet_id: `{packet['packet_id']}`",
        f"- content_hash: `{packet['content_hash']}`",
        f"- verdict_class: {packet['decision']['verdict_class']}",
        f"- live spend approved: {packet['spend_posture']['live_spend_approved']}",
        f"- provider winner selected: {packet['spend_posture']['provider_winner_selected']}",
        f"- savings guaranteed: {packet['spend_posture']['savings_guaranteed']}",
        "",
        "## Review Posture",
        "",
        packet["decision"]["review_posture"],
        "",
        "## Required Evidence",
        "",
    ]
    for item in packet["required_evidence"]:
        lines.append(
            "- {evidence} — owner: {owner}; unblocks: {unblocks}".format(**item)
        )
    lines.extend(["", "## Blocked Claims", ""])
    for item in packet["blocked_claims"]:
        lines.append(f"- {item['claim']} Reason: {item['reason']}")
    lines.extend(["", "## Reviewers", ""])
    for item in packet["reviewer_owners"]:
        lines.append(
            "- {owner}: {review_area} ({current_state})".format(**item)
        )
    lines.extend(
        [
            "",
            "## Next Human Action",
            "",
            packet["next_human_action"]["action"],
            "",
        ]
    )
    return "\n".join(lines)


def render_finance_receipt_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Finance Evidence Receipt",
        "",
        "Private engine, public proof.",
        "",
        f"- receipt_id: `{receipt['receipt_id']}`",
        f"- packet_id: `{receipt['packet_id']}`",
        f"- review_owner: {receipt['review_owner']}",
        f"- approves spend: {receipt['safety_boundary']['approves_spend']}",
        f"- guarantees savings: {receipt['safety_boundary']['guarantees_savings']}",
        "",
        "## Evidence Required",
        "",
    ]
    lines.extend(f"- {item}" for item in receipt["evidence_required"])
    lines.extend(["", "## Blocked Until", ""])
    lines.extend(f"- {item}" for item in receipt["blocked_until"])
    lines.append("")
    return "\n".join(lines)


def render_procurement_memo_markdown(memo: dict[str, Any]) -> str:
    lines = [
        "# Procurement Review Memo",
        "",
        "Private engine, public proof.",
        "",
        f"- memo_id: `{memo['memo_id']}`",
        f"- packet_id: `{memo['packet_id']}`",
        f"- decision: {memo['decision']}",
        f"- approves spend: {memo['safety_boundary']['approves_spend']}",
        f"- selects provider: {memo['safety_boundary']['selects_provider']}",
        "",
        memo["summary"],
        "",
        "## Required Review",
        "",
    ]
    lines.extend(f"- {item}" for item in memo["required_review"])
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in memo["blocked_claims"])
    lines.extend(["", "## Next Human Action", "", memo["next_human_action"], ""])
    return "\n".join(lines)


def write_spend_review_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Write spend review artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = build_spend_review_packet()
    receipt = build_finance_evidence_receipt(packet)
    memo = build_procurement_review_memo(packet)
    artifacts = {
        f"{SPEND_SCENARIO_ID}.spend_packet.json": spend_packet_to_pretty_json(packet) + "\n",
        f"{SPEND_SCENARIO_ID}.spend_packet.md": render_spend_review_packet_markdown(packet),
        f"{SPEND_SCENARIO_ID}.finance_receipt.json": spend_packet_to_pretty_json(receipt) + "\n",
        f"{SPEND_SCENARIO_ID}.finance_receipt.md": render_finance_receipt_markdown(receipt),
        f"{SPEND_SCENARIO_ID}.procurement_memo.json": spend_packet_to_pretty_json(memo) + "\n",
        f"{SPEND_SCENARIO_ID}.procurement_memo.md": render_procurement_memo_markdown(memo),
    }
    written: list[Path] = []
    for file_name, content in artifacts.items():
        path = output_dir / file_name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def build_spend_review_bundle() -> dict[str, Any]:
    """Build all spend lane outputs as one machine-readable bundle."""
    packet = build_spend_review_packet()
    receipt = build_finance_evidence_receipt(packet)
    memo = build_procurement_review_memo(packet)
    return {
        "schema_version": "ai_spend_review_bundle.v0",
        "scenario": SPEND_SCENARIO_ID,
        "packet": packet,
        "finance_receipt": receipt,
        "procurement_memo": memo,
        "safety": {
            "approves_spend": False,
            "guarantees_savings": False,
            "selects_provider": False,
            "executes_external_writes": False,
            "requires_human_review": True,
        },
        "artifacts": {
            "packet_markdown": f"examples/generated/{SPEND_SCENARIO_ID}.spend_packet.md",
            "packet_json": f"examples/generated/{SPEND_SCENARIO_ID}.spend_packet.json",
            "finance_receipt_markdown": f"examples/generated/{SPEND_SCENARIO_ID}.finance_receipt.md",
            "finance_receipt_json": f"examples/generated/{SPEND_SCENARIO_ID}.finance_receipt.json",
            "procurement_memo_markdown": f"examples/generated/{SPEND_SCENARIO_ID}.procurement_memo.md",
            "procurement_memo_json": f"examples/generated/{SPEND_SCENARIO_ID}.procurement_memo.json",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.spend",
        description="Build the public AI spend review packet.",
    )
    parser.add_argument("--json", action="store_true", help="Print the spend review bundle as JSON.")
    parser.add_argument("--write", action="store_true", help="Write spend review artifacts.")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writes even if --write is omitted; useful for explicit smoke checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    bundle = build_spend_review_bundle()

    if args.write:
        for path in write_spend_review_artifacts():
            print(path.relative_to(ROOT_DIR))
        return 0

    if args.json:
        print(json.dumps(bundle, indent=2, sort_keys=True))
    else:
        print(render_spend_review_packet_markdown(bundle["packet"]))
        print(render_finance_receipt_markdown(bundle["finance_receipt"]))
        print(render_procurement_memo_markdown(bundle["procurement_memo"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
