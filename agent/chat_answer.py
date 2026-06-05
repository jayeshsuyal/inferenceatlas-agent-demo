"""Structured public chat answers for the web demo."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .decision_brief import build_agent_access_decision_brief
from .packet import build_support_triage_decision_packet
from .spend import build_spend_review_bundle


CHAT_ANSWER_SCHEMA_VERSION = "chat_answer.v0"
SAFETY_ANCHOR = "IA did not approve. The next human action is named below."


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass(frozen=True)
class ChatAnswer:
    """Machine-readable wrapper around a natural, packet-backed reply."""

    answer_kind: str
    source: str
    reply_markdown: str
    artifacts: tuple[str, ...] = ()
    packet_refs: tuple[dict[str, str], ...] = ()
    safety: dict[str, bool] = field(default_factory=dict)
    next_human_action: str = ""
    evidence_basis: tuple[str, ...] = ()
    schema_version: str = CHAT_ANSWER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "answer_kind": self.answer_kind,
            "source": self.source,
            "reply_markdown": self.reply_markdown,
            "artifacts": list(self.artifacts),
            "packet_refs": list(self.packet_refs),
            "safety": dict(self.safety),
            "next_human_action": self.next_human_action,
            "evidence_basis": list(self.evidence_basis),
        }
        payload["answer_id"] = f"ia-chat-answer-{_stable_digest(payload)}"
        return payload


def _default_safety(**overrides: bool) -> dict[str, bool]:
    safety = {
        "approves_access": False,
        "grants_permissions": False,
        "production_access": False,
        "external_writes": False,
        "approves_spend": False,
        "selects_provider": False,
        "guarantees_savings": False,
        "requires_human_review": True,
    }
    safety.update(overrides)
    return safety


def _lines(items: list[str], *, limit: int = 4) -> list[str]:
    return [f"- {item}" for item in items[:limit]]


def build_product_positioning_answer() -> ChatAnswer:
    reply = "\n\n".join(
        [
            "## Short answer",
            (
                "InferenceAtlas is the packet authority layer. It does not try to be a "
                "better generic chatbot; it creates the proof packet humans and downstream "
                "systems trust before an AI agent gets tools, data, spend, or production access."
            ),
            "## What IA gives you",
            "\n".join(
                [
                    "- A DecisionPacket that says what can move and what stays blocked.",
                    "- Proof debt, reviewer routing, and a next human validation step.",
                    "- Subscriber-ready packet authority for gateways, CI, spend controls, review queues, and observability.",
                    "- Sponsor proof slots where Nebius, Tavily, Composio, and OpenClaw can add evidence without becoming approval authorities.",
                    "- Finance/Procurement spend review before budget caps, vendor switches, or savings claims move.",
                ]
            ),
            "## Why this is different",
            (
                "ChatGPT or Claude can answer. A tool gateway can execute. IA sits before "
                "execution and says: here is the reviewable packet, here is the blocked scope, "
                "here is the missing proof, and here is who must approve next."
            ),
            f"**Safety anchor:** {SAFETY_ANCHOR}",
        ]
    )
    return ChatAnswer(
        answer_kind="product_positioning",
        source="deterministic_chat_answer",
        reply_markdown=reply,
        artifacts=(
            "docs/PRODUCT_TOUR.md",
            "docs/CONTRACT.md",
            "examples/generated/trust_receipt.md",
        ),
        safety=_default_safety(),
        next_human_action="Choose one real agent workflow and generate the packet before granting access.",
        evidence_basis=(
            "public product tour",
            "public conformance contract",
            "trust receipt",
        ),
    )


def build_access_review_answer(message: str = "") -> ChatAnswer:
    packet = build_support_triage_decision_packet(mode="live_review_room_demo")
    brief = build_agent_access_decision_brief(packet)
    go_no_go = brief["go_no_go"]
    proof = [
        f"{item['item']} - owner: {item['owner']}"
        for item in packet.get("missing_proof", [])
    ]
    reviewers = [
        f"{item['owner']}: {item['review_area']}"
        for item in packet.get("reviewer_owners", [])
    ]
    blocked = [item["claim"] for item in packet.get("blocked_claims", [])]
    next_action = str(packet["next_validation"]["action"])
    reply = "\n\n".join(
        [
            "## Access review",
            (
                "No production access. The support-triage agent can move only into scoped "
                "validation, and Composio stays dry-run."
            ),
            "## Decision",
            "\n".join(
                [
                    f"- production access: {go_no_go['production_access']}",
                    f"- scoped validation review: {go_no_go['scoped_validation_review']}",
                    f"- external writes: {go_no_go['external_writes']}",
                    f"- Composio dry-run: {go_no_go['composio_dry_run']}",
                ]
            ),
            "## Missing proof",
            "\n".join(_lines(proof)),
            "## Blocked claims",
            "\n".join(_lines(blocked)),
            "## Review owners",
            "\n".join(_lines(reviewers)),
            "## Next human action",
            next_action,
            f"**Safety anchor:** {SAFETY_ANCHOR}",
        ]
    )
    return ChatAnswer(
        answer_kind="agent_access_review",
        source="decision_packet",
        reply_markdown=reply,
        artifacts=(
            "examples/generated/support_triage_agent.packet.json",
            "examples/generated/support_triage_agent.decision_brief.json",
            "examples/generated/support_triage_agent.outcome_memo.md",
        ),
        packet_refs=(
            {
                "packet_id": packet["packet_id"],
                "artifact": "examples/generated/support_triage_agent.packet.json",
            },
        ),
        safety=_default_safety(
            production_access=bool(go_no_go["production_access"]),
            external_writes=bool(go_no_go["external_writes"]),
        ),
        next_human_action=next_action,
        evidence_basis=("DecisionPacket", "Agent Access Decision Brief", "Packet Outcome Memo"),
    )


def build_spend_review_answer() -> ChatAnswer:
    bundle = build_spend_review_bundle()
    packet = bundle["packet"]
    finance = bundle["finance_receipt"]
    procurement = bundle["procurement_memo"]
    evidence = [
        f"{item['evidence']} - owner: {item['owner']}"
        for item in packet["required_evidence"]
    ]
    blocked = [item["claim"] for item in packet["blocked_claims"]]
    reviewers = [
        f"{item['owner']}: {item['review_area']}"
        for item in packet["reviewer_owners"]
    ]
    next_action = str(packet["next_human_action"]["action"])
    reply = "\n\n".join(
        [
            "## Spend review",
            (
                "This is a Finance and Procurement review packet, not an optimizer verdict. "
                "IA does not approve a cap, switch vendors, pick a provider, or promise savings."
            ),
            "## Decision posture",
            "\n".join(
                [
                    f"- verdict class: {packet['decision']['verdict_class']}",
                    f"- live spend approved: {packet['spend_posture']['live_spend_approved']}",
                    f"- provider selected: {packet['spend_posture']['provider_winner_selected']}",
                    f"- savings guaranteed: {packet['spend_posture']['savings_guaranteed']}",
                ]
            ),
            "## Evidence Finance/Procurement need",
            "\n".join(_lines(evidence)),
            "## Claims IA keeps blocked",
            "\n".join(_lines(blocked)),
            "## Review owners",
            "\n".join(_lines(reviewers)),
            "## Next human action",
            next_action,
            f"**Safety anchor:** {SAFETY_ANCHOR}",
        ]
    )
    return ChatAnswer(
        answer_kind="ai_spend_review",
        source="spend_review_packet",
        reply_markdown=reply,
        artifacts=(
            bundle["artifacts"]["packet_json"],
            bundle["artifacts"]["finance_receipt_json"],
            bundle["artifacts"]["procurement_memo_json"],
        ),
        packet_refs=(
            {
                "packet_id": packet["packet_id"],
                "content_hash": packet["content_hash"],
                "artifact": bundle["artifacts"]["packet_json"],
            },
            {
                "packet_id": finance["packet_id"],
                "content_hash": finance["content_hash"],
                "artifact": bundle["artifacts"]["finance_receipt_json"],
            },
            {
                "packet_id": procurement["packet_id"],
                "content_hash": procurement["content_hash"],
                "artifact": bundle["artifacts"]["procurement_memo_json"],
            },
        ),
        safety=_default_safety(),
        next_human_action=next_action,
        evidence_basis=("AI Spend Review packet", "Finance Evidence Receipt", "Procurement Review Memo"),
    )


def build_catalog_answer(summary: str) -> ChatAnswer:
    return ChatAnswer(
        answer_kind="catalog_overview",
        source="catalog_tool",
        reply_markdown="## Catalog overview\n\n" + summary,
        safety=_default_safety(),
        next_human_action="Use catalog output as a shortlist, then run human procurement review before spend changes.",
        evidence_basis=("get_catalog_summary",),
    )


def build_pricing_answer(*, title: str, body: str) -> ChatAnswer:
    reply = "\n\n".join(
        [
            f"## {title}",
            body,
            "Use this as a procurement shortlist, not a savings guarantee.",
            f"**Safety anchor:** {SAFETY_ANCHOR}",
        ]
    )
    return ChatAnswer(
        answer_kind="pricing_shortlist",
        source="catalog_or_live_search",
        reply_markdown=reply,
        safety=_default_safety(),
        next_human_action="Finance and Procurement review invoice, usage, and contract evidence before any spend or vendor change.",
        evidence_basis=("compare_providers", "optional Tavily live evidence"),
    )
