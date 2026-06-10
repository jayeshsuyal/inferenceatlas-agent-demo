"""ProofGraph v0 for packet-authority proof provenance.

The ProofGraph is the shared object sponsor proof attaches to. The default
graph stays packet-only; sponsor layers can be included explicitly when they
are non-mutating projections of already-built proof contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Literal

from .adapters.core import (
    ADAPTER_CONTRACT_VERSION,
    NEBIUS_FORBIDDEN_NARRATION_PHRASES,
    NEBIUS_REQUIRED_TONE_ANCHORS,
    build_adapter_result,
)
from .composio_dry_run_diff import (
    COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION,
    build_composio_dry_run_diff,
)
from .packet_authority import (
    build_packet_authority_snapshot_for_scenario,
    derive_decision_lock,
    stable_sha256,
)
from .portkey_guardrail_proof_loop import (
    PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION,
    build_portkey_guardrail_proof_loop,
)
from .scenarios import SCENARIOS, build_scenario_packet
from .tavily_live_evidence import (
    TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
    build_tavily_live_evidence,
)


PROOF_GRAPH_SCHEMA_VERSION = "proof_graph.v0"
PROOF_GRAPH_GENERATED_BY = "inferenceatlas-agent-demo"
DEFAULT_SCENARIO = "support_triage_agent"

Provider = Literal["ia_packet", "tavily", "composio", "openclaw", "nebius", "portkey"]
ProofMode = Literal["deterministic_packet_authority", "deterministic_fallback", "live_when_configured"]
NodeType = Literal["packet", "proof"]
EdgeType = Literal[
    "attaches_to_packet_field",
    "supports_review",
    "blocks_action",
    "requires_human_owner",
    "observed_by_downstream",
]

PACKET_ONLY_PROOF_FIELDS: tuple[str, ...] = (
    "decision_lock",
    "blocked_claims",
    "missing_proof",
    "reviewer_routing",
    "next_human_action",
    "safety_invariants",
)


def _first_text(value: Any, *, limit: int = 220) -> str:
    return " ".join(str(value or "").split())[:limit]


def _stringify_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        label = (
            item.get("claim")
            or item.get("item")
            or item.get("owner")
            or item.get("action")
            or item.get("review_area")
            or "item"
        )
        detail = item.get("reason") or item.get("unblocks") or item.get("review_area") or item.get("blocks") or ""
        return _first_text(f"{label} - {detail}" if detail else label)
    return _first_text(item)


def _stringify_items(items: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(items, (list, tuple)):
        return []
    return [_stringify_item(item) for item in list(items)[:limit]]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:72] or "item"


def _packet_safety(packet: dict[str, Any]) -> dict[str, bool]:
    safety = packet.get("safety_state", {})
    return {
        "approval_granted": bool(safety.get("approval_granted")),
        "external_writes_enabled": bool(safety.get("external_writes_enabled")),
        "packet_state_mutation": bool(safety.get("packet_state_mutation")),
        "requires_human_approval": bool(safety.get("requires_human_approval", True)),
    }


def _next_human_action(packet: dict[str, Any]) -> str:
    next_validation = packet.get("next_validation", {})
    if isinstance(next_validation, dict):
        action = _first_text(next_validation.get("action"))
        owner = _first_text(next_validation.get("owner"))
        if action and owner:
            return f"{action} Owner: {owner}."
        if action:
            return action
    return "Route the packet to named human reviewers before any movement."


@dataclass(frozen=True)
class PacketNode:
    node_id: str
    packet_id: str
    revision_id: str
    content_hash: str
    decision_lock: str
    verdict: str
    review_posture: str
    next_human_action: str
    safety_state: dict[str, bool]
    node_type: NodeType = "packet"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "packet_id": self.packet_id,
            "revision_id": self.revision_id,
            "content_hash": self.content_hash,
            "decision_lock": self.decision_lock,
            "verdict": self.verdict,
            "review_posture": self.review_posture,
            "next_human_action": self.next_human_action,
            "safety_state": dict(self.safety_state),
        }


@dataclass(frozen=True)
class ProofNode:
    node_id: str
    label: str
    provider: Provider
    mode: ProofMode
    attached_packet_field: str
    summary: str
    source_refs: tuple[str, ...]
    next_human_action: str
    api_call_made: bool = False
    fallback_used: bool = False
    external_write_made: bool = False
    can_change_packet_verdict: bool = False
    human_review_required: bool = True
    node_type: NodeType = "proof"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "provider": self.provider,
            "mode": self.mode,
            "api_call_made": self.api_call_made,
            "fallback_used": self.fallback_used,
            "external_write_made": self.external_write_made,
            "can_change_packet_verdict": self.can_change_packet_verdict,
            "attached_packet_field": self.attached_packet_field,
            "human_review_required": self.human_review_required,
            "next_human_action": self.next_human_action,
            "summary": self.summary,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class ProofEdge:
    edge_id: str
    edge_type: EdgeType
    from_node_id: str
    to_node_id: str
    packet_field: str
    human_review_required: bool = True
    can_change_packet_verdict: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "packet_field": self.packet_field,
            "human_review_required": self.human_review_required,
            "can_change_packet_verdict": self.can_change_packet_verdict,
        }


def _proof_node(
    *,
    field: str,
    label: str,
    summary: str,
    source_refs: list[str],
    next_human_action: str,
) -> ProofNode:
    return ProofNode(
        node_id=f"proof:ia_packet:{field}",
        label=label,
        provider="ia_packet",
        mode="deterministic_packet_authority",
        attached_packet_field=field,
        summary=summary,
        source_refs=tuple(source_refs),
        next_human_action=next_human_action,
    )


def _composio_proof_node(
    *,
    node_id: str,
    field: str,
    label: str,
    summary: str,
    source_refs: list[str],
    next_human_action: str,
) -> ProofNode:
    return ProofNode(
        node_id=node_id,
        label=label,
        provider="composio",
        mode="deterministic_fallback",
        attached_packet_field=field,
        summary=summary,
        source_refs=tuple(source_refs),
        next_human_action=next_human_action,
        fallback_used=True,
    )


def _sponsor_proof_node(
    *,
    provider: Provider,
    node_id: str,
    field: str,
    label: str,
    summary: str,
    source_refs: list[str],
    next_human_action: str,
) -> ProofNode:
    return ProofNode(
        node_id=node_id,
        label=label,
        provider=provider,
        mode="deterministic_fallback",
        attached_packet_field=field,
        summary=summary,
        source_refs=tuple(source_refs),
        next_human_action=next_human_action,
        fallback_used=True,
    )


def _packet_only_nodes(packet: dict[str, Any], *, next_human_action: str) -> tuple[ProofNode, ...]:
    decision = packet.get("decision", {})
    posture = packet.get("approval_posture", {})
    return (
        _proof_node(
            field="decision_lock",
            label="Decision lock",
            summary=(
                f"{_first_text(decision.get('verdict'))} "
                f"Review posture: {_first_text(decision.get('review_posture'))}"
            ),
            source_refs=["decision.verdict", "approval_posture", "safety_state"],
            next_human_action=next_human_action,
        ),
        _proof_node(
            field="blocked_claims",
            label="Blocked claims",
            summary="; ".join(_stringify_items(packet.get("blocked_claims"), limit=4)),
            source_refs=["blocked_claims"],
            next_human_action=next_human_action,
        ),
        _proof_node(
            field="missing_proof",
            label="Missing proof",
            summary="; ".join(_stringify_items(packet.get("missing_proof"), limit=5)),
            source_refs=["missing_proof"],
            next_human_action=next_human_action,
        ),
        _proof_node(
            field="reviewer_routing",
            label="Reviewer routing",
            summary="; ".join(_stringify_items(packet.get("reviewer_owners"), limit=4)),
            source_refs=["reviewer_owners", "reviewer_action_items"],
            next_human_action=next_human_action,
        ),
        _proof_node(
            field="next_human_action",
            label="Next human action",
            summary=next_human_action,
            source_refs=["next_validation.action", "next_validation.owner"],
            next_human_action=next_human_action,
        ),
        _proof_node(
            field="safety_invariants",
            label="Safety invariants",
            summary=(
                f"production_access={posture.get('production_access', 'unknown')}; "
                f"approval_granted={_packet_safety(packet)['approval_granted']}; "
                f"external_writes_enabled={_packet_safety(packet)['external_writes_enabled']}; "
                f"packet_state_mutation={_packet_safety(packet)['packet_state_mutation']}"
            ),
            source_refs=["safety_state", "approval_posture.production_access"],
            next_human_action=next_human_action,
        ),
    )


def _composio_blast_radius_summary(composio_diff: dict[str, Any]) -> dict[str, Any]:
    summary = composio_diff["permission_diff_summary"]
    blast_summary = composio_diff["blast_radius"]["summary"]
    return {
        "schema_version": COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION,
        "provider": "composio",
        "mode": "deterministic_fallback",
        "dry_run_enforced": bool(composio_diff["dry_run_enforced"]),
        "api_call_made": bool(composio_diff["api_call_made"]),
        "composio_execute_allowed": bool(composio_diff["composio_execute_allowed"]),
        "fallback_used": bool(composio_diff["fallback_used"]),
        "tool_count": int(summary["tool_count"]),
        "blocked_action_count": int(blast_summary["blocked_action_count"]),
        "write_like_action_count": int(blast_summary["write_like_action_count"]),
        "admin_like_action_count": int(blast_summary["admin_like_action_count"]),
        "high_or_critical_action_count": int(blast_summary["high_or_critical_action_count"]),
        "required_proof_count": int(summary["required_proof_count"]),
        "max_risk_level": blast_summary["max_risk_level"],
        "all_blocked_before_execution": bool(blast_summary["all_blocked_before_execution"]),
        "all_write_or_admin_blocked": bool(blast_summary["all_write_or_admin_blocked"]),
        "would_execute": bool(blast_summary["would_execute"]),
        "candidate_action_slugs": list(summary["candidate_action_slugs"]),
        "docs_reference": composio_diff["docs_reference"],
        "sdk_docs_reference": composio_diff["sdk_docs_reference"],
        "safety_impact": composio_diff["safety_impact"],
    }


def _composio_blast_radius_nodes(
    packet: dict[str, Any],
    *,
    scenario_name: str,
    next_human_action: str,
) -> tuple[tuple[ProofNode, ...], tuple[ProofEdge, ...], dict[str, Any]]:
    composio_diff = build_composio_dry_run_diff(
        packet,
        scenario_name=scenario_name,
        dry_run_enabled=True,
    )
    nodes: list[ProofNode] = []
    edges: list[ProofEdge] = []

    for diff in composio_diff["permission_diffs"]:
        tool = diff["tool"]
        tool_slug = _slug(tool)
        matrix = diff["permission_review_matrix"]
        tool_node = _composio_proof_node(
            node_id=f"proof:composio:tool_scope:{tool_slug}",
            field="tool_scope",
            label=f"Composio tool scope: {tool}",
            summary=(
                f"{diff['candidate_action_slug']} stays dry-run. "
                f"{matrix['blocked_action_count']} blocked actions; "
                f"risk={matrix['blast_radius_class']}."
            ),
            source_refs=[
                f"tool_access_plan.{tool}",
                f"composio.permission_diffs.{tool}.execute_action_preview",
                f"composio.permission_diffs.{tool}.permission_review_matrix",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(tool_node)

        for index, action in enumerate(diff["blast_radius"]["blocked_actions"], start=1):
            action_slug = _slug(action["action"])
            action_node = _composio_proof_node(
                node_id=f"proof:composio:blocked_action:{tool_slug}:{index}:{action_slug}",
                field="tool_scope",
                label=f"Blocked {tool} action",
                summary=(
                    f"{action['action']} is {action['policy_decision']} "
                    f"({action['risk_level']}/{action['action_class']}). "
                    f"{action['blocked_reason']}"
                ),
                source_refs=[
                    f"tool_access_plan.{tool}.blocked_actions[{index - 1}]",
                    f"composio.permission_diffs.{tool}.blast_radius.blocked_actions[{index - 1}]",
                ],
                next_human_action=next_human_action,
            )
            nodes.append(action_node)
            edges.append(
                ProofEdge(
                    edge_id=f"edge:{action_node.node_id}:to:{tool_node.node_id}:blocks_action",
                    edge_type="blocks_action",
                    from_node_id=action_node.node_id,
                    to_node_id=tool_node.node_id,
                    packet_field="tool_scope",
                )
            )

        for index, proof in enumerate(diff["required_scopes_or_proof"], start=1):
            proof_slug = _slug(proof)
            proof_node = _composio_proof_node(
                node_id=f"proof:composio:required_proof:{tool_slug}:{index}:{proof_slug}",
                field="missing_proof",
                label=f"Required proof for {tool}",
                summary=proof,
                source_refs=[
                    f"tool_access_plan.{tool}.required_proof[{index - 1}]",
                    f"composio.permission_diffs.{tool}.required_scopes_or_proof[{index - 1}]",
                ],
                next_human_action=next_human_action,
            )
            nodes.append(proof_node)
            edges.append(
                ProofEdge(
                    edge_id=f"edge:{proof_node.node_id}:to:{tool_node.node_id}:requires_human_owner",
                    edge_type="requires_human_owner",
                    from_node_id=proof_node.node_id,
                    to_node_id=tool_node.node_id,
                    packet_field="missing_proof",
                )
            )

    return tuple(nodes), tuple(edges), _composio_blast_radius_summary(composio_diff)


def _openclaw_runtime_trace_summary(openclaw: dict[str, Any]) -> dict[str, Any]:
    quality = openclaw["trace_quality_summary"]
    return {
        "schema_version": ADAPTER_CONTRACT_VERSION,
        "provider": "openclaw",
        "mode": "deterministic_fallback",
        "status": openclaw["status"],
        "api_call_made": False,
        "fallback_used": True,
        "checkpoint_count": int(quality["checkpoint_count"]),
        "attempted_action_count": int(quality["attempted_action_count"]),
        "blocked_event_count": int(quality["blocked_event_count"]),
        "write_like_blocked_count": int(quality["write_like_blocked_count"]),
        "admin_like_blocked_count": int(quality["admin_like_blocked_count"]),
        "high_or_critical_action_count": int(quality["high_or_critical_action_count"]),
        "all_attempted_actions_blocked": bool(quality["all_attempted_actions_blocked"]),
        "runtime_write_attempted": bool(quality["runtime_write_attempted"]),
        "human_review_boundary_preserved": bool(quality["human_review_boundary_preserved"]),
        "would_execute": bool(openclaw["would_execute"]),
        "safety_impact": openclaw["safety_impact"],
    }


def _openclaw_runtime_trace_nodes(
    *,
    scenario_name: str,
    next_human_action: str,
) -> tuple[tuple[ProofNode, ...], tuple[ProofEdge, ...], dict[str, Any]]:
    openclaw = build_adapter_result("openclaw", scenario_name)
    nodes: list[ProofNode] = []
    edges: list[ProofEdge] = []
    checkpoint_nodes: dict[str, ProofNode] = {}
    attempted_nodes: dict[tuple[str, str], ProofNode] = {}

    for checkpoint in openclaw["trace_timeline"]:
        checkpoint_name = checkpoint["checkpoint"]
        checkpoint_node = _sponsor_proof_node(
            provider="openclaw",
            node_id=f"proof:openclaw:checkpoint:{checkpoint['order']}:{_slug(checkpoint_name)}",
            field="runtime_trace",
            label=f"OpenClaw checkpoint: {checkpoint_name}",
            summary=(
                f"{checkpoint['outcome']} observed `{checkpoint['packet_field_observed']}`; "
                f"policy_decision={checkpoint['policy_decision']}; would_execute={checkpoint['would_execute']}."
            ),
            source_refs=[
                f"openclaw.trace_timeline[{checkpoint['order'] - 1}]",
                f"openclaw.trace_steps.{checkpoint_name}",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(checkpoint_node)
        checkpoint_nodes[checkpoint_name] = checkpoint_node

    policy_checkpoint = checkpoint_nodes.get("plan_tool_actions") or checkpoint_nodes.get("evaluate_policy_gate")
    for attempted in openclaw["attempted_action_timeline"]:
        tool = attempted["tool"]
        action = attempted["attempted_action"]
        attempted_node = _sponsor_proof_node(
            provider="openclaw",
            node_id=(
                f"proof:openclaw:attempted_action:{attempted['order']}:"
                f"{_slug(tool)}:{_slug(action)}"
            ),
            field="runtime_trace",
            label=f"OpenClaw attempted action: {tool}",
            summary=(
                f"{action} checked by {attempted['packet_check']} and "
                f"{attempted['policy_decision']} ({attempted['risk_level']}/{attempted['action_class']}). "
                f"would_execute={attempted['would_execute']}."
            ),
            source_refs=[
                f"openclaw.attempted_action_timeline[{attempted['order'] - 1}]",
                f"tool_access_plan.{tool}.blocked_actions",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(attempted_node)
        attempted_nodes[(tool, action)] = attempted_node
        if policy_checkpoint:
            edges.append(
                ProofEdge(
                    edge_id=(
                        f"edge:{attempted_node.node_id}:to:"
                        f"{policy_checkpoint.node_id}:observed_by_downstream"
                    ),
                    edge_type="observed_by_downstream",
                    from_node_id=attempted_node.node_id,
                    to_node_id=policy_checkpoint.node_id,
                    packet_field="runtime_trace",
                )
            )

    for index, event in enumerate(openclaw["blocked_action_events"], start=1):
        tool = event["tool"]
        action = event["blocked_action"]
        blocked_node = _sponsor_proof_node(
            provider="openclaw",
            node_id=f"proof:openclaw:blocked_event:{index}:{_slug(tool)}:{_slug(action)}",
            field="runtime_trace",
            label=f"OpenClaw blocked event: {tool}",
            summary=(
                f"{action} is {event['policy_decision']} "
                f"({event['risk_level']}/{event['action_class']}). "
                f"{event['blocked_reason']}"
            ),
            source_refs=[
                f"openclaw.blocked_action_events[{index - 1}]",
                f"tool_access_plan.{tool}.blocked_actions",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(blocked_node)
        attempted_node = attempted_nodes.get((tool, action))
        if attempted_node:
            edges.append(
                ProofEdge(
                    edge_id=f"edge:{blocked_node.node_id}:to:{attempted_node.node_id}:blocks_action",
                    edge_type="blocks_action",
                    from_node_id=blocked_node.node_id,
                    to_node_id=attempted_node.node_id,
                    packet_field="runtime_trace",
                )
            )

    return tuple(nodes), tuple(edges), _openclaw_runtime_trace_summary(openclaw)


def _nebius_reviewer_synthesis_summary(nebius: dict[str, Any]) -> dict[str, Any]:
    contract = nebius["reviewer_narration_contract"]
    narration = nebius["narration"]
    forbidden = [
        phrase for phrase in NEBIUS_FORBIDDEN_NARRATION_PHRASES if phrase.lower() in narration.lower()
    ]
    return {
        "schema_version": ADAPTER_CONTRACT_VERSION,
        "provider": "nebius",
        "mode": "deterministic_fallback",
        "status": nebius["status"],
        "api_call_made": False,
        "fallback_used": True,
        "input_field_count": len(contract["input_fields"]),
        "draft_output_count": len(contract["draft_outputs"]),
        "locked_field_count": len(contract["locked_fields"]),
        "llm_may_edit_count": len(nebius["llm_may_edit"]),
        "llm_must_not_edit_count": len(nebius["llm_must_not_edit"]),
        "required_anchor_count": len(NEBIUS_REQUIRED_TONE_ANCHORS),
        "required_anchors_present": all(anchor in narration for anchor in NEBIUS_REQUIRED_TONE_ANCHORS),
        "forbidden_phrases_present": forbidden,
        "can_change_verdict": False,
        "can_mutate_packet": False,
        "human_review_required": bool(contract["human_review_required"]),
        "safety_impact": nebius["safety_impact"],
    }


def _nebius_field_for_locked_field(field: str) -> str:
    if field == "blocked_claims":
        return "blocked_claims"
    if field == "safety_state":
        return "safety_invariants"
    return "decision_lock"


def _nebius_reviewer_synthesis_nodes(
    *,
    scenario_name: str,
    next_human_action: str,
) -> tuple[tuple[ProofNode, ...], tuple[ProofEdge, ...], dict[str, Any]]:
    nebius = build_adapter_result("nebius", scenario_name)
    contract = nebius["reviewer_narration_contract"]
    nodes: list[ProofNode] = []
    edges: list[ProofEdge] = []
    contract_node = _sponsor_proof_node(
        provider="nebius",
        node_id="proof:nebius:reviewer_synthesis_contract",
        field="claim_ledger",
        label="Nebius reviewer synthesis contract",
        summary=(
            f"human_review_required={contract['human_review_required']}; "
            f"inputs={len(contract['input_fields'])}; locked_fields={len(contract['locked_fields'])}; "
            "Nebius may draft language but cannot own verdicts."
        ),
        source_refs=[
            "nebius.reviewer_narration_contract",
            "nebius.llm_may_edit",
            "nebius.llm_must_not_edit",
        ],
        next_human_action=next_human_action,
    )
    nodes.append(contract_node)

    for index, field in enumerate(contract["locked_fields"], start=1):
        locked_node = _sponsor_proof_node(
            provider="nebius",
            node_id=f"proof:nebius:locked_field:{index}:{_slug(field)}",
            field=_nebius_field_for_locked_field(field),
            label=f"Nebius locked field: {field}",
            summary=(
                f"{field} is locked before narration. Nebius must not edit this field "
                "or change the packet decision."
            ),
            source_refs=[
                f"nebius.reviewer_narration_contract.locked_fields[{index - 1}]",
                "nebius.llm_must_not_edit",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(locked_node)
        edges.append(
            ProofEdge(
                edge_id=f"edge:{locked_node.node_id}:to:{contract_node.node_id}:supports_review",
                edge_type="supports_review",
                from_node_id=locked_node.node_id,
                to_node_id=contract_node.node_id,
                packet_field=locked_node.attached_packet_field,
            )
        )

    for index, draft_output in enumerate(contract["draft_outputs"], start=1):
        draft_node = _sponsor_proof_node(
            provider="nebius",
            node_id=f"proof:nebius:draft_output:{index}:{_slug(draft_output)}",
            field="claim_ledger",
            label=f"Nebius draft output: {draft_output}",
            summary=(
                f"{draft_output} is reviewer-facing language only. "
                "It can explain packet truth but cannot approve access."
            ),
            source_refs=[
                f"nebius.reviewer_narration_contract.draft_outputs[{index - 1}]",
                "nebius.llm_may_edit",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(draft_node)
        edges.append(
            ProofEdge(
                edge_id=f"edge:{draft_node.node_id}:to:{contract_node.node_id}:supports_review",
                edge_type="supports_review",
                from_node_id=draft_node.node_id,
                to_node_id=contract_node.node_id,
                packet_field="claim_ledger",
            )
        )

    anchor_node = _sponsor_proof_node(
        provider="nebius",
        node_id="proof:nebius:safety_anchor:no_approval",
        field="safety_invariants",
        label="Nebius safety anchor",
        summary=" ".join(NEBIUS_REQUIRED_TONE_ANCHORS),
        source_refs=["nebius.narration", "nebius.required_tone_anchors"],
        next_human_action=next_human_action,
    )
    nodes.append(anchor_node)
    edges.append(
        ProofEdge(
            edge_id=f"edge:{anchor_node.node_id}:to:{contract_node.node_id}:supports_review",
            edge_type="supports_review",
            from_node_id=anchor_node.node_id,
            to_node_id=contract_node.node_id,
            packet_field="safety_invariants",
        )
    )

    return tuple(nodes), tuple(edges), _nebius_reviewer_synthesis_summary(nebius)


def _tavily_evidence_summary(tavily: dict[str, Any]) -> dict[str, Any]:
    query_summary = tavily["query_plan_summary"]
    source_summary = tavily["source_quality_summary"]
    return {
        "schema_version": TAVILY_LIVE_EVIDENCE_SCHEMA_VERSION,
        "provider": "tavily",
        "mode": "deterministic_fallback",
        "status": tavily["status"],
        "live_requested": bool(tavily["live_requested"]),
        "live_call_attempted": bool(tavily["live_call_attempted"]),
        "live_call_count": int(tavily["live_call_count"]),
        "used_live_key": bool(tavily["used_live_key"]),
        "fallback_used": bool(tavily["fallback_used"]),
        "fallback_reason": tavily["fallback_reason"],
        "query_count": int(query_summary["query_count"]),
        "query_variant_count": int(query_summary["query_variant_count"]),
        "total_planned_searches": int(query_summary["total_planned_searches"]),
        "source_url_count": int(source_summary["source_url_count"]),
        "unique_source_url_count": int(source_summary["unique_source_url_count"]),
        "source_domain_count": int(source_summary["source_domain_count"]),
        "domain_diversity_score": float(source_summary["domain_diversity_score"]),
        "freshness_labels": list(source_summary["freshness_labels"]),
        "can_reduce_proof_debt": bool(source_summary["can_reduce_proof_debt"]),
        "cannot_grant_access": bool(source_summary["cannot_grant_access"]),
        "human_review_required": bool(source_summary["human_review_required"]),
        "docs_reference": tavily["docs_reference"],
        "safety_impact": tavily["safety_impact"],
    }


def _tavily_evidence_nodes(
    packet: dict[str, Any],
    *,
    scenario_name: str,
    next_human_action: str,
) -> tuple[tuple[ProofNode, ...], tuple[ProofEdge, ...], dict[str, Any]]:
    tavily = build_tavily_live_evidence(
        packet,
        scenario_name=scenario_name,
        live_enabled=False,
    )
    nodes: list[ProofNode] = []
    edges: list[ProofEdge] = []

    for index, candidate in enumerate(tavily["evidence_candidates"], start=1):
        candidate_slug = _slug(candidate["query"])
        candidate_node = _sponsor_proof_node(
            provider="tavily",
            node_id=f"proof:tavily:evidence_candidate:{index}:{candidate_slug}",
            field="source_candidates",
            label=f"Tavily evidence candidate: {candidate.get('reviewer_owner', 'reviewer')}",
            summary=(
                f"{candidate['query']} ({candidate['evidence_type']}); "
                f"freshness={candidate['freshness']}; "
                f"sources={len(candidate.get('source_urls', []))}; "
                f"can_reduce_proof_debt={candidate['can_reduce_proof_debt']}."
            ),
            source_refs=[
                f"missing_proof[{index - 1}]",
                f"tavily.evidence_candidates[{index - 1}]",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(candidate_node)

        for variant_index, query in enumerate(candidate.get("query_variants", [candidate["query"]]), start=1):
            query_node = _sponsor_proof_node(
                provider="tavily",
                node_id=(
                    f"proof:tavily:query_variant:{index}:{variant_index}:"
                    f"{_slug(query)}"
                ),
                field="source_candidates",
                label="Tavily query variant",
                summary=(
                    f"Planned search `{query}` using {candidate['search_mode']}; "
                    "human review required before any proof debt changes."
                ),
                source_refs=[
                    f"tavily.evidence_candidates[{index - 1}].query_variants[{variant_index - 1}]",
                    "tavily.query_plan_summary",
                ],
                next_human_action=next_human_action,
            )
            nodes.append(query_node)
            edges.append(
                ProofEdge(
                    edge_id=f"edge:{query_node.node_id}:to:{candidate_node.node_id}:supports_review",
                    edge_type="supports_review",
                    from_node_id=query_node.node_id,
                    to_node_id=candidate_node.node_id,
                    packet_field="source_candidates",
                )
            )

        quality = candidate["source_quality"]
        quality_node = _sponsor_proof_node(
            provider="tavily",
            node_id=f"proof:tavily:source_quality:{index}:{candidate_slug}",
            field="source_candidates",
            label="Tavily source quality",
            summary=(
                f"source_count={quality['source_count']}; "
                f"unique_sources={quality['unique_source_count']}; "
                f"domain_diversity={quality['diversity_score']}; "
                f"trust_tiers={quality['trust_tiers']}."
            ),
            source_refs=[
                f"tavily.evidence_candidates[{index - 1}].source_quality",
                "tavily.source_quality_summary",
            ],
            next_human_action=next_human_action,
        )
        nodes.append(quality_node)
        edges.append(
            ProofEdge(
                edge_id=f"edge:{quality_node.node_id}:to:{candidate_node.node_id}:supports_review",
                edge_type="supports_review",
                from_node_id=quality_node.node_id,
                to_node_id=candidate_node.node_id,
                packet_field="source_candidates",
            )
        )

        for source_index, source in enumerate(candidate.get("source_notes", []), start=1):
            source_node = _sponsor_proof_node(
                provider="tavily",
                node_id=f"proof:tavily:source:{index}:{source_index}:{_slug(source['domain'])}",
                field="source_candidates",
                label=f"Tavily source: {source['domain']}",
                summary=(
                    f"{source['title']} ({source['trust_tier']}); "
                    f"url={source['url']}; score={source.get('score')}."
                ),
                source_refs=[
                    f"tavily.evidence_candidates[{index - 1}].source_notes[{source_index - 1}]",
                    source["url"],
                ],
                next_human_action=next_human_action,
            )
            nodes.append(source_node)
            edges.append(
                ProofEdge(
                    edge_id=f"edge:{source_node.node_id}:to:{candidate_node.node_id}:supports_review",
                    edge_type="supports_review",
                    from_node_id=source_node.node_id,
                    to_node_id=candidate_node.node_id,
                    packet_field="source_candidates",
                )
            )

    return tuple(nodes), tuple(edges), _tavily_evidence_summary(tavily)


def _portkey_guardrail_summary(proof_loop: dict[str, Any]) -> dict[str, Any]:
    call = proof_loop["portkey_call"]
    truth = proof_loop["packet_truth"]
    policy = proof_loop["portkey_policy_preview"]
    invariants = proof_loop["invariants"]
    return {
        "schema_version": PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION,
        "provider": "portkey",
        "mode": "deterministic_fallback",
        "delivery_mode": proof_loop["delivery_mode"],
        "webhook_path": call["path"],
        "auth_required": bool(call["auth_required"]),
        "webhook_records_event": bool(call["event_recording"]["webhook_records_event"]),
        "preview_written_to_ledger": bool(call["event_recording"]["preview_written_to_ledger"]),
        "response_verdict": bool(call["response_verdict"]),
        "reason": truth.get("reason"),
        "deny_reason_count": len(truth.get("deny_reasons", [])),
        "policy_preview_mode": policy["mode"],
        "api_call_made": bool(policy["api_call_made"]),
        "portkey_api_call_made": bool(invariants["portkey_api_call_made"]),
        "portkey_policy_mutation_allowed": bool(invariants["portkey_policy_mutation_allowed"]),
        "packet_remains_authority": bool(invariants["packet_remains_authority"]),
        "raw_agent_intent_trusted": bool(invariants["raw_agent_intent_trusted"]),
        "live_portkey_mutation_enabled": bool(invariants["live_portkey_mutation_enabled"]),
        "preview_does_not_write_ledger": bool(invariants["preview_does_not_write_ledger"]),
        "human_review_required": True,
        "docs_reference": proof_loop["docs_reference"],
        "safety_impact": "none",
    }


def _portkey_guardrail_nodes(
    *,
    scenario_name: str,
    next_human_action: str,
) -> tuple[tuple[ProofNode, ...], tuple[ProofEdge, ...], dict[str, Any]]:
    proof_loop = build_portkey_guardrail_proof_loop(
        fixture=scenario_name,
        requested_mode="model_request",
    )
    call = proof_loop["portkey_call"]
    truth = proof_loop["packet_truth"]
    policy = proof_loop["portkey_policy_preview"]
    usage_policy = policy["usage_policy_plan"]["request_body"]

    webhook_node = _sponsor_proof_node(
        provider="portkey",
        node_id="proof:portkey:byo_guardrail_webhook",
        field="downstream_verdict",
        label="Portkey BYO guardrail webhook",
        summary=(
            f"{call['method']} {call['path']} accepts {call['event_type']} with auth. "
            f"IA returns a packet-backed verdict={call['response_verdict']}."
        ),
        source_refs=[
            "portkey_guardrail_proof_loop.portkey_call",
            proof_loop["docs_reference"]["guardrail_webhook"],
        ],
        next_human_action=next_human_action,
    )
    verdict_node = _sponsor_proof_node(
        provider="portkey",
        node_id="proof:portkey:packet_backed_verdict",
        field="downstream_verdict",
        label="Portkey packet-backed verdict",
        summary=(
            f"verdict={truth['verdict']}; reason={truth.get('reason')}; "
            f"deny_reasons={len(truth.get('deny_reasons', []))}; "
            "raw agent intent is not trusted."
        ),
        source_refs=[
            "portkey_guardrail_proof_loop.packet_truth",
            "portkey_guardrail_proof_loop.ia_packet_reference",
        ],
        next_human_action=next_human_action,
    )
    policy_node = _sponsor_proof_node(
        provider="portkey",
        node_id="proof:portkey:policy_preview",
        field="safety_invariants",
        label="Portkey policy preview",
        summary=(
            f"mode={policy['mode']}; api_call_made={policy['api_call_made']}; "
            f"credit_limit={usage_policy['credit_limit']}; no Portkey policy mutation."
        ),
        source_refs=[
            "portkey_guardrail_proof_loop.portkey_policy_preview",
            "portkey_guardrail_proof_loop.invariants",
        ],
        next_human_action=next_human_action,
    )
    edges = (
        ProofEdge(
            edge_id=f"edge:{verdict_node.node_id}:to:{webhook_node.node_id}:observed_by_downstream",
            edge_type="observed_by_downstream",
            from_node_id=verdict_node.node_id,
            to_node_id=webhook_node.node_id,
            packet_field="downstream_verdict",
        ),
        ProofEdge(
            edge_id=f"edge:{policy_node.node_id}:to:{webhook_node.node_id}:supports_review",
            edge_type="supports_review",
            from_node_id=policy_node.node_id,
            to_node_id=webhook_node.node_id,
            packet_field="safety_invariants",
        ),
    )
    return (webhook_node, verdict_node, policy_node), edges, _portkey_guardrail_summary(proof_loop)


def _edge_for_node(packet_node_id: str, node: ProofNode) -> ProofEdge:
    edge_type: EdgeType = "attaches_to_packet_field"
    if node.attached_packet_field == "blocked_claims":
        edge_type = "blocks_action"
    elif node.attached_packet_field in {"reviewer_routing", "next_human_action"}:
        edge_type = "requires_human_owner"
    elif node.attached_packet_field == "safety_invariants":
        edge_type = "supports_review"
    return ProofEdge(
        edge_id=f"edge:{node.node_id}:to:{packet_node_id}:{edge_type}",
        edge_type=edge_type,
        from_node_id=node.node_id,
        to_node_id=packet_node_id,
        packet_field=node.attached_packet_field,
    )


def _graph_invariants(nodes: tuple[ProofNode, ...], edges: tuple[ProofEdge, ...]) -> dict[str, bool]:
    return {
        "packet_remains_authority": True,
        "graph_can_approve": False,
        "graph_can_mutate_packet": False,
        "graph_can_execute_external_write": False,
        "graph_can_change_verdict": False,
        "all_nodes_require_human_review": all(node.human_review_required for node in nodes),
        "all_nodes_non_mutating": all(
            not node.external_write_made and not node.can_change_packet_verdict for node in nodes
        ),
        "all_edges_non_mutating": all(not edge.can_change_packet_verdict for edge in edges),
    }


def build_proof_graph(
    packet: dict[str, Any],
    *,
    scenario_name: str = DEFAULT_SCENARIO,
    include_tavily_evidence: bool = False,
    include_composio_blast_radius: bool = False,
    include_openclaw_runtime_trace: bool = False,
    include_nebius_reviewer_synthesis: bool = False,
    include_portkey_guardrail: bool = False,
    include_all_sponsor_proof: bool = False,
) -> dict[str, Any]:
    """Build a ProofGraph from one DecisionPacket."""
    if include_all_sponsor_proof:
        include_tavily_evidence = True
        include_composio_blast_radius = True
        include_openclaw_runtime_trace = True
        include_nebius_reviewer_synthesis = True
        include_portkey_guardrail = True

    snapshot = build_packet_authority_snapshot_for_scenario(packet, scenario_name)
    next_action = _next_human_action(packet)
    decision = packet.get("decision", {})
    packet_node = PacketNode(
        node_id=f"packet:{snapshot['packet_id']}",
        packet_id=snapshot["packet_id"],
        revision_id=snapshot["revision_id"],
        content_hash=snapshot["content_hash"],
        decision_lock=derive_decision_lock(packet),
        verdict=_first_text(decision.get("verdict")),
        review_posture=_first_text(decision.get("review_posture")),
        next_human_action=next_action,
        safety_state=_packet_safety(packet),
    )
    packet_proof_nodes = _packet_only_nodes(packet, next_human_action=next_action)
    tavily_nodes: tuple[ProofNode, ...] = ()
    tavily_edges: tuple[ProofEdge, ...] = ()
    tavily_summary: dict[str, Any] | None = None
    composio_nodes: tuple[ProofNode, ...] = ()
    composio_edges: tuple[ProofEdge, ...] = ()
    composio_summary: dict[str, Any] | None = None
    openclaw_nodes: tuple[ProofNode, ...] = ()
    openclaw_edges: tuple[ProofEdge, ...] = ()
    openclaw_summary: dict[str, Any] | None = None
    nebius_nodes: tuple[ProofNode, ...] = ()
    nebius_edges: tuple[ProofEdge, ...] = ()
    nebius_summary: dict[str, Any] | None = None
    portkey_nodes: tuple[ProofNode, ...] = ()
    portkey_edges: tuple[ProofEdge, ...] = ()
    portkey_summary: dict[str, Any] | None = None
    if include_tavily_evidence:
        tavily_nodes, tavily_edges, tavily_summary = _tavily_evidence_nodes(
            packet,
            scenario_name=scenario_name,
            next_human_action=next_action,
        )
    if include_composio_blast_radius:
        composio_nodes, composio_edges, composio_summary = _composio_blast_radius_nodes(
            packet,
            scenario_name=scenario_name,
            next_human_action=next_action,
        )
    if include_openclaw_runtime_trace:
        openclaw_nodes, openclaw_edges, openclaw_summary = _openclaw_runtime_trace_nodes(
            scenario_name=scenario_name,
            next_human_action=next_action,
        )
    if include_nebius_reviewer_synthesis:
        nebius_nodes, nebius_edges, nebius_summary = _nebius_reviewer_synthesis_nodes(
            scenario_name=scenario_name,
            next_human_action=next_action,
        )
    if include_portkey_guardrail:
        portkey_nodes, portkey_edges, portkey_summary = _portkey_guardrail_nodes(
            scenario_name=scenario_name,
            next_human_action=next_action,
        )
    proof_nodes = (
        *packet_proof_nodes,
        *tavily_nodes,
        *composio_nodes,
        *openclaw_nodes,
        *nebius_nodes,
        *portkey_nodes,
    )
    packet_edges = tuple(_edge_for_node(packet_node.node_id, node) for node in proof_nodes)
    edges = (
        *packet_edges,
        *tavily_edges,
        *composio_edges,
        *openclaw_edges,
        *nebius_edges,
        *portkey_edges,
    )
    base_payload = {
        "schema_version": PROOF_GRAPH_SCHEMA_VERSION,
        "scenario_name": scenario_name,
        "packet_node": packet_node.to_dict(),
        "proof_nodes": [node.to_dict() for node in proof_nodes],
        "proof_edges": [edge.to_dict() for edge in edges],
        "invariants": _graph_invariants(proof_nodes, edges),
    }
    if tavily_summary:
        base_payload["tavily_evidence"] = tavily_summary
    if composio_summary:
        base_payload["composio_blast_radius"] = composio_summary
    if openclaw_summary:
        base_payload["openclaw_runtime_trace"] = openclaw_summary
    if nebius_summary:
        base_payload["nebius_reviewer_synthesis"] = nebius_summary
    if portkey_summary:
        base_payload["portkey_guardrail"] = portkey_summary
    digest = stable_sha256(base_payload)
    return {
        **base_payload,
        "graph_id": f"ia-proof-graph-{scenario_name}-{digest[:16]}-public-v0",
        "graph_revision_id": f"pgr_{digest[:16]}",
        "content_hash": f"sha256:{digest}",
        "generated_by": PROOF_GRAPH_GENERATED_BY,
        "mode": "offline_deterministic",
        "packet_reference": {
            "packet_id": snapshot["packet_id"],
            "revision_id": snapshot["revision_id"],
            "content_hash": snapshot["content_hash"],
        },
        "node_counts": {
            "packet": 1,
            "proof": len(proof_nodes),
            "edge": len(edges),
        },
        "safety_boundary": {
            "approves_access": False,
            "grants_permissions": False,
            "executes_external_writes": False,
            "mutates_packet": False,
            "mutates_production": False,
            "changes_verdict": False,
            "requires_human_review": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def build_proof_graph_for_scenario(
    scenario_name: str = DEFAULT_SCENARIO,
    *,
    include_tavily_evidence: bool = False,
    include_composio_blast_radius: bool = False,
    include_openclaw_runtime_trace: bool = False,
    include_nebius_reviewer_synthesis: bool = False,
    include_portkey_guardrail: bool = False,
    include_all_sponsor_proof: bool = False,
) -> dict[str, Any]:
    """Build a ProofGraph for a registered public access scenario."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    return build_proof_graph(
        build_scenario_packet(scenario_name),
        scenario_name=scenario_name,
        include_tavily_evidence=include_tavily_evidence,
        include_composio_blast_radius=include_composio_blast_radius,
        include_openclaw_runtime_trace=include_openclaw_runtime_trace,
        include_nebius_reviewer_synthesis=include_nebius_reviewer_synthesis,
        include_portkey_guardrail=include_portkey_guardrail,
        include_all_sponsor_proof=include_all_sponsor_proof,
    )


def proof_graph_to_pretty_json(graph: dict[str, Any]) -> str:
    return json.dumps(graph, indent=2, sort_keys=True)


def render_proof_graph_markdown(graph: dict[str, Any]) -> str:
    packet = graph["packet_reference"]
    invariants = graph["invariants"]
    lines = [
        "# ProofGraph",
        "",
        "Private engine, public proof.",
        "",
        f"- graph_id: `{graph['graph_id']}`",
        f"- graph_revision_id: `{graph['graph_revision_id']}`",
        f"- content_hash: `{graph['content_hash']}`",
        f"- packet_id: `{packet['packet_id']}`",
        f"- packet_revision_id: `{packet['revision_id']}`",
        f"- proof nodes: {graph['node_counts']['proof']}",
        f"- packet remains authority: {invariants['packet_remains_authority']}",
        f"- graph can approve: {invariants['graph_can_approve']}",
        f"- graph can mutate packet: {invariants['graph_can_mutate_packet']}",
        f"- graph can change verdict: {invariants['graph_can_change_verdict']}",
        "",
        "## Packet Proof Nodes",
        "",
    ]
    for node in graph["proof_nodes"]:
        lines.extend(
            [
                f"### {node['label']}",
                "",
                f"- provider: `{node['provider']}`",
                f"- mode: `{node['mode']}`",
                f"- attached field: `{node['attached_packet_field']}`",
                f"- api call made: {node['api_call_made']}",
                f"- fallback used: {node['fallback_used']}",
                f"- external write made: {node['external_write_made']}",
                f"- can change packet verdict: {node['can_change_packet_verdict']}",
                f"- human review required: {node['human_review_required']}",
                f"- summary: {node['summary']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.proof_graph",
        description="Build the ProofGraph v0 contract.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=sorted(SCENARIOS))
    parser.add_argument(
        "--include-tavily-evidence",
        action="store_true",
        help="Attach Tavily evidence query/source proof nodes without live calls.",
    )
    parser.add_argument(
        "--include-composio-blast-radius",
        action="store_true",
        help="Attach Composio dry-run blast-radius proof nodes without live calls or execute.",
    )
    parser.add_argument(
        "--include-openclaw-runtime-trace",
        action="store_true",
        help="Attach OpenClaw runtime trace proof nodes without live calls or execute.",
    )
    parser.add_argument(
        "--include-nebius-reviewer-synthesis",
        action="store_true",
        help="Attach Nebius reviewer synthesis proof nodes without live calls or verdict ownership.",
    )
    parser.add_argument(
        "--include-portkey-guardrail",
        action="store_true",
        help="Attach Portkey downstream guardrail proof nodes without Portkey API calls or policy mutation.",
    )
    parser.add_argument(
        "--include-all-sponsors",
        action="store_true",
        help=(
            "Attach Tavily, Composio, OpenClaw, Nebius, and Portkey proof nodes "
            "in one reviewer-friendly preset."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print the graph as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        graph = build_proof_graph_for_scenario(
            args.scenario,
            include_tavily_evidence=args.include_tavily_evidence,
            include_composio_blast_radius=args.include_composio_blast_radius,
            include_openclaw_runtime_trace=args.include_openclaw_runtime_trace,
            include_nebius_reviewer_synthesis=args.include_nebius_reviewer_synthesis,
            include_portkey_guardrail=args.include_portkey_guardrail,
            include_all_sponsor_proof=args.include_all_sponsors,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(proof_graph_to_pretty_json(graph) if args.json else render_proof_graph_markdown(graph))
    return 0


if __name__ == "__main__":
    sys.exit(main())
