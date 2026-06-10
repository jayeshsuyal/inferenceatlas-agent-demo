"""Sponsor Value Receipts for packet-bound proof contribution.

These receipts make sponsor/downstream value inspectable without changing the
IA Packet. Sponsors provide proof signals; IA converts them into packet
authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .packet_authority import stable_sha256
from .proof_graph import build_proof_graph_for_scenario
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS


SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION = "sponsor_value_receipts.v0"
SPONSOR_VALUE_RECEIPT_SCHEMA_VERSION = "sponsor_value_receipt.v0"
DEFAULT_SCENARIO = "support_triage_agent"
OUTPUT_STEM = "sponsor_value_receipts"
PROVIDER_ORDER = ("tavily", "composio", "openclaw", "nebius", "portkey")

PROVIDER_COPY = {
    "tavily": {
        "role": "Evidence search and freshness layer",
        "contribution_type": "source_candidate_planning",
        "sponsor_value": "Turns missing proof into query plans, source candidates, freshness labels, and reviewer-owned evidence slots.",
        "downstream_value": "Reviewers can see which evidence should be fetched before proof debt is reduced.",
        "what_stayed_blocked": "No proof debt is reduced and no access is approved from search output alone.",
    },
    "composio": {
        "role": "Tool permission blast-radius layer",
        "contribution_type": "dry_run_permission_diff",
        "sponsor_value": "Projects connector actions into blocked write/admin scopes before any tool executes.",
        "downstream_value": "Security and engineering can review the exact tool blast radius before granting scope.",
        "what_stayed_blocked": "Write-like and admin-like actions stay blocked before execution.",
    },
    "openclaw": {
        "role": "Runtime trace and blocked-action layer",
        "contribution_type": "runtime_trace_projection",
        "sponsor_value": "Shows the checkpoint timeline, attempted actions, policy decisions, and blocked outcomes.",
        "downstream_value": "Operators get an audit-shaped trace of what would happen without allowing the agent to act.",
        "what_stayed_blocked": "Attempted writes remain blocked and runtime traces cannot replace human review.",
    },
    "nebius": {
        "role": "Reviewer synthesis layer",
        "contribution_type": "locked_field_narration",
        "sponsor_value": "Drafts reviewer-facing summaries from locked packet facts while preserving verdict and safety state.",
        "downstream_value": "CFO, Security, CTO, and Legal readers get readable summaries without losing packet authority.",
        "what_stayed_blocked": "Narration cannot edit verdicts, blocked claims, safety state, or approval posture.",
    },
    "portkey": {
        "role": "Downstream guardrail consumer",
        "contribution_type": "packet_backed_guardrail_verdict",
        "sponsor_value": "Consumes IA packet truth as a guardrail verdict before model or spend movement.",
        "downstream_value": "Gateways can ask IA for a packet-backed allow/block answer instead of trusting raw agent intent.",
        "what_stayed_blocked": "IA does not push policy, call Portkey APIs, mutate Portkey state, or approve spend.",
    },
}


def _safety_boundary() -> dict[str, bool]:
    return {
        "can_approve": False,
        "can_grant_permissions": False,
        "can_execute_external_write": False,
        "can_mutate_packet": False,
        "can_change_verdict": False,
        "can_reduce_proof_debt_automatically": False,
        "requires_human_review": True,
    }


def _provider_summary(graph: dict[str, Any], provider: str) -> dict[str, Any]:
    if provider == "tavily":
        summary = graph["tavily_evidence"]
        return {
            "mode": summary["mode"],
            "api_call_made": summary["live_call_attempted"],
            "fallback_used": summary["fallback_used"],
            "query_count": summary["query_count"],
            "query_variant_count": summary["query_variant_count"],
            "source_url_count": summary["source_url_count"],
            "freshness_labels": summary["freshness_labels"],
            "can_reduce_proof_debt": summary["can_reduce_proof_debt"],
            "cannot_grant_access": summary["cannot_grant_access"],
        }
    if provider == "composio":
        summary = graph["composio_blast_radius"]
        return {
            "mode": summary["mode"],
            "api_call_made": summary["api_call_made"],
            "fallback_used": summary["fallback_used"],
            "tool_count": summary["tool_count"],
            "blocked_action_count": summary["blocked_action_count"],
            "write_like_action_count": summary["write_like_action_count"],
            "admin_like_action_count": summary["admin_like_action_count"],
            "max_risk_level": summary["max_risk_level"],
            "would_execute": summary["would_execute"],
        }
    if provider == "openclaw":
        summary = graph["openclaw_runtime_trace"]
        return {
            "mode": summary["mode"],
            "api_call_made": summary["api_call_made"],
            "fallback_used": summary["fallback_used"],
            "checkpoint_count": summary["checkpoint_count"],
            "attempted_action_count": summary["attempted_action_count"],
            "blocked_event_count": summary["blocked_event_count"],
            "runtime_write_attempted": summary["runtime_write_attempted"],
            "human_review_boundary_preserved": summary["human_review_boundary_preserved"],
        }
    if provider == "nebius":
        summary = graph["nebius_reviewer_synthesis"]
        return {
            "mode": summary["mode"],
            "api_call_made": summary["api_call_made"],
            "fallback_used": summary["fallback_used"],
            "locked_field_count": summary["locked_field_count"],
            "draft_output_count": summary["draft_output_count"],
            "required_anchors_present": summary["required_anchors_present"],
            "forbidden_phrases_present": summary["forbidden_phrases_present"],
            "can_change_verdict": summary["can_change_verdict"],
            "can_mutate_packet": summary["can_mutate_packet"],
        }
    if provider == "portkey":
        summary = graph["portkey_guardrail"]
        return {
            "mode": summary["mode"],
            "delivery_mode": summary["delivery_mode"],
            "webhook_path": summary["webhook_path"],
            "auth_required": summary["auth_required"],
            "api_call_made": summary["api_call_made"],
            "portkey_api_call_made": summary["portkey_api_call_made"],
            "portkey_policy_mutation_allowed": summary["portkey_policy_mutation_allowed"],
            "response_verdict": summary["response_verdict"],
            "reason": summary["reason"],
            "raw_agent_intent_trusted": summary["raw_agent_intent_trusted"],
        }
    raise ValueError(f"unsupported provider: {provider}")


def _receipt_id(graph: dict[str, Any], provider: str) -> str:
    seed = {
        "graph_revision_id": graph["graph_revision_id"],
        "packet_id": graph["packet_reference"]["packet_id"],
        "provider": provider,
        "schema_version": SPONSOR_VALUE_RECEIPT_SCHEMA_VERSION,
    }
    return f"svr_{provider}_{stable_sha256(seed)[:12]}"


def _build_receipt(graph: dict[str, Any], provider: str) -> dict[str, Any]:
    nodes = [node for node in graph["proof_nodes"] if node["provider"] == provider]
    copy = PROVIDER_COPY[provider]
    safety = _safety_boundary()
    return {
        "schema_version": SPONSOR_VALUE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id(graph, provider),
        "provider": provider,
        "role": copy["role"],
        "contribution_type": copy["contribution_type"],
        "sponsor_value": copy["sponsor_value"],
        "downstream_value": copy["downstream_value"],
        "what_stayed_blocked": copy["what_stayed_blocked"],
        "proof_node_count": len(nodes),
        "attached_packet_fields": sorted({node["attached_packet_field"] for node in nodes}),
        "source_refs": sorted({ref for node in nodes for ref in node["source_refs"]})[:12],
        "key_metrics": _provider_summary(graph, provider),
        "ia_authority_boundary": "Provider proof can inform review, but IA Packet identity, decision lock, verdict, and next human action remain authoritative.",
        "safety_boundary": safety,
    }


def build_sponsor_value_receipts(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    """Build sponsor value receipts from the all-sponsor ProofGraph."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")

    graph = build_proof_graph_for_scenario(scenario_name, include_all_sponsor_proof=True)
    receipts = [_build_receipt(graph, provider) for provider in PROVIDER_ORDER]
    digest_seed = {
        "schema_version": SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION,
        "graph_content_hash": graph["content_hash"],
        "receipt_ids": [receipt["receipt_id"] for receipt in receipts],
    }
    safety = {
        "packet_remains_authority": graph["invariants"]["packet_remains_authority"],
        "all_receipts_require_human_review": all(
            receipt["safety_boundary"]["requires_human_review"] for receipt in receipts
        ),
        "all_receipts_non_approving": all(not receipt["safety_boundary"]["can_approve"] for receipt in receipts),
        "all_receipts_non_granting": all(
            not receipt["safety_boundary"]["can_grant_permissions"] for receipt in receipts
        ),
        "all_receipts_non_executing": all(
            not receipt["safety_boundary"]["can_execute_external_write"] for receipt in receipts
        ),
        "all_receipts_non_mutating": all(not receipt["safety_boundary"]["can_mutate_packet"] for receipt in receipts),
        "all_receipts_preserve_verdict": all(
            not receipt["safety_boundary"]["can_change_verdict"] for receipt in receipts
        ),
        "all_receipts_non_auto_reducing": all(
            not receipt["safety_boundary"]["can_reduce_proof_debt_automatically"] for receipt in receipts
        ),
    }
    digest = stable_sha256(digest_seed)
    return {
        "schema_version": SPONSOR_VALUE_RECEIPTS_SCHEMA_VERSION,
        "receipt_set_id": f"ia-sponsor-value-receipts-{scenario_name}-{digest[:16]}-public-v0",
        "generated_by": "inferenceatlas-agent-demo",
        "scenario": scenario_name,
        "headline": "Sponsors provide proof signals. IA converts them into packet authority.",
        "graph_reference": {
            "graph_id": graph["graph_id"],
            "graph_revision_id": graph["graph_revision_id"],
            "content_hash": graph["content_hash"],
        },
        "packet_reference": graph["packet_reference"],
        "summary": {
            "provider_count": len(PROVIDER_ORDER),
            "receipt_count": len(receipts),
            "providers": list(PROVIDER_ORDER),
            "proof_node_count": graph["node_counts"]["proof"],
            "proof_edge_count": graph["node_counts"]["edge"],
        },
        "safety": safety,
        "receipts": receipts,
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def sponsor_value_receipts_have_failures(payload: dict[str, Any]) -> bool:
    safety = payload["safety"]
    return (
        not safety["packet_remains_authority"]
        or not safety["all_receipts_require_human_review"]
        or not safety["all_receipts_non_approving"]
        or not safety["all_receipts_non_granting"]
        or not safety["all_receipts_non_executing"]
        or not safety["all_receipts_non_mutating"]
        or not safety["all_receipts_preserve_verdict"]
        or not safety["all_receipts_non_auto_reducing"]
        or payload["private_boundary"]["private_source_exposed"]
    )


def sponsor_value_receipts_to_pretty_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def render_sponsor_value_receipts_markdown(payload: dict[str, Any]) -> str:
    safety = payload["safety"]
    summary = payload["summary"]
    lines = [
        "# Sponsor Value Receipts",
        "",
        "Private engine, public proof.",
        "",
        payload["headline"],
        "",
        "Each receipt explains what a sponsor or downstream system contributed, what stayed blocked, and why the IA Packet remains the authority.",
        "",
        "## Summary",
        "",
        f"- scenario: `{payload['scenario']}`",
        f"- receipt_set_id: `{payload['receipt_set_id']}`",
        f"- packet_id: `{payload['packet_reference']['packet_id']}`",
        f"- graph_id: `{payload['graph_reference']['graph_id']}`",
        f"- providers: {', '.join(summary['providers'])}",
        f"- proof nodes: {summary['proof_node_count']}",
        f"- proof edges: {summary['proof_edge_count']}",
        "",
        "## Safety",
        "",
        f"- packet remains authority: {safety['packet_remains_authority']}",
        f"- all require human review: {safety['all_receipts_require_human_review']}",
        f"- all non-approving: {safety['all_receipts_non_approving']}",
        f"- all non-granting: {safety['all_receipts_non_granting']}",
        f"- all non-executing: {safety['all_receipts_non_executing']}",
        f"- all non-mutating: {safety['all_receipts_non_mutating']}",
        f"- all preserve verdict: {safety['all_receipts_preserve_verdict']}",
        "",
        "## Receipts",
        "",
        "| Provider | Role | Contribution | Stayed Blocked | Proof Nodes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for receipt in payload["receipts"]:
        lines.append(
            "| {provider} | {role} | {contribution} | {blocked} | {nodes} |".format(
                provider=receipt["provider"],
                role=receipt["role"],
                contribution=receipt["sponsor_value"],
                blocked=receipt["what_stayed_blocked"],
                nodes=receipt["proof_node_count"],
            )
        )
    lines.extend(
        [
            "",
            "## Authority Boundary",
            "",
            "Provider proof can inform review, but IA Packet identity, decision lock, verdict, and next human action remain authoritative.",
            "",
        ]
    )
    return "\n".join(lines)


def write_sponsor_value_receipts_artifacts(
    scenario_name: str = DEFAULT_SCENARIO,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write Sponsor Value Receipt Markdown and JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_sponsor_value_receipts(scenario_name)
    md_path = output_dir / f"{OUTPUT_STEM}.md"
    json_path = output_dir / f"{OUTPUT_STEM}.json"
    md_path.write_text(render_sponsor_value_receipts_markdown(payload), encoding="utf-8")
    json_path.write_text(sponsor_value_receipts_to_pretty_json(payload) + "\n", encoding="utf-8")
    return [md_path, json_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.sponsor_value_receipts",
        description="Generate Sponsor Value Receipts from the all-sponsor ProofGraph.",
    )
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO, choices=sorted(SCENARIOS))
    parser.add_argument("--output-dir", type=Path, default=GENERATED_DIR, help="Output directory for artifacts.")
    parser.add_argument("--json", action="store_true", help="Print the receipts as machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Skip writing artifacts and print only.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_sponsor_value_receipts(args.scenario)

    if not args.no_write:
        paths = write_sponsor_value_receipts_artifacts(args.scenario, args.output_dir)
        if not args.json:
            for path in paths:
                print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)

    if args.json:
        print(sponsor_value_receipts_to_pretty_json(payload))
    elif args.no_write:
        print(render_sponsor_value_receipts_markdown(payload))
    return 1 if sponsor_value_receipts_have_failures(payload) else 0


if __name__ == "__main__":
    sys.exit(main())
