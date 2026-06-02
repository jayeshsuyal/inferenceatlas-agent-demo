"""
Renderers for public DecisionPacket artifacts.

The packet object should stay structured. Renderers turn it into judge-friendly
Markdown and terminal output without changing the underlying safety state.
"""

from __future__ import annotations

from typing import Any


def _bullet(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _capability_lines(capabilities: list[dict[str, Any]]) -> str:
    lines = []
    for item in capabilities:
        lines.append(
            "- {system}: {requested_access} ({risk_level}, {default_demo_state})".format(
                system=item.get("system", "Unknown"),
                requested_access=item.get("requested_access", "unspecified"),
                risk_level=item.get("risk_level", "unknown risk"),
                default_demo_state=item.get("default_demo_state", "unspecified state"),
            )
        )
    return "\n".join(lines) if lines else "- None"


def _tool_scope_lines(tool_scope: dict[str, dict[str, list[str]]]) -> str:
    lines = []
    for tool_name in sorted(tool_scope):
        scope = tool_scope[tool_name]
        read_scope = ", ".join(scope.get("read", [])) or "none"
        write_scope = ", ".join(scope.get("write", [])) or "none"
        blocked = ", ".join(scope.get("blocked_until_proven", [])) or "none"
        lines.append(f"- {tool_name}: read [{read_scope}] | write [{write_scope}] | blocked [{blocked}]")
    return "\n".join(lines) if lines else "- None"


def _key_value_lines(items: dict[str, Any]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {key.replace('_', ' ')}: {value}" for key, value in items.items())


def _tool_access_plan_lines(tool_access_plan: dict[str, dict[str, Any]]) -> str:
    lines = []
    for tool_name in sorted(tool_access_plan):
        plan = tool_access_plan[tool_name]
        blocked = ", ".join(plan.get("blocked_actions", [])) or "none"
        proof = ", ".join(plan.get("required_proof", [])) or "none"
        lines.extend(
            [
                f"- **{tool_name}**",
                f"  - requested: {plan.get('requested', 'unspecified')}",
                f"  - demo allowance: {plan.get('demo_allowance', 'unspecified')}",
                f"  - blocked actions: {blocked}",
                f"  - required proof: {proof}",
            ]
        )
    return "\n".join(lines) if lines else "- None"


def _dict_list_lines(items: list[dict[str, Any]], *, title_key: str, detail_keys: list[str]) -> str:
    lines = []
    for item in items:
        title = item.get(title_key, "Unnamed")
        details = []
        for key in detail_keys:
            value = item.get(key)
            if value:
                details.append(f"{key.replace('_', ' ')}: {value}")
        suffix = f": {'; '.join(details)}" if details else ""
        lines.append(f"- **{title}**{suffix}")
    return "\n".join(lines) if lines else "- None"


def render_packet_markdown(packet: dict[str, Any]) -> str:
    """Render the DecisionPacket as Markdown."""
    decision = packet["decision"]
    data_scope = packet["data_scope"]
    safety = packet["safety_state"]
    next_validation = packet["next_validation"]

    sections = [
        "# DecisionPacket: Support Triage Agent Access",
        "",
        "## Verdict",
        "",
        decision["verdict"],
        "",
        decision["review_posture"],
        "",
        "## Approval Posture",
        "",
        _key_value_lines(packet["approval_posture"]),
        "",
        "## Source Status",
        "",
        _key_value_lines(packet["source_status"]),
        "",
        "## Requested Capability",
        "",
        _capability_lines(packet["requested_capability"]),
        "",
        "## Tool Access Plan",
        "",
        _tool_access_plan_lines(packet["tool_access_plan"]),
        "",
        "## Tool Scope",
        "",
        _tool_scope_lines(packet["tool_scope"]),
        "",
        "## Data Scope",
        "",
        "May include:",
        "",
        _bullet(data_scope["may_include"]),
        "",
        "Must define before access:",
        "",
        _bullet(data_scope["must_define_before_access"]),
        "",
        "## Evidence Notes",
        "",
        _dict_list_lines(packet["evidence_notes"], title_key="source", detail_keys=["status", "note"]),
        "",
        "## Blocked Claims",
        "",
        _dict_list_lines(packet["blocked_claims"], title_key="claim", detail_keys=["reason"]),
        "",
        "## Missing Proof",
        "",
        _dict_list_lines(packet["missing_proof"], title_key="item", detail_keys=["owner", "unblocks"]),
        "",
        "## Reviewer Owners",
        "",
        _dict_list_lines(packet["reviewer_owners"], title_key="owner", detail_keys=["review_area", "current_state"]),
        "",
        "## Reviewer Action Items",
        "",
        _dict_list_lines(packet["reviewer_action_items"], title_key="owner", detail_keys=["action", "blocks"]),
        "",
        "## Next Human Validation",
        "",
        f"Action: {next_validation['action']}",
        "",
        f"Owner: {next_validation['owner']}",
        "",
        "Success criteria:",
        "",
        _bullet(next_validation["success_criteria"]),
        "",
        "## Safety State",
        "",
        f"- Approval granted: {safety['approval_granted']}",
        f"- External writes enabled: {safety['external_writes_enabled']}",
        f"- Composio dry-run: {safety['composio_dry_run']}",
        f"- Packet state mutation: {safety['packet_state_mutation']}",
        f"- Requires human approval: {safety['requires_human_approval']}",
        f"- Public demo posture: {safety['default_public_demo_posture']}",
        "",
        "## Raw Prompt",
        "",
        decision["raw_prompt"],
        "",
    ]
    return "\n".join(sections)


def render_trace_markdown(trace: list[dict[str, str]]) -> str:
    """Render the deterministic review trace as Markdown."""
    sections = ["# Decision Trace", ""]
    for index, item in enumerate(trace, start=1):
        sections.append(f"{index}. {item['step']}: {item['result']}")
    sections.append("")
    return "\n".join(sections)
