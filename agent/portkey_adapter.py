"""Portkey dry-run adapter backed by IA Packet truth.

Generates a Portkey-ready guardrail verdict and usage-limit policy plan from an
IA Packet. This public adapter is intentionally non-mutating: it makes no
Portkey API calls, stores no Portkey secrets, and never approves spend.

Docs verified: 2026-06-07
- BYO Guardrail webhook verdict:
  https://portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails
- Usage limit policy shape:
  https://portkey.ai/docs/api-reference/admin-api/control-plane/policies/usage-limits/create-usage-limits-policy
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Literal

from .workbench import build_workbench_result


PORTKEY_ADAPTER_SCHEMA_VERSION = "portkey_gate_v0"
DEFAULT_FIXTURE = "ai_spend_budget_overrun"
DEFAULT_MODE = "dry-run"
PORTKEY_GUARDRAIL_DOC_URL = "https://portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails"
PORTKEY_USAGE_LIMIT_DOC_URL = (
    "https://portkey.ai/docs/api-reference/admin-api/control-plane/policies/usage-limits/"
    "create-usage-limits-policy"
)

PortkeyMode = Literal["ready", "dry-run", "live"]


def _packet_reference(result: dict[str, Any]) -> dict[str, str]:
    ref = result["packet_reference"]
    return {
        "packet_id": ref["packet_id"],
        "revision_id": ref["revision_id"],
        "content_hash": ref["content_hash"],
    }


def _docs_reference() -> dict[str, str]:
    return {
        "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
        "usage_limit_policy": PORTKEY_USAGE_LIMIT_DOC_URL,
        "last_verified": "2026-06-07",
    }


def _guardrail_response(result: dict[str, Any]) -> dict[str, Any]:
    safety = result["safety_boundary"]
    deny_reasons = list(result["blocked_claims"])
    verdict = bool(
        result["decision"].get("approval_granted")
        and not safety["requires_human_review"]
        and safety["approves_spend"]
        and not safety["executes_external_writes"]
    )
    return {
        "verdict": verdict,
        "data": {
            "ia_packet_id": result["packet_reference"]["packet_id"],
            "ia_revision_id": result["packet_reference"]["revision_id"],
            "deny_reasons": deny_reasons,
            "next_human_action": result["decision"]["next_human_action"],
        },
    }


def _guardrail_config_preview(result: dict[str, Any]) -> dict[str, Any]:
    packet_id = result["packet_reference"]["packet_id"]
    return {
        "portkey_surface": "BYO Guardrail webhook",
        "event_type": "beforeRequestHook",
        "method": "POST",
        "expected_response_shape": {
            "verdict": "boolean",
            "data": "optional IA packet reference and deny reasons",
        },
        "metadata_expected": {
            "ia_packet_id": packet_id,
            "ia_revision_id": result["packet_reference"]["revision_id"],
        },
        "recommended_timeout_ms": 3000,
    }


def _usage_policy_plan(result: dict[str, Any]) -> dict[str, Any]:
    packet = result["packet_reference"]
    packet_id = packet["packet_id"]
    return {
        "portkey_surface": "Usage Limits Policy",
        "endpoint": "POST https://api.portkey.ai/v1/policies/usage-limits",
        "request_body": {
            "name": f"IA blocked spend gate - {packet_id}",
            "conditions": [
                {"key": "metadata.ia_packet_id", "value": packet_id},
                {"key": "metadata.ia_revision_id", "value": packet["revision_id"]},
            ],
            "group_by": [{"key": "api_key"}],
            "type": "cost",
            "credit_limit": 0,
            "alert_threshold": None,
            "periodic_reset": "monthly",
        },
        "note": (
            "Dry-run plan caps matching packet-scoped spend at zero until Finance and "
            "Procurement review the required proof."
        ),
    }


def _diff_preview(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_portkey_policy": {
            "source": "not_fetched_in_public_dry_run",
            "api_call_made": False,
        },
        "proposed_policy_from_packet": {
            "guardrail_verdict": False,
            "usage_credit_limit": 0,
            "requires_human_review": result["safety_boundary"]["requires_human_review"],
        },
        "diff": [
            {
                "field": "guardrail.verdict",
                "from": "unknown",
                "to": False,
                "reason": "IA Packet does not approve spend or provider movement.",
            },
            {
                "field": "usage_limits.credit_limit",
                "from": "unknown",
                "to": 0,
                "reason": "Budget owner approval and spend cap proof are missing.",
            },
        ],
    }


def build_portkey_adapter_payload(
    *,
    fixture: str = DEFAULT_FIXTURE,
    mode: PortkeyMode = DEFAULT_MODE,
) -> dict[str, Any]:
    """Build the Portkey dry-run contract from an IA Packet."""
    if mode not in {"ready", "dry-run", "live"}:
        raise ValueError(f"unsupported Portkey adapter mode: {mode}")
    if mode == "live":
        raise ValueError("live Portkey mutation is disabled in the public demo")

    result = build_workbench_result(fixture)
    guardrail = _guardrail_response(result)
    dry_run = mode == "dry-run"

    return {
        "schema_version": PORTKEY_ADAPTER_SCHEMA_VERSION,
        "mode": mode,
        "dry_run": dry_run,
        "api_call_made": False,
        "portkey_claim": "Generates Portkey-ready guardrail and usage-limit policy payloads.",
        "docs_reference": _docs_reference(),
        "fixture": result["fixture"],
        "ia_packet_reference": _packet_reference(result),
        "packet_truth": {
            "verdict_class": result["decision"]["verdict_class"],
            "approves_spend": result["safety_boundary"]["approves_spend"],
            "selects_provider": result["safety_boundary"]["selects_provider"],
            "guarantees_savings": result["safety_boundary"]["guarantees_savings"],
            "requires_human_review": result["safety_boundary"]["requires_human_review"],
            "next_human_action": result["decision"]["next_human_action"],
        },
        "portkey_guardrail_response": guardrail,
        "deny_reasons": list(result["blocked_claims"]),
        "missing_proof": list(result["missing_proof"]),
        "reviewer_routing": list(result["reviewer_routing"]),
        "guardrail_config_preview": _guardrail_config_preview(result),
        "usage_policy_plan": _usage_policy_plan(result),
        "dry_run_diff": _diff_preview(result),
        "invariants": {
            "read_only": True,
            "raw_agent_intent_trusted": False,
            "packet_mutation_allowed": False,
            "portkey_api_call_made": False,
            "live_mutation_enabled": False,
            "approves_spend": result["safety_boundary"]["approves_spend"],
            "selects_provider": result["safety_boundary"]["selects_provider"],
            "guarantees_savings": result["safety_boundary"]["guarantees_savings"],
            "requires_human_review": result["safety_boundary"]["requires_human_review"],
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def render_portkey_adapter_markdown(payload: dict[str, Any]) -> str:
    packet = payload["ia_packet_reference"]
    truth = payload["packet_truth"]
    guardrail = payload["portkey_guardrail_response"]
    return "\n".join(
        [
            "# Portkey Adapter Preview",
            "",
            "Private engine, public proof.",
            "",
            f"- mode: `{payload['mode']}`",
            f"- api call made: {payload['api_call_made']}",
            f"- packet_id: `{packet['packet_id']}`",
            f"- revision_id: `{packet['revision_id']}`",
            f"- verdict_class: {truth['verdict_class']}",
            f"- Portkey guardrail verdict: {guardrail['verdict']}",
            f"- usage policy credit_limit: {payload['usage_policy_plan']['request_body']['credit_limit']}",
            f"- approves spend: {truth['approves_spend']}",
            f"- selects provider: {truth['selects_provider']}",
            f"- guarantees savings: {truth['guarantees_savings']}",
            f"- next human action: {truth['next_human_action']}",
            "",
            "Docs:",
            f"- Guardrail webhook: {payload['docs_reference']['guardrail_webhook']}",
            f"- Usage limit policy: {payload['docs_reference']['usage_limit_policy']}",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.portkey_adapter",
        description="Generate a dry-run Portkey gate contract from an IA Packet.",
    )
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="Workbench fixture id.")
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        choices=("ready", "dry-run", "live"),
        help="Adapter mode. Public demo supports ready and dry-run only.",
    )
    parser.add_argument(
        "--i-understand-this-mutates-production",
        action="store_true",
        help="Reserved for future live mode; public demo still refuses live mutation.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "live" and not args.i_understand_this_mutates_production:
            raise ValueError("live mode requires --i-understand-this-mutates-production")
        payload = build_portkey_adapter_payload(fixture=args.fixture, mode=args.mode)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_portkey_adapter_markdown(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
