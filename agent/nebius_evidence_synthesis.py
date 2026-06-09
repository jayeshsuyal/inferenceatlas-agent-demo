"""Nebius synthesis over already-collected sponsor proof.

Nebius may explain the proof that IA already collected, but it cannot invent
sources, reduce proof debt, approve movement, grant permissions, or mutate the
IA Packet. Tavily owns source discovery; Nebius owns reviewer-facing synthesis.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from . import config
from .adapters.core import ADAPTER_CONTRACT_VERSION, NEBIUS_FORBIDDEN_NARRATION_PHRASES


NEBIUS_EVIDENCE_SYNTHESIS_SCHEMA_VERSION = "nebius_evidence_synthesis.v0"
NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR = (
    "IA does not approve this request. Sources are evidence candidates only; "
    "human review is required before any proof debt changes."
)
NEBIUS_EVIDENCE_SYNTHESIS_KEYS = (
    "reviewer_summary",
    "cited_source_ids",
    "source_findings",
    "remaining_proof_gaps",
    "next_human_action",
    "safety_anchor",
)
NEBIUS_EVIDENCE_SYNTHESIS_FORBIDDEN_PHRASES = (
    "safe to proceed",
    "permission granted",
    "approved for production",
    "approved to proceed",
    "proof debt reduced",
    "reduces proof debt",
    "source proves",
    "sources prove",
    "no review needed",
)

ClientFactory = Callable[[], Any]


def _client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - fallback behavior is tested.
        raise RuntimeError("openai package not installed") from exc
    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


def _first_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text[:240]


def _next_human_action(packet: dict[str, Any]) -> str:
    next_validation = packet.get("next_validation", {})
    if isinstance(next_validation, dict):
        action = _first_text(next_validation.get("action"))
        owner = _first_text(next_validation.get("owner"))
        if action and owner:
            return f"{action} Owner: {owner}."
        if action:
            return action
    return "Route the packet to the named owners with source candidates and proof debt attached."


def _missing_proof_labels(packet: dict[str, Any], *, limit: int = 4) -> list[str]:
    labels = []
    for item in packet.get("missing_proof", [])[:limit]:
        if isinstance(item, dict):
            label = item.get("item") or item.get("claim") or item.get("unblocks")
            owner = item.get("owner")
            labels.append(_first_text(f"{label} - {owner}" if owner else label))
        else:
            labels.append(_first_text(item))
    return [label for label in labels if label]


def _source_index(tavily_proof: dict[str, Any] | None, *, limit: int = 8) -> list[dict[str, Any]]:
    if not tavily_proof:
        return []
    sources: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for candidate in tavily_proof.get("evidence_candidates", []):
        if not isinstance(candidate, dict):
            continue
        notes = candidate.get("source_notes") or []
        if not notes and candidate.get("source_urls"):
            notes = [{"url": url, "title": "Tavily source candidate"} for url in candidate["source_urls"]]
        for note in notes:
            if not isinstance(note, dict):
                continue
            url = _first_text(note.get("url"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(
                {
                    "source_id": f"tavily:{len(sources) + 1}",
                    "provider": "tavily",
                    "url": url,
                    "title": _first_text(note.get("title") or "Tavily source candidate"),
                    "content_snippet": _first_text(note.get("content_snippet") or note.get("content")),
                    "score": note.get("score"),
                    "query": _first_text(candidate.get("query")),
                    "reviewer_owner": _first_text(candidate.get("reviewer_owner")),
                    "unblocks": _first_text(candidate.get("unblocks")),
                    "human_review_required": True,
                    "can_reduce_proof_debt": False,
                }
            )
            if len(sources) >= limit:
                return sources
    return sources


def _fallback_synthesis(packet: dict[str, Any], source_index: list[dict[str, Any]]) -> dict[str, Any]:
    cited = [source["source_id"] for source in source_index[:3]]
    findings = [
        {
            "source_id": source["source_id"],
            "finding": (
                f"Candidate source for reviewer owner {source.get('reviewer_owner') or 'named reviewer'} "
                f"on query: {source.get('query') or 'packet proof debt'}."
            ),
            "limitation": "Evidence candidate only; it does not reduce proof debt without human review.",
        }
        for source in source_index[:3]
    ]
    gaps = _missing_proof_labels(packet)
    return {
        "reviewer_summary": (
            "IA collected source candidates for the packet proof debt; the packet verdict and safety state stay locked."
        ),
        "cited_source_ids": cited,
        "source_findings": findings,
        "remaining_proof_gaps": "; ".join(gaps)
        or "Named reviewers must inspect the packet proof debt before any movement.",
        "next_human_action": _next_human_action(packet),
        "safety_anchor": NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR,
    }


def _role_specific_briefs(packet: dict[str, Any], source_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    briefs = []
    for owner in packet.get("reviewer_owners", [])[:4]:
        if not isinstance(owner, dict):
            continue
        reviewer_owner = _first_text(owner.get("owner") or "Named reviewer")
        review_area = _first_text(owner.get("review_area") or owner.get("area") or "packet proof debt")
        matching_sources = [
            source for source in source_index if source.get("reviewer_owner") == reviewer_owner
        ]
        if not matching_sources:
            matching_sources = source_index[:2]
        source_ids = [source["source_id"] for source in matching_sources[:2]]
        source_phrase = (
            f"{len(source_ids)} source candidate(s)"
            if source_ids
            else "no source candidates yet"
        )
        briefs.append(
            {
                "reviewer_owner": reviewer_owner,
                "review_area": review_area,
                "source_ids": source_ids,
                "brief": (
                    f"{reviewer_owner} should inspect {source_phrase} against {review_area}; "
                    "the packet decision and proof debt remain locked until human review."
                ),
                "remaining_question": (
                    f"What evidence would let {reviewer_owner} reduce the named proof debt without changing "
                    "the packet verdict?"
                ),
                "next_human_action": _next_human_action(packet),
                "safety_anchor": NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR,
                "human_review_required": True,
                "can_reduce_proof_debt": False,
            }
        )
    return briefs


def _base_payload(
    packet: dict[str, Any],
    source_index: list[dict[str, Any]],
    *,
    live_enabled: bool,
    fallback_reason: str,
) -> dict[str, Any]:
    synthesis = _fallback_synthesis(packet, source_index)
    role_briefs = _role_specific_briefs(packet, source_index)
    return {
        "schema_version": NEBIUS_EVIDENCE_SYNTHESIS_SCHEMA_VERSION,
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "mode": "live_read_only_evidence_synthesis" if live_enabled else "offline_dry_run_contract",
        "status": "deterministic_evidence_synthesis_fallback",
        "live_requested": live_enabled,
        "live_call_attempted": False,
        "live_call_count": 0,
        "used_live_key": False,
        "fallback_used": True,
        "fallback_reason": fallback_reason,
        "source_index": source_index,
        "source_index_count": len(source_index),
        "synthesis": synthesis,
        "role_specific_briefs": role_briefs,
        "role_brief_count": len(role_briefs),
        "required_anchors_present": True,
        "forbidden_phrases_present": [],
        "docs_reference": "docs/LIVE_INTEGRATION_CONTRACT.md#nebius",
        "safety_impact": "none",
        "invariants": {
            "source_ids_from_tavily_only": True,
            "source_urls_from_tavily_only": True,
            "no_new_urls": True,
            "can_reduce_proof_debt": False,
            "can_approve_access": False,
            "can_grant_permissions": False,
            "can_mutate_packet": False,
            "decision_lock_unchanged": True,
            "role_briefs_source_bound": True,
            "human_review_required": True,
        },
    }


def _prompt(
    packet: dict[str, Any],
    source_index: list[dict[str, Any]],
    *,
    composio_proof: dict[str, Any] | None,
    openclaw_trace: dict[str, Any] | None,
    portkey_preview: dict[str, Any] | None,
) -> str:
    packet_payload = {
        "packet_id": packet["packet_id"],
        "decision": packet["decision"],
        "safety_state": packet["safety_state"],
        "blocked_claims": packet["blocked_claims"],
        "missing_proof": packet["missing_proof"],
        "reviewer_owners": packet["reviewer_owners"],
    }
    proof_payload = {
        "source_index": source_index,
        "composio_summary": (composio_proof or {}).get("permission_diff_summary", {}),
        "openclaw_trace_steps": (openclaw_trace or {}).get("trace_steps", []),
        "portkey_invariants": (portkey_preview or {}).get("invariants", {}),
        "portkey_diff": (portkey_preview or {}).get("dry_run_diff", {}),
    }
    return (
        "You are Nebius synthesizing already-collected InferenceAtlas proof for a human reviewer. "
        "You may only cite source IDs present in source_index. Do not write URLs. Do not invent sources. "
        "Do not approve access, grant permissions, reduce proof debt, change verdicts, or say the request is safe.\n\n"
        "Return minified JSON only with exactly these keys: reviewer_summary, cited_source_ids, source_findings, "
        "remaining_proof_gaps, next_human_action, safety_anchor.\n"
        "cited_source_ids must be an array of 1 to 3 source_id strings from source_index only. "
        "source_findings must be an array of at most 3 objects with exactly source_id, finding, limitation. "
        f"safety_anchor must be exactly: {NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR!r}\n"
        "Each finding must explain relevance, not proof completion. Every limitation must say human review is required.\n\n"
        f"Locked packet fields:\n{json.dumps(packet_payload, sort_keys=True)}\n\n"
        f"Collected proof inputs:\n{json.dumps(proof_payload, sort_keys=True)}"
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
        raise ValueError("Nebius synthesis did not contain a JSON object")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Nebius synthesis was not a JSON object")
    return parsed


def _clean_string(value: Any, *, max_len: int = 520) -> str:
    text = " ".join(str(value or "").split())
    return text[: max_len - 3].rstrip() + "..." if len(text) > max_len else text


def _urls_in_text(value: Any) -> list[str]:
    text = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return re.findall(r"https?://[^\s\"'<>]+", text)


def _validate_synthesis(parsed: dict[str, Any], source_index: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [key for key in NEBIUS_EVIDENCE_SYNTHESIS_KEYS if key not in parsed]
    if missing:
        raise ValueError(f"Nebius synthesis missing keys: {', '.join(missing)}")
    unexpected = [key for key in parsed if key not in NEBIUS_EVIDENCE_SYNTHESIS_KEYS]
    if unexpected:
        raise ValueError(f"Nebius synthesis contained unexpected keys: {', '.join(unexpected)}")
    if parsed["safety_anchor"] != NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR:
        raise ValueError("Nebius synthesis missed required safety anchor")

    allowed_ids = {source["source_id"] for source in source_index}
    cited = parsed["cited_source_ids"]
    if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
        raise ValueError("Nebius synthesis cited_source_ids must be a string array")
    invalid_ids = [item for item in cited if item not in allowed_ids]
    if invalid_ids:
        raise ValueError(f"Nebius synthesis cited unknown source id: {invalid_ids[0]}")

    findings = parsed["source_findings"]
    if not isinstance(findings, list):
        raise ValueError("Nebius synthesis source_findings must be an array")
    clean_findings = []
    for finding in findings[:5]:
        if not isinstance(finding, dict):
            raise ValueError("Nebius synthesis source_findings entries must be objects")
        unexpected = [key for key in finding if key not in {"source_id", "finding", "limitation"}]
        if unexpected:
            raise ValueError(f"Nebius synthesis finding contained unexpected key: {unexpected[0]}")
        source_id = str(finding.get("source_id") or "")
        if source_id not in allowed_ids:
            raise ValueError(f"Nebius synthesis finding cited unknown source id: {source_id}")
        limitation = _clean_string(finding.get("limitation"))
        if "human review" not in limitation.lower():
            raise ValueError("Nebius synthesis finding limitation must require human review")
        clean_findings.append(
            {
                "source_id": source_id,
                "finding": _clean_string(finding.get("finding")),
                "limitation": limitation,
            }
        )

    if _urls_in_text(parsed):
        raise ValueError("Nebius synthesis must cite source IDs, not URLs")
    joined = json.dumps(parsed, sort_keys=True).lower()
    forbidden = [
        phrase
        for phrase in tuple(NEBIUS_FORBIDDEN_NARRATION_PHRASES) + NEBIUS_EVIDENCE_SYNTHESIS_FORBIDDEN_PHRASES
        if phrase.lower() in joined
    ]
    if forbidden:
        raise ValueError(f"Nebius synthesis contained forbidden phrase: {forbidden[0]}")
    if "IA does not approve this request." not in parsed["safety_anchor"]:
        raise ValueError("Nebius synthesis safety anchor does not preserve no-approval language")

    return {
        "reviewer_summary": _clean_string(parsed["reviewer_summary"]),
        "cited_source_ids": cited,
        "source_findings": clean_findings,
        "remaining_proof_gaps": _clean_string(parsed["remaining_proof_gaps"]),
        "next_human_action": _clean_string(parsed["next_human_action"]),
        "safety_anchor": parsed["safety_anchor"],
    }


def build_nebius_evidence_synthesis(
    packet: dict[str, Any],
    *,
    tavily_proof: dict[str, Any] | None = None,
    composio_proof: dict[str, Any] | None = None,
    openclaw_trace: dict[str, Any] | None = None,
    portkey_preview: dict[str, Any] | None = None,
    live_enabled: bool = False,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Synthesize collected proof without expanding authority."""
    sources = _source_index(tavily_proof)
    if not live_enabled:
        return _base_payload(packet, sources, live_enabled=False, fallback_reason="live_not_requested")
    if not sources:
        return _base_payload(packet, sources, live_enabled=True, fallback_reason="no_tavily_sources")
    if config.LLM_PROVIDER != "nebius" or not config.LLM_API_KEY:
        return _base_payload(packet, sources, live_enabled=True, fallback_reason="nebius_api_key_missing")

    payload = _base_payload(packet, sources, live_enabled=True, fallback_reason="nebius_live_guardrail_fallback")
    payload["live_call_attempted"] = True
    try:
        client = (client_factory or _client)()
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. You synthesize collected proof; you do not approve, "
                        "grant, write, mutate, invent URLs, or reduce proof debt."
                    ),
                },
                {
                    "role": "user",
                    "content": _prompt(
                        packet,
                        sources,
                        composio_proof=composio_proof,
                        openclaw_trace=openclaw_trace,
                        portkey_preview=portkey_preview,
                    ),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=1400,
        )
        raw = response.choices[0].message.content or ""
        synthesis = _validate_synthesis(_parse_json_object(raw), sources)
    except Exception as exc:
        payload["fallback_detail"] = str(exc).splitlines()[0][:180]
        return payload

    payload.update(
        {
            "status": "live_evidence_synthesis_built",
            "live_call_count": 1,
            "used_live_key": True,
            "fallback_used": False,
            "fallback_reason": "",
            "synthesis": synthesis,
            "required_anchors_present": True,
            "forbidden_phrases_present": [],
        }
    )
    return payload
