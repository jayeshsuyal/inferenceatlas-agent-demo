"""Nebius reviewer narration guardrail tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from agent.nebius_reviewer_narration import (
    NEBIUS_REQUIRED_SAFETY_ANCHOR,
    build_nebius_reviewer_narration,
)
from agent.scenarios import build_scenario_packet


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


def _valid_content() -> str:
    return (
        "{"
        '"reviewer_summary":"IA does not approve this request. The packet is blocked for live movement until the named proof is reviewed.",'
        '"decision_lock_sentence":"Human review is required before any access, spend, or production movement. Decision lock unchanged.",'
        '"next_human_action":"Route the request to the named reviewer owners with proof debt attached.",'
        f'"safety_anchor":"{NEBIUS_REQUIRED_SAFETY_ANCHOR}"'
        "}"
    )


def test_nebius_live_narration_uses_key_only_for_safe_structured_language() -> None:
    packet = build_scenario_packet("support_triage_agent")

    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"
    ), patch("agent.nebius_reviewer_narration.config.LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct"):
        payload = build_nebius_reviewer_narration(
            packet,
            live_enabled=True,
            client_factory=lambda: _fake_client(_valid_content()),
        )

    assert payload["status"] == "live_reviewer_narration_built"
    assert payload["live_call_attempted"] is True
    assert payload["live_call_count"] == 1
    assert payload["used_live_key"] is True
    assert payload["fallback_used"] is False
    assert payload["required_anchors_present"] is True
    assert payload["forbidden_phrases_present"] == []
    assert payload["would_execute"] is False
    assert payload["can_approve_access"] is False
    assert payload["can_grant_permissions"] is False
    assert payload["can_mutate_external_state"] is False
    assert payload["human_review_required"] is True
    assert NEBIUS_REQUIRED_SAFETY_ANCHOR in payload["narration"]


def test_nebius_live_narration_falls_back_without_key() -> None:
    packet = build_scenario_packet("support_triage_agent")

    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", ""
    ):
        payload = build_nebius_reviewer_narration(packet, live_enabled=True)

    assert payload["status"] == "deterministic_narration_fallback"
    assert payload["live_call_attempted"] is False
    assert payload["live_call_count"] == 0
    assert payload["used_live_key"] is False
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "nebius_api_key_missing"
    assert payload["required_anchors_present"] is True
    assert payload["can_approve_access"] is False


def test_nebius_live_narration_falls_back_on_unsafe_output() -> None:
    packet = build_scenario_packet("support_triage_agent")
    unsafe = (
        "{"
        '"reviewer_summary":"IA does not approve this request, but it is safe to proceed.",'
        '"decision_lock_sentence":"Human review is required before any access, spend, or production movement. Decision lock unchanged.",'
        '"next_human_action":"Proceed.",'
        f'"safety_anchor":"{NEBIUS_REQUIRED_SAFETY_ANCHOR}"'
        "}"
    )

    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"
    ):
        payload = build_nebius_reviewer_narration(
            packet,
            live_enabled=True,
            client_factory=lambda: _fake_client(unsafe),
        )

    assert payload["status"] == "deterministic_narration_fallback"
    assert payload["live_call_attempted"] is True
    assert payload["live_call_count"] == 0
    assert payload["used_live_key"] is False
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "nebius_live_guardrail_fallback"
    assert "forbidden narration phrase" in payload["fallback_detail"]
    assert "safe to proceed" not in payload["narration"].lower()


def test_nebius_live_narration_falls_back_on_generic_output() -> None:
    packet = build_scenario_packet("support_triage_agent")
    generic = (
        "{"
        '"reviewer_summary":"Access blocked",'
        '"decision_lock_sentence":"Human review is required before any access, spend, or production movement. Decision lock unchanged.",'
        '"next_human_action":"Review packet",'
        f'"safety_anchor":"{NEBIUS_REQUIRED_SAFETY_ANCHOR}"'
        "}"
    )

    with patch("agent.nebius_reviewer_narration.config.LLM_PROVIDER", "nebius"), patch(
        "agent.nebius_reviewer_narration.config.LLM_API_KEY", "test-key"
    ):
        payload = build_nebius_reviewer_narration(
            packet,
            live_enabled=True,
            client_factory=lambda: _fake_client(generic),
        )

    assert payload["status"] == "deterministic_narration_fallback"
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "nebius_live_guardrail_fallback"
    assert "too terse" in payload["fallback_detail"]
