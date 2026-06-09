"""Composio dry-run permission diff tests."""

from __future__ import annotations

from agent.composio_dry_run_diff import (
    COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION,
    COMPOSIO_EXECUTE_ACTION_DOCS_URL,
    COMPOSIO_PYTHON_SDK_DOCS_URL,
    build_composio_dry_run_diff,
)
from agent.scenarios import build_scenario_packet


def test_composio_dry_run_diff_defaults_to_existing_fallback_shape() -> None:
    packet = build_scenario_packet("support_triage_agent")
    payload = build_composio_dry_run_diff(
        packet,
        scenario_name="support_triage_agent",
        dry_run_enabled=False,
    )

    assert payload["dry_run_diff_schema_version"] == COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION
    assert payload["status"] == "dry_run_planned"
    assert payload["dry_run_requested"] is False
    assert payload["dry_run_enforced"] is True
    assert payload["api_call_made"] is False
    assert payload["composio_execute_allowed"] is False
    assert payload["docs_reference"] == COMPOSIO_EXECUTE_ACTION_DOCS_URL
    assert payload["sdk_docs_reference"] == COMPOSIO_PYTHON_SDK_DOCS_URL
    assert all(plan["would_execute"] is False for plan in payload["action_plans"])


def test_composio_dry_run_diff_builds_permission_envelope_without_execution() -> None:
    packet = build_scenario_packet("support_triage_agent")
    payload = build_composio_dry_run_diff(
        packet,
        scenario_name="support_triage_agent",
        dry_run_enabled=True,
    )

    assert payload["dry_run_diff_schema_version"] == COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION
    assert payload["status"] == "dry_run_permission_diff_built"
    assert payload["mode"] == "composio_dry_run_permission_diff"
    assert payload["dry_run_requested"] is True
    assert payload["dry_run_enforced"] is True
    assert payload["api_call_made"] is False
    assert payload["composio_execute_allowed"] is False
    assert payload["requires_api_key"] is False
    assert payload["live_mode_enabled"] is False
    assert payload["used_live_key"] is False
    assert payload["fallback_used"] is True
    assert payload["would_execute"] is False
    assert payload["can_approve_access"] is False
    assert payload["can_grant_permissions"] is False
    assert payload["can_mutate_external_state"] is False
    assert payload["blocked_from_approving_access"] is True
    assert payload["human_review_required"] is True
    assert payload["safety_impact"] == "none"
    assert "call Composio execute" in payload["proof_pack"]["cannot_do"]

    diffs = payload["permission_diffs"]
    assert {item["tool"] for item in diffs} == {"github", "slack", "jira"}
    assert payload["permission_diff_summary"] == {
        "tool_count": 3,
        "blocked_write_count": 9,
        "required_proof_count": 9,
        "write_like_action_count": 9,
        "highest_risk_level": "high",
        "toolkits": ["github", "slack", "jira"],
        "candidate_action_slugs": [
            "GITHUB_LIST_ISSUES",
            "SLACK_FETCH_CONVERSATION_HISTORY",
            "JIRA_CREATE_ISSUE",
        ],
        "execute_preview_count": 3,
        "dry_run_only": True,
        "api_call_made": False,
        "human_review_required": True,
    }
    for diff in diffs:
        assert diff["decision"] == "dry_run_only"
        assert diff["api_call_made"] is False
        assert diff["would_execute"] is False
        assert diff["can_approve_access"] is False
        assert diff["can_grant_permissions"] is False
        assert diff["can_mutate_external_state"] is False
        assert diff["human_review_required"] is True
        assert diff["permission_delta"]["production_permission_grant"] is False
        assert diff["permission_delta"]["external_write_enabled"] is False
        matrix = diff["permission_review_matrix"]
        assert matrix["tool"] == diff["tool"]
        assert matrix["risk_level"] == "high"
        assert matrix["write_like_action_count"] == len(diff["blocked_actions"])
        assert matrix["required_proof_count"] == len(diff["required_scopes_or_proof"])
        assert matrix["dry_run_only"] is True
        assert matrix["api_call_made"] is False
        assert matrix["can_execute"] is False
        preview = diff["execute_action_preview"]
        assert preview["docs_reference"] == COMPOSIO_EXECUTE_ACTION_DOCS_URL
        assert preview["would_call_composio"] is False
        assert preview["dry_run_only"] is True
        assert preview["request_body_preview"]["input"]["packet_id"] == packet["packet_id"]
