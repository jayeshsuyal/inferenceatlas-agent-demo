"""Compact chat salience surface over packet-backed answers."""

from __future__ import annotations

from typing import Any

from .portkey_adapter import build_portkey_adapter_payload


CHAT_SALIENCE_SCHEMA_VERSION = "chat_salience_surface.v0"


def _first(items: list[str], fallback: str) -> str:
    return items[0] if items else fallback


def _top_blocker(blocked_claims: list[str]) -> str:
    blocked_claim = _first(blocked_claims, "Unsafe movement stays blocked until human review.")
    if " - " in blocked_claim:
        return blocked_claim.split(" - ", 1)[1]
    return blocked_claim


def _proof_question(missing_proof: list[str]) -> str:
    if not missing_proof:
        return "What evidence should a human attach before this packet moves?"
    first = missing_proof[0].rstrip(".")
    return f"Can the owner attach `{first}` before this packet moves?"


def _destination(answer: dict[str, Any]) -> dict[str, str]:
    gate = answer.get("downstream_gate") or {}
    subscriber = answer.get("subscriber") or gate.get("subscriber") or ""
    fixture_id = answer.get("fixture", {}).get("fixture_id", "")
    if subscriber == "portkey_model_spend_gate":
        return {
            "surface": "portkey_adapter_preview",
            "label": "Preview Portkey gate",
            "path": f"/api/packets/{fixture_id}/downstream/portkey?mode=dry-run",
        }
    if answer["answer_kind"] == "proof_status":
        return {
            "surface": "packet_proof_review",
            "label": "Inspect missing proof",
            "path": f"/packet?fixture={fixture_id}&autorun=1",
        }
    if answer["answer_kind"] == "reviewer_routing":
        return {
            "surface": "reviewer_routing",
            "label": "Inspect reviewer routing",
            "path": f"/packet?fixture={fixture_id}&autorun=1",
        }
    if answer["answer_kind"] == "safety_status":
        return {
            "surface": "packet_verification",
            "label": "Inspect verification",
            "path": f"/api/ia-packet?fixture={fixture_id}",
        }
    return {
        "surface": "technical_packet",
        "label": "Inspect technical packet",
        "path": f"/packet?fixture={fixture_id}&autorun=1",
    }


def _current_read(answer: dict[str, Any], destination: dict[str, str]) -> str:
    gate = answer.get("downstream_gate") or {}
    packet_id = answer["packet_reference"]["packet_id"]
    if destination["surface"] == "portkey_adapter_preview":
        return (
            "Portkey cannot allow this request from the current IA Packet. "
            f"Packet `{packet_id}` is `{answer['verdict_class']}` and spend movement stays blocked."
        )
    if answer["answer_kind"] == "proof_status":
        return f"IA requires proof before packet `{packet_id}` can move."
    if answer["answer_kind"] == "reviewer_routing":
        return f"Packet `{packet_id}` needs named human review before anything moves."
    if answer["answer_kind"] == "safety_status":
        return f"Packet `{packet_id}` is locked to a non-approving safety state."
    if gate:
        return f"{gate['subscriber']} received a read-only packet answer; IA did not approve movement."
    return f"IA can only answer this from packet `{packet_id}` when the question targets decision, proof, routing, or safety."


def build_chat_salience_surface(answer: dict[str, Any]) -> dict[str, Any]:
    """Build the compact chat projection from one Packet Advisor answer."""
    destination = _destination(answer)
    fixture_id = answer["fixture"]["fixture_id"]
    top_blocker = _top_blocker(answer["blocked_claims"])
    preview: dict[str, Any] | None = None
    if destination["surface"] == "portkey_adapter_preview":
        preview = build_portkey_adapter_payload(fixture=fixture_id, mode="dry-run")

    source_line = (
        "Packet-backed"
        f" - packet_id `{answer['packet_reference']['packet_id']}`"
        f" - revision `{answer['packet_reference']['revision_id']}`"
        f" - answer_kind `{answer['answer_kind']}`"
    )
    return {
        "schema_version": CHAT_SALIENCE_SCHEMA_VERSION,
        "current_read": _current_read(answer, destination),
        "top_blocker": top_blocker,
        "next_human_action": answer["next_human_action"],
        "one_proof_question": _proof_question(answer["missing_proof"]),
        "destination_surface": destination["surface"],
        "destination_label": destination["label"],
        "destination_path": destination["path"],
        "source_line": source_line,
        "portkey_adapter_preview": preview,
        "guardrails": {
            "read_only": True,
            "approved": False,
            "mutated_packet": False,
            "dispatched": False,
            "autonomous_action": False,
            "raw_packet_dumped": False,
        },
    }


def render_chat_salience_markdown(surface: dict[str, Any]) -> str:
    lines = [
        "## Current read",
        surface["current_read"],
        "",
        f"**Top blocker:** {surface['top_blocker']}",
        "",
        f"**Next human action:** {surface['next_human_action']}",
        "",
        f"**One proof question:** {surface['one_proof_question']}",
        "",
        f"**Inspect:** {surface['destination_label']} - `{surface['destination_path']}`",
        "",
        f"**Source:** {surface['source_line']}",
        "",
        "IA does not approve this request. Human review is required and unsafe movement stays blocked.",
    ]
    preview = surface.get("portkey_adapter_preview")
    if preview:
        verdict = str(preview["portkey_guardrail_response"]["verdict"]).lower()
        api_call_made = str(preview["api_call_made"]).lower()
        lines.extend(
            [
                "",
                "## Portkey preview",
                f"- guardrail verdict: `{verdict}`",
                f"- usage policy credit_limit: `{preview['usage_policy_plan']['request_body']['credit_limit']}`",
                f"- api call made: `{api_call_made}`",
            ]
        )
    return "\n".join(lines)
