"""Packet-derived blast radius for sponsor proof runs.

The blast radius object is observational. It classifies requested tool scope so
Composio and OpenClaw can show what would be blocked before execution without
granting access, executing tools, or changing packet authority.
"""

from __future__ import annotations

from typing import Any


BLAST_RADIUS_SCHEMA_VERSION = "blast_radius.v0"

WRITE_LIKE_KEYWORDS = (
    "edit",
    "edits",
    "create",
    "creation",
    "posting",
    "post",
    "status change",
    "status changes",
    "assignment",
    "dispatch",
)
ADMIN_LIKE_KEYWORDS = (
    "configuration",
    "workflow dispatch",
    "workspace-wide",
    "dm access",
    "permission",
    "admin",
)
SENSITIVE_READ_KEYWORDS = (
    "customer",
    "history",
    "incident",
    "dm access",
    "workspace-wide",
)


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in keywords)


def classify_action(action: str) -> str:
    """Classify one requested/blocked action for review routing."""
    if _contains_any(action, ADMIN_LIKE_KEYWORDS):
        return "admin_like"
    if _contains_any(action, WRITE_LIKE_KEYWORDS):
        return "write_like"
    if _contains_any(action, SENSITIVE_READ_KEYWORDS):
        return "sensitive_read"
    return "read_like"


def risk_level_for_action(action_class: str) -> str:
    return {
        "admin_like": "critical",
        "write_like": "high",
        "sensitive_read": "medium",
        "read_like": "low",
    }[action_class]


def _blocked_reason(action_class: str) -> str:
    return {
        "admin_like": "Admin or workspace-wide scope cannot move without named owner approval and rollback/off-switch proof.",
        "write_like": "Write-like scope cannot move while external writes and permission grants remain blocked.",
        "sensitive_read": "Sensitive read scope needs data-boundary, retention, and reviewer-owner proof before access expands.",
        "read_like": "Read scope still needs the packet's required proof before validation expands.",
    }[action_class]


def build_tool_blast_radius(tool_name: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Build blast-radius classification for one tool plan."""
    blocked_actions = []
    for action in plan["blocked_actions"]:
        action_class = classify_action(action)
        blocked_actions.append(
            {
                "action": action,
                "action_class": action_class,
                "risk_level": risk_level_for_action(action_class),
                "policy_decision": "blocked_before_execution",
                "blocked_reason": _blocked_reason(action_class),
                "would_execute": False,
                "can_approve_access": False,
                "can_grant_permissions": False,
                "can_mutate_external_state": False,
                "human_review_required": True,
            }
        )

    write_like_count = sum(item["action_class"] == "write_like" for item in blocked_actions)
    admin_like_count = sum(item["action_class"] == "admin_like" for item in blocked_actions)
    sensitive_read_count = sum(item["action_class"] == "sensitive_read" for item in blocked_actions)
    high_or_critical_count = sum(item["risk_level"] in {"high", "critical"} for item in blocked_actions)
    blast_radius_class = (
        "admin_or_workspace_scope"
        if admin_like_count
        else "write_scope"
        if write_like_count
        else "sensitive_read_scope"
        if sensitive_read_count
        else "read_scope"
    )

    return {
        "schema_version": BLAST_RADIUS_SCHEMA_VERSION,
        "tool": tool_name,
        "requested_scope": plan["requested"],
        "validation_scope": plan["demo_allowance"],
        "blast_radius_class": blast_radius_class,
        "blocked_actions": blocked_actions,
        "required_proof": list(plan["required_proof"]),
        "summary": {
            "blocked_action_count": len(blocked_actions),
            "write_like_action_count": write_like_count,
            "admin_like_action_count": admin_like_count,
            "sensitive_read_action_count": sensitive_read_count,
            "high_or_critical_action_count": high_or_critical_count,
            "all_blocked_before_execution": True,
            "all_write_or_admin_blocked": True,
            "would_execute": False,
            "human_review_required": True,
        },
        "safety_boundary": {
            "read_only": True,
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_external_state": False,
            "requires_human_review": True,
        },
    }


def build_packet_blast_radius(packet: dict[str, Any], *, scenario_name: str) -> dict[str, Any]:
    """Build one packet-level blast-radius object from tool access plans."""
    tool_radii = [
        build_tool_blast_radius(tool_name, plan)
        for tool_name, plan in packet["tool_access_plan"].items()
    ]
    blocked_action_count = sum(item["summary"]["blocked_action_count"] for item in tool_radii)
    write_like_count = sum(item["summary"]["write_like_action_count"] for item in tool_radii)
    admin_like_count = sum(item["summary"]["admin_like_action_count"] for item in tool_radii)
    high_or_critical_count = sum(item["summary"]["high_or_critical_action_count"] for item in tool_radii)
    max_risk_level = (
        "critical"
        if any(event["risk_level"] == "critical" for item in tool_radii for event in item["blocked_actions"])
        else "high"
        if any(event["risk_level"] == "high" for item in tool_radii for event in item["blocked_actions"])
        else "medium"
        if any(event["risk_level"] == "medium" for item in tool_radii for event in item["blocked_actions"])
        else "low"
    )
    return {
        "schema_version": BLAST_RADIUS_SCHEMA_VERSION,
        "packet_id": packet["packet_id"],
        "scenario_name": scenario_name,
        "tool_count": len(tool_radii),
        "tools": tool_radii,
        "summary": {
            "blocked_action_count": blocked_action_count,
            "write_like_action_count": write_like_count,
            "admin_like_action_count": admin_like_count,
            "high_or_critical_action_count": high_or_critical_count,
            "max_risk_level": max_risk_level,
            "all_blocked_before_execution": True,
            "all_write_or_admin_blocked": True,
            "would_execute": False,
            "can_approve_access": False,
            "can_grant_permissions": False,
            "can_mutate_external_state": False,
            "human_review_required": True,
        },
        "downstream_use": {
            "composio": "permission diff explains blocked tool actions before execute",
            "openclaw": "runtime trace records attempted vs blocked movement",
        },
    }
