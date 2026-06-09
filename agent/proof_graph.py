"""ProofGraph v0 for packet-authority proof provenance.

The ProofGraph is the shared object sponsor proof attaches to. In this first
slice it is intentionally packet-only: no live calls, no sponsor-specific
nodes, no approval, no writes, and no packet mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Literal

from .packet_authority import (
    build_packet_authority_snapshot_for_scenario,
    derive_decision_lock,
    stable_sha256,
)
from .scenarios import SCENARIOS, build_scenario_packet


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


def build_proof_graph(packet: dict[str, Any], *, scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    """Build a packet-only ProofGraph from one DecisionPacket."""
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
    proof_nodes = _packet_only_nodes(packet, next_human_action=next_action)
    edges = tuple(_edge_for_node(packet_node.node_id, node) for node in proof_nodes)
    base_payload = {
        "schema_version": PROOF_GRAPH_SCHEMA_VERSION,
        "scenario_name": scenario_name,
        "packet_node": packet_node.to_dict(),
        "proof_nodes": [node.to_dict() for node in proof_nodes],
        "proof_edges": [edge.to_dict() for edge in edges],
        "invariants": _graph_invariants(proof_nodes, edges),
    }
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


def build_proof_graph_for_scenario(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    """Build a ProofGraph for a registered public access scenario."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    return build_proof_graph(build_scenario_packet(scenario_name), scenario_name=scenario_name)


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
        description="Build the packet-only ProofGraph v0 contract.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=sorted(SCENARIOS))
    parser.add_argument("--json", action="store_true", help="Print the graph as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        graph = build_proof_graph_for_scenario(args.scenario)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(proof_graph_to_pretty_json(graph) if args.json else render_proof_graph_markdown(graph))
    return 0


if __name__ == "__main__":
    sys.exit(main())
