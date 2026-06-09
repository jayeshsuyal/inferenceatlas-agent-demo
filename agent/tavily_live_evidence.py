"""Optional Tavily evidence collection for sponsor proof runs.

Tavily may add source candidates to a SponsorProofTrace. It must not approve
access, reduce proof debt, grant permissions, write externally, or mutate the
IA Packet.
"""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any, Callable

from .adapters import build_adapter_result
from .config import TAVILY_API_KEY


TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION = "tavily_live_evidence.v0"
TAVILY_DOCS_URL = "https://docs.tavily.com/documentation/api-reference/endpoint/search"
DEFAULT_TAVILY_MAX_RESULTS = 2
DEFAULT_QUERY_VARIANTS_PER_CANDIDATE = 2

ClientFactory = Callable[[str], Any]


def _sanitize_error(exc: Exception) -> dict[str, str]:
    return {
        "type": exc.__class__.__name__,
        "message": "Tavily live evidence collection failed; deterministic fallback retained.",
    }


def _trust_tier(domain: str) -> str:
    if domain.endswith(".gov") or domain.endswith(".mil"):
        return "public_authority"
    if domain.endswith(".edu"):
        return "academic"
    if domain in {
        "anthropic.com",
        "composio.dev",
        "docs.composio.dev",
        "docs.tavily.com",
        "github.com",
        "openai.com",
        "portkey.ai",
        "docs.portkey.ai",
        "tavily.com",
    }:
        return "platform_or_vendor"
    if domain in {
        "axios.com",
        "bloomberg.com",
        "reuters.com",
        "techcrunch.com",
        "theverge.com",
        "wired.com",
    }:
        return "recognized_media"
    return "unknown_public_source"


def _source_from_result(result: dict[str, Any], *, query: str) -> dict[str, Any]:
    url = str(result.get("url") or "")
    domain = _domain(url)
    return {
        "title": str(result.get("title") or "Untitled")[:180],
        "url": url,
        "domain": domain,
        "trust_tier": _trust_tier(domain),
        "query": query,
        "content_snippet": str(result.get("content") or "")[:500],
        "score": result.get("score"),
    }


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def _source_quality(candidate: dict[str, Any]) -> dict[str, Any]:
    source_urls = [str(url) for url in candidate.get("source_urls", []) if url]
    unique_urls = list(dict.fromkeys(source_urls))
    domains = list(dict.fromkeys(_domain(url) for url in unique_urls if _domain(url)))
    trust_tiers = [
        _trust_tier(domain)
        for domain in domains
    ]
    return {
        "source_count": len(source_urls),
        "unique_source_count": len(unique_urls),
        "source_domains": domains,
        "source_domain_count": len(domains),
        "trust_tiers": trust_tiers,
        "trust_tier_counts": {tier: trust_tiers.count(tier) for tier in sorted(set(trust_tiers))},
        "diversity_score": min(len(domains), 5) / 5,
        "freshness": candidate.get("freshness", "not_fetched_in_offline_mode"),
        "search_mode": candidate.get("search_mode", "planned_search_extract_or_crawl"),
        "human_review_required": True,
        "can_reduce_proof_debt": False,
        "cannot_grant_access": True,
    }


def _with_source_quality(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**candidate, "source_quality": _source_quality(candidate)} for candidate in candidates]


def _query_plan_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    owners = [candidate.get("reviewer_owner") for candidate in candidates if candidate.get("reviewer_owner")]
    total_searches = sum(len(candidate.get("query_variants", [candidate["query"]])) for candidate in candidates)
    return {
        "query_count": len(candidates),
        "query_variant_count": total_searches,
        "total_planned_searches": total_searches,
        "query_strategy": "packet_missing_proof_multi_query",
        "reviewer_owners": list(dict.fromkeys(owners)),
        "planned_queries": [candidate["query"] for candidate in candidates],
        "planned_query_variants": [
            {
                "query": candidate["query"],
                "variants": candidate.get("query_variants", [candidate["query"]]),
            }
            for candidate in candidates
        ],
        "search_depth": "basic",
        "include_raw_content": False,
        "human_review_required": True,
    }


def _source_quality_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    source_urls = [
        str(url)
        for candidate in candidates
        for url in candidate.get("source_urls", [])
        if url
    ]
    unique_urls = list(dict.fromkeys(source_urls))
    domains = list(dict.fromkeys(_domain(url) for url in unique_urls if _domain(url)))
    trust_tiers = [_trust_tier(domain) for domain in domains]
    return {
        "query_count": len(candidates),
        "query_variant_count": sum(len(candidate.get("query_variants", [candidate["query"]])) for candidate in candidates),
        "source_url_count": len(source_urls),
        "unique_source_url_count": len(unique_urls),
        "source_domain_count": len(domains),
        "source_domains": domains,
        "trust_tier_counts": {tier: trust_tiers.count(tier) for tier in sorted(set(trust_tiers))},
        "domain_diversity_score": min(len(domains), 5) / 5,
        "sources_per_query": [
            {
                "query": candidate["query"],
                "query_variant_count": len(candidate.get("query_variants", [candidate["query"]])),
                "source_count": len(candidate.get("source_urls", [])),
                "unique_source_count": candidate.get("source_quality", {}).get(
                    "unique_source_count",
                    len(set(candidate.get("source_urls", []))),
                ),
            }
            for candidate in candidates
        ],
        "freshness_labels": list(
            dict.fromkeys(
                candidate.get("freshness", "not_fetched_in_offline_mode")
                for candidate in candidates
            )
        ),
        "human_review_required": True,
        "can_reduce_proof_debt": False,
        "cannot_grant_access": True,
    }


def _query_variants(candidate: dict[str, Any], *, max_variants: int) -> list[str]:
    base = str(candidate["query"])
    owner = str(candidate.get("reviewer_owner") or "").strip()
    unblocks = str(candidate.get("unblocks") or "").strip()
    variants = [base]
    if owner:
        variants.append(f"{owner} {base}")
    if unblocks:
        variants.append(f"{unblocks} evidence")
    return list(dict.fromkeys(variants))[: max(1, min(max_variants, 3))]


def _with_query_variants(candidates: list[dict[str, Any]], *, max_variants: int) -> list[dict[str, Any]]:
    return [
        {
            **candidate,
            "query_variants": _query_variants(candidate, max_variants=max_variants),
        }
        for candidate in candidates
    ]


def _fallback_payload(scenario_name: str, *, live_requested: bool, reason: str) -> dict[str, Any]:
    fallback = build_adapter_result("tavily", scenario_name)
    candidates = _with_source_quality(
        _with_query_variants(
            fallback["evidence_candidates"],
            max_variants=DEFAULT_QUERY_VARIANTS_PER_CANDIDATE,
        )
    )
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
            "evidence_candidates": candidates,
            "query_plan_summary": _query_plan_summary(candidates),
            "source_quality_summary": _source_quality_summary(candidates),
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
    query_variants_per_candidate: int = DEFAULT_QUERY_VARIANTS_PER_CANDIDATE,
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
        for candidate in _with_query_variants(
            fallback["evidence_candidates"],
            max_variants=query_variants_per_candidate,
        ):
            sources = []
            for query in candidate["query_variants"]:
                response = client.search(
                    query=query,
                    max_results=max(1, min(int(max_results), 5)),
                    search_depth="basic",
                    include_answer=False,
                    include_raw_content=False,
                    auto_parameters=False,
                )
                live_call_count += 1
                sources.extend(
                    _source_from_result(item, query=query)
                    for item in (response or {}).get("results", [])
                    if isinstance(item, dict) and item.get("url")
                )
            unique_sources = []
            seen_urls = set()
            for source in sources:
                if source["url"] in seen_urls:
                    continue
                seen_urls.add(source["url"])
                unique_sources.append(source)
            enriched_candidates.append(
                {
                    **candidate,
                    "source_urls": [source["url"] for source in unique_sources],
                    "source_notes": unique_sources,
                    "freshness": "fetched_at_runtime",
                    "search_mode": "tavily_search_basic_multi_query",
                    "human_review_required": True,
                    "can_reduce_proof_debt": False,
                    "cannot_grant_access": True,
                }
            )
        enriched_candidates = _with_source_quality(enriched_candidates)

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
            "query_plan_summary": _query_plan_summary(enriched_candidates),
            "source_quality_summary": _source_quality_summary(enriched_candidates),
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
        candidates = _with_source_quality(
            _with_query_variants(
                fallback["evidence_candidates"],
                max_variants=query_variants_per_candidate,
            )
        )
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
                "evidence_candidates": candidates,
                "query_plan_summary": _query_plan_summary(candidates),
                "source_quality_summary": _source_quality_summary(candidates),
            }
        )
        return fallback
