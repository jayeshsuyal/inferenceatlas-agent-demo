"""Pure rules for deriving DecisionPacket sections from an AccessRequest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from .access_request import AccessRequest, ToolRequest


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
    "bigquery": "low",
    "looker": "low",
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
    "aggregate_product_usage_metrics": "aggregate product usage metrics",
    "internal_business_metrics": "internal business metrics",
    "production_infrastructure_context": "production infrastructure context",
    "source_code": "source code",
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


def _is_support_triage_request(request: AccessRequest) -> bool:
    return request.agent_name == "support triage agent"


def _data_label(data_class: str) -> str:
    return _DATA_CLASS_LABELS.get(data_class, data_class.replace("_", " "))


def _is_sensitive_data_class(data_class: str) -> bool:
    sensitive_markers = ("customer", "incident", "support", "production", "source_code", "credential")
    return any(marker in data_class for marker in sensitive_markers)


def _touches_sensitive_data(request: AccessRequest) -> bool:
    return any(_is_sensitive_data_class(data_class) for data_class in request.data_classes)


def _touches_support_context(request: AccessRequest) -> bool:
    return any("support" in data_class or "incident" in data_class for data_class in request.data_classes)


def _touches_production_context(request: AccessRequest) -> bool:
    return request.environment == "prod" and any(
        "production" in data_class or "source_code" in data_class for data_class in request.data_classes
    )


def _is_admin_scope(scope: str) -> bool:
    lowered = scope.lower()
    return "admin" in lowered or "iam:" in lowered or "owner" in lowered


def _is_write_like(value: str) -> bool:
    lowered = value.lower()
    if "read_only" in lowered or "read-only" in lowered:
        return False
    write_markers = (
        "write",
        "create",
        "update",
        "delete",
        "mutate",
        "post",
        "send",
        "push",
        "trigger",
        "change",
        "deploy",
        "restart",
        "admin",
    )
    return any(marker in lowered for marker in write_markers)


def _tool_has_write(tool: ToolRequest) -> bool:
    return any(_is_write_like(item) for item in tool.requested_actions + tool.scopes)


def _request_has_write(request: AccessRequest) -> bool:
    return any(_tool_has_write(tool) for tool in request.requested_tools)


def _request_has_admin_scope(request: AccessRequest) -> bool:
    return any(_is_admin_scope(scope) for tool in request.requested_tools for scope in tool.scopes)


def _risk_level(tool: ToolRequest, request: AccessRequest) -> Literal["low", "medium", "high", "critical"]:
    if any(_is_admin_scope(scope) for scope in tool.scopes):
        return "critical"
    if request.environment == "prod" and _tool_has_write(tool) and _touches_production_context(request):
        return "critical"
    if _tool_has_write(tool):
        return "high"
    known_tool_risk = _TOOL_RISK_LEVEL.get(_tool_key(tool.system))
    if known_tool_risk == "high":
        return "high"
    if _touches_sensitive_data(request):
        return "medium"
    return known_tool_risk or "medium"


def _highest_risk(request: AccessRequest) -> Literal["low", "medium", "high", "critical"]:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    risks = [_risk_level(tool, request) for tool in request.requested_tools]
    return max(risks, key=lambda risk: order[risk])


def _tool_list(request: AccessRequest) -> str:
    systems = [tool.system for tool in request.requested_tools]
    if len(systems) == 1:
        return systems[0]
    if len(systems) == 2:
        return " and ".join(systems)
    return ", ".join(systems[:-1]) + f", and {systems[-1]}"


def decision_rule(request: AccessRequest) -> list[RuleEffect]:
    highest_risk = _highest_risk(request)
    if highest_risk == "critical":
        verdict = "Do not approve this access request."
        review_posture = "Block validation until admin scopes, production writes, rollback proof, and Security/Engineering approval are resolved."
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        verdict = "Do not approve production access yet; allow read-only validation review."
        review_posture = "Approve a scoped read-only validation review after data owner scope confirmation."
    else:
        verdict = "Do not approve production tool access yet."
        review_posture = "Approve a scoped validation review before any production permission grant."
    return [
        RuleEffect(
            rule_id="agent_access_request_sets_review_question",
            target="decision",
            value={
                "question": f"Should the {request.agent_name} get {_tool_list(request)} access?",
                "verdict": verdict,
                "review_posture": review_posture,
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
    if _highest_risk(request) == "critical":
        posture = {
            "production_access": "blocked",
            "validation_review": "blocked_until_security_review",
            "read_access": "blocked_until_admin_scope_removed",
            "write_access": "blocked_due_to_admin_and_production_mutation",
            "compliance_claims": "blocked_until_security_legal_and_change_review",
        }
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        posture = {
            "production_access": "blocked",
            "validation_review": "allowed",
            "read_access": "allowed_after_data_owner_scope_review",
            "write_access": "not_requested",
            "compliance_claims": "blocked_until_data_owner_review",
        }
    else:
        posture = {
            "production_access": "blocked",
            "validation_review": "allowed",
            "read_access": "candidate_after_scope_review",
            "write_access": "blocked_until_rollback_and_off_switch_proof",
            "compliance_claims": "blocked_until_named_reviewer_evidence",
        }
    return [
        RuleEffect(
            rule_id="production_access_requires_named_review",
            target="approval_posture",
            value=posture,
            reason="Production and write access stay blocked until scope, proof, rollback, and reviewers are named.",
        )
    ]


def requested_capability_rule(request: AccessRequest) -> list[RuleEffect]:
    capabilities = []
    for tool in request.requested_tools:
        capabilities.append(
            {
                "system": tool.system,
                "requested_access": "; ".join(tool.requested_actions),
                "risk_level": _risk_level(tool, request),
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
        if _is_support_triage_request(request) and tool_key in _TOOL_SCOPE:
            scope[tool_key] = _TOOL_SCOPE[tool_key]
            continue

        write_items = [item for item in tool.requested_actions + tool.scopes if _is_write_like(item)]
        read_items = [scope_item for scope_item in tool.scopes if not _is_write_like(scope_item)]
        if not read_items:
            read_items = ["named allowlisted resources only"]
        blocked = write_items or ["permission changes", "data export", "workspace-wide access"]
        if any(_is_admin_scope(item) for item in tool.scopes):
            blocked = ["admin scope", "production mutation", "permission changes", "workflow dispatch"]
        scope[tool_key] = {
            "read": list(read_items),
            "write": [] if not write_items else ["dry-run proposal only"],
            "blocked_until_proven": blocked,
        }
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
        if _is_support_triage_request(request) and tool_key in _TOOL_ACCESS_PLAN:
            base_plan = _TOOL_ACCESS_PLAN[tool_key]
            plan[tool_key] = {
                "requested": "; ".join(tool.requested_actions),
                "demo_allowance": base_plan["demo_allowance"],
                "blocked_actions": base_plan["blocked_actions"],
                "required_proof": base_plan["required_proof"],
            }
            continue

        write_items = [item for item in tool.requested_actions + tool.scopes if _is_write_like(item)]
        if any(_is_admin_scope(scope) for scope in tool.scopes):
            demo_allowance = "blocked; admin/write actions require Security and Engineering approval"
            blocked_actions = ["admin scope", "production repository mutation", "workflow dispatch", "permission changes"]
            required_proof = [
                "admin scope removal or explicit approval",
                "repository allowlist",
                "rollback/off-switch plan",
                "change-management owner",
            ]
        elif write_items:
            demo_allowance = "dry-run write proposal only; no production mutation"
            blocked_actions = list(write_items)
            required_proof = ["resource allowlist", "rollback/off-switch plan", "audit log owner"]
        else:
            demo_allowance = "read-only validation plan only"
            blocked_actions = ["writes", "exports", "permission changes"]
            required_proof = ["dataset/resource allowlist", "data owner approval", "read-only credential proof"]
        plan[tool_key] = {
            "requested": "; ".join(tool.requested_actions),
            "demo_allowance": demo_allowance,
            "blocked_actions": blocked_actions,
            "required_proof": required_proof,
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
                "may_include": [_data_label(item) for item in request.data_classes],
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
    if _is_support_triage_request(request):
        claims = [
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
        ]
    elif _highest_risk(request) == "critical":
        claims = [
            {
                "claim": "Admin or production write access is approved.",
                "reason": "Admin scopes and production mutations require explicit Security and Engineering approval.",
            },
            {
                "claim": "The agent may change organization security settings.",
                "reason": "Organization-level permissions are blocked until admin scope removal or break-glass approval exists.",
            },
            {
                "claim": "The agent may trigger production workflows.",
                "reason": "Workflow dispatch can mutate production state and requires rollback/off-switch proof.",
            },
            {
                "claim": "The workflow is compliance-ready.",
                "reason": "Compliance approval cannot be inferred from an agent request or demo transcript.",
            },
        ]
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        claims = [
            {
                "claim": "Production access is broadly approved.",
                "reason": "Only a read-only validation review can move before data owner scope confirmation.",
            },
            {
                "claim": "The agent may export rows or mutate dashboards.",
                "reason": "The request is read-only and does not include export, write, or dashboard mutation proof.",
            },
        ]
    else:
        claims = [
            {
                "claim": "Production tool access is approved.",
                "reason": "Named reviewer evidence and tool scope proof are missing.",
            },
            {
                "claim": "The agent may perform write actions.",
                "reason": "Write actions require rollback/off-switch proof and explicit human approval.",
            },
        ]
    return [
        RuleEffect(
            rule_id="unsupported_access_and_compliance_claims_stay_blocked",
            target="blocked_claims",
            value=claims,
            reason="Claims that lack reviewer evidence remain visible as blocked claims.",
        )
    ]


def missing_proof_rule(request: AccessRequest) -> list[RuleEffect]:
    missing_proof = []
    for tool in request.requested_tools:
        tool_key = _tool_key(tool.system)
        if _is_support_triage_request(request) and tool_key in _MISSING_PROOF_BY_TOOL:
            missing_proof.append(_MISSING_PROOF_BY_TOOL[tool_key])
            continue
        if any(_is_admin_scope(scope) for scope in tool.scopes):
            missing_proof.append(
                {
                    "item": f"{tool.system} admin scope removal or explicit break-glass approval",
                    "owner": "Security/Engineering",
                    "unblocks": "admin access rejection review",
                }
            )
        elif _tool_has_write(tool):
            missing_proof.append(
                {
                    "item": f"{tool.system} write-action rollback, off-switch, and audit plan",
                    "owner": "Engineering",
                    "unblocks": "write-action validation review",
                }
            )
        else:
            missing_proof.append(
                {
                    "item": f"{tool.system} read-only allowlist and credential proof",
                    "owner": "Data/Engineering",
                    "unblocks": "read-only validation review",
                }
            )

    if _touches_support_context(request):
        missing_proof.append(
            {
                "item": "Support escalation workflow and human handoff owner",
                "owner": "Support Ops",
                "unblocks": "triage workflow fit review",
            }
        )
    if _request_has_write(request) or _request_has_admin_scope(request) or _touches_sensitive_data(request):
        missing_proof.append(
            {
                "item": "Audit log shape for tool calls, evidence intake, and reviewer decisions",
                "owner": "Security/Engineering",
                "unblocks": "reviewable pilot packet",
            }
        )
    if not _request_has_write(request) and not _touches_sensitive_data(request):
        missing_proof.append(
            {
                "item": "Data owner confirmation that requested metrics are aggregate and non-customer-specific",
                "owner": "Data/Analytics",
                "unblocks": "read-only analytics validation",
            }
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
    if _is_support_triage_request(request):
        owners = [
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
        ]
    elif _highest_risk(request) == "critical":
        owners = [
            {
                "owner": "Security/Engineering",
                "review_area": "admin scopes, production mutation, workflow dispatch, rollback/off-switch",
                "current_state": "required_before_validation",
            },
            {
                "owner": "Engineering Leadership",
                "review_area": "production change authority, repository allowlist, incident rollback owner",
                "current_state": "required_before_any_write_path",
            },
            {
                "owner": "Security/Legal",
                "review_area": "source-code and production infrastructure exposure",
                "current_state": "required_before_access",
            },
        ]
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        owners = [
            {
                "owner": "Data/Analytics",
                "review_area": "aggregate metric scope, dashboard allowlist, read-only credentials",
                "current_state": "required_before_validation",
            },
            {
                "owner": "Engineering",
                "review_area": "read-only credential boundary and audit log owner",
                "current_state": "required_before_access",
            },
        ]
    else:
        owners = [
            {
                "owner": "Security/Legal",
                "review_area": "data exposure, retention, logging, policy boundary",
                "current_state": "required_before_access",
            },
            {
                "owner": "Engineering",
                "review_area": "permission boundaries, rollback, off-switch, audit logs",
                "current_state": "required_before_write_actions",
            },
        ]
    return [
        RuleEffect(
            rule_id="sensitive_agent_access_names_reviewer_owners",
            target="reviewer_owners",
            value=owners,
            reason="Reviewer ownership is explicit before validation or production access can move.",
        )
    ]


def reviewer_action_items_rule(request: AccessRequest) -> list[RuleEffect]:
    if _is_support_triage_request(request):
        action_items = [
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
        ]
    elif _highest_risk(request) == "critical":
        action_items = [
            {
                "owner": "Security/Engineering",
                "action": "Reject or remove admin scopes, define repository allowlist, and require rollback/off-switch proof",
                "blocks": "admin validation and all production write actions",
            },
            {
                "owner": "Engineering Leadership",
                "action": "Confirm production change authority and named incident rollback owner",
                "blocks": "production workflow dispatch or repository mutation",
            },
            {
                "owner": "Security/Legal",
                "action": "Review production infrastructure and source-code exposure boundaries",
                "blocks": "source-code and production context access",
            },
        ]
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        action_items = [
            {
                "owner": "Data/Analytics",
                "action": "Confirm metrics are aggregate, allowlisted, and non-customer-specific",
                "blocks": "read-only analytics validation",
            },
            {
                "owner": "Engineering",
                "action": "Provide read-only credential proof and audit log owner",
                "blocks": "warehouse/dashboard connection",
            },
        ]
    else:
        action_items = [
            {
                "owner": "Security/Legal",
                "action": "Confirm allowed data scope, retention, and logging terms",
                "blocks": "sensitive data access",
            },
            {
                "owner": "Engineering",
                "action": "Provide allowlists, permission boundaries, audit logs, and off-switch proof",
                "blocks": "tool connection and any write-action pilot",
            },
        ]
    return [
        RuleEffect(
            rule_id="reviewer_action_items_make_proof_debt_actionable",
            target="reviewer_action_items",
            value=action_items,
            reason="Each reviewer receives the proof task that blocks access from moving forward.",
        )
    ]


def next_validation_rule(request: AccessRequest) -> list[RuleEffect]:
    if _is_support_triage_request(request):
        next_validation = {
            "action": "Run a scoped dry-run pilot review with named repositories, channels, and Jira project.",
            "owner": "Security/Legal + Engineering",
            "success_criteria": [
                "approved data and tool scope",
                "audit log reviewed",
                "write actions remain draft-only",
                "rollback/off-switch owner named",
            ],
        }
    elif _highest_risk(request) == "critical":
        next_validation = {
            "action": "Reject production write/admin access until the request is rewritten without admin scopes and with rollback proof.",
            "owner": "Security/Engineering + Engineering Leadership",
            "success_criteria": [
                "admin scopes removed or explicitly approved",
                "production write path remains blocked",
                "repository allowlist reviewed",
                "rollback/off-switch owner named",
            ],
        }
    elif not _request_has_write(request) and not _touches_sensitive_data(request):
        next_validation = {
            "action": "Run a read-only analytics validation with named datasets, dashboards, and aggregate-only metrics.",
            "owner": "Data/Analytics + Engineering",
            "success_criteria": [
                "dataset and dashboard allowlist approved",
                "read-only credentials verified",
                "no row export or dashboard mutation allowed",
                "audit log owner named",
            ],
        }
    else:
        next_validation = {
            "action": "Run a scoped dry-run pilot review with named tools and resources.",
            "owner": "Security/Legal + Engineering",
            "success_criteria": [
                "approved data and tool scope",
                "audit log reviewed",
                "write actions remain draft-only",
                "rollback/off-switch owner named",
            ],
        }
    return [
        RuleEffect(
            rule_id="next_step_is_scoped_dry_run_validation",
            target="next_validation",
            value=next_validation,
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
