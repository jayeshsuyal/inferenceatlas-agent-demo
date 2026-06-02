"""Pure rules for deriving DecisionPacket sections from an AccessRequest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .access_request import AccessRequest


@dataclass(frozen=True)
class RuleEffect:
    """One deterministic rule output used to assemble a DecisionPacket."""

    rule_id: str
    target: str
    value: Any
    reason: str = ""


Rule = Callable[[AccessRequest], list[RuleEffect]]


_TOOL_RISK_LEVEL = {
    "github": "medium",
    "slack": "high",
    "jira": "high",
}

_TOOL_SCOPE = {
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
}

_TOOL_ACCESS_PLAN = {
    "github": {
        "demo_allowance": "dry-run read-scope plan only",
        "blocked_actions": ["issue edits", "repo configuration changes", "workflow dispatch"],
        "required_proof": ["repository allowlist", "permission level", "audit log owner"],
    },
    "slack": {
        "demo_allowance": "dry-run named-channel summary plan only",
        "blocked_actions": ["posting messages", "DM access", "workspace-wide history"],
        "required_proof": ["channel allowlist", "retention terms", "customer-data boundary"],
    },
    "jira": {
        "demo_allowance": "draft ticket proposal only; no production creation",
        "blocked_actions": ["ticket creation", "status changes", "assignment changes"],
        "required_proof": ["project scope", "draft-only mode", "rollback/off-switch plan"],
    },
}

_DATA_CLASS_LABELS = {
    "customer_incident_context": "customer incident context",
    "engineering_bug_reports": "engineering bug reports",
    "support_escalation_notes": "support escalation notes",
    "internal_incident_channel_summaries": "internal incident channel summaries",
}

_MISSING_PROOF_BY_TOOL = {
    "github": {
        "item": "GitHub repository allowlist and permission level",
        "owner": "Engineering",
        "unblocks": "read-only repository evidence review",
    },
    "slack": {
        "item": "Slack channel allowlist, retention policy, and customer-data boundary",
        "owner": "Security/Legal",
        "unblocks": "incident-channel summarization review",
    },
    "jira": {
        "item": "Jira project scope, draft-only mode, and rollback/off-switch plan",
        "owner": "Engineering",
        "unblocks": "draft ticket validation",
    },
}


def _tool_key(system: str) -> str:
    return system.strip().lower()


def _tool_list(request: AccessRequest) -> str:
    systems = [tool.system for tool in request.requested_tools]
    if len(systems) == 1:
        return systems[0]
    if len(systems) == 2:
        return " and ".join(systems)
    return ", ".join(systems[:-1]) + f", and {systems[-1]}"


def decision_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="agent_access_request_sets_review_question",
            target="decision",
            value={
                "question": f"Should the {request.agent_name} get {_tool_list(request)} access?",
                "verdict": "Do not approve production tool access yet.",
                "review_posture": "Approve a scoped validation review before any production permission grant.",
                "raw_prompt": request.raw_prompt,
            },
            reason="The packet preserves the original access question and keeps production access blocked.",
        )
    ]


def source_status_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="offline_mode_marks_unfetched_sources",
            target="source_status",
            value={
                "user_prompt": "provided",
                "live_vendor_evidence": "not_fetched_in_offline_mode",
                "workspace_policy": "missing",
                "tool_auth_state": "not_connected_in_offline_mode",
                "reviewer_confirmation": "missing",
                "deterministic_packet": "generated",
            },
            reason="Offline mode cannot claim live vendor evidence, tool auth, policy, or reviewer confirmation.",
        )
    ]


def approval_posture_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="production_access_requires_named_review",
            target="approval_posture",
            value={
                "production_access": "blocked",
                "validation_review": "allowed",
                "read_access": "candidate_after_scope_review",
                "write_access": "blocked_until_rollback_and_off_switch_proof",
                "compliance_claims": "blocked_until_named_reviewer_evidence",
            },
            reason="Production and write access stay blocked until scope, proof, rollback, and reviewers are named.",
        )
    ]


def requested_capability_rule(request: AccessRequest) -> list[RuleEffect]:
    capabilities = []
    for tool in request.requested_tools:
        tool_key = _tool_key(tool.system)
        capabilities.append(
            {
                "system": tool.system,
                "requested_access": "; ".join(tool.requested_actions),
                "risk_level": _TOOL_RISK_LEVEL[tool_key],
                "default_demo_state": "dry_run_only",
            }
        )
    return [
        RuleEffect(
            rule_id="requested_tools_become_capability_rows",
            target="requested_capability",
            value=capabilities,
            reason="Each requested system is represented with risk and dry-run posture.",
        )
    ]


def tool_scope_rule(request: AccessRequest) -> list[RuleEffect]:
    scope = {}
    for tool in request.requested_tools:
        tool_key = _tool_key(tool.system)
        scope[tool_key] = _TOOL_SCOPE[tool_key]
    return [
        RuleEffect(
            rule_id="split_read_write_and_blocked_tool_scope",
            target="tool_scope",
            value=scope,
            reason="Read, write, and blocked tool paths are separated before approval posture is interpreted.",
        )
    ]


def tool_access_plan_rule(request: AccessRequest) -> list[RuleEffect]:
    plan = {}
    for tool in request.requested_tools:
        tool_key = _tool_key(tool.system)
        base_plan = _TOOL_ACCESS_PLAN[tool_key]
        plan[tool_key] = {
            "requested": "; ".join(tool.requested_actions),
            "demo_allowance": base_plan["demo_allowance"],
            "blocked_actions": base_plan["blocked_actions"],
            "required_proof": base_plan["required_proof"],
        }
    return [
        RuleEffect(
            rule_id="tool_access_plan_keeps_writes_dry_run",
            target="tool_access_plan",
            value=plan,
            reason="Composio-facing tool plans stay scoped and dry-run by default.",
        )
    ]


def data_scope_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="sensitive_data_requires_policy_boundaries",
            target="data_scope",
            value={
                "may_include": [_DATA_CLASS_LABELS[item] for item in request.data_classes],
                "must_define_before_access": [
                    "retention period",
                    "logging policy",
                    "allowed channel and repository list",
                    "customer data handling boundary",
                    "reviewer-owned deletion and rollback process",
                ],
            },
            reason="Sensitive data classes require retention, logging, channel, repository, and rollback boundaries.",
        )
    ]


def evidence_notes_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="offline_evidence_notes_stay_deterministic",
            target="evidence_notes",
            value=[
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
            reason="Offline evidence can document missing sources but cannot invent live proof.",
        )
    ]


def blocked_claims_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="unsupported_access_and_compliance_claims_stay_blocked",
            target="blocked_claims",
            value=[
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
            reason="Claims that lack reviewer evidence remain visible as blocked claims.",
        )
    ]


def missing_proof_rule(request: AccessRequest) -> list[RuleEffect]:
    missing_proof = []
    for tool in request.requested_tools:
        missing_proof.append(_MISSING_PROOF_BY_TOOL[_tool_key(tool.system)])
    missing_proof.extend(
        [
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
        ]
    )
    return [
        RuleEffect(
            rule_id="required_proof_is_routed_to_owners",
            target="missing_proof",
            value=missing_proof,
            reason="Each requested system creates proof debt before access can move forward.",
        )
    ]


def reviewer_owners_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="sensitive_agent_access_names_reviewer_owners",
            target="reviewer_owners",
            value=[
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
            reason="Reviewer ownership is explicit before validation or production access can move.",
        )
    ]


def reviewer_action_items_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="reviewer_action_items_make_proof_debt_actionable",
            target="reviewer_action_items",
            value=[
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
            reason="Each reviewer receives the proof task that blocks access from moving forward.",
        )
    ]


def next_validation_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="next_step_is_scoped_dry_run_validation",
            target="next_validation",
            value={
                "action": "Run a scoped dry-run pilot review with named repositories, channels, and Jira project.",
                "owner": "Security/Legal + Engineering",
                "success_criteria": [
                    "approved data and tool scope",
                    "audit log reviewed",
                    "write actions remain draft-only",
                    "rollback/off-switch owner named",
                ],
            },
            reason="The next action is validation, not production access.",
        )
    ]


def safety_state_rule(request: AccessRequest) -> list[RuleEffect]:
    return [
        RuleEffect(
            rule_id="public_demo_safety_defaults_block_external_action",
            target="safety_state",
            value={
                "approval_granted": False,
                "external_writes_enabled": False,
                "composio_dry_run": True,
                "packet_state_mutation": False,
                "requires_human_approval": True,
                "default_public_demo_posture": "review_packet_only",
            },
            reason="The public harness prepares review packets and never grants access by default.",
        )
    ]


PACKET_RULES: tuple[Rule, ...] = (
    decision_rule,
    source_status_rule,
    approval_posture_rule,
    requested_capability_rule,
    tool_scope_rule,
    tool_access_plan_rule,
    data_scope_rule,
    evidence_notes_rule,
    blocked_claims_rule,
    missing_proof_rule,
    reviewer_owners_rule,
    reviewer_action_items_rule,
    next_validation_rule,
    safety_state_rule,
)


def evaluate_rules(request: AccessRequest) -> list[RuleEffect]:
    """Return all rule effects in deterministic registry order."""
    effects = []
    for rule in PACKET_RULES:
        effects.extend(rule(request))
    return effects
