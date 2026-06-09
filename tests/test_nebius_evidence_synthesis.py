"""Nebius evidence synthesis guardrail tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from agent.nebius_evidence_synthesis import (
    NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR,
    NEBIUS_EVIDENCE_SYNTHESIS_SCHEMA_VERSION,
    build_nebius_evidence_synthesis,
)
from agent.scenarios import build_scenario_packet


def _tavily_proof() -> dict:
    return {
        "evidence_candidates": [
            {
                "query": "customer data retention policy evidence",
                "reviewer_owner": "Security/Legal",
                "unblocks": "Customer-data handling is safe.",
                "source_urls": ["https://example.com/security-policy"],
                "source_notes": [
                    {
                        "title": "Security policy evidence",
                        "url": "https://example.com/security-policy",
                        "content_snippet": "Evidence candidate for reviewer inspection.",
                        "score": 0.91,
                    }
                ],
                "human_review_required": True,
                "can_reduce_proof_debt": False,
            }
        ]
    }


def _fake_client(content: str):
    def create(**kwargs):
        return SimpleNamespace(
            request=kwargs,
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ],
        )

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _valid_synthesis_content() -> str:
    return (
        "{"
        '"reviewer_summary":"IA collected Tavily source candidates for reviewer inspection while the packet decision remains locked.",'
        '"cited_source_ids":["tavily:1"],'
        '"source_findings":[{"source_id":"tavily:1","finding":"The source is relevant context for the named Security reviewer.","limitation":"Human review is required before this can affect proof debt."}],'
        '"remaining_proof_gaps":"Internal policy evidence, owner approval, and audit logs remain missing.",'
        '"next_human_action":"Route the source candidate to Security/Legal with the packet proof debt attached.",'
        f'"safety_anchor":"{NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR}"'
        "}"
    )


def test_evidence_synthesis_fallback_indexes_tavily_sources_without_deciding() -> None:
    packet = build_scenario_packet("support_triage_agent")
    payload = build_nebius_evidence_synthesis(packet, tavily_proof=_tavily_proof())

    assert payload["schema_version"] == NEBIUS_EVIDENCE_SYNTHESIS_SCHEMA_VERSION
    assert payload["status"] == "deterministic_evidence_synthesis_fallback"
    assert payload["live_call_attempted"] is False
    assert payload["live_call_count"] == 0
    assert payload["fallback_used"] is True
    assert payload["source_index_count"] == 1
    assert payload["source_index"][0]["source_id"] == "tavily:1"
    assert payload["source_index"][0]["url"] == "https://example.com/security-policy"
    assert payload["synthesis"]["cited_source_ids"] == ["tavily:1"]
    assert payload["synthesis"]["safety_anchor"] == NEBIUS_EVIDENCE_SYNTHESIS_SAFETY_ANCHOR
    assert payload["invariants"]["source_ids_from_tavily_only"] is True
    assert payload["invariants"]["source_urls_from_tavily_only"] is True
    assert payload["invariants"]["no_new_urls"] is True
    assert payload["invariants"]["can_reduce_proof_debt"] is False
    assert payload["invariants"]["can_approve_access"] is False
    assert payload["invariants"]["can_grant_permissions"] is False
    assert payload["invariants"]["can_mutate_packet"] is False
    assert payload["invariants"]["human_review_required"] is True


def test_live_evidence_synthesis_cites_only_existing_tavily_source_ids() -> None:
    packet = build_scenario_packet("support_triage_agent")

    with patch("agent.nebius_evidence_synthesis.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_evidence_synthesis.config.LLM_API_KEY", "test-key"
    ), patch("agent.nebius_evidence_synthesis.config.LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct"):
        payload = build_nebius_evidence_synthesis(
            packet,
            tavily_proof=_tavily_proof(),
            live_enabled=True,
            client_factory=lambda: _fake_client(_valid_synthesis_content()),
        )

    assert payload["status"] == "live_evidence_synthesis_built"
    assert payload["mode"] == "live_read_only_evidence_synthesis"
    assert payload["live_call_attempted"] is True
    assert payload["live_call_count"] == 1
    assert payload["used_live_key"] is True
    assert payload["fallback_used"] is False
    assert payload["synthesis"]["cited_source_ids"] == ["tavily:1"]
    assert payload["synthesis"]["source_findings"][0]["source_id"] == "tavily:1"
    assert payload["required_anchors_present"] is True
    assert payload["forbidden_phrases_present"] == []
    assert payload["invariants"]["no_new_urls"] is True
    assert payload["invariants"]["can_reduce_proof_debt"] is False


def test_live_evidence_synthesis_falls_back_on_unknown_source_id() -> None:
    packet = build_scenario_packet("support_triage_agent")
    invented = _valid_synthesis_content().replace('"tavily:1"', '"tavily:999"')

    with patch("agent.nebius_evidence_synthesis.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_evidence_synthesis.config.LLM_API_KEY", "test-key"
    ):
        payload = build_nebius_evidence_synthesis(
            packet,
            tavily_proof=_tavily_proof(),
            live_enabled=True,
            client_factory=lambda: _fake_client(invented),
        )

    assert payload["status"] == "deterministic_evidence_synthesis_fallback"
    assert payload["live_call_attempted"] is True
    assert payload["live_call_count"] == 0
    assert payload["used_live_key"] is False
    assert payload["fallback_used"] is True
    assert "unknown source id" in payload["fallback_detail"]
    assert payload["synthesis"]["cited_source_ids"] == ["tavily:1"]
    assert payload["invariants"]["no_new_urls"] is True


def test_live_evidence_synthesis_falls_back_when_model_writes_urls() -> None:
    packet = build_scenario_packet("support_triage_agent")
    with_url = _valid_synthesis_content().replace(
        "The source is relevant context",
        "https://invented.example.com is relevant context",
    )

    with patch("agent.nebius_evidence_synthesis.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_evidence_synthesis.config.LLM_API_KEY", "test-key"
    ):
        payload = build_nebius_evidence_synthesis(
            packet,
            tavily_proof=_tavily_proof(),
            live_enabled=True,
            client_factory=lambda: _fake_client(with_url),
        )

    assert payload["status"] == "deterministic_evidence_synthesis_fallback"
    assert payload["fallback_used"] is True
    assert "source IDs, not URLs" in payload["fallback_detail"]
    assert payload["invariants"]["no_new_urls"] is True
