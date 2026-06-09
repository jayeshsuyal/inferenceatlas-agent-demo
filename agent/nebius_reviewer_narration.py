"""Nebius reviewer narration over locked IA Packet fields.

The adapter is intentionally narrow: Nebius may turn locked packet fields into
reviewer-ready language, but it cannot decide, approve, grant, write, or mutate
the packet. Any malformed or unsafe model output falls back to deterministic
narration.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from . import config
from .adapters.core import (
    ADAPTER_CONTRACT_VERSION,
    NEBIUS_FORBIDDEN_NARRATION_PHRASES,
    NEBIUS_REQUIRED_TONE_ANCHORS,
    build_adapter_result,
)


NEBIUS_REVIEWER_NARRATION_SCHEMA_VERSION = "nebius_reviewer_narration.v0"
NEBIUS_RESPONSE_KEYS = (
    "reviewer_summary",
    "decision_lock_sentence",
    "next_human_action",
    "safety_anchor",
)
NEBIUS_REQUIRED_SAFETY_ANCHOR = (
    "IA does not approve this request. Human review is required before any access, "
    "spend, or production movement. Decision lock unchanged."
)
NEBIUS_EXTRA_FORBIDDEN_PHRASES = (
    "safe to proceed",
    "permission granted",
    "no review needed",
    "approved for production",
    "approved to proceed",
)
NEBIUS_TOO_GENERIC_RESPONSES = (
    "access blocked",
    "review packet",
    "review required",
    "decision lock unchanged",
)

ClientFactory = Callable[[], Any]


def _next_human_action(packet: dict[str, Any]) -> str:
    next_validation = packet.get("next_validation", {})
    if isinstance(next_validation, dict):
        action = str(next_validation.get("action") or "").strip()
        owner = str(next_validation.get("owner") or "").strip()
        if action and owner:
            return f"{action} Owner: {owner}."
        if action:
            return action
    return str(next_validation or "Human review is required before this request can move.").strip()


def _join_narration(narration: dict[str, str]) -> str:
    return " ".join(str(narration[key]) for key in NEBIUS_RESPONSE_KEYS)


def _fallback_narration(packet: dict[str, Any]) -> dict[str, str]:
    decision = packet["decision"]
    safety = packet["safety_state"]
    return {
        "reviewer_summary": (
            f"Packet verdict is {decision['verdict']}. "
            f"Review posture is {decision['review_posture']}. "
            "The packet names blocked claims, missing proof, reviewer owners, and the next human action."
        ),
        "decision_lock_sentence": (
            f"Decision lock unchanged: production access remains blocked, "
            f"external writes are {safety['external_writes_enabled']}, "
            f"and approval granted is {safety['approval_granted']}."
        ),
        "next_human_action": _next_human_action(packet),
        "safety_anchor": NEBIUS_REQUIRED_SAFETY_ANCHOR,
    }


def _base_payload(packet: dict[str, Any], scenario_name: str, *, live_enabled: bool) -> dict[str, Any]:
    fallback = build_adapter_result("nebius", scenario_name)
    narration = _fallback_narration(packet)
    fallback.update(
        {
            "schema_version": NEBIUS_REVIEWER_NARRATION_SCHEMA_VERSION,
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "mode": "live_read_only_narration" if live_enabled else "offline_dry_run_contract",
            "live_requested": live_enabled,
            "live_call_attempted": False,
            "live_call_count": 0,
            "used_live_key": False,
            "fallback_used": True,
            "fallback_reason": "live_not_requested" if not live_enabled else "nebius_api_key_missing",
            "narration": _join_narration(narration),
            "structured_narration": narration,
            "required_anchors": list(NEBIUS_REQUIRED_TONE_ANCHORS) + [NEBIUS_REQUIRED_SAFETY_ANCHOR],
            "required_anchors_present": True,
            "forbidden_phrases_present": [],
            "docs_reference": "docs/LIVE_INTEGRATION_CONTRACT.md#nebius",
            "safety_impact": "none",
        }
    )
    return fallback


def _client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - covered by fallback behavior
        raise RuntimeError("openai package not installed") from exc
    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


def _packet_prompt(packet: dict[str, Any]) -> str:
    payload = {
        "packet_id": packet["packet_id"],
        "decision": packet["decision"],
        "approval_posture": packet["approval_posture"],
        "safety_state": packet["safety_state"],
        "blocked_claims": packet["blocked_claims"],
        "missing_proof": packet["missing_proof"],
        "reviewer_owners": packet["reviewer_owners"],
    }
    return (
        "You are Nebius providing reviewer narration for InferenceAtlas. "
        "You may only explain locked packet fields. You must not approve access, grant permissions, "
        "change the verdict, reduce proof debt, or say the request is safe to proceed.\n\n"
        "Return JSON only with exactly these string keys: "
        "reviewer_summary, decision_lock_sentence, next_human_action, safety_anchor.\n"
        f"The safety_anchor value must be exactly: {NEBIUS_REQUIRED_SAFETY_ANCHOR!r}\n"
        "Each field except safety_anchor must be one complete, packet-specific sentence between 60 and 220 "
        "characters. Mention the packet verdict or blocked proof in reviewer_summary. Mention the named owner "
        "or proof debt in next_human_action. Mention that the decision lock is unchanged. Do not return terse "
        "labels like 'Access blocked' or 'Review packet'.\n\n"
        f"Locked packet fields:\n{json.dumps(payload, sort_keys=True)}"
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Nebius response did not contain a JSON object")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Nebius response was not a JSON object")
    return parsed


def _sanitize_field(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > 420:
        text = text[:417].rstrip() + "..."
    return text


def _validate_narration(parsed: dict[str, Any]) -> dict[str, str]:
    missing = [key for key in NEBIUS_RESPONSE_KEYS if key not in parsed]
    if missing:
        raise ValueError(f"Nebius response missing keys: {', '.join(missing)}")
    unexpected = [key for key in parsed if key not in NEBIUS_RESPONSE_KEYS]
    if unexpected:
        raise ValueError(f"Nebius response contained unexpected keys: {', '.join(unexpected)}")
    narration = {key: _sanitize_field(parsed[key]) for key in NEBIUS_RESPONSE_KEYS}
    joined = _join_narration(narration)
    required = list(NEBIUS_REQUIRED_TONE_ANCHORS) + [NEBIUS_REQUIRED_SAFETY_ANCHOR]
    missing_anchors = [anchor for anchor in required if anchor not in joined]
    if missing_anchors:
        raise ValueError("Nebius response missed required safety anchors")
    forbidden = [
        phrase
        for phrase in tuple(NEBIUS_FORBIDDEN_NARRATION_PHRASES) + NEBIUS_EXTRA_FORBIDDEN_PHRASES
        if phrase.lower() in joined.lower()
    ]
    if forbidden:
        raise ValueError(f"Nebius response contained forbidden narration phrase: {forbidden[0]}")
    if len(narration["reviewer_summary"]) < 40 or len(narration["next_human_action"]) < 25:
        raise ValueError("Nebius response was too terse for reviewer narration")
    generic = [
        phrase
        for phrase in NEBIUS_TOO_GENERIC_RESPONSES
        if phrase == narration["reviewer_summary"].lower() or phrase == narration["next_human_action"].lower()
    ]
    if generic:
        raise ValueError(f"Nebius response used generic narration: {generic[0]}")
    return narration


def build_nebius_reviewer_narration(
    packet: dict[str, Any],
    *,
    scenario_name: str = "support_triage_agent",
    live_enabled: bool = False,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Build Nebius narration with deterministic fallback and strict guardrails."""
    payload = _base_payload(packet, scenario_name, live_enabled=live_enabled)
    if not live_enabled:
        return payload
    if config.LLM_PROVIDER != "nebius" or not config.LLM_API_KEY:
        payload["fallback_reason"] = "nebius_api_key_missing"
        return payload

    payload["live_call_attempted"] = True
    try:
        client = (client_factory or _client)()
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. You explain packet facts; you do not approve, "
                        "grant, write, mutate, or decide."
                    ),
                },
                {"role": "user", "content": _packet_prompt(packet)},
            ],
            temperature=0,
            max_tokens=500,
        )
        raw = response.choices[0].message.content or ""
        narration = _validate_narration(_parse_json_object(raw))
    except Exception as exc:
        payload["fallback_reason"] = "nebius_live_guardrail_fallback"
        payload["fallback_detail"] = str(exc).splitlines()[0][:180]
        return payload

    payload.update(
        {
            "status": "live_reviewer_narration_built",
            "live_call_count": 1,
            "used_live_key": True,
            "fallback_used": False,
            "fallback_reason": "",
            "narration": _join_narration(narration),
            "structured_narration": narration,
            "required_anchors_present": True,
            "forbidden_phrases_present": [],
        }
    )
    return payload
