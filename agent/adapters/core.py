"""Dry-run sponsor adapter contracts for the public judge harness."""

from __future__ import annotations

import json
from typing import Any

from agent.scenarios import SCENARIOS, build_scenario_packet


ADAPTER_NAMES = ("composio", "tavily", "nebius", "openclaw")
ADAPTER_CONTRACT_VERSION = "sponsor_adapter_contract.v0"


def _adapter_base(provider: str, scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "provider": provider,
        "scenario": scenario_name,
        "packet_id": packet["packet_id"],
        "mode": "offline_dry_run_contract",
        "requires_api_key": False,
        "live_mode_enabled": False,
        "would_execute": False,
        "can_approve_access": False,
        "can_grant_permissions": False,
        "can_mutate_external_state": False,
        "blocked_from_approving_access": True,
        "human_review_required": True,
    }


def _composio_result(scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    result = _adapter_base("composio", scenario_name)
    result.update(
        {
            "status": "dry_run_planned",
            "purpose": "Convert packet tool access plan into dry-run action plans.",
            "writes_default": "blocked",
            "proof_pack": {
                "proof_type": "permission_diff",
                "value_added": "Shows the exact requested tool actions, validation-only allowances, blocked actions, and proof required before any tool grant.",
                "visible_output": "tool-by-tool permission diff and dry-run invocation plan",
                "reviewer_question": "Which actions can be validated safely, and which actions must stay blocked?",
                "human_review_required": True,
                "cannot_do": ["approve access", "grant permissions", "execute writes", "reduce proof debt automatically"],
            },
            "action_plans": [
                {
                    "tool": tool_name,
                    "requested": plan["requested"],
                    "demo_allowance": plan["demo_allowance"],
                    "allowed_for_validation": [plan["demo_allowance"]],
                    "would_execute": False,
                    "blocked_actions": plan["blocked_actions"],
                    "required_scopes_or_proof": plan["required_proof"],
                    "dry_run_invocation": {
                        "mode": "plan_only",
                        "would_execute": False,
                        "writes_default": "blocked",
                    },
                }
                for tool_name, plan in packet["tool_access_plan"].items()
            ],
            "receipt_field": "permission_envelope.dry_run_only",
            "safety_impact": "none",
        }
    )
    return result


def _tavily_result(scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    result = _adapter_base("tavily", scenario_name)
    result.update(
        {
            "status": "evidence_candidates_planned",
            "purpose": "Plan reviewer-safe evidence queries from missing proof and blocked claims.",
            "evidence_candidates": [
                {
                    "query": f"{proof['item']} policy evidence",
                    "evidence_type": "policy_or_control_evidence",
                    "reviewer_owner": proof["owner"],
                    "unblocks": proof["unblocks"],
                    "source_urls": [],
                    "freshness": "not_fetched_in_offline_mode",
                    "search_mode": "planned_search_extract_or_crawl",
                    "human_review_required": True,
                    "can_reduce_proof_debt": False,
                    "cannot_grant_access": True,
                }
                for proof in packet["missing_proof"]
            ],
            "proof_pack": {
                "proof_type": "evidence_candidate_plan",
                "value_added": "Turns missing proof into reviewer-safe evidence queries with freshness and source placeholders.",
                "visible_output": "evidence query plan with owners, source URL slots, and freshness state",
                "reviewer_question": "What evidence should reviewers inspect before reducing proof debt?",
                "human_review_required": True,
                "cannot_do": ["approve access", "grant permissions", "declare compliance", "reduce proof debt automatically"],
            },
            "receipt_field": "evidence_plan",
            "safety_impact": "none",
        }
    )
    return result


def _nebius_result(scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    result = _adapter_base("nebius", scenario_name)
    result.update(
        {
            "status": "deterministic_narration_fallback",
            "purpose": "Prepare reviewer-ready narration without letting model output own the verdict.",
            "narration": (
                f"{scenario_name}: {packet['decision']['verdict']} "
                f"{packet['decision']['review_posture']}"
            ),
            "reviewer_narration_contract": {
                "input_fields": ["decision", "approval_posture", "blocked_claims", "missing_proof", "reviewer_owners"],
                "draft_outputs": ["reviewer summary", "decision brief language", "executive skim copy"],
                "locked_fields": ["verdict", "blocked_claims", "safety_state", "policy_gate_status"],
                "human_review_required": True,
            },
            "llm_may_edit": ["summary language", "reviewer-facing explanation"],
            "llm_must_not_edit": ["verdict", "blocked_claims", "safety_state", "policy_gate_status"],
            "proof_pack": {
                "proof_type": "locked_field_narration",
                "value_added": "Projects deterministic packet truth into reviewer-ready language while keeping safety-critical fields locked.",
                "visible_output": "narration contract with editable language fields and locked verdict fields",
                "reviewer_question": "Can the packet be explained faster without letting an LLM own the access decision?",
                "human_review_required": True,
                "cannot_do": ["approve access", "grant permissions", "change verdict", "change safety state"],
            },
            "receipt_field": "inference_plan",
            "safety_impact": "none",
        }
    )
    return result


def _openclaw_result(scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    result = _adapter_base("openclaw", scenario_name)
    result.update(
        {
            "status": "trace_contract_planned",
            "purpose": "Record runtime steps and blocked/allowed outcomes without bypassing safety state.",
            "trace_steps": [
                {
                    "step": "load_packet",
                    "outcome": "packet_loaded",
                    "policy_decision": "inspect_only",
                    "would_execute": False,
                },
                {
                    "step": "evaluate_policy_gate",
                    "outcome": "policy_gate_required_before_access",
                    "policy_decision": "gate_before_access",
                    "would_execute": False,
                },
                {
                    "step": "plan_tool_actions",
                    "outcome": "dry_run_only" if packet["safety_state"]["composio_dry_run"] else "blocked",
                    "policy_decision": "dry_run_only",
                    "would_execute": False,
                },
            ],
            "runtime_trace_contract": {
                "records": ["step", "outcome", "policy_decision", "would_execute"],
                "must_preserve": ["blocked attempts", "human approval boundary", "dry-run state"],
                "human_review_required": True,
            },
            "proof_pack": {
                "proof_type": "runtime_trace_plan",
                "value_added": "Shows how attempted agent steps would be traced with policy decisions before any live action.",
                "visible_output": "runtime trace contract for blocked and dry-run steps",
                "reviewer_question": "What would the runtime record when an agent attempts tool access?",
                "human_review_required": True,
                "cannot_do": ["approve access", "grant permissions", "execute runtime steps", "hide blocked attempts"],
            },
            "receipt_field": "runtime_trace_plan",
            "safety_impact": "none",
        }
    )
    return result


def build_adapter_result(provider: str, scenario_name: str = "support_triage_agent") -> dict[str, Any]:
    """Build one dry-run sponsor adapter result."""
    if provider not in ADAPTER_NAMES:
        raise ValueError(f"unknown adapter provider: {provider}")
    if scenario_name not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario_name}")
    builders = {
        "composio": _composio_result,
        "tavily": _tavily_result,
        "nebius": _nebius_result,
        "openclaw": _openclaw_result,
    }
    return builders[provider](scenario_name)


def build_all_adapter_results(scenario_name: str = "support_triage_agent") -> dict[str, dict[str, Any]]:
    """Build every dry-run sponsor adapter result for one scenario."""
    return {provider: build_adapter_result(provider, scenario_name) for provider in ADAPTER_NAMES}


def result_to_pretty_json(result: dict[str, Any]) -> str:
    """Render adapter output as stable, human-readable JSON."""
    return json.dumps(result, indent=2, sort_keys=True)
