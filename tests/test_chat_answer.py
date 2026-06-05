"""Structured chat answer contract."""

from agent.chat_answer import (
    CHAT_ANSWER_SCHEMA_VERSION,
    build_access_review_answer,
    build_product_positioning_answer,
    build_spend_review_answer,
)


def test_product_positioning_answer_is_control_layer_not_chatbot_hype():
    answer = build_product_positioning_answer().to_dict()

    assert answer["schema_version"] == CHAT_ANSWER_SCHEMA_VERSION
    assert answer["answer_kind"] == "product_positioning"
    assert "packet authority layer" in answer["reply_markdown"]
    assert "better generic chatbot" in answer["reply_markdown"]
    assert "export_report" not in answer["reply_markdown"]
    assert answer["safety"]["requires_human_review"] is True
    assert answer["safety"]["production_access"] is False
    assert "docs/CONTRACT.md" in answer["artifacts"]


def test_access_review_answer_is_packet_backed_and_non_approving():
    answer = build_access_review_answer().to_dict()

    assert answer["schema_version"] == CHAT_ANSWER_SCHEMA_VERSION
    assert answer["answer_kind"] == "agent_access_review"
    assert answer["packet_refs"][0]["packet_id"] == "ia-agent-access-support-triage-v0"
    assert "No production access" in answer["reply_markdown"]
    assert "Missing proof" in answer["reply_markdown"]
    assert answer["safety"]["approves_access"] is False
    assert answer["safety"]["external_writes"] is False
    assert answer["next_human_action"]


def test_spend_review_answer_routes_to_finance_without_savings_claim():
    answer = build_spend_review_answer().to_dict()
    reply = answer["reply_markdown"].lower()

    assert answer["schema_version"] == CHAT_ANSWER_SCHEMA_VERSION
    assert answer["answer_kind"] == "ai_spend_review"
    assert "finance and procurement review packet" in reply
    assert "not an optimizer verdict" in reply
    assert "evidence finance/procurement need" in reply
    assert answer["safety"]["approves_spend"] is False
    assert answer["safety"]["selects_provider"] is False
    assert answer["safety"]["guarantees_savings"] is False
    assert "will save" not in reply
    assert "best provider" not in reply
    assert "final winner" not in reply
