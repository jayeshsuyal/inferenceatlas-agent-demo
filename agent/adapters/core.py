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
    }


def _composio_result(scenario_name: str) -> dict[str, Any]:
    packet = build_scenario_packet(scenario_name)
    result = _adapter_base("composio", scenario_name)
    result.update(
        {
            "status": "dry_run_planned",
            "purpose": "Convert packet tool access plan into dry-run action plans.",
            "writes_default": "blocked",
            "action_plans": [
                {
                    "tool": tool_name,
                    "requested": plan["requested"],
                    "demo_allowance": plan["demo_allowance"],
                    "would_execute": False,
                    "blocked_actions": plan["blocked_actions"],
                    "required_proof": plan["required_proof"],
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
                    "owner": proof["owner"],
                    "unblocks": proof["unblocks"],
                    "source_urls": [],
                    "freshness": "not_fetched_in_offline_mode",
                    "can_reduce_proof_debt": False,
                }
                for proof in packet["missing_proof"]
            ],
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
            "llm_may_edit": ["summary language", "reviewer-facing explanation"],
            "llm_must_not_edit": ["verdict", "blocked_claims", "safety_state", "policy_gate_status"],
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
                    "would_execute": False,
                },
                {
                    "step": "evaluate_policy_gate",
                    "outcome": "policy_gate_required_before_access",
                    "would_execute": False,
                },
                {
                    "step": "plan_tool_actions",
                    "outcome": "dry_run_only" if packet["safety_state"]["composio_dry_run"] else "blocked",
                    "would_execute": False,
                },
            ],
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
