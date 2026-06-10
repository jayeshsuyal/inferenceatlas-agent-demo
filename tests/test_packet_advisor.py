"""Shared Packet Advisor contract for CLI and Ask IA."""

from __future__ import annotations

import json
import subprocess
import sys

from agent.chat_orchestrator import ASK_IA_INTAKE_SCHEMA_VERSION, orchestrate_chat
from agent.packet_advisor import (
    PACKET_ADVISOR_SCHEMA_VERSION,
    build_packet_advisor_answer,
    route_question,
    should_use_packet_advisor,
)


REQUIRED_TONE_ANCHORS = (
    "does not approve",
    "human review",
    "stays blocked",
)

FORBIDDEN_HEDGES = (
    "probably",
    "technically",
    "looks like",
)


def assert_safe_tone(answer: dict) -> None:
    rendered = answer["rendered_text"].lower()
    for anchor in REQUIRED_TONE_ANCHORS:
        assert anchor in rendered
    for hedge in FORBIDDEN_HEDGES:
        assert hedge not in rendered
    assert answer["tone_invariants"]["forbidden_hedges"] == []


def test_question_router_is_bounded_and_deterministic() -> None:
    assert route_question("Can Portkey allow this spend?") == "decision"
    assert route_question("What proof is missing before changing AI spend or vendors?") == "proof_status"
    assert route_question("Who should Finance and Procurement route this to?") == "reviewer_routing"
    assert route_question("Is production access safe?") == "safety_status"
    assert route_question("tell me a joke") == "unsupported"
    assert should_use_packet_advisor("hey", current_fixture="mcp_tool_blast_radius") is False


def test_portkey_spend_gate_answer_is_packet_backed_and_non_approving() -> None:
    answer = build_packet_advisor_answer(
        fixture="ai_spend_budget_overrun",
        subscriber="portkey_model_spend_gate",
        question="Can Portkey allow this spend?",
    )

    assert answer["schema_version"] == PACKET_ADVISOR_SCHEMA_VERSION
    assert answer["answer_kind"] == "decision"
    assert answer["fixture"]["fixture_id"] == "ai_spend_budget_overrun"
    assert answer["subscriber"] == "portkey_model_spend_gate"
    assert answer["packet_reference"]["packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert answer["decision"]["approves_spend"] is False
    assert answer["safety"]["approves_spend"] is False
    assert answer["safety"]["selects_provider"] is False
    assert answer["safety"]["guarantees_savings"] is False
    assert answer["downstream_gate"]["requested_action_can_proceed"] is False
    assert answer["downstream_gate"]["invariants"]["can_mutate_packet"] is False
    assert "Portkey cannot allow this request" in answer["rendered_text"]
    assert_safe_tone(answer)


def test_cli_emits_same_packet_advisor_json_contract() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.packet_advisor",
            "--fixture",
            "ai_spend_budget_overrun",
            "--subscriber",
            "portkey_model_spend_gate",
            "--question",
            "Can Portkey allow this spend?",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    answer = json.loads(proc.stdout)

    assert answer["schema_version"] == PACKET_ADVISOR_SCHEMA_VERSION
    assert answer["answer_kind"] == "decision"
    assert answer["packet_reference"]["packet_id"] == "ia-spend-review-ai_spend_budget_overrun-v0"
    assert answer["downstream_gate"]["decision"] == "blocked"
    assert_safe_tone(answer)


def test_ask_ia_and_cli_share_packet_advisor_truth() -> None:
    question = "Can Portkey allow this spend?"
    cli_answer = build_packet_advisor_answer(
        fixture="ai_spend_budget_overrun",
        subscriber="portkey_model_spend_gate",
        question=question,
    )
    orch = orchestrate_chat(
        message=question,
        skill_ids=[],
        skill_position="prepend",
        session_id="packet-advisor-parity",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
        current_fixture="ai_spend_budget_overrun",
    )
    ask_answer = orch.direct_answer

    assert orch.direct_reply_source == "packet_advisor"
    assert ask_answer["schema_version"] == PACKET_ADVISOR_SCHEMA_VERSION
    assert ask_answer["packet_reference"] == cli_answer["packet_reference"]
    assert ask_answer["verdict_class"] == cli_answer["verdict_class"]
    assert ask_answer["answer_kind"] == cli_answer["answer_kind"]
    assert ask_answer["next_human_action"] == cli_answer["next_human_action"]
    assert ask_answer["decision"] == cli_answer["decision"]
    assert ask_answer["safety"] == cli_answer["safety"]
    assert ask_answer["downstream_gate"] == cli_answer["downstream_gate"]
    assert orch.use_tools is False
    assert "Packet-backed chat: shared CLI/API truth" in orch.context_manifest
    assert ask_answer["chat_salience"]["destination_surface"] == "portkey_adapter_preview"
    assert_safe_tone(ask_answer)


def test_buyer_language_spend_question_uses_packet_advisor_not_catalog_tools() -> None:
    orch = orchestrate_chat(
        message="What proof does IA require before changing AI spend or vendors?",
        skill_ids=[],
        skill_position="prepend",
        session_id="packet-advisor-buyer-language",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
    )

    assert orch.direct_reply_source == "packet_advisor"
    assert orch.direct_answer["answer_kind"] == "proof_status"
    assert orch.direct_answer["fixture"]["fixture_id"] == "ai_spend_budget_overrun"
    assert orch.use_tools is False
    assert "Catalog" not in orch.direct_reply
    assert "IA requires proof" in orch.direct_reply
    assert_safe_tone(orch.direct_answer)


def test_ask_ia_greeting_uses_intake_not_packet_dump() -> None:
    orch = orchestrate_chat(
        message="hey",
        skill_ids=[],
        skill_position="prepend",
        session_id="ask-ia-greeting",
        github_repos=[],
        drive_file_ids=[],
        file_blocks=[],
        attach_warnings=[],
        current_fixture="mcp_tool_blast_radius",
    )

    assert orch.direct_reply_source == "ask_ia_intake"
    assert orch.direct_answer["schema_version"] == ASK_IA_INTAKE_SCHEMA_VERSION
    assert orch.direct_answer["invariants"]["raw_packet_dumped"] is False
    assert orch.direct_answer["invariants"]["uses_packet_advisor"] is False
    assert orch.use_tools is False
    assert "Ask IA intake" in orch.context_manifest
    assert "Can this move?" in orch.direct_reply
    assert "What proof is missing?" in orch.direct_reply
    assert "packet_id" not in orch.direct_reply
    assert "Top blocker" not in orch.direct_reply
