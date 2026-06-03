"""Public conformance contract for agent-access review packets.

This contract is intentionally public-facing. It validates the proof surface
that a reviewer or external implementation should be able to inspect without
exposing private InferenceAtlas v1 schemas, prompts, lanes, or routing logic.
"""

from __future__ import annotations

from typing import Any


PUBLIC_CONTRACT_VERSION = "agent_access_public.v0"

PUBLIC_REQUIRED_PACKET_FIELDS = (
    "schema_version",
    "packet_id",
    "decision",
    "approval_posture",
    "requested_capability",
    "tool_access_plan",
    "tool_scope",
    "blocked_claims",
    "missing_proof",
    "reviewer_owners",
    "reviewer_action_items",
    "next_validation",
    "safety_state",
)

PUBLIC_REQUIRED_BRIEF_FIELDS = (
    "schema_version",
    "brief_id",
    "derived_from_packet_id",
    "decision",
    "go_no_go",
    "access_eligibility",
    "access_envelope",
    "reviewer_gates",
    "safety_state",
)

PUBLIC_ARTIFACT_PROJECTIONS = (
    "packet_json",
    "packet_markdown",
    "decision_brief_json",
    "decision_brief_markdown",
)

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_VALIDATION_POSTURES = {"allowed", "blocked_until_security_review"}


def _missing_fields(item: dict[str, Any], required: tuple[str, ...], prefix: str) -> list[str]:
    return [f"{prefix}.{field}: missing" for field in required if field not in item]


def _expect_type(value: Any, expected_type: type, path: str) -> list[str]:
    if not isinstance(value, expected_type):
        return [f"{path}: expected {expected_type.__name__}"]
    return []


def _expect_non_empty_string(value: Any, path: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{path}: expected non-empty string"]
    return []


def _expect_non_empty_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{path}: expected non-empty list"]
    return []


def validate_public_packet(packet: dict[str, Any]) -> list[str]:
    """Return public contract errors for a DecisionPacket."""
    errors = _missing_fields(packet, PUBLIC_REQUIRED_PACKET_FIELDS, "packet")
    if errors:
        return errors

    errors.extend(_expect_non_empty_string(packet["packet_id"], "packet.packet_id"))
    errors.extend(_expect_type(packet["decision"], dict, "packet.decision"))
    errors.extend(_expect_type(packet["approval_posture"], dict, "packet.approval_posture"))
    errors.extend(_expect_non_empty_list(packet["requested_capability"], "packet.requested_capability"))
    errors.extend(_expect_type(packet["tool_access_plan"], dict, "packet.tool_access_plan"))
    errors.extend(_expect_type(packet["tool_scope"], dict, "packet.tool_scope"))
    errors.extend(_expect_non_empty_list(packet["blocked_claims"], "packet.blocked_claims"))
    errors.extend(_expect_non_empty_list(packet["missing_proof"], "packet.missing_proof"))
    errors.extend(_expect_non_empty_list(packet["reviewer_owners"], "packet.reviewer_owners"))
    errors.extend(_expect_non_empty_list(packet["reviewer_action_items"], "packet.reviewer_action_items"))
    errors.extend(_expect_type(packet["next_validation"], dict, "packet.next_validation"))
    errors.extend(_expect_type(packet["safety_state"], dict, "packet.safety_state"))

    decision = packet["decision"]
    errors.extend(_missing_fields(decision, ("question", "verdict", "review_posture", "raw_prompt"), "packet.decision"))
    for field in ("question", "verdict", "review_posture", "raw_prompt"):
        if field in decision:
            errors.extend(_expect_non_empty_string(decision[field], f"packet.decision.{field}"))

    posture = packet["approval_posture"]
    errors.extend(
        _missing_fields(
            posture,
            ("production_access", "validation_review", "read_access", "write_access", "compliance_claims"),
            "packet.approval_posture",
        )
    )
    if posture.get("production_access") != "blocked":
        errors.append("packet.approval_posture.production_access: must be blocked")
    if posture.get("validation_review") not in VALID_VALIDATION_POSTURES:
        errors.append("packet.approval_posture.validation_review: invalid public posture")

    for index, capability in enumerate(packet["requested_capability"]):
        path = f"packet.requested_capability[{index}]"
        if not isinstance(capability, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(capability, ("system", "requested_access", "risk_level", "default_demo_state"), path))
        if capability.get("risk_level") not in VALID_RISK_LEVELS:
            errors.append(f"{path}.risk_level: invalid risk level")

    for tool_name, plan in packet["tool_access_plan"].items():
        path = f"packet.tool_access_plan.{tool_name}"
        if not isinstance(plan, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(plan, ("requested", "demo_allowance", "blocked_actions", "required_proof"), path))
        if "blocked_actions" in plan:
            errors.extend(_expect_non_empty_list(plan["blocked_actions"], f"{path}.blocked_actions"))
        if "required_proof" in plan:
            errors.extend(_expect_non_empty_list(plan["required_proof"], f"{path}.required_proof"))

    for index, blocked_claim in enumerate(packet["blocked_claims"]):
        path = f"packet.blocked_claims[{index}]"
        if not isinstance(blocked_claim, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(blocked_claim, ("claim", "reason"), path))

    for index, proof in enumerate(packet["missing_proof"]):
        path = f"packet.missing_proof[{index}]"
        if not isinstance(proof, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(proof, ("item", "owner", "unblocks"), path))

    for index, owner in enumerate(packet["reviewer_owners"]):
        path = f"packet.reviewer_owners[{index}]"
        if not isinstance(owner, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(owner, ("owner", "review_area", "current_state"), path))

    for index, item in enumerate(packet["reviewer_action_items"]):
        path = f"packet.reviewer_action_items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(item, ("owner", "action", "blocks"), path))

    next_validation = packet["next_validation"]
    errors.extend(_missing_fields(next_validation, ("action", "owner", "success_criteria"), "packet.next_validation"))
    if "success_criteria" in next_validation:
        errors.extend(_expect_non_empty_list(next_validation["success_criteria"], "packet.next_validation.success_criteria"))

    safety = packet["safety_state"]
    for field in ("approval_granted", "external_writes_enabled", "packet_state_mutation"):
        if safety.get(field) is not False:
            errors.append(f"packet.safety_state.{field}: must be false")
    if safety.get("composio_dry_run") is not True:
        errors.append("packet.safety_state.composio_dry_run: must be true")
    if safety.get("requires_human_approval") is not True:
        errors.append("packet.safety_state.requires_human_approval: must be true")

    return errors


def validate_public_brief(brief: dict[str, Any]) -> list[str]:
    """Return public contract errors for an Agent Access Decision Brief."""
    errors = _missing_fields(brief, PUBLIC_REQUIRED_BRIEF_FIELDS, "brief")
    if errors:
        return errors

    errors.extend(_expect_non_empty_string(brief["brief_id"], "brief.brief_id"))
    errors.extend(_expect_non_empty_string(brief["derived_from_packet_id"], "brief.derived_from_packet_id"))
    errors.extend(_expect_type(brief["decision"], dict, "brief.decision"))
    errors.extend(_expect_type(brief["go_no_go"], dict, "brief.go_no_go"))
    errors.extend(_expect_non_empty_list(brief["access_eligibility"], "brief.access_eligibility"))
    errors.extend(_expect_type(brief["access_envelope"], dict, "brief.access_envelope"))
    errors.extend(_expect_non_empty_list(brief["reviewer_gates"], "brief.reviewer_gates"))
    errors.extend(_expect_type(brief["safety_state"], dict, "brief.safety_state"))

    decision = brief["decision"]
    errors.extend(_missing_fields(decision, ("question", "verdict", "recommended_next_step", "reason"), "brief.decision"))
    if decision.get("verdict") != "Do not grant production access.":
        errors.append("brief.decision.verdict: public brief must not grant production access")

    go_no_go = brief["go_no_go"]
    errors.extend(
        _missing_fields(
            go_no_go,
            ("production_access", "scoped_validation_review", "external_writes", "composio_dry_run", "next_validation"),
            "brief.go_no_go",
        )
    )
    if go_no_go.get("production_access") is not False:
        errors.append("brief.go_no_go.production_access: must be false")
    if go_no_go.get("external_writes") is not False:
        errors.append("brief.go_no_go.external_writes: must be false")
    if go_no_go.get("composio_dry_run") is not True:
        errors.append("brief.go_no_go.composio_dry_run: must be true")

    for index, item in enumerate(brief["access_eligibility"]):
        path = f"brief.access_eligibility[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(
            _missing_fields(
                item,
                ("system", "requested_access", "risk_level", "eligibility", "validation_allowance", "production_status", "required_proof"),
                path,
            )
        )
        if item.get("production_status") != "blocked":
            errors.append(f"{path}.production_status: must be blocked")

    for index, gate in enumerate(brief["reviewer_gates"]):
        path = f"brief.reviewer_gates[{index}]"
        if not isinstance(gate, dict):
            errors.append(f"{path}: expected object")
            continue
        errors.extend(_missing_fields(gate, ("owner", "gate", "blocks", "required_before"), path))

    safety = brief["safety_state"]
    for field in ("approval_granted", "external_writes_enabled", "packet_state_mutation"):
        if safety.get(field) is not False:
            errors.append(f"brief.safety_state.{field}: must be false")
    if safety.get("composio_dry_run") is not True:
        errors.append("brief.safety_state.composio_dry_run: must be true")

    return errors


def validate_public_review_artifacts(packet: dict[str, Any], brief: dict[str, Any]) -> list[str]:
    """Validate a packet/brief pair against the public conformance surface."""
    errors = []
    errors.extend(validate_public_packet(packet))
    errors.extend(validate_public_brief(brief))
    if packet.get("packet_id") != brief.get("derived_from_packet_id"):
        errors.append("packet.packet_id and brief.derived_from_packet_id: must match")
    return errors
