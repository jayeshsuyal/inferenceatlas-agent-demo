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


DEFAULT_AGENT_ACCESS_PROMPT = (
    "Should this support triage agent get GitHub, Slack, and Jira access? "
    "It will read GitHub issues, summarize Slack incident channels, and create "
    "Jira draft tickets. It may touch customer incident context, engineering "
    "bug reports, and support escalations."
)


def build_support_triage_decision_packet(
    prompt: str = DEFAULT_AGENT_ACCESS_PROMPT,
    *,
    mode: str = "offline_deterministic",
) -> dict[str, Any]:
    """Build the canonical offline packet for the hackathon demo scenario."""
    return {
        "schema_version": "decision_packet.v0",
        "packet_id": "ia-agent-access-support-triage-v0",
        "generated_by": "inferenceatlas-agent-demo",
        "mode": mode,
        "decision": {
            "question": "Should the support triage agent get GitHub, Slack, and Jira access?",
            "verdict": "Do not approve production tool access yet.",
            "review_posture": "Approve a scoped validation review before any production permission grant.",
            "raw_prompt": prompt,
        },
        "source_status": {
            "user_prompt": "provided",
            "live_vendor_evidence": "not_fetched_in_offline_mode",
            "workspace_policy": "missing",
            "tool_auth_state": "not_connected_in_offline_mode",
            "reviewer_confirmation": "missing",
            "deterministic_packet": "generated",
        },
        "approval_posture": {
            "production_access": "blocked",
            "validation_review": "allowed",
            "read_access": "candidate_after_scope_review",
            "write_access": "blocked_until_rollback_and_off_switch_proof",
            "compliance_claims": "blocked_until_named_reviewer_evidence",
        },
        "requested_capability": [
            {
                "system": "GitHub",
                "requested_access": "read issues for bug reports and incident context",
                "risk_level": "medium",
                "default_demo_state": "dry_run_only",
            },
            {
                "system": "Slack",
                "requested_access": "summarize incident channels",
                "risk_level": "high",
                "default_demo_state": "dry_run_only",
            },
            {
                "system": "Jira",
                "requested_access": "create draft tickets",
                "risk_level": "high",
                "default_demo_state": "dry_run_only",
            },
        ],
        "tool_scope": {
            "github": {
                "read": ["issues", "labels", "linked incident references"],
                "write": [],
                "blocked_until_proven": ["issue mutation", "repo configuration changes"],
            },
            "slack": {
                "read": ["named incident channels only"],
                "write": [],
                "blocked_until_proven": ["posting messages", "DM access", "workspace-wide history"],
            },
            "jira": {
                "read": ["named project metadata"],
                "write": ["draft ticket proposal only"],
                "blocked_until_proven": ["ticket creation in production", "status changes", "assignment changes"],
            },
        },
        "tool_access_plan": {
            "github": {
                "requested": "read issues for bug reports and incident context",
                "demo_allowance": "dry-run read-scope plan only",
                "blocked_actions": ["issue edits", "repo configuration changes", "workflow dispatch"],
                "required_proof": ["repository allowlist", "permission level", "audit log owner"],
            },
            "slack": {
                "requested": "summarize incident channels",
                "demo_allowance": "dry-run named-channel summary plan only",
                "blocked_actions": ["posting messages", "DM access", "workspace-wide history"],
                "required_proof": ["channel allowlist", "retention terms", "customer-data boundary"],
            },
            "jira": {
                "requested": "create draft tickets",
                "demo_allowance": "draft ticket proposal only; no production creation",
                "blocked_actions": ["ticket creation", "status changes", "assignment changes"],
                "required_proof": ["project scope", "draft-only mode", "rollback/off-switch plan"],
            },
        },
        "data_scope": {
            "may_include": [
                "customer incident context",
                "engineering bug reports",
                "support escalation notes",
                "internal incident channel summaries",
            ],
            "must_define_before_access": [
                "retention period",
                "logging policy",
                "allowed channel and repository list",
                "customer data handling boundary",
                "reviewer-owned deletion and rollback process",
            ],
        },
        "evidence_notes": [
            {
                "source": "offline harness",
                "status": "deterministic",
                "note": "No live vendor, policy, or workspace evidence was fetched in offline mode.",
            },
            {
                "source": "safety contract",
                "status": "enforced_by_default",
                "note": "The public demo path prepares review packets and does not grant access.",
            },
        ],
        "blocked_claims": [
            {
                "claim": "Production tool access is approved.",
                "reason": "No named Security/Legal reviewer and no tool scope proof.",
            },
            {
                "claim": "Customer-data handling is safe.",
                "reason": "Retention, logging, deletion, and channel/repository boundaries are not proven.",
            },
            {
                "claim": "The agent may create or mutate Jira/GitHub/Slack state.",
                "reason": "Write actions require rollback/off-switch proof and explicit human approval.",
            },
            {
                "claim": "The workflow is compliance-ready.",
                "reason": "Compliance approval cannot be inferred from an agent request or demo transcript.",
            },
        ],
        "missing_proof": [
            {
                "item": "GitHub repository allowlist and permission level",
                "owner": "Engineering",
                "unblocks": "read-only repository evidence review",
            },
            {
                "item": "Slack channel allowlist, retention policy, and customer-data boundary",
                "owner": "Security/Legal",
                "unblocks": "incident-channel summarization review",
            },
            {
                "item": "Jira project scope, draft-only mode, and rollback/off-switch plan",
                "owner": "Engineering",
                "unblocks": "draft ticket validation",
            },
            {
                "item": "Support escalation workflow and human handoff owner",
                "owner": "Support Ops",
                "unblocks": "triage workflow fit review",
            },
            {
                "item": "Audit log shape for tool calls, evidence intake, and reviewer decisions",
                "owner": "Security/Engineering",
                "unblocks": "reviewable pilot packet",
            },
        ],
        "reviewer_owners": [
            {
                "owner": "Security/Legal",
                "review_area": "customer-data exposure, retention, logging, policy boundary",
                "current_state": "required_before_access",
            },
            {
                "owner": "Engineering",
                "review_area": "permission boundaries, rollback, off-switch, audit logs",
                "current_state": "required_before_write_actions",
            },
            {
                "owner": "Support Ops",
                "review_area": "workflow fit, escalation rules, human handoff",
                "current_state": "required_before_pilot",
            },
            {
                "owner": "Procurement/Finance",
                "review_area": "paid tool/vendor spend if live actions or seats are enabled",
                "current_state": "conditional",
            },
        ],
        "reviewer_action_items": [
            {
                "owner": "Security/Legal",
                "action": "Confirm allowed data scope, retention, and logging terms",
                "blocks": "Slack channel summarization and customer incident context access",
            },
            {
                "owner": "Engineering",
                "action": "Provide repository/project allowlists, permission boundaries, audit logs, and off-switch proof",
                "blocks": "GitHub/Jira tool connection and any write-action pilot",
            },
            {
                "owner": "Support Ops",
                "action": "Validate triage workflow fit, escalation rules, and human handoff owner",
                "blocks": "support operations pilot",
            },
            {
                "owner": "Procurement/Finance",
                "action": "Review paid seats or vendor spend only if live integrations move beyond dry-run",
                "blocks": "paid production rollout",
            },
        ],
        "next_validation": {
            "action": "Run a scoped dry-run pilot review with named repositories, channels, and Jira project.",
            "owner": "Security/Legal + Engineering",
            "success_criteria": [
                "approved data and tool scope",
                "audit log reviewed",
                "write actions remain draft-only",
                "rollback/off-switch owner named",
            ],
        },
        "safety_state": {
            "approval_granted": False,
            "external_writes_enabled": False,
            "composio_dry_run": True,
            "packet_state_mutation": False,
            "requires_human_approval": True,
            "default_public_demo_posture": "review_packet_only",
        },
    }


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
