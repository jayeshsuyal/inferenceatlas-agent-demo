"""
Agent Access Decision Brief projection.

The DecisionPacket is the source of truth. This module derives a compact
reviewer-facing brief from that packet so a judge can inspect the access
decision without reading the whole packet or private v1 code.
"""

from __future__ import annotations

import json
from typing import Any


def _system_key(system: str) -> str:
    return system.strip().lower()


def _access_eligibility(packet: dict[str, Any]) -> list[dict[str, Any]]:
    tool_plan = packet["tool_access_plan"]
    eligibility = []
    for capability in packet["requested_capability"]:
        system = capability["system"]
        plan = tool_plan[_system_key(system)]
        eligibility.append(
            {
                "system": system,
                "requested_access": capability["requested_access"],
                "risk_level": capability["risk_level"],
                "eligibility": "candidate_for_scoped_validation_review",
                "validation_allowance": plan["demo_allowance"],
                "production_status": "blocked",
                "required_proof": plan["required_proof"],
            }
        )
    return eligibility


def _access_envelope(packet: dict[str, Any]) -> dict[str, list[str]]:
    tool_plan = packet["tool_access_plan"]
    return {
        "allowed_for_validation": [
            "GitHub read-scope review against an approved repository allowlist",
            "Slack named-channel summarization review after retention and customer-data scope are approved",
            "Jira draft ticket proposal review with no production ticket creation",
        ],
        "blocked_in_validation": [
            f"{tool_name}: {action}"
            for tool_name in sorted(tool_plan)
            for action in tool_plan[tool_name]["blocked_actions"]
        ],
        "blocked_before_production": [
            "production access grant",
            "external write actions",
            "workspace-wide Slack access",
            "customer-data safety or compliance claims without named reviewer evidence",
            "automated permission expansion without a new packet",
        ],
    }


def _risk_register() -> list[dict[str, str]]:
    return [
        {
            "risk": "excessive agency",
            "why_it_matters": "The agent is asking for multiple operational systems at once.",
            "mitigation": "Split read and write paths, keep validation scoped, and require a new packet before expansion.",
        },
        {
            "risk": "sensitive information exposure",
            "why_it_matters": "Slack incidents, support escalations, and bug reports may contain customer context.",
            "mitigation": "Require retention, logging, deletion, and channel/repository boundaries before access.",
        },
        {
            "risk": "prompt injection via tool content",
            "why_it_matters": "Issues, tickets, and incident messages can contain instructions that should not become policy.",
            "mitigation": "Treat tool content as evidence, not authority; preserve source status and reviewer gates.",
        },
        {
            "risk": "unauthorized write actions",
            "why_it_matters": "Jira, GitHub, or Slack mutations can affect customers, incidents, and engineering operations.",
            "mitigation": "Keep Composio dry-run by default and block write actions until rollback and off-switch proof exists.",
        },
        {
            "risk": "missing audit trail",
            "why_it_matters": "Reviewers need to know what evidence was used, what was blocked, and who approved scope changes.",
            "mitigation": "Require audit log shape for tool calls, evidence intake, reviewer decisions, and future packet updates.",
        },
    ]


def _reviewer_gates(packet: dict[str, Any]) -> list[dict[str, str]]:
    gates = []
    for item in packet["reviewer_action_items"]:
        gates.append(
            {
                "owner": item["owner"],
                "gate": item["action"],
                "blocks": item["blocks"],
                "required_before": "production_access" if item["owner"] != "Procurement/Finance" else "paid_rollout",
            }
        )
    return gates


def build_agent_access_decision_brief(packet: dict[str, Any]) -> dict[str, Any]:
    """Derive the public reviewer brief from a DecisionPacket."""
    safety = packet["safety_state"]
    next_validation = packet["next_validation"]
    return {
        "schema_version": "agent_access_decision_brief.v0",
        "brief_id": "ia-agent-access-brief-support-triage-v0",
        "generated_by": "inferenceatlas-agent-demo",
        "mode": packet["mode"],
        "derived_from_packet_id": packet["packet_id"],
        "decision": {
            "question": packet["decision"]["question"],
            "verdict": "Do not grant production access.",
            "recommended_next_step": "Approve a scoped validation review only.",
            "reason": "The request touches sensitive support, engineering, and incident systems without named reviewer proof.",
        },
        "go_no_go": {
            "production_access": False,
            "scoped_validation_review": True,
            "external_writes": False,
            "composio_dry_run": safety["composio_dry_run"],
            "next_validation": next_validation["action"],
        },
        "access_eligibility": _access_eligibility(packet),
        "access_envelope": _access_envelope(packet),
        "risk_register": _risk_register(),
        "reviewer_gates": _reviewer_gates(packet),
        "runtime_permission_boundary": {
            "runtime_permission_prompt_answers": "Can the agent perform this specific action now?",
            "inferenceatlas_decision_brief_answers": "Should this agent be eligible for this class of access at all, and what proof is required first?",
            "why_this_is_different": "Runtime prompts are last-mile execution checks. The Decision Brief is the pre-permission governance review that decides eligibility, missing proof, and reviewer gates before runtime tools are granted.",
        },
        "sponsor_readiness": {
            "nebius": "Optional live narration layer for reviewer-ready packet language; offline truth remains deterministic.",
            "tavily": "Optional live evidence notes with source URLs and freshness status; search results do not auto-approve access.",
            "composio": "Scoped GitHub/Slack/Jira tool planning remains dry-run by default.",
            "openclaw": "Optional live runtime trace should preserve the same blocked-access contract.",
        },
        "safety_state": {
            "approval_granted": safety["approval_granted"],
            "external_writes_enabled": safety["external_writes_enabled"],
            "composio_dry_run": safety["composio_dry_run"],
            "packet_state_mutation": safety["packet_state_mutation"],
            "requires_human_approval": safety["requires_human_approval"],
            "default_public_demo_posture": safety["default_public_demo_posture"],
        },
    }


def brief_to_pretty_json(brief: dict[str, Any]) -> str:
    """Render a brief as stable, human-readable JSON."""
    return json.dumps(brief, indent=2, sort_keys=True)
