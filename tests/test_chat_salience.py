"""Chat salience surface over packet-backed answers."""

from __future__ import annotations

from agent.chat_salience import (
    CHAT_SALIENCE_SCHEMA_VERSION,
    build_chat_salience_surface,
    render_chat_salience_markdown,
)
from agent.packet_advisor import build_packet_advisor_answer


def test_salience_surface_projects_portkey_question_without_changing_truth() -> None:
    answer = build_packet_advisor_answer(
        fixture="ai_spend_budget_overrun",
        subscriber="portkey_model_spend_gate",
        question="Can Portkey allow this spend?",
    )
    surface = build_chat_salience_surface(answer)

    assert surface["schema_version"] == CHAT_SALIENCE_SCHEMA_VERSION
    assert surface["destination_surface"] == "portkey_adapter_preview"
    assert surface["destination_label"] == "Preview Portkey gate"
    assert surface["destination_path"] == "/api/packets/ai_spend_budget_overrun/downstream/portkey?mode=dry-run"
    assert "Portkey cannot allow this request" in surface["current_read"]
    assert surface["top_blocker"] == "The packet has no invoice-backed Finance approval."
    assert surface["next_human_action"] == answer["next_human_action"]
    assert "vendor invoices" in surface["one_proof_question"]
    assert "Packet-backed" in surface["source_line"]
    assert "ia-spend-review-ai_spend_budget_overrun-v0" in surface["source_line"]
    assert surface["guardrails"]["read_only"] is True
    assert surface["guardrails"]["approved"] is False
    assert surface["guardrails"]["mutated_packet"] is False
    assert surface["guardrails"]["dispatched"] is False


def test_salience_portkey_preview_uses_adapter_contract() -> None:
    answer = build_packet_advisor_answer(
        fixture="ai_spend_budget_overrun",
        question="Can Portkey allow this spend?",
    )
    surface = build_chat_salience_surface(answer)
    preview = surface["portkey_adapter_preview"]

    assert preview["schema_version"] == "portkey_gate_v0"
    assert preview["api_call_made"] is False
    assert preview["portkey_guardrail_response"]["verdict"] is False
    assert preview["usage_policy_plan"]["request_body"]["credit_limit"] == 0
    assert preview["invariants"]["packet_mutation_allowed"] is False


def test_salience_markdown_is_compact_and_not_raw_packet_dump() -> None:
    answer = build_packet_advisor_answer(
        fixture="ai_spend_budget_overrun",
        subscriber="portkey_model_spend_gate",
        question="Can Portkey allow this spend?",
    )
    markdown = render_chat_salience_markdown(build_chat_salience_surface(answer))

    assert "## Current read" in markdown
    assert "**Top blocker:**" in markdown
    assert "**Next human action:**" in markdown
    assert "**One proof question:**" in markdown
    assert "**Inspect:** Preview Portkey gate" in markdown
    assert "**Source:** Packet-backed" in markdown
    assert "## Portkey preview" in markdown
    assert "guardrail verdict: `false`" in markdown
    assert "api call made: `false`" in markdown
    assert "schema_version" not in markdown
    assert "raw packet" not in markdown.lower()
    assert "probably" not in markdown.lower()
    assert "looks like" not in markdown.lower()
