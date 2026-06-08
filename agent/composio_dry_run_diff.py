"""Composio dry-run permission diff for sponsor proof runs.

The diff translates an IA Packet tool access plan into a Composio-shaped
pre-execution permission envelope. It never calls Composio, grants scopes,
executes tools, writes externally, or changes packet authority.
"""

from __future__ import annotations

from typing import Any

from .adapters import build_adapter_result


COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION = "composio_dry_run_diff.v0"
COMPOSIO_EXECUTE_ACTION_DOCS_URL = "https://docs.composio.dev/docs/tools-direct/executing-tools"
COMPOSIO_PYTHON_SDK_DOCS_URL = "https://docs.composio.dev/reference/sdk-reference/python"

_ACTION_INTENTS = {
    "github": {
        "toolkit": "github",
        "candidate_action_intent": "read issues only",
        "candidate_action_slug": "GITHUB_LIST_ISSUES",
    },
    "slack": {
        "toolkit": "slack",
        "candidate_action_intent": "read named channel history only",
        "candidate_action_slug": "SLACK_FETCH_CONVERSATION_HISTORY",
    },
    "jira": {
        "toolkit": "jira",
        "candidate_action_intent": "draft issue proposal only",
        "candidate_action_slug": "JIRA_CREATE_ISSUE",
    },
}


def _intent_for_tool(tool_name: str) -> dict[str, str]:
    return _ACTION_INTENTS.get(
        tool_name,
        {
            "toolkit": tool_name,
            "candidate_action_intent": "validation-only tool review",
            "candidate_action_slug": f"{tool_name.upper()}_VALIDATION_ONLY",
        },
    )


def _permission_diff(tool_name: str, plan: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    intent = _intent_for_tool(tool_name)
    blocked_actions = list(plan["blocked_actions"])
    required_proof = list(plan["required_proof"])
    return {
        "tool": tool_name,
        "toolkit": intent["toolkit"],
        "candidate_action_slug": intent["candidate_action_slug"],
        "candidate_action_intent": intent["candidate_action_intent"],
        "requested": plan["requested"],
        "demo_allowance": plan["demo_allowance"],
        "allowed_for_validation": [plan["demo_allowance"]],
        "blocked_actions": blocked_actions,
        "required_scopes_or_proof": required_proof,
        "permission_delta": {
            "requested_scope": plan["requested"],
            "validation_scope": plan["demo_allowance"],
            "blocked_write_count": len(blocked_actions),
            "required_proof_count": len(required_proof),
            "production_permission_grant": False,
            "external_write_enabled": False,
        },
        "execute_action_preview": {
            "docs_reference": COMPOSIO_EXECUTE_ACTION_DOCS_URL,
            "method": "POST",
            "endpoint_shape": "/api/v2/actions/:actionId/execute",
            "would_call_composio": False,
            "dry_run_only": True,
            "request_body_preview": {
                "actionId": intent["candidate_action_slug"],
                "input": {
                    "packet_id": packet["packet_id"],
                    "requested": plan["requested"],
                    "validation_scope": plan["demo_allowance"],
                    "blocked_actions": blocked_actions,
                    "required_proof": required_proof,
                },
                "customDescription": "IA dry-run permission diff; no Composio action is executed.",
            },
        },
        "decision": "dry_run_only",
        "api_call_made": False,
        "would_execute": False,
        "can_approve_access": False,
        "can_grant_permissions": False,
        "can_mutate_external_state": False,
        "human_review_required": True,
    }


def build_composio_dry_run_diff(
    packet: dict[str, Any],
    *,
    scenario_name: str,
    dry_run_enabled: bool = False,
) -> dict[str, Any]:
    """Build a Composio dry-run diff, with the existing adapter as fallback."""
    fallback = build_adapter_result("composio", scenario_name)
    if not dry_run_enabled:
        fallback.update(
            {
                "dry_run_diff_schema_version": COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION,
                "dry_run_requested": False,
                "dry_run_enforced": True,
                "api_call_made": False,
                "composio_execute_allowed": False,
                "docs_reference": COMPOSIO_EXECUTE_ACTION_DOCS_URL,
                "sdk_docs_reference": COMPOSIO_PYTHON_SDK_DOCS_URL,
            }
        )
        return fallback

    diffs = [
        _permission_diff(tool_name, plan, packet)
        for tool_name, plan in packet["tool_access_plan"].items()
    ]
    blocked_write_count = sum(len(item["blocked_actions"]) for item in diffs)
    required_proof_count = sum(len(item["required_scopes_or_proof"]) for item in diffs)
    payload = {
        **fallback,
        "dry_run_diff_schema_version": COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION,
        "status": "dry_run_permission_diff_built",
        "mode": "composio_dry_run_permission_diff",
        "dry_run_requested": True,
        "dry_run_enforced": True,
        "api_call_made": False,
        "composio_execute_allowed": False,
        "requires_api_key": False,
        "live_mode_enabled": False,
        "used_live_key": False,
        "fallback_used": True,
        "fallback_reason": "local_dry_run_contract",
        "permission_diffs": diffs,
        "permission_diff_summary": {
            "tool_count": len(diffs),
            "blocked_write_count": blocked_write_count,
            "required_proof_count": required_proof_count,
            "dry_run_only": True,
            "api_call_made": False,
            "human_review_required": True,
        },
        "action_plans": diffs,
        "proof_pack": {
            **fallback["proof_pack"],
            "proof_type": "composio_permission_diff",
            "visible_output": "tool-by-tool Composio execute-action preview with blocked writes and required proof",
            "cannot_do": [
                "approve access",
                "grant permissions",
                "execute writes",
                "call Composio execute",
                "reduce proof debt automatically",
                "mutate external systems",
            ],
        },
        "docs_reference": COMPOSIO_EXECUTE_ACTION_DOCS_URL,
        "sdk_docs_reference": COMPOSIO_PYTHON_SDK_DOCS_URL,
        "safety_impact": "none",
    }
    return payload
