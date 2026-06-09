"""Packet-derived blast-radius tests."""

from __future__ import annotations

from agent.blast_radius import BLAST_RADIUS_SCHEMA_VERSION, build_packet_blast_radius, classify_action
from agent.scenarios import build_scenario_packet


def test_blast_radius_classifies_write_and_admin_scope_without_execution() -> None:
    packet = build_scenario_packet("support_triage_agent")
    blast_radius = build_packet_blast_radius(packet, scenario_name="support_triage_agent")

    assert blast_radius["schema_version"] == BLAST_RADIUS_SCHEMA_VERSION
    assert blast_radius["packet_id"] == packet["packet_id"]
    assert blast_radius["tool_count"] == 3
    assert blast_radius["summary"]["blocked_action_count"] == 9
    assert blast_radius["summary"]["write_like_action_count"] == 5
    assert blast_radius["summary"]["admin_like_action_count"] == 4
    assert blast_radius["summary"]["max_risk_level"] == "critical"
    assert blast_radius["summary"]["all_blocked_before_execution"] is True
    assert blast_radius["summary"]["all_write_or_admin_blocked"] is True
    assert blast_radius["summary"]["would_execute"] is False
    assert blast_radius["summary"]["can_approve_access"] is False
    assert blast_radius["summary"]["can_grant_permissions"] is False
    assert blast_radius["summary"]["can_mutate_external_state"] is False
    assert blast_radius["summary"]["human_review_required"] is True

    for tool in blast_radius["tools"]:
        assert tool["summary"]["all_blocked_before_execution"] is True
        assert tool["summary"]["would_execute"] is False
        assert tool["safety_boundary"]["read_only"] is True
        assert tool["safety_boundary"]["executes_external_writes"] is False
        for action in tool["blocked_actions"]:
            assert action["policy_decision"] == "blocked_before_execution"
            assert action["would_execute"] is False
            assert action["can_approve_access"] is False
            assert action["can_grant_permissions"] is False
            assert action["can_mutate_external_state"] is False
            assert action["human_review_required"] is True


def test_blast_radius_action_classifier_has_stable_operator_terms() -> None:
    assert classify_action("repo configuration changes") == "admin_like"
    assert classify_action("workflow dispatch") == "admin_like"
    assert classify_action("posting messages") == "write_like"
    assert classify_action("ticket creation") == "write_like"
    assert classify_action("read incident summary") == "sensitive_read"
