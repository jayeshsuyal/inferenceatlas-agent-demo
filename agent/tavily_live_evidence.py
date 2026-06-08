"""Optional Tavily evidence collection for sponsor proof runs.

Tavily may add source candidates to a SponsorProofTrace. It must not approve
access, reduce proof debt, grant permissions, write externally, or mutate the
IA Packet.
"""

from __future__ import annotations

from typing import Any, Callable

from .adapters import build_adapter_result
from .config import TAVILY_API_KEY


TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION = "tavily_live_evidence.v0"
TAVILY_DOCS_URL = "https://docs.tavily.com/documentation/api-reference/endpoint/search"
DEFAULT_TAVILY_MAX_RESULTS = 2

ClientFactory = Callable[[str], Any]


def _sanitize_error(exc: Exception) -> dict[str, str]:
    return {
        "type": exc.__class__.__name__,
        "message": "Tavily live evidence collection failed; deterministic fallback retained.",
    }


def _source_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(result.get("title") or "Untitled")[:180],
        "url": str(result.get("url") or ""),
        "content_snippet": str(result.get("content") or "")[:500],
        "score": result.get("score"),
    }


def _fallback_payload(scenario_name: str, *, live_requested: bool, reason: str) -> dict[str, Any]:
    fallback = build_adapter_result("tavily", scenario_name)
    fallback.update(
        {
            "live_evidence_schema_version": TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
            "live_requested": live_requested,
            "live_call_attempted": False,
            "live_call_count": 0,
            "used_live_key": False,
            "fallback_used": True,
            "fallback_reason": reason,
            "docs_reference": TAVILY_DOCS_URL,
        }
    )
    return fallback


def build_tavily_live_evidence(
    packet: dict[str, Any],
    *,
    scenario_name: str,
    live_enabled: bool = False,
    api_key: str | None = None,
    max_results: int = DEFAULT_TAVILY_MAX_RESULTS,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Build Tavily evidence candidates, with deterministic fallback by default.

    Tavily's Search API requires `query`; this adapter pins `search_depth` to
    `basic`, sets `max_results` explicitly, and disables raw-content retrieval
    so live collection remains small and review-oriented.
    """
    if not live_enabled:
        return _fallback_payload(
            scenario_name,
            live_requested=False,
            reason="live_tavily_not_requested",
        )

    key = (api_key if api_key is not None else TAVILY_API_KEY).strip()
    if not key:
        return _fallback_payload(
            scenario_name,
            live_requested=True,
            reason="tavily_api_key_missing",
        )

    fallback = build_adapter_result("tavily", scenario_name)
    try:
        if client_factory is None:
            from tavily import TavilyClient

            client = TavilyClient(api_key=key)
        else:
            client = client_factory(key)

        enriched_candidates = []
        live_call_count = 0
        for candidate in fallback["evidence_candidates"]:
            query = candidate["query"]
            response = client.search(
                query=query,
                max_results=max(1, min(int(max_results), 5)),
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
                auto_parameters=False,
            )
            live_call_count += 1
            sources = [
                _source_from_result(item)
                for item in (response or {}).get("results", [])
                if isinstance(item, dict) and item.get("url")
            ]
            enriched_candidates.append(
                {
                    **candidate,
                    "source_urls": [source["url"] for source in sources],
                    "source_notes": sources,
                    "freshness": "fetched_at_runtime",
                    "search_mode": "tavily_search_basic",
                    "human_review_required": True,
                    "can_reduce_proof_debt": False,
                    "cannot_grant_access": True,
                }
            )

        live_payload = {
            **fallback,
            "live_evidence_schema_version": TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
            "status": "live_evidence_candidates_fetched",
            "mode": "live_read_only_evidence_collection",
            "requires_api_key": True,
            "live_mode_enabled": True,
            "live_requested": True,
            "live_call_attempted": True,
            "live_call_count": live_call_count,
            "used_live_key": True,
            "fallback_used": False,
            "fallback_reason": "",
            "evidence_candidates": enriched_candidates,
            "proof_pack": {
                **fallback["proof_pack"],
                "proof_type": "live_evidence_candidates",
                "visible_output": "source-backed evidence candidates with URLs and freshness labels",
                "cannot_do": [
                    "approve access",
                    "grant permissions",
                    "declare compliance",
                    "reduce proof debt automatically",
                    "mutate external systems",
                ],
            },
            "docs_reference": TAVILY_DOCS_URL,
            "safety_impact": "none",
        }
        return live_payload
    except Exception as exc:  # pragma: no cover - exact SDK failures vary.
        fallback.update(
            {
                "live_evidence_schema_version": TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
                "live_requested": True,
                "live_call_attempted": True,
                "live_call_count": 0,
                "used_live_key": True,
                "fallback_used": True,
                "fallback_reason": "tavily_live_error",
                "live_error": _sanitize_error(exc),
                "docs_reference": TAVILY_DOCS_URL,
            }
        )
        return fallback
