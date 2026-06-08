"""Optional Tavily live evidence adapter tests."""

from __future__ import annotations

from agent.scenarios import build_scenario_packet
from agent.tavily_live_evidence import (
    TAVILY_DOCS_URL,
    TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
    build_tavily_live_evidence,
)


class FakeTavilyClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def search(self, **kwargs):
        self.requests.append(kwargs)
        return {
            "query": kwargs["query"],
            "results": [
                {
                    "title": "Example policy evidence",
                    "url": "https://example.com/security-policy",
                    "content": "Evidence candidate for reviewer inspection.",
                    "score": 0.91,
                }
            ],
        }


def test_tavily_live_evidence_falls_back_without_key() -> None:
    packet = build_scenario_packet("support_triage_agent")
    payload = build_tavily_live_evidence(
        packet,
        scenario_name="support_triage_agent",
        live_enabled=True,
        api_key="",
    )

    assert payload["live_evidence_schema_version"] == TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION
    assert payload["status"] == "evidence_candidates_planned"
    assert payload["live_requested"] is True
    assert payload["live_call_attempted"] is False
    assert payload["live_call_count"] == 0
    assert payload["used_live_key"] is False
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "tavily_api_key_missing"
    assert payload["docs_reference"] == TAVILY_DOCS_URL
    assert all(candidate["source_urls"] == [] for candidate in payload["evidence_candidates"])
    assert all(candidate["can_reduce_proof_debt"] is False for candidate in payload["evidence_candidates"])
    assert all(candidate["cannot_grant_access"] is True for candidate in payload["evidence_candidates"])


def test_tavily_live_evidence_collects_sources_without_reducing_proof_debt() -> None:
    packet = build_scenario_packet("support_triage_agent")
    fake_client = FakeTavilyClient()
    payload = build_tavily_live_evidence(
        packet,
        scenario_name="support_triage_agent",
        live_enabled=True,
        api_key="unit-test-key",
        max_results=1,
        client_factory=lambda _key: fake_client,
    )

    assert payload["status"] == "live_evidence_candidates_fetched"
    assert payload["mode"] == "live_read_only_evidence_collection"
    assert payload["live_call_attempted"] is True
    assert payload["live_call_count"] == len(packet["missing_proof"])
    assert payload["used_live_key"] is True
    assert payload["fallback_used"] is False
    assert payload["would_execute"] is False
    assert payload["can_approve_access"] is False
    assert payload["can_grant_permissions"] is False
    assert payload["can_mutate_external_state"] is False
    assert payload["blocked_from_approving_access"] is True
    assert payload["human_review_required"] is True
    assert payload["safety_impact"] == "none"
    assert "mutate external systems" in payload["proof_pack"]["cannot_do"]
    assert all(candidate["source_urls"] for candidate in payload["evidence_candidates"])
    assert all(candidate["source_notes"] for candidate in payload["evidence_candidates"])
    assert all(candidate["can_reduce_proof_debt"] is False for candidate in payload["evidence_candidates"])
    assert all(candidate["cannot_grant_access"] is True for candidate in payload["evidence_candidates"])

    assert fake_client.requests
    for request in fake_client.requests:
        assert request["max_results"] == 1
        assert request["search_depth"] == "basic"
        assert request["include_answer"] is False
        assert request["include_raw_content"] is False
        assert request["auto_parameters"] is False
