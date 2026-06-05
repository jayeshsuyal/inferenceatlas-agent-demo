"""One-command offline judge harness for the public proof surface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters import ADAPTER_NAMES, build_all_adapter_results
from .contract import validate_all
from .evidence_receipts import build_evidence_receipt_ledger
from .gate import evaluate_all
from .outcome_memo import build_packet_outcome_memo, write_packet_outcome_memo_artifacts
from .packet import build_support_triage_trace
from .packet_authority import build_packet_authority_snapshot_for_scenario
from .packet_diff import build_packet_diff_report, write_packet_diff_artifacts
from .pilot_memo import PILOT_MEMO_SAFETY_ANCHOR, build_pilot_memo, write_pilot_memo_artifacts
from .proof_health import build_proof_health_report, write_proof_health_artifacts
from .renderers import render_trace_markdown
from .review_room import write_review_room_html
from .scenarios import GENERATED_DIR, ROOT_DIR, SCENARIOS, build_scenario_packet, write_scenario_artifacts
from .sponsor_readiness import build_sponsor_live_readiness, write_sponsor_live_readiness_artifacts
from .spend import SPEND_SCENARIO_ID, build_spend_review_bundle, write_spend_review_artifacts
from .trust import build_trust_receipt, write_trust_artifacts
from .trial import DEFAULT_TRIAL_REQUEST, build_trial_report, write_trial_artifacts
from .trial_evidence_replay import build_trial_evidence_replay, write_trial_evidence_replay_artifacts
from .trial_outcome_memo import build_trial_outcome_memo, write_trial_outcome_memo_artifacts
from .verification import build_verification_artifact


JUDGE_HARNESS_VERSION = "agent_judge_harness.v0"

JUDGE_COMMANDS = [
    "python3 -m agent.judge",
    "python3 -m agent.demo",
    "python3 -m agent.review --list",
    "python3 -m agent.skills",
    "python3 -m agent.packet_diff",
    "python3 -m agent.evidence_receipts",
    "python3 -m agent.packet_authority",
    "python3 -m agent.verification --all",
    "python3 -m agent.outcome_memo",
    "python3 -m agent.contract --all",
    "python3 -m agent.gate --all",
    "python3 -m agent.adapters --all",
    "python3 -m agent.sponsor_readiness",
    "python3 -m agent.trust",
    "python3 -m agent.review_room",
    "python3 -m agent.proof_health",
    "python3 -m agent.spend",
    "python3 -m agent.trial examples/requests/support_triage_trial.yml",
    "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
    "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
    "python3 -m agent.pilot_memo examples/requests/support_triage_trial.yml",
    "python3 -m unittest discover -s tests",
]

PRIMARY_ARTIFACTS = [
    "docs/PRODUCT_TOUR.md",
    "docs/AGENT_SKILLS.md",
    "docs/PRODUCT_QUALITY_AUDIT.md",
    "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
    "examples/generated/demo_transcript.md",
    "examples/generated/trust_receipt.md",
    "examples/generated/packet_diff.md",
    "examples/generated/packet_diff.json",
    "examples/generated/support_triage_agent.evidence_receipts.md",
    "examples/generated/support_triage_agent.evidence_receipts.json",
    "examples/generated/support_triage_agent.snapshot.json",
    "examples/generated/support_triage_agent.verification.json",
    "examples/generated/support_triage_agent.outcome_memo.md",
    "examples/generated/support_triage_agent.outcome_memo.json",
    "examples/generated/sponsor_live_readiness.md",
    "examples/generated/sponsor_live_readiness.json",
    "examples/generated/review_room.md",
    "examples/generated/review_room.html",
    "examples/generated/support_triage_agent.proof_health.md",
    "examples/generated/support_triage_agent.proof_health.json",
    "examples/generated/ai_spend_budget_overrun.spend_packet.md",
    "examples/generated/ai_spend_budget_overrun.spend_packet.json",
    "examples/generated/ai_spend_budget_overrun.finance_receipt.md",
    "examples/generated/ai_spend_budget_overrun.finance_receipt.json",
    "examples/generated/ai_spend_budget_overrun.procurement_memo.md",
    "examples/generated/ai_spend_budget_overrun.procurement_memo.json",
    "docs/REVIEW_ROOM_WALKTHROUGH.md",
    "docs/DESIGN_PARTNER_BRIEF.md",
    "docs/DESIGN_PARTNER_TRIAL_KIT.md",
    "examples/requests/design_partner_trial.yml",
    "examples/requests/support_triage_trial.yml",
    "examples/generated/support_triage_trial_report.md",
    "examples/generated/support_triage_trial_report.json",
    "examples/generated/support_triage_trial.packet.json",
    "examples/generated/support_triage_trial.decision_brief.json",
    "examples/generated/support_triage_trial.outcome_memo.md",
    "examples/generated/support_triage_trial.outcome_memo.json",
    "examples/generated/support_triage_trial.pilot_memo.md",
    "examples/generated/support_triage_trial.pilot_memo.json",
    "examples/generated/support_triage_trial.copy_review_brief.md",
    "schemas/pilot_memo.schema.json",
    "examples/generated/support_triage_trial.evidence_replay.md",
    "examples/generated/support_triage_trial.evidence_replay.json",
    "examples/generated/review_room.desktop.jpg",
    "policy/agent_access.yml",
    "agent/adapters/",
    "examples/generated/support_triage_agent.decision_brief.md",
    "examples/generated/support_triage_agent.packet.md",
    "examples/generated/admin_code_fix_bot.packet.json",
    "docs/CONTRACT.md",
    "docs/SAFETY_CONTRACT.md",
    "docs/V1_CAPABILITY_PASSPORT.md",
]


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _write_support_trace(output_dir: Path = GENERATED_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = build_support_triage_trace()
    trace_json = output_dir / "support_triage_agent.trace.json"
    trace_md = output_dir / "support_triage_agent.trace.md"
    trace_json.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    trace_md.write_text(render_trace_markdown(trace), encoding="utf-8")
    return [trace_json, trace_md]


def write_judge_artifacts(output_dir: Path = GENERATED_DIR) -> list[Path]:
    """Regenerate the offline public artifacts a judge should inspect."""
    written = []
    written.extend(write_scenario_artifacts(output_dir))
    written.extend(_write_support_trace(output_dir))
    written.extend(write_sponsor_live_readiness_artifacts(output_dir=output_dir))
    written.extend(write_trust_artifacts(output_dir))
    written.extend(write_packet_diff_artifacts(output_dir))
    written.extend(write_packet_outcome_memo_artifacts(output_dir=output_dir))
    written.append(write_review_room_html(output_dir))
    written.extend(write_proof_health_artifacts(output_dir=output_dir))
    written.extend(write_spend_review_artifacts(output_dir=output_dir))
    written.extend(write_trial_artifacts(DEFAULT_TRIAL_REQUEST, output_dir))
    written.extend(write_trial_outcome_memo_artifacts(DEFAULT_TRIAL_REQUEST, output_dir))
    written.extend(write_trial_evidence_replay_artifacts(DEFAULT_TRIAL_REQUEST, output_dir))
    written.extend(write_pilot_memo_artifacts(DEFAULT_TRIAL_REQUEST, output_dir))
    return written


def _adapter_summary() -> dict[str, dict[str, Any]]:
    scenario_results = {
        scenario_name: build_all_adapter_results(scenario_name)
        for scenario_name in SCENARIOS
    }
    summary: dict[str, dict[str, Any]] = {}
    for provider in ADAPTER_NAMES:
        provider_results = [scenario_results[scenario_name][provider] for scenario_name in SCENARIOS]
        summary[provider] = {
            "statuses": sorted({result["status"] for result in provider_results}),
            "proof_pack_types": sorted({result["proof_pack"]["proof_type"] for result in provider_results}),
            "human_review_required": all(result["human_review_required"] for result in provider_results),
            "would_execute": any(result["would_execute"] for result in provider_results),
            "can_approve_access": any(result["can_approve_access"] for result in provider_results),
            "can_grant_permissions": any(result["can_grant_permissions"] for result in provider_results),
            "can_mutate_external_state": any(result["can_mutate_external_state"] for result in provider_results),
        }
    return summary


def _artifact_status(paths: list[str]) -> list[dict[str, Any]]:
    statuses = []
    for item in paths:
        path = ROOT_DIR / item
        statuses.append(
            {
                "path": item,
                "exists": path.exists(),
                "kind": "directory" if path.is_dir() else "file",
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return statuses


def build_judge_report(*, write_artifacts: bool = True) -> dict[str, Any]:
    """Build a machine-readable judge report for the offline public harness."""
    written_paths = write_judge_artifacts() if write_artifacts else []
    contract_results = validate_all(generated_dir=GENERATED_DIR)
    gate_results = evaluate_all()
    adapter_summary = _adapter_summary()
    sponsor_readiness = build_sponsor_live_readiness()
    trust_receipt = build_trust_receipt()
    packet_diff = build_packet_diff_report()
    outcome_memo = build_packet_outcome_memo()
    trial_report = build_trial_report(DEFAULT_TRIAL_REQUEST)
    trial_outcome_memo = build_trial_outcome_memo(DEFAULT_TRIAL_REQUEST)
    trial_evidence_replay = build_trial_evidence_replay(DEFAULT_TRIAL_REQUEST)
    pilot_memo = build_pilot_memo(DEFAULT_TRIAL_REQUEST)
    proof_health = build_proof_health_report()
    spend_review = build_spend_review_bundle()
    primary_packet = build_scenario_packet("support_triage_agent")
    primary_receipt_ledger = build_evidence_receipt_ledger(primary_packet, "support_triage_agent")
    primary_snapshot = build_packet_authority_snapshot_for_scenario(primary_packet, "support_triage_agent")
    primary_verification = build_verification_artifact(primary_packet, snapshot=primary_snapshot)

    return {
        "schema_version": JUDGE_HARNESS_VERSION,
        "mode": "offline_deterministic",
        "generated_by": "inferenceatlas-agent-demo",
        "commands": JUDGE_COMMANDS,
        "written_artifacts": [_relative(path) for path in written_paths],
        "scenario_matrix": [
            {
                "scenario": scenario_name,
                "policy_gate_decision": gate_results[scenario_name]["decision"],
                "production_access": gate_results[scenario_name]["safety_state"]["production_access"],
                "scoped_validation_review": gate_results[scenario_name]["safety_state"]["scoped_validation_review"],
                "composio_dry_run": gate_results[scenario_name]["safety_state"]["composio_dry_run"],
                "approval_granted": gate_results[scenario_name]["safety_state"]["approval_granted"],
            }
            for scenario_name in SCENARIOS
        ],
        "packet_diff": {
            "scenario_count": packet_diff["summary"]["scenario_count"],
            "load_bearing_field_count": packet_diff["summary"]["load_bearing_field_count"],
            "differing_field_count": packet_diff["summary"]["differing_field_count"],
            "has_relaxed_read_only_lane": packet_diff["summary"]["has_relaxed_read_only_lane"],
            "has_proof_routed_lane": packet_diff["summary"]["has_proof_routed_lane"],
            "has_blocked_critical_lane": packet_diff["summary"]["has_blocked_critical_lane"],
            "all_production_access_blocked": packet_diff["summary"]["all_production_access_blocked"],
            "all_external_writes_blocked": packet_diff["summary"]["all_external_writes_blocked"],
        },
        "evidence_receipt_ledger": {
            "scenario": "support_triage_agent",
            "packet_id": primary_receipt_ledger["packet_id"],
            "decision_lock_before": primary_receipt_ledger["decision_lock_before"],
            "decision_lock_after": primary_receipt_ledger["decision_lock_after"],
            "receipt_count": primary_receipt_ledger["summary"]["receipt_count"],
            "tool_scope_receipts": primary_receipt_ledger["summary"]["tool_scope_receipts"],
            "proof_debt_receipts": primary_receipt_ledger["summary"]["proof_debt_receipts"],
            "reviewer_route_receipts": primary_receipt_ledger["summary"]["reviewer_route_receipts"],
            "cost_procurement_receipts": primary_receipt_ledger["summary"]["cost_procurement_receipts"],
            "all_require_human_review": primary_receipt_ledger["safety"]["all_require_human_review"],
            "all_non_approving": primary_receipt_ledger["safety"]["all_non_approving"],
            "all_non_granting": primary_receipt_ledger["safety"]["all_non_granting"],
            "all_non_executing": primary_receipt_ledger["safety"]["all_non_executing"],
            "all_non_mutating": primary_receipt_ledger["safety"]["all_non_mutating"],
            "all_non_auto_reducing": primary_receipt_ledger["safety"]["all_non_auto_reducing"],
            "budget_owner_required": primary_receipt_ledger["finance_procurement"]["budget_owner_required"],
            "token_or_tool_spend_cap_required": primary_receipt_ledger["finance_procurement"][
                "token_or_tool_spend_cap_required"
            ],
            "artifact": "examples/generated/support_triage_agent.evidence_receipts.md",
            "json_artifact": "examples/generated/support_triage_agent.evidence_receipts.json",
        },
        "packet_authority_snapshot": {
            "scenario": "support_triage_agent",
            "packet_id": primary_snapshot["packet_id"],
            "revision_id": primary_snapshot["revision_id"],
            "content_hash": primary_snapshot["content_hash"],
            "decision_lock_before": primary_snapshot["decision_lock_before"],
            "decision_lock_after": primary_snapshot["decision_lock_after"],
            "evidence_receipt_count": len(primary_snapshot["evidence_receipt_ids"]),
            "next_human_action": primary_snapshot["next_human_action"],
            "artifact": "examples/generated/support_triage_agent.snapshot.json",
        },
        "packet_verification": {
            "scenario": "support_triage_agent",
            "verification_status": primary_verification["verification_status"],
            "production_access": primary_verification["production_access"],
            "external_writes": primary_verification["external_writes"],
            "permission_grants": primary_verification["permission_grants"],
            "approval_granted": primary_verification["approval_granted"],
            "scoped_validation": primary_verification["scoped_validation"],
            "artifact": "examples/generated/support_triage_agent.verification.json",
        },
        "packet_outcome_memo": {
            "scenario": outcome_memo["scenario"],
            "decision_code": outcome_memo["decision"]["code"],
            "decision_summary": outcome_memo["decision"]["summary"],
            "policy_gate": outcome_memo["decision"]["policy_gate"],
            "production_access": outcome_memo["decision"]["production_access"],
            "scoped_validation_review": outcome_memo["decision"]["scoped_validation_review"],
            "external_writes": outcome_memo["decision"]["external_writes"],
            "proof_debt_assignment_count": len(outcome_memo["proof_debt_assignments"]),
            "reviewer_route_count": len(outcome_memo["reviewer_routes"]),
            "next_human_health_check": outcome_memo["packet_refresh"]["next_human_health_check"],
            "approves_access": outcome_memo["safety_boundary"]["approves_access"],
            "grants_permissions": outcome_memo["safety_boundary"]["grants_permissions"],
            "executes_external_writes": outcome_memo["safety_boundary"]["executes_external_writes"],
        },
        "access_speed_layer": trust_receipt["access_speed_layer"],
        "design_partner_trial": {
            "request_path": trial_report["request_path"],
            "request_readiness": trial_report["request_readiness"],
            "access_speed_lane": trial_report["access_speed_lane"]["lane"],
            "production_access": trial_report["decision_brief_summary"]["production_access"],
            "scoped_validation_review": trial_report["decision_brief_summary"]["scoped_validation_review"],
            "validation_errors": trial_report["validation"]["errors"],
            "approves_access": trial_report["safety"]["public_runner_approves_access"],
            "grants_permissions": trial_report["safety"]["public_runner_grants_permissions"],
            "executes_external_writes": trial_report["safety"]["public_runner_executes_external_writes"],
        },
        "design_partner_outcome_memo": {
            "request_path": trial_outcome_memo["request_path"],
            "decision_code": trial_outcome_memo["decision"]["code"],
            "decision_summary": trial_outcome_memo["decision"]["summary"],
            "access_speed_lane": trial_outcome_memo["decision"]["access_speed_lane"],
            "production_access": trial_outcome_memo["decision"]["production_access"],
            "scoped_validation_review": trial_outcome_memo["decision"]["scoped_validation_review"],
            "permission_grants": trial_outcome_memo["decision"]["permission_grants"],
            "external_writes": trial_outcome_memo["decision"]["external_writes"],
            "proof_debt_assignment_count": len(trial_outcome_memo["proof_debt_assignments"]),
            "reviewer_route_count": len(trial_outcome_memo["reviewer_routes"]),
            "approves_access": trial_outcome_memo["safety_boundary"]["approves_access"],
            "grants_permissions": trial_outcome_memo["safety_boundary"]["grants_permissions"],
            "executes_external_writes": trial_outcome_memo["safety_boundary"]["executes_external_writes"],
        },
        "design_partner_evidence_replay": {
            "request_path": trial_evidence_replay["request_path"],
            "decision_code": trial_evidence_replay["decision_lock"]["decision_code"],
            "production_access": trial_evidence_replay["decision_lock"]["production_access"],
            "permission_grants": trial_evidence_replay["decision_lock"]["permission_grants"],
            "external_writes": trial_evidence_replay["decision_lock"]["external_writes"],
            "can_sponsor_change_decision": trial_evidence_replay["decision_lock"]["can_sponsor_change_decision"],
            "provider_count": trial_evidence_replay["summary"]["provider_count"],
            "proof_owner_count": trial_evidence_replay["summary"]["proof_owner_count"],
            "proof_attachment_count": trial_evidence_replay["summary"]["proof_attachment_count"],
            "all_non_executing": trial_evidence_replay["summary"]["all_non_executing"],
            "all_non_approving": trial_evidence_replay["summary"]["all_non_approving"],
            "all_non_granting": trial_evidence_replay["summary"]["all_non_granting"],
            "all_non_mutating": trial_evidence_replay["summary"]["all_non_mutating"],
            "approves_access": trial_evidence_replay["safety_boundary"]["approves_access"],
            "grants_permissions": trial_evidence_replay["safety_boundary"]["grants_permissions"],
            "executes_external_writes": trial_evidence_replay["safety_boundary"]["executes_external_writes"],
        },
        "pilot_memo": {
            "memo_id": pilot_memo["memo_id"],
            "schema_version": pilot_memo["schema_version"],
            "packet_id": pilot_memo["packet_reference"]["packet_id"],
            "revision_id": pilot_memo["packet_reference"]["revision_id"],
            "content_hash": pilot_memo["packet_reference"]["content_hash"],
            "packet_artifact": pilot_memo["packet_reference"]["packet_artifact"],
            "verdict_class": pilot_memo["verdict_class"],
            "sponsor_contribution_count": len(pilot_memo["sponsor_contributions"]),
            "all_sponsors_human_review_required": all(
                item["human_review_required"] for item in pilot_memo["sponsor_contributions"]
            ),
            "sponsors_can_change_decision": any(item["can_change_decision"] for item in pilot_memo["sponsor_contributions"]),
            "reviewer_route_count": len(pilot_memo["reviewer_routing"]),
            "blocked_claim_count": len(pilot_memo["blocked_claims"]),
            "missing_proof_count": len(pilot_memo["missing_proof"]),
            "next_human_action": pilot_memo["next_human_action"],
            "safety_anchor": pilot_memo["safety_anchor"],
            "approves_access": pilot_memo["safety_boundary"]["approves_access"],
            "grants_permissions": pilot_memo["safety_boundary"]["grants_permissions"],
            "executes_external_writes": pilot_memo["safety_boundary"]["executes_external_writes"],
            "mutates_production": pilot_memo["safety_boundary"]["mutates_production"],
            "artifact": "examples/generated/support_triage_trial.pilot_memo.md",
            "json_artifact": "examples/generated/support_triage_trial.pilot_memo.json",
            "copy_artifact": "examples/generated/support_triage_trial.copy_review_brief.md",
        },
        "proof_health": {
            "scenario": proof_health["scenario"],
            "overall_status": proof_health["overall_status"],
            "overall_score": proof_health["overall_score"],
            "next_human_health_check": proof_health["next_human_health_check"],
            "current_checkpoints": proof_health["proof_health_summary"]["current_checkpoints"],
            "drifting_checkpoints": proof_health["proof_health_summary"]["drifting_checkpoints"],
            "stale_checkpoints": proof_health["proof_health_summary"]["stale_checkpoints"],
            "human_review_required": proof_health["proof_health_summary"]["human_review_required"],
            "approves_access": proof_health["safety_boundary"]["approves_access"],
            "grants_permissions": proof_health["safety_boundary"]["grants_permissions"],
            "executes_external_writes": proof_health["safety_boundary"]["executes_external_writes"],
            "mutates_production": proof_health["safety_boundary"]["mutates_production"],
        },
        "ai_spend_review": {
            "scenario": SPEND_SCENARIO_ID,
            "packet_id": spend_review["packet"]["packet_id"],
            "verdict_class": spend_review["packet"]["decision"]["verdict_class"],
            "required_evidence_count": len(spend_review["packet"]["required_evidence"]),
            "blocked_claim_count": len(spend_review["packet"]["blocked_claims"]),
            "finance_receipt_id": spend_review["finance_receipt"]["receipt_id"],
            "procurement_memo_id": spend_review["procurement_memo"]["memo_id"],
            "approves_spend": spend_review["safety"]["approves_spend"],
            "guarantees_savings": spend_review["safety"]["guarantees_savings"],
            "selects_provider": spend_review["safety"]["selects_provider"],
            "executes_external_writes": spend_review["safety"]["executes_external_writes"],
            "requires_human_review": spend_review["safety"]["requires_human_review"],
            "artifact": spend_review["artifacts"]["packet_markdown"],
            "finance_receipt_artifact": spend_review["artifacts"]["finance_receipt_markdown"],
            "procurement_memo_artifact": spend_review["artifacts"]["procurement_memo_markdown"],
        },
        "public_contract": {
            "status": "ok" if all(errors == [] for errors in contract_results.values()) else "fail",
            "results": contract_results,
        },
        "policy_gate": {
            scenario_name: {
                "decision": result["decision"],
                "reason": result["reason"],
                "triggered_rule_ids": [rule["rule_id"] for rule in result["triggered_rules"]],
            }
            for scenario_name, result in gate_results.items()
        },
        "sponsor_adapters": adapter_summary,
        "sponsor_live_readiness": {
            "all_contracts_ready": sponsor_readiness["summary"]["all_contracts_ready"],
            "default_path_requires_keys": sponsor_readiness["summary"]["default_path_requires_keys"],
            "all_non_executing": sponsor_readiness["summary"]["all_non_executing"],
            "all_non_approving": sponsor_readiness["summary"]["all_non_approving"],
            "all_non_granting": sponsor_readiness["summary"]["all_non_granting"],
            "all_non_mutating": sponsor_readiness["summary"]["all_non_mutating"],
            "human_review_required": sponsor_readiness["summary"]["human_review_required"],
            "providers": [
                {
                    "provider": provider["provider"],
                    "proof_pack_type": provider["proof_pack_type"],
                    "live_value": provider["live_value"],
                }
                for provider in sponsor_readiness["providers"]
            ],
        },
        "safety": {
            "approves_access": False,
            "grants_permissions": False,
            "external_writes_default": False,
            "composio_dry_run_default": True,
            "packet_state_mutation_default": False,
            "requires_human_approval": True,
            "all_adapters_non_executing": all(not item["would_execute"] for item in adapter_summary.values()),
            "all_adapters_non_approving": all(not item["can_approve_access"] for item in adapter_summary.values()),
        },
        "artifact_checklist": _artifact_status(PRIMARY_ARTIFACTS),
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def report_has_failures(report: dict[str, Any]) -> bool:
    """Return whether the judge report violates the public review contract."""
    return (
        report["public_contract"]["status"] != "ok"
        or not all(item["exists"] for item in report["artifact_checklist"])
        or not report["safety"]["all_adapters_non_executing"]
        or not report["safety"]["all_adapters_non_approving"]
        or not report["packet_diff"]["has_relaxed_read_only_lane"]
        or not report["packet_diff"]["has_proof_routed_lane"]
        or not report["packet_diff"]["has_blocked_critical_lane"]
        or not report["packet_diff"]["all_production_access_blocked"]
        or not report["packet_diff"]["all_external_writes_blocked"]
        or (
            report["evidence_receipt_ledger"]["decision_lock_before"]
            != report["evidence_receipt_ledger"]["decision_lock_after"]
        )
        or not report["evidence_receipt_ledger"]["all_require_human_review"]
        or not report["evidence_receipt_ledger"]["all_non_approving"]
        or not report["evidence_receipt_ledger"]["all_non_granting"]
        or not report["evidence_receipt_ledger"]["all_non_executing"]
        or not report["evidence_receipt_ledger"]["all_non_mutating"]
        or not report["evidence_receipt_ledger"]["all_non_auto_reducing"]
        or not report["evidence_receipt_ledger"]["budget_owner_required"]
        or not report["evidence_receipt_ledger"]["token_or_tool_spend_cap_required"]
        or (
            report["packet_authority_snapshot"]["decision_lock_before"]
            != report["packet_authority_snapshot"]["decision_lock_after"]
        )
        or report["packet_verification"]["verification_status"] != "valid_review_required"
        or report["packet_verification"]["production_access"]
        or report["packet_verification"]["external_writes"]
        or report["packet_verification"]["permission_grants"]
        or report["packet_verification"]["approval_granted"]
        or report["packet_outcome_memo"]["production_access"]
        or report["packet_outcome_memo"]["external_writes"]
        or report["packet_outcome_memo"]["approves_access"]
        or report["packet_outcome_memo"]["grants_permissions"]
        or report["packet_outcome_memo"]["executes_external_writes"]
        or not report["sponsor_live_readiness"]["all_contracts_ready"]
        or report["sponsor_live_readiness"]["default_path_requires_keys"]
        or not report["sponsor_live_readiness"]["all_non_executing"]
        or not report["sponsor_live_readiness"]["all_non_approving"]
        or not report["sponsor_live_readiness"]["all_non_granting"]
        or not report["sponsor_live_readiness"]["all_non_mutating"]
        or not report["sponsor_live_readiness"]["human_review_required"]
        or any(item["production_access"] for item in report["scenario_matrix"])
        or any(item["approval_granted"] for item in report["scenario_matrix"])
        or not report["access_speed_layer"]["all_routes_immediate"]
        or any(item["production_access"] for item in report["access_speed_layer"]["routes"])
        or bool(report["design_partner_trial"]["validation_errors"])
        or report["design_partner_trial"]["production_access"]
        or report["design_partner_trial"]["approves_access"]
        or report["design_partner_trial"]["grants_permissions"]
        or report["design_partner_trial"]["executes_external_writes"]
        or report["design_partner_outcome_memo"]["production_access"]
        or report["design_partner_outcome_memo"]["permission_grants"]
        or report["design_partner_outcome_memo"]["external_writes"]
        or report["design_partner_outcome_memo"]["approves_access"]
        or report["design_partner_outcome_memo"]["grants_permissions"]
        or report["design_partner_outcome_memo"]["executes_external_writes"]
        or report["design_partner_evidence_replay"]["production_access"]
        or report["design_partner_evidence_replay"]["permission_grants"]
        or report["design_partner_evidence_replay"]["external_writes"]
        or report["design_partner_evidence_replay"]["can_sponsor_change_decision"]
        or not report["design_partner_evidence_replay"]["all_non_executing"]
        or not report["design_partner_evidence_replay"]["all_non_approving"]
        or not report["design_partner_evidence_replay"]["all_non_granting"]
        or not report["design_partner_evidence_replay"]["all_non_mutating"]
        or report["design_partner_evidence_replay"]["approves_access"]
        or report["design_partner_evidence_replay"]["grants_permissions"]
        or report["design_partner_evidence_replay"]["executes_external_writes"]
        or report["pilot_memo"]["sponsors_can_change_decision"]
        or not report["pilot_memo"]["all_sponsors_human_review_required"]
        or report["pilot_memo"]["safety_anchor"] != PILOT_MEMO_SAFETY_ANCHOR
        or report["pilot_memo"]["approves_access"]
        or report["pilot_memo"]["grants_permissions"]
        or report["pilot_memo"]["executes_external_writes"]
        or report["pilot_memo"]["mutates_production"]
        or not report["proof_health"]["human_review_required"]
        or report["proof_health"]["approves_access"]
        or report["proof_health"]["grants_permissions"]
        or report["proof_health"]["executes_external_writes"]
        or report["proof_health"]["mutates_production"]
        or report["ai_spend_review"]["approves_spend"]
        or report["ai_spend_review"]["guarantees_savings"]
        or report["ai_spend_review"]["selects_provider"]
        or report["ai_spend_review"]["executes_external_writes"]
        or not report["ai_spend_review"]["requires_human_review"]
    )


def _status(value: bool) -> str:
    return "OK" if value else "MISSING"


def render_judge_report_markdown(report: dict[str, Any]) -> str:
    """Render the judge report as compact human-readable Markdown."""
    lines = [
        "# InferenceAtlas Judge Harness",
        "",
        f"- mode: {report['mode']}",
        "- live keys required: False",
        "- external writes enabled: False",
        "- approval granted: False",
        "- private source exposed: False",
        "",
        "Private engine, public proof.",
        "",
        "## Command",
        "",
        "```bash",
        "python3 -m agent.judge",
        "```",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Policy Gate | Scoped Validation | Production |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["scenario_matrix"]:
        lines.append(
            "| {scenario} | {gate} | {validation} | {production} |".format(
                scenario=item["scenario"],
                gate=item["policy_gate_decision"],
                validation=item["scoped_validation_review"],
                production=item["production_access"],
            )
        )

    diff = report["packet_diff"]
    lines.extend(
        [
            "",
            "## Packet Diff",
            "",
            "The same packet engine must bend across risk levels without changing safety defaults.",
            "",
            f"- scenarios compared: {diff['scenario_count']}",
            f"- differing load-bearing fields: {diff['differing_field_count']} of {diff['load_bearing_field_count']}",
            f"- relaxed read-only lane: {diff['has_relaxed_read_only_lane']}",
            f"- proof-routed lane: {diff['has_proof_routed_lane']}",
            f"- blocked critical lane: {diff['has_blocked_critical_lane']}",
            f"- all production access blocked: {diff['all_production_access_blocked']}",
            f"- all external writes blocked: {diff['all_external_writes_blocked']}",
            f"- artifact: `examples/generated/packet_diff.md`",
        ]
    )

    receipts = report["evidence_receipt_ledger"]
    lines.extend(
        [
            "",
            "## Evidence Receipt Ledger",
            "",
            "Receipts attach proof context to the packet without changing the packet decision lock.",
            "",
            f"- scenario: `{receipts['scenario']}`",
            f"- packet_id: `{receipts['packet_id']}`",
            f"- decision lock: {receipts['decision_lock_before']} -> {receipts['decision_lock_after']}",
            f"- receipts: {receipts['receipt_count']}",
            f"- tool scope receipts: {receipts['tool_scope_receipts']}",
            f"- proof debt receipts: {receipts['proof_debt_receipts']}",
            f"- reviewer route receipts: {receipts['reviewer_route_receipts']}",
            f"- cost/procurement receipts: {receipts['cost_procurement_receipts']}",
            f"- all require human review: {receipts['all_require_human_review']}",
            f"- all non-approving: {receipts['all_non_approving']}",
            f"- all non-granting: {receipts['all_non_granting']}",
            f"- all non-executing: {receipts['all_non_executing']}",
            f"- budget owner required: {receipts['budget_owner_required']}",
            f"- token/tool spend cap required: {receipts['token_or_tool_spend_cap_required']}",
            f"- artifact: `{receipts['artifact']}`",
        ]
    )

    snapshot = report["packet_authority_snapshot"]
    verification = report["packet_verification"]
    lines.extend(
        [
            "",
            "## Packet Authority Snapshot",
            "",
            "The packet now has canonical identity, revision, hash, and lock state for read-only verification.",
            "",
            f"- scenario: `{snapshot['scenario']}`",
            f"- packet_id: `{snapshot['packet_id']}`",
            f"- revision_id: `{snapshot['revision_id']}`",
            f"- content_hash: `{snapshot['content_hash']}`",
            f"- decision lock: {snapshot['decision_lock_before']} -> {snapshot['decision_lock_after']}",
            f"- evidence receipts: {snapshot['evidence_receipt_count']}",
            f"- next human action: {snapshot['next_human_action']}",
            f"- artifact: `{snapshot['artifact']}`",
            "",
            "## Packet Verification",
            "",
            "The verification artifact is the read-only surface a future CI gate or subscriber can consume.",
            "",
            f"- status: {verification['verification_status']}",
            f"- scoped validation: {verification['scoped_validation']}",
            f"- production access: {verification['production_access']}",
            f"- external writes: {verification['external_writes']}",
            f"- permission grants: {verification['permission_grants']}",
            f"- approval granted: {verification['approval_granted']}",
            f"- artifact: `{verification['artifact']}`",
        ]
    )

    memo = report["packet_outcome_memo"]
    lines.extend(
        [
            "",
            "## Packet Outcome Memo",
            "",
            "The memo converts the packet into the human decision a CTO, Security lead, or AI platform owner can act on.",
            "",
            f"- scenario: `{memo['scenario']}`",
            f"- decision: {memo['decision_code']}",
            f"- summary: {memo['decision_summary']}",
            f"- policy gate: {memo['policy_gate']}",
            f"- production access: {memo['production_access']}",
            f"- scoped validation review: {memo['scoped_validation_review']}",
            f"- external writes: {memo['external_writes']}",
            f"- proof debt assignments: {memo['proof_debt_assignment_count']}",
            f"- reviewer routes: {memo['reviewer_route_count']}",
            f"- next human health check: {memo['next_human_health_check']}",
            f"- artifact: `examples/generated/support_triage_agent.outcome_memo.md`",
        ]
    )

    speed_layer = report["access_speed_layer"]
    lines.extend(
        [
            "",
            "## Access Speed Layer",
            "",
            speed_layer["headline"],
            "",
            f"- Decision time: {speed_layer['decision_time']}",
            f"- auto-generated packet: {speed_layer['packet_generated_automatically']}",
            f"- fast lane routes: {speed_layer['fast_lane_count']}",
            f"- proof-routed routes: {speed_layer['proof_routed_count']}",
            f"- blocked-fast routes: {speed_layer['blocked_fast_count']}",
            "",
            "| Scenario | Lane | Decision Time | Production |",
            "| --- | --- | --- | --- |",
        ]
    )
    for route in speed_layer["routes"]:
        lines.append(
            "| {scenario} | {lane} | {decision_time} | {production} |".format(
                scenario=route["scenario"],
                lane=route["lane"],
                decision_time=route["decision_time"],
                production=route["production_access"],
            )
        )

    trial = report["design_partner_trial"]
    lines.extend(
        [
            "",
            "## Design Partner Trial Runner",
            "",
            f"- request: `{trial['request_path']}`",
            f"- readiness: {trial['request_readiness']}",
            f"- access speed lane: {trial['access_speed_lane']}",
            f"- scoped validation review: {trial['scoped_validation_review']}",
            f"- production access: {trial['production_access']}",
            f"- approves access: {trial['approves_access']}",
            f"- grants permissions: {trial['grants_permissions']}",
            f"- executes external writes: {trial['executes_external_writes']}",
        ]
    )

    trial_memo = report["design_partner_outcome_memo"]
    lines.extend(
        [
            "",
            "## Design Partner Outcome Memo",
            "",
            "The memo turns the trial request into the meeting decision: what can move, what stays blocked, and who owns proof.",
            "",
            f"- request: `{trial_memo['request_path']}`",
            f"- decision: {trial_memo['decision_code']}",
            f"- summary: {trial_memo['decision_summary']}",
            f"- access speed lane: {trial_memo['access_speed_lane']}",
            f"- production access: {trial_memo['production_access']}",
            f"- scoped validation review: {trial_memo['scoped_validation_review']}",
            f"- permission grants: {trial_memo['permission_grants']}",
            f"- external writes: {trial_memo['external_writes']}",
            f"- proof debt assignments: {trial_memo['proof_debt_assignment_count']}",
            f"- reviewer routes: {trial_memo['reviewer_route_count']}",
            f"- artifact: `examples/generated/support_triage_trial.outcome_memo.md`",
        ]
    )

    evidence_replay = report["design_partner_evidence_replay"]
    lines.extend(
        [
            "",
            "## Sponsor Evidence Replay",
            "",
            "Sponsor proof attaches to the trial decision without changing the verdict, granting permissions, or executing live actions.",
            "",
            f"- request: `{evidence_replay['request_path']}`",
            f"- decision: {evidence_replay['decision_code']}",
            f"- providers: {evidence_replay['provider_count']}",
            f"- proof owners: {evidence_replay['proof_owner_count']}",
            f"- proof attachments: {evidence_replay['proof_attachment_count']}",
            f"- production access: {evidence_replay['production_access']}",
            f"- permission grants: {evidence_replay['permission_grants']}",
            f"- external writes: {evidence_replay['external_writes']}",
            f"- sponsors can change decision: {evidence_replay['can_sponsor_change_decision']}",
            f"- all non-executing: {evidence_replay['all_non_executing']}",
            f"- all non-approving: {evidence_replay['all_non_approving']}",
            f"- all non-granting: {evidence_replay['all_non_granting']}",
            f"- all non-mutating: {evidence_replay['all_non_mutating']}",
            f"- artifact: `examples/generated/support_triage_trial.evidence_replay.md`",
        ]
    )

    pilot = report["pilot_memo"]
    lines.extend(
        [
            "",
            "## Pilot Memo",
            "",
            "The PilotMemo is the buyer-carried export artifact: packet reference, sponsor proof roles, reviewer routing, blocked claims, missing proof, and next human action.",
            "",
            f"- memo_id: `{pilot['memo_id']}`",
            f"- packet_id: `{pilot['packet_id']}`",
            f"- revision_id: `{pilot['revision_id']}`",
            f"- content_hash: `{pilot['content_hash']}`",
            f"- packet artifact: `{pilot['packet_artifact']}`",
            f"- verdict class: {pilot['verdict_class']}",
            f"- sponsor contributions: {pilot['sponsor_contribution_count']}",
            f"- sponsors can change decision: {pilot['sponsors_can_change_decision']}",
            f"- all sponsors require human review: {pilot['all_sponsors_human_review_required']}",
            f"- reviewer routes: {pilot['reviewer_route_count']}",
            f"- blocked claims: {pilot['blocked_claim_count']}",
            f"- missing proof: {pilot['missing_proof_count']}",
            f"- next human action: {pilot['next_human_action']}",
            f"- safety anchor: {pilot['safety_anchor']}",
            f"- approves access: {pilot['approves_access']}",
            f"- grants permissions: {pilot['grants_permissions']}",
            f"- executes external writes: {pilot['executes_external_writes']}",
            f"- artifact: `{pilot['artifact']}`",
            f"- copy brief: `{pilot['copy_artifact']}`",
        ]
    )

    lines.extend(
        [
            "",
            "## Proof Health",
            "",
            "Packet lifecycle status for the primary support-triage packet.",
            "",
            f"- scenario: `{report['proof_health']['scenario']}`",
            f"- status: {report['proof_health']['overall_status']}",
            f"- score: {report['proof_health']['overall_score']}",
            f"- next human health check: {report['proof_health']['next_human_health_check']}",
            f"- human review required: {report['proof_health']['human_review_required']}",
            f"- approves access: {report['proof_health']['approves_access']}",
            f"- grants permissions: {report['proof_health']['grants_permissions']}",
            "",
            "## AI Spend Review",
            "",
            "The spend lane creates a Finance/Procurement review packet before usage caps, vendor switches, or savings claims move.",
            "",
            f"- scenario: `{report['ai_spend_review']['scenario']}`",
            f"- packet_id: `{report['ai_spend_review']['packet_id']}`",
            f"- verdict class: {report['ai_spend_review']['verdict_class']}",
            f"- required evidence items: {report['ai_spend_review']['required_evidence_count']}",
            f"- blocked claims: {report['ai_spend_review']['blocked_claim_count']}",
            f"- approves spend: {report['ai_spend_review']['approves_spend']}",
            f"- guarantees savings: {report['ai_spend_review']['guarantees_savings']}",
            f"- selects provider: {report['ai_spend_review']['selects_provider']}",
            f"- artifact: `{report['ai_spend_review']['artifact']}`",
            f"- finance receipt: `{report['ai_spend_review']['finance_receipt_artifact']}`",
            f"- procurement memo: `{report['ai_spend_review']['procurement_memo_artifact']}`",
            "",
            "## Public Contract",
            "",
            f"- status: {report['public_contract']['status']}",
        ]
    )
    for scenario_name, errors in report["public_contract"]["results"].items():
        lines.append(f"- {scenario_name}: {'OK' if not errors else 'FAIL'}")

    lines.extend(["", "## Sponsor Adapter Safety", ""])
    for provider, summary in report["sponsor_adapters"].items():
        lines.append(
            "- {provider}: statuses={statuses}; proof={proof}; human_review_required={review}; would_execute={would_execute}; can_approve_access={can_approve}".format(
                provider=provider,
                statuses=", ".join(summary["statuses"]),
                proof=", ".join(summary["proof_pack_types"]),
                review=summary["human_review_required"],
                would_execute=summary["would_execute"],
                can_approve=summary["can_approve_access"],
            )
        )

    readiness = report["sponsor_live_readiness"]
    lines.extend(
        [
            "",
            "## Sponsor Live Readiness",
            "",
            "- all contracts ready: {ready}".format(ready=readiness["all_contracts_ready"]),
            "- default path requires keys: {requires_keys}".format(
                requires_keys=readiness["default_path_requires_keys"]
            ),
            "- all non-executing: {non_executing}".format(non_executing=readiness["all_non_executing"]),
            "- all non-approving: {non_approving}".format(non_approving=readiness["all_non_approving"]),
            "- all non-granting: {non_granting}".format(non_granting=readiness["all_non_granting"]),
            "- all non-mutating: {non_mutating}".format(non_mutating=readiness["all_non_mutating"]),
            "",
        ]
    )
    for provider in readiness["providers"]:
        lines.append(
            "- {provider}: proof={proof}; live_value={live_value}".format(
                provider=provider["provider"],
                proof=provider["proof_pack_type"],
                live_value=provider["live_value"],
            )
        )

    lines.extend(["", "## Artifact Checklist", ""])
    for item in report["artifact_checklist"]:
        lines.append(f"- [{_status(item['exists'])}] `{item['path']}`")

    lines.extend(
        [
            "",
            "## Next Human Review",
            "",
            "1. Read `docs/PRODUCT_TOUR.md`.",
            "2. Read `docs/PRODUCT_QUALITY_AUDIT.md`.",
            "3. Read `docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md`.",
            "4. Read `examples/generated/packet_diff.md`.",
            "5. Read `examples/generated/support_triage_agent.evidence_receipts.md`.",
            "6. Read `examples/generated/support_triage_agent.outcome_memo.md`.",
            "7. Skim `examples/generated/review_room.html`.",
            "8. Read `examples/generated/trust_receipt.md`.",
            "9. Read `examples/generated/support_triage_agent.proof_health.md`.",
            "10. Read `examples/generated/sponsor_live_readiness.md`.",
            "11. Read `docs/DESIGN_PARTNER_BRIEF.md` for the one-workflow trial path.",
            "12. Open `docs/DESIGN_PARTNER_TRIAL_KIT.md` and `examples/requests/design_partner_trial.yml`.",
            "13. Run `python3 -m agent.trial examples/requests/support_triage_trial.yml`.",
            "14. Read `examples/generated/support_triage_trial.outcome_memo.md`.",
            "15. Read `examples/generated/support_triage_trial.evidence_replay.md`.",
            "16. Read `examples/generated/support_triage_trial.pilot_memo.md` and copy `examples/generated/support_triage_trial.copy_review_brief.md`.",
            "17. Use `docs/REVIEW_ROOM_WALKTHROUGH.md` for the demo talk track.",
            "18. Confirm `admin_code_fix_bot` remains blocked before validation.",
            "19. Confirm sponsor adapters stay dry-run and non-approving.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.judge",
        description="Run the no-key InferenceAtlas judge harness and print the review checklist.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the judge report as machine-readable JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip regenerating artifacts before building the report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_judge_report(write_artifacts=not args.no_write)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_judge_report_markdown(report))

    return 1 if report_has_failures(report) else 0


if __name__ == "__main__":
    sys.exit(main())
