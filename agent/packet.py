"""
Deterministic DecisionPacket core for the public judge harness.

This module is intentionally offline-first: it builds the review packet that
judges should be able to inspect without API keys, network access, or live tool
permissions. Live Nebius/Tavily/Composio/OpenClaw paths can enrich this packet
later, but they should preserve the same safety posture.
"""

from __future__ import annotations

import json
from typing import Any

from .access_request import AccessRequest, ToolRequest
from .rules import RuleEffect, evaluate_rules


DEFAULT_AGENT_ACCESS_PROMPT = (
    "Should this support triage agent get GitHub, Slack, and Jira access? "
    "It will read GitHub issues, summarize Slack incident channels, and create "
    "Jira draft tickets. It may touch customer incident context, engineering "
    "bug reports, and support escalations."
)

SUPPORT_TRIAGE_REQUEST = AccessRequest(
    agent_name="support triage agent",
    purpose="Read GitHub issues, summarize Slack incident channels, and create Jira draft tickets.",
    environment="prod",
    requested_tools=(
        ToolRequest(
            system="GitHub",
            requested_actions=("read issues for bug reports and incident context",),
            scopes=("issues", "labels", "linked incident references"),
        ),
        ToolRequest(
            system="Slack",
            requested_actions=("summarize incident channels",),
            scopes=("named incident channels only",),
        ),
        ToolRequest(
            system="Jira",
            requested_actions=("create draft tickets",),
            scopes=("named project metadata", "draft ticket proposal only"),
        ),
    ),
    data_classes=(
        "customer_incident_context",
        "engineering_bug_reports",
        "support_escalation_notes",
        "internal_incident_channel_summaries",
    ),
    raw_prompt=DEFAULT_AGENT_ACCESS_PROMPT,
)


def _packet_id(request: AccessRequest) -> str:
    agent_slug = request.agent_name.lower().replace(" agent", "").replace(" ", "-")
    return f"ia-agent-access-{agent_slug}-v0"


def _effects_by_target(effects: list[RuleEffect]) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for effect in effects:
        sections[effect.target] = effect.value
    return sections


def _section(sections: dict[str, Any], name: str) -> Any:
    if name not in sections:
        raise KeyError(f"missing packet section from rules: {name}")
    return sections[name]


def build_decision_packet(
    request: AccessRequest,
    *,
    mode: str = "offline_deterministic",
) -> dict[str, Any]:
    """Build a deterministic DecisionPacket from a structured access request."""
    sections = _effects_by_target(evaluate_rules(request))
    return {
        "schema_version": "decision_packet.v0",
        "packet_id": _packet_id(request),
        "generated_by": "inferenceatlas-agent-demo",
        "mode": mode,
        "decision": _section(sections, "decision"),
        "source_status": _section(sections, "source_status"),
        "approval_posture": _section(sections, "approval_posture"),
        "requested_capability": _section(sections, "requested_capability"),
        "tool_scope": _section(sections, "tool_scope"),
        "tool_access_plan": _section(sections, "tool_access_plan"),
        "data_scope": _section(sections, "data_scope"),
        "evidence_notes": _section(sections, "evidence_notes"),
        "blocked_claims": _section(sections, "blocked_claims"),
        "missing_proof": _section(sections, "missing_proof"),
        "reviewer_owners": _section(sections, "reviewer_owners"),
        "reviewer_action_items": _section(sections, "reviewer_action_items"),
        "next_validation": _section(sections, "next_validation"),
        "safety_state": _section(sections, "safety_state"),
    }


def support_triage_request(prompt: str = DEFAULT_AGENT_ACCESS_PROMPT) -> AccessRequest:
    """Return the canonical support-triage request fixture."""
    if prompt == SUPPORT_TRIAGE_REQUEST.raw_prompt:
        return SUPPORT_TRIAGE_REQUEST
    return AccessRequest(
        agent_name=SUPPORT_TRIAGE_REQUEST.agent_name,
        purpose=SUPPORT_TRIAGE_REQUEST.purpose,
        environment=SUPPORT_TRIAGE_REQUEST.environment,
        requested_tools=SUPPORT_TRIAGE_REQUEST.requested_tools,
        data_classes=SUPPORT_TRIAGE_REQUEST.data_classes,
        raw_prompt=prompt,
    )


def build_support_triage_decision_packet(
    prompt: str = DEFAULT_AGENT_ACCESS_PROMPT,
    *,
    mode: str = "offline_deterministic",
) -> dict[str, Any]:
    """Build the canonical offline packet for the hackathon demo scenario."""
    return build_decision_packet(support_triage_request(prompt), mode=mode)


def build_support_triage_trace() -> list[dict[str, str]]:
    """Return a deterministic review trace for the same scenario."""
    return [
        {
            "step": "intake",
            "result": "Agent request asks for GitHub, Slack, and Jira access.",
        },
        {
            "step": "scope_split",
            "result": "Read paths and write paths are separated before any approval posture is set.",
        },
        {
            "step": "tool_access_plan",
            "result": "GitHub, Slack, and Jira get scoped dry-run allowances plus blocked write actions.",
        },
        {
            "step": "data_scope",
            "result": "Customer incident context and support escalations are treated as sensitive until policy proof exists.",
        },
        {
            "step": "safety_gate",
            "result": "Production access, compliance readiness, and write-action claims remain blocked.",
        },
        {
            "step": "reviewer_routing",
            "result": "Security/Legal, Engineering, Support Ops, and conditional Finance owners are named.",
        },
        {
            "step": "reviewer_action_items",
            "result": "Each reviewer owner receives the proof task that blocks access from moving forward.",
        },
        {
            "step": "next_validation",
            "result": "A scoped dry-run pilot review is the next step, not production access.",
        },
    ]


def packet_to_pretty_json(packet: dict[str, Any]) -> str:
    """Render a packet as stable, human-readable JSON."""
    return json.dumps(packet, indent=2, sort_keys=True)


def main() -> None:
    """Small inspection entry point: `python3 -m agent.packet`."""
    packet = build_support_triage_decision_packet()
    print(packet_to_pretty_json(packet))


if __name__ == "__main__":
    main()
