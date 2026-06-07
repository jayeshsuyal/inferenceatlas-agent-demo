"""IA Packet detail projection for the public review surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .scenarios import ROOT_DIR
from .workbench import WORKBENCH_SAFETY_ANCHOR, build_workbench_result, workbench_result_to_pretty_json


IA_PACKET_DETAIL_SCHEMA_VERSION = "ia_packet_detail.v0"
IA_PACKET_SAFETY_ANCHOR = WORKBENCH_SAFETY_ANCHOR
IA_PACKET_DEFINITION = (
    "An IA Packet is the canonical proof object downstream systems trust before an AI agent "
    "receives tools, data, spend, or production access."
)
SUBSCRIBER_ROOT = ROOT_DIR / "examples" / "subscribers"


def _load_subscriber_patterns() -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    if not SUBSCRIBER_ROOT.exists():
        return patterns
    for path in sorted(SUBSCRIBER_ROOT.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        effect = data.get("subscriber_effect", {})
        patterns.append(
            {
                "subscriber": data["subscriber"],
                "subscriber_category": data["subscriber_category"],
                "consumer_question": data["consumer_question"],
                "owner": effect.get("owner", "Human reviewer"),
                "subscriber_action": effect.get("subscriber_action", "wait for a human-approved packet revision"),
                "fields_used": data.get("fields_used", []),
                "pattern_source": str(path.relative_to(ROOT_DIR)),
                "can_approve_access": bool(effect.get("can_approve_access")),
                "can_grant_permissions": bool(effect.get("can_grant_permissions")),
                "can_mutate_packet": bool(effect.get("can_mutate_packet")),
                "can_override_verdict": bool(effect.get("can_override_verdict")),
                "executes_external_writes": bool(effect.get("executes_external_writes")),
                "requires_human_review": bool(effect.get("requires_human_review", True)),
            }
        )
    return patterns


def _downstream_consumers(packet_reference: dict[str, str]) -> list[dict[str, Any]]:
    consumers: list[dict[str, Any]] = []
    for pattern in _load_subscriber_patterns():
        consumers.append(
            {
                **pattern,
                "packet_reference": packet_reference,
                "source_of_truth": "ia_packet.packet_reference",
            }
        )
    return consumers


def build_ia_packet_detail(fixture_id: str) -> dict[str, Any]:
    """Build the reviewer-facing IA Packet detail object from one registered fixture."""
    workbench = build_workbench_result(fixture_id)
    packet_reference = workbench["packet_reference"]
    downstream_consumers = _downstream_consumers(packet_reference)
    decision = workbench["decision"]
    safety_boundary = workbench["safety_boundary"]
    return {
        "schema_version": IA_PACKET_DETAIL_SCHEMA_VERSION,
        "ok": True,
        "product_object": "IA Packet",
        "definition": IA_PACKET_DEFINITION,
        "title": f"IA Packet: {workbench['title']}",
        "fixture": workbench["fixture"],
        "mode": workbench["mode"],
        "packet_reference": packet_reference,
        "local_verification": workbench["local_verification"],
        "decision": decision,
        "blocked_claims": workbench["blocked_claims"],
        "missing_proof": workbench["missing_proof"],
        "reviewer_routing": workbench["reviewer_routing"],
        "requested_systems": workbench["requested_systems"],
        "sponsor_proof_trace": workbench.get("sponsor_proof_trace"),
        "downstream_consumers": downstream_consumers,
        "source_artifacts": workbench["source_artifacts"],
        "copy_review_brief": workbench["copy_review_brief"],
        "safety_anchor": IA_PACKET_SAFETY_ANCHOR,
        "workbench_safety_anchor": workbench["safety_anchor"],
        "safety_boundary": {
            **safety_boundary,
            "downstream_can_approve": any(c["can_approve_access"] for c in downstream_consumers),
            "downstream_can_mutate_packet": any(c["can_mutate_packet"] for c in downstream_consumers),
            "downstream_can_override_verdict": any(c["can_override_verdict"] for c in downstream_consumers),
            "calls_v1": bool(workbench["local_verification"]["calls_v1"]),
        },
        "export_label": "Copy IA Packet brief",
        "verification_link_hint": "/packet?fixture={fixture_id}&autorun=1",
        "source_workbench_schema_version": workbench["schema_version"],
    }


def render_ia_packet_detail_markdown(detail: dict[str, Any]) -> str:
    """Render an IA Packet detail object as a meeting-ready Markdown artifact."""
    decision = detail["decision"]
    packet = detail["packet_reference"]
    lines = [
        f"# {detail['title']}",
        "",
        "Private engine, public proof.",
        "",
        detail["definition"],
        "",
        f"- fixture: `{detail['fixture']['fixture_id']}`",
        f"- packet_id: `{packet['packet_id']}`",
        f"- revision_id: `{packet['revision_id']}`",
        f"- content_hash: `{packet['content_hash']}`",
        f"- verdict_class: `{decision['verdict_class']}`",
        f"- production_access: `{decision['production_access']}`",
        f"- permission_grants: `{decision['permission_grants']}`",
        f"- external_writes: `{decision['external_writes']}`",
        "",
        "## Blocked Claims",
        "",
        *[f"- {item}" for item in detail["blocked_claims"]],
        "",
        "## Missing Proof",
        "",
        *[f"- {item}" for item in detail["missing_proof"]],
        "",
        "## Reviewer Routing",
        "",
        *[f"- {item}" for item in detail["reviewer_routing"]],
        "",
        "## Downstream Consumers",
        "",
        *[
            f"- {item['subscriber']} ({item['subscriber_category']}): {item['subscriber_action']}"
            for item in detail["downstream_consumers"]
        ],
        "",
        "## Safety Anchor",
        "",
        detail["safety_anchor"],
        detail["workbench_safety_anchor"],
        "",
    ]
    return "\n".join(lines)


def ia_packet_detail_to_pretty_json(detail: dict[str, Any]) -> str:
    return workbench_result_to_pretty_json(detail)
