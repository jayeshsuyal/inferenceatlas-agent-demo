"""Trust Receipt and Review Room projections for agent-access reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .adapters import ADAPTER_NAMES, build_all_adapter_results
from .contract import validate_all
from .gate import evaluate_all as evaluate_policy_gates
from .scenarios import (
    GENERATED_DIR,
    ROOT_DIR,
    SCENARIOS,
    build_scenario_brief,
    build_scenario_packet,
)


TRUST_RECEIPT_SCHEMA_VERSION = "agent_trust_receipt.v0"
REVIEW_ROOM_SCHEMA_VERSION = "agent_access_review_room.v0"
TRUST_RECEIPT_ID = "ia-agent-trust-receipt-public-v0"
REVIEW_ROOM_ID = "ia-agent-access-review-room-public-v0"

RISK_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _pretty_json(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def _stable_hash(item: dict[str, Any]) -> str:
    encoded = json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _highest_risk(packet: dict[str, Any]) -> str:
    risk_levels = [item["risk_level"] for item in packet["requested_capability"]]
    return max(risk_levels, key=lambda level: RISK_RANK[level])


def _blast_radius_tier(highest_risk: str) -> str:
    if highest_risk == "critical":
        return "critical_admin_or_production_write"
    if highest_risk == "high":
        return "medium_high_cross_system_workflow"
    return "low_read_only_or_bounded_scope"


def _scenario_summary(scenario_name: str, packet: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    request = SCENARIOS[scenario_name]
    highest_risk = _highest_risk(packet)
    return {
        "scenario": scenario_name,
        "agent_name": request.agent_name,
        "purpose": request.purpose,
        "environment": request.environment,
        "packet_id": packet["packet_id"],
        "brief_id": brief["brief_id"],
        "highest_risk": highest_risk,
        "blast_radius_tier": _blast_radius_tier(highest_risk),
        "requested_systems": [item["system"] for item in packet["requested_capability"]],
        "verdict": packet["decision"]["verdict"],
        "review_posture": packet["decision"]["review_posture"],
        "production_access": brief["go_no_go"]["production_access"],
        "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
        "external_writes": brief["go_no_go"]["external_writes"],
        "composio_dry_run": brief["go_no_go"]["composio_dry_run"],
        "write_access": packet["approval_posture"]["write_access"],
        "missing_proof_count": len(packet["missing_proof"]),
        "reviewer_gate_count": len(brief["reviewer_gates"]),
    }


def _tool_runtime_plan(packet: dict[str, Any]) -> list[dict[str, Any]]:
    plans = []
    for tool_name, plan in packet["tool_access_plan"].items():
        plans.append(
            {
                "tool": tool_name,
                "demo_allowance": plan["demo_allowance"],
                "blocked_actions": plan["blocked_actions"],
                "required_proof": plan["required_proof"],
            }
        )
    return plans


def _build_permission_envelope(packets: dict[str, dict[str, Any]], briefs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    allowed = []
    blocked_validation = []
    blocked_production = []
    dry_run = []
    for scenario_name, brief in briefs.items():
        envelope = brief["access_envelope"]
        allowed.extend(f"{scenario_name}: {item}" for item in envelope["allowed_for_validation"])
        blocked_validation.extend(f"{scenario_name}: {item}" for item in envelope["blocked_in_validation"])
        blocked_production.extend(envelope["blocked_before_production"])
    for scenario_name, packet in packets.items():
        dry_run.extend(
            f"{scenario_name}: {item['tool']} -> {item['demo_allowance']}"
            for item in _tool_runtime_plan(packet)
        )
    return {
        "allowed_for_validation": _unique(allowed),
        "dry_run_only": _unique(dry_run),
        "blocked_in_validation": _unique(blocked_validation),
        "blocked_before_production": _unique(blocked_production),
        "never_allowed_in_public_demo": [
            "production access grant",
            "external writes",
            "tool permission expansion without a new packet",
            "compliance, safety, readiness, or savings claims without named proof",
            "live sponsor action without explicit non-default enablement",
        ],
    }


def _build_proof_debt_ledger(packets: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    ledger = []
    for scenario_name, packet in packets.items():
        for proof in packet["missing_proof"]:
            ledger.append(
                {
                    "scenario": scenario_name,
                    "item": proof["item"],
                    "owner": proof["owner"],
                    "unblocks": proof["unblocks"],
                    "status": "missing",
                }
            )
    return ledger


def _build_reviewer_routing(briefs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_owner: dict[str, dict[str, Any]] = {}
    for scenario_name, brief in briefs.items():
        for gate in brief["reviewer_gates"]:
            owner = gate["owner"]
            route = by_owner.setdefault(owner, {"owner": owner, "scenarios": [], "gates": []})
            if scenario_name not in route["scenarios"]:
                route["scenarios"].append(scenario_name)
            route["gates"].append(
                {
                    "scenario": scenario_name,
                    "gate": gate["gate"],
                    "blocks": gate["blocks"],
                    "required_before": gate["required_before"],
                }
            )
    return list(by_owner.values())


def _build_sponsor_runtime_plan() -> dict[str, dict[str, Any]]:
    return {
        "composio": {
            "role": "tool access planner and dry-run action surface",
            "public_default": "dry_run_only",
            "must_not_do": "execute writes or grant tool permissions by default",
            "receipt_field": "permission_envelope.dry_run_only",
        },
        "tavily": {
            "role": "evidence candidate source for current security, vendor, and policy context",
            "public_default": "evidence_notes_only",
            "must_not_do": "turn search results into approval or production readiness",
            "receipt_field": "evidence_plan",
        },
        "nebius": {
            "role": "optional inference layer for reviewer-ready narration",
            "public_default": "deterministic_fallback_without_key",
            "must_not_do": "own verdicts, blocked claims, or safety state",
            "receipt_field": "inference_plan",
        },
        "openclaw": {
            "role": "optional runtime trace harness for agent steps",
            "public_default": "trace_only",
            "must_not_do": "hide blocked attempts or bypass human approval",
            "receipt_field": "runtime_trace_plan",
        },
    }


def _sponsor_adapter_status() -> dict[str, Any]:
    scenario_results = {
        scenario_name: build_all_adapter_results(scenario_name)
        for scenario_name in SCENARIOS
    }
    provider_summary: dict[str, dict[str, Any]] = {}
    for provider in ADAPTER_NAMES:
        provider_results = [scenario_results[scenario_name][provider] for scenario_name in SCENARIOS]
        provider_summary[provider] = {
            "contract_version": provider_results[0]["contract_version"],
            "scenarios": list(SCENARIOS),
            "statuses": sorted({result["status"] for result in provider_results}),
            "requires_api_key": any(result["requires_api_key"] for result in provider_results),
            "would_execute": any(result["would_execute"] for result in provider_results),
            "can_approve_access": any(result["can_approve_access"] for result in provider_results),
            "can_grant_permissions": any(result["can_grant_permissions"] for result in provider_results),
            "can_mutate_external_state": any(result["can_mutate_external_state"] for result in provider_results),
            "receipt_fields": sorted({result["receipt_field"] for result in provider_results}),
            "proof_pack_types": sorted({result["proof_pack"]["proof_type"] for result in provider_results}),
            "human_review_required": all(result["human_review_required"] for result in provider_results),
            "value_added": provider_results[0]["proof_pack"]["value_added"],
        }
    return {
        "mode": "offline_dry_run_contract",
        "providers": provider_summary,
        "all_adapters_non_executing": all(not summary["would_execute"] for summary in provider_summary.values()),
        "all_adapters_non_approving": all(not summary["can_approve_access"] for summary in provider_summary.values()),
        "all_adapters_without_keys": all(not summary["requires_api_key"] for summary in provider_summary.values()),
    }


def _proof_contribution_count(result: dict[str, Any]) -> int:
    provider = result["provider"]
    if provider == "composio":
        return len(result["action_plans"])
    if provider == "tavily":
        return len(result["evidence_candidates"])
    if provider == "openclaw":
        return len(result["trace_steps"])
    return len(result.get("reviewer_narration_contract", {}).get("draft_outputs", []))


def _build_sponsor_proof_pack() -> dict[str, Any]:
    scenario_results = {
        scenario_name: build_all_adapter_results(scenario_name)
        for scenario_name in SCENARIOS
    }
    providers: dict[str, dict[str, Any]] = {}
    for provider in ADAPTER_NAMES:
        provider_results = [scenario_results[scenario_name][provider] for scenario_name in SCENARIOS]
        first = provider_results[0]
        proof_pack = first["proof_pack"]
        providers[provider] = {
            "proof_type": proof_pack["proof_type"],
            "value_added": proof_pack["value_added"],
            "visible_output": proof_pack["visible_output"],
            "reviewer_question": proof_pack["reviewer_question"],
            "cannot_do": proof_pack["cannot_do"],
            "human_review_required": all(result["human_review_required"] for result in provider_results),
            "scenarios": list(SCENARIOS),
            "contribution_count": sum(_proof_contribution_count(result) for result in provider_results),
            "would_execute": any(result["would_execute"] for result in provider_results),
            "can_approve_access": any(result["can_approve_access"] for result in provider_results),
            "can_grant_permissions": any(result["can_grant_permissions"] for result in provider_results),
            "can_mutate_external_state": any(result["can_mutate_external_state"] for result in provider_results),
        }
    return {
        "headline": "Sponsor tools enrich proof packets; they do not approve agents.",
        "mode": "offline_dry_run_contract",
        "providers": providers,
        "all_human_review_required": all(item["human_review_required"] for item in providers.values()),
        "all_non_executing": all(not item["would_execute"] for item in providers.values()),
        "all_non_approving": all(not item["can_approve_access"] for item in providers.values()),
    }


def _contract_status() -> dict[str, Any]:
    results = validate_all()
    return {
        "contract": "agent_access_public.v0",
        "status": "ok" if all(errors == [] for errors in results.values()) else "fail",
        "results": results,
    }


def _policy_gate_status() -> dict[str, Any]:
    results = evaluate_policy_gates()
    return {
        "policy": "policy/agent_access.yml",
        "policy_version": next(iter(results.values()))["policy_version"],
        "results": {
            scenario_name: {
                "decision": result["decision"],
                "reason": result["reason"],
                "triggered_rule_ids": [rule["rule_id"] for rule in result["triggered_rules"]],
            }
            for scenario_name, result in results.items()
        },
    }


def build_trust_receipt() -> dict[str, Any]:
    """Build the public Trust Receipt from all deterministic access-review scenarios."""
    packets = {scenario_name: build_scenario_packet(scenario_name) for scenario_name in SCENARIOS}
    briefs = {scenario_name: build_scenario_brief(scenario_name) for scenario_name in SCENARIOS}
    scenario_matrix = [
        _scenario_summary(scenario_name, packets[scenario_name], briefs[scenario_name])
        for scenario_name in SCENARIOS
    ]
    receipt: dict[str, Any] = {
        "schema_version": TRUST_RECEIPT_SCHEMA_VERSION,
        "trust_receipt_id": TRUST_RECEIPT_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "product_frame": {
            "name": "InferenceAtlas Agent Trust Gateway",
            "public_surface": "Agent Access Review Room",
            "receipt_name": "Trust Receipt",
            "one_line": "Pre-permission control plane for AI agent tool, data, spend, and production access.",
        },
        "agent_identity": {
            "subject": "public scenario set",
            "human_sponsor": "design_partner_named_owner_required",
            "environment": "prod",
            "identity_status": "not_connected_in_public_demo",
        },
        "scenario_matrix": scenario_matrix,
        "blast_radius_diff": [
            {
                "scenario": item["scenario"],
                "tier": item["blast_radius_tier"],
                "highest_risk": item["highest_risk"],
                "posture": item["review_posture"],
                "production_access": item["production_access"],
                "scoped_validation_review": item["scoped_validation_review"],
            }
            for item in scenario_matrix
        ],
        "permission_envelope": _build_permission_envelope(packets, briefs),
        "proof_debt_ledger": _build_proof_debt_ledger(packets),
        "reviewer_routing": _build_reviewer_routing(briefs),
        "sponsor_runtime_plan": _build_sponsor_runtime_plan(),
        "sponsor_proof_pack": _build_sponsor_proof_pack(),
        "sponsor_adapter_status": _sponsor_adapter_status(),
        "evidence_plan": {
            "default": "offline evidence notes only",
            "live_tavily_role": "source candidates and freshness signals",
            "guardrail": "evidence can reduce proof debt only after reviewer inspection",
        },
        "inference_plan": {
            "default": "deterministic packet and brief builders own truth",
            "live_nebius_role": "reviewer-ready narration and summary projection",
            "guardrail": "LLM output must not own verdicts, blocked claims, or safety state",
        },
        "runtime_trace_plan": {
            "default": "offline generated trace only",
            "live_openclaw_role": "record runtime steps and blocked/allowed outcomes",
            "guardrail": "runtime trace must preserve blocked access and human approval boundary",
        },
        "public_contract_status": _contract_status(),
        "policy_gate_status": _policy_gate_status(),
        "safety_state": {
            "approval_granted": False,
            "production_access_granted": False,
            "external_writes_enabled": False,
            "composio_dry_run": True,
            "packet_state_mutation": False,
            "requires_human_approval": True,
            "all_scenarios_production_blocked": all(
                item["production_access"] is False for item in scenario_matrix
            ),
        },
        "private_boundary": {
            "public_repo_role": "redacted judge harness and public proof surface",
            "private_source_exposed": False,
            "not_exposed": [
                "private v1 source code",
                "private prompts",
                "production routing logic",
                "private reviewer queues",
                "customer or workspace context",
                "live sponsor tokens",
                "account-specific tool grants",
            ],
            "principle": "Private engine, public proof.",
        },
        "design_partner_signal": {
            "pilot_shape": "one workflow, three representative agents, dry-run review, no production writes",
            "what_partner_validates": [
                "whether access requests become reviewable faster",
                "whether proof debt is routed to the right owners",
                "whether dry-run envelopes match security expectations",
                "whether sponsor/runtime/evidence traces help reviewers without approving access",
            ],
        },
        "derived_artifacts": {
            "review_room_html": "examples/generated/review_room.html",
            "review_room_markdown": "examples/generated/review_room.md",
            "review_room_json": "examples/generated/review_room.json",
            "review_room_screenshot": "examples/generated/review_room.desktop.jpg",
            "review_room_walkthrough": "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "trust_receipt_markdown": "examples/generated/trust_receipt.md",
            "trust_receipt_json": "examples/generated/trust_receipt.json",
        },
    }
    receipt["trust_receipt_hash"] = _stable_hash(receipt)
    return receipt


def build_review_room(receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the skim-ready public Review Room projection."""
    if receipt is None:
        receipt = build_trust_receipt()
    return {
        "schema_version": REVIEW_ROOM_SCHEMA_VERSION,
        "review_room_id": REVIEW_ROOM_ID,
        "generated_by": "inferenceatlas-agent-demo",
        "derived_from_trust_receipt_id": receipt["trust_receipt_id"],
        "trust_receipt_hash": receipt["trust_receipt_hash"],
        "title": "InferenceAtlas Agent Access Review Room",
        "headline": "Before an AI agent gets access, issue the Trust Receipt.",
        "copy_paste_commands": [
            "python3 -m agent.demo",
            "python3 -m agent.review --list",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m unittest discover -s tests",
        ],
        "first_artifacts_to_inspect": [
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.md",
            "examples/generated/review_room.html",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "policy/agent_access.yml",
            "agent/adapters/",
            "examples/generated/support_triage_agent.decision_brief.md",
            "examples/generated/admin_code_fix_bot.packet.json",
            "docs/CONTRACT.md",
        ],
        "product_loop": [
            "messy agent-access request",
            "deterministic rules engine",
            "scenario blast-radius diff",
            "DecisionPacket",
            "Agent Access Decision Brief",
            "Trust Receipt",
            "static Review Room HTML",
            "walkthrough-ready visual review",
            "public policy gate",
            "dry-run sponsor adapter contracts",
            "public contract validation",
            "optional sponsor/runtime/evidence enrichment",
        ],
        "scenario_matrix": receipt["scenario_matrix"],
        "permission_envelope": receipt["permission_envelope"],
        "proof_debt_summary": {
            "open_items": len(receipt["proof_debt_ledger"]),
            "owners": sorted({item["owner"] for item in receipt["proof_debt_ledger"]}),
        },
        "reviewer_routing_summary": [
            {
                "owner": item["owner"],
                "scenario_count": len(item["scenarios"]),
                "gate_count": len(item["gates"]),
            }
            for item in receipt["reviewer_routing"]
        ],
        "sponsor_runtime_plan": receipt["sponsor_runtime_plan"],
        "sponsor_proof_pack": receipt["sponsor_proof_pack"],
        "sponsor_adapter_status": receipt["sponsor_adapter_status"],
        "public_contract_status": receipt["public_contract_status"],
        "policy_gate_status": receipt["policy_gate_status"],
        "safety_state": receipt["safety_state"],
        "private_boundary": receipt["private_boundary"],
        "design_partner_signal": receipt["design_partner_signal"],
    }


def _bullet(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _scenario_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| Scenario | Risk | Validation | Production | Systems |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| {scenario} | {risk} | {validation} | {production} | {systems} |".format(
                scenario=item["scenario"],
                risk=item["highest_risk"],
                validation=item["scoped_validation_review"],
                production=item["production_access"],
                systems=", ".join(item["requested_systems"]),
            )
        )
    return "\n".join(lines)


def _proof_debt_lines(items: list[dict[str, str]]) -> str:
    lines = []
    for item in items:
        lines.append(
            "- {scenario}: {item} | owner: {owner} | unblocks: {unblocks}".format(
                scenario=item["scenario"],
                item=item["item"],
                owner=item["owner"],
                unblocks=item["unblocks"],
            )
        )
    return "\n".join(lines) if lines else "- None"


def _reviewer_routing_lines(items: list[dict[str, Any]]) -> str:
    lines = []
    for item in items:
        scenarios = ", ".join(item["scenarios"])
        gate_count = len(item["gates"])
        noun = "gate" if gate_count == 1 else "gates"
        lines.append(f"- **{item['owner']}**: {gate_count} {noun} across {scenarios}")
    return "\n".join(lines) if lines else "- None"


def _sponsor_plan_lines(items: dict[str, dict[str, Any]]) -> str:
    lines = []
    for sponsor, plan in items.items():
        lines.append(
            "- **{sponsor}**: {role}; default: {default}; guardrail: {guardrail}".format(
                sponsor=sponsor,
                role=plan["role"],
                default=plan["public_default"],
                guardrail=f"must not {plan['must_not_do']}",
            )
        )
    return "\n".join(lines)


def _sponsor_proof_pack_lines(items: dict[str, dict[str, Any]]) -> str:
    lines = []
    for sponsor, proof in items.items():
        cannot_do = ", ".join(proof["cannot_do"])
        lines.append(
            "- **{sponsor}** ({proof_type}): {value_added} Visible output: {visible}. "
            "Contributions: {count}; human review required: {review}; cannot: {cannot}.".format(
                sponsor=sponsor,
                proof_type=proof["proof_type"],
                value_added=proof["value_added"],
                visible=proof["visible_output"],
                count=proof["contribution_count"],
                review=proof["human_review_required"],
                cannot=cannot_do,
            )
        )
    return "\n".join(lines)


def render_trust_receipt_markdown(receipt: dict[str, Any]) -> str:
    """Render a Trust Receipt as Markdown."""
    envelope = receipt["permission_envelope"]
    safety = receipt["safety_state"]
    sections = [
        "# Trust Receipt: Agent Access Review",
        "",
        receipt["product_frame"]["one_line"],
        "",
        f"Receipt ID: `{receipt['trust_receipt_id']}`",
        "",
        f"Receipt hash: `{receipt['trust_receipt_hash']}`",
        "",
        "Private engine, public proof.",
        "",
        "## Scenario Blast-Radius Diff",
        "",
        _scenario_table(receipt["scenario_matrix"]),
        "",
        "## Permission Envelope",
        "",
        "Allowed for validation:",
        "",
        _bullet(envelope["allowed_for_validation"]),
        "",
        "Dry-run only:",
        "",
        _bullet(envelope["dry_run_only"]),
        "",
        "Blocked in validation:",
        "",
        _bullet(envelope["blocked_in_validation"]),
        "",
        "Blocked before production:",
        "",
        _bullet(envelope["blocked_before_production"]),
        "",
        "Never allowed in the public demo:",
        "",
        _bullet(envelope["never_allowed_in_public_demo"]),
        "",
        "## Proof Debt Ledger",
        "",
        _proof_debt_lines(receipt["proof_debt_ledger"]),
        "",
        "## Reviewer Routing",
        "",
        _reviewer_routing_lines(receipt["reviewer_routing"]),
        "",
        "## Sponsor Runtime Plan",
        "",
        _sponsor_plan_lines(receipt["sponsor_runtime_plan"]),
        "",
        "## Sponsor Proof Pack",
        "",
        receipt["sponsor_proof_pack"]["headline"],
        "",
        _sponsor_proof_pack_lines(receipt["sponsor_proof_pack"]["providers"]),
        "",
        "## Sponsor Adapter Status",
        "",
        _bullet(
            [
                (
                    f"{provider}: statuses={', '.join(summary['statuses'])}; "
                    f"would_execute={summary['would_execute']}; "
                    f"can_approve_access={summary['can_approve_access']}"
                )
                for provider, summary in receipt["sponsor_adapter_status"]["providers"].items()
            ]
        ),
        "",
        "## Public Contract Status",
        "",
        f"- contract: {receipt['public_contract_status']['contract']}",
        f"- status: {receipt['public_contract_status']['status']}",
        "",
        "## Policy Gate Status",
        "",
        f"- policy: {receipt['policy_gate_status']['policy']}",
        f"- policy version: {receipt['policy_gate_status']['policy_version']}",
        "",
        _bullet(
            [
                f"{scenario}: {result['decision']} ({', '.join(result['triggered_rule_ids'])})"
                for scenario, result in receipt["policy_gate_status"]["results"].items()
            ]
        ),
        "",
        "## Safety State",
        "",
        f"- approval granted: {safety['approval_granted']}",
        f"- production access granted: {safety['production_access_granted']}",
        f"- external writes enabled: {safety['external_writes_enabled']}",
        f"- Composio dry-run: {safety['composio_dry_run']}",
        f"- packet state mutation: {safety['packet_state_mutation']}",
        f"- requires human approval: {safety['requires_human_approval']}",
        f"- all scenarios production blocked: {safety['all_scenarios_production_blocked']}",
        "",
        "## Design Partner Signal",
        "",
        f"Pilot shape: {receipt['design_partner_signal']['pilot_shape']}",
        "",
        "What a partner validates:",
        "",
        _bullet(receipt["design_partner_signal"]["what_partner_validates"]),
        "",
        "## Private Boundary",
        "",
        f"- public repo role: {receipt['private_boundary']['public_repo_role']}",
        f"- private source exposed: {receipt['private_boundary']['private_source_exposed']}",
        f"- principle: {receipt['private_boundary']['principle']}",
        "",
    ]
    return "\n".join(sections)


def render_review_room_markdown(review_room: dict[str, Any]) -> str:
    """Render the Review Room as Markdown."""
    sections = [
        "# InferenceAtlas Agent Access Review Room",
        "",
        review_room["headline"],
        "",
        f"Trust Receipt hash: `{review_room['trust_receipt_hash']}`",
        "",
        "## Copy-Paste Review Commands",
        "",
        "```bash",
        "\n".join(review_room["copy_paste_commands"]),
        "```",
        "",
        "## Product Loop",
        "",
        _bullet(review_room["product_loop"]),
        "",
        "## Scenario Matrix",
        "",
        _scenario_table(review_room["scenario_matrix"]),
        "",
        "## Proof Debt Summary",
        "",
        f"- open items: {review_room['proof_debt_summary']['open_items']}",
        f"- owners: {', '.join(review_room['proof_debt_summary']['owners'])}",
        "",
        "## Reviewer Routing Summary",
        "",
        _bullet(
            [
                (
                    f"{item['owner']}: {item['gate_count']} "
                    f"{'gate' if item['gate_count'] == 1 else 'gates'} across "
                    f"{item['scenario_count']} "
                    f"{'scenario' if item['scenario_count'] == 1 else 'scenarios'}"
                )
                for item in review_room["reviewer_routing_summary"]
            ]
        ),
        "",
        "## First Artifacts To Inspect",
        "",
        _bullet(review_room["first_artifacts_to_inspect"]),
        "",
        "## Policy Gate Status",
        "",
        _bullet(
            [
                f"{scenario}: {result['decision']}"
                for scenario, result in review_room["policy_gate_status"]["results"].items()
            ]
        ),
        "",
        "## Sponsor Adapter Status",
        "",
        _bullet(
            [
                f"{provider}: {', '.join(summary['statuses'])}; would_execute={summary['would_execute']}"
                for provider, summary in review_room["sponsor_adapter_status"]["providers"].items()
            ]
        ),
        "",
        "## Sponsor Proof Pack",
        "",
        review_room["sponsor_proof_pack"]["headline"],
        "",
        _sponsor_proof_pack_lines(review_room["sponsor_proof_pack"]["providers"]),
        "",
        "## Safety State",
        "",
        _bullet([f"{key}: {value}" for key, value in review_room["safety_state"].items()]),
        "",
        "## Private Boundary",
        "",
        f"- private source exposed: {review_room['private_boundary']['private_source_exposed']}",
        f"- principle: {review_room['private_boundary']['principle']}",
        "",
    ]
    return "\n".join(sections)


def write_trust_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Write Trust Receipt and Review Room artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = build_trust_receipt()
    review_room = build_review_room(receipt)
    paths = [
        output_dir / "trust_receipt.md",
        output_dir / "trust_receipt.json",
        output_dir / "review_room.md",
        output_dir / "review_room.json",
    ]
    paths[0].write_text(render_trust_receipt_markdown(receipt), encoding="utf-8")
    paths[1].write_text(_pretty_json(receipt) + "\n", encoding="utf-8")
    paths[2].write_text(render_review_room_markdown(review_room), encoding="utf-8")
    paths[3].write_text(_pretty_json(review_room) + "\n", encoding="utf-8")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.trust",
        description="Generate the public InferenceAtlas Trust Receipt and Review Room artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory where Trust Receipt and Review Room artifacts should be written.",
    )
    parser.add_argument(
        "--print-json",
        choices=("trust_receipt", "review_room"),
        help="Print one artifact as JSON instead of writing files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_json:
        receipt = build_trust_receipt()
        artifact = receipt if args.print_json == "trust_receipt" else build_review_room(receipt)
        print(_pretty_json(artifact))
        return 0

    for path in write_trust_artifacts(args.output_dir):
        print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
