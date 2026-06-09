"""Read-only Portkey guardrail proof-loop summary.

This module turns the existing Portkey BYO Guardrails webhook and dry-run
adapter into one reviewer-friendly proof object. It does not call Portkey,
create policies, mutate virtual keys, or change the IA Packet.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from .portkey_adapter import build_portkey_adapter_payload
from .portkey_guardrail import (
    PORTKEY_GUARDRAIL_DELIVERY_MODE,
    PORTKEY_GUARDRAIL_DOC_URL,
    PORTKEY_GUARDRAIL_TOKEN_HEADER,
    PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
    build_portkey_guardrail_response,
)


PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION = "portkey_guardrail_proof_loop.v0"
DEFAULT_FIXTURE = "ai_spend_budget_overrun"
DEFAULT_REQUESTED_MODE = "model_request"


def build_portkey_guardrail_probe_payload(
    *,
    fixture: str = DEFAULT_FIXTURE,
    requested_mode: str = DEFAULT_REQUESTED_MODE,
) -> dict[str, Any]:
    """Build the harmless Portkey-shaped request used by the proof loop."""
    return {
        "eventType": "beforeRequestHook",
        "provider": "openai",
        "requestType": "chatComplete",
        "metadata": {
            "ia_fixture": fixture,
            "ia_requested_mode": requested_mode,
        },
        "request": {
            "json": {
                "model": "demo-model",
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": "IA Portkey guardrail proof loop: can this packet-backed request move?",
                    }
                ],
            },
            "isStreamingRequest": False,
            "isTransformed": False,
        },
        "response": {
            "json": {},
            "text": "",
            "statusCode": None,
            "isTransformed": False,
        },
    }


def build_portkey_guardrail_proof_loop(
    *,
    fixture: str = DEFAULT_FIXTURE,
    requested_mode: str = DEFAULT_REQUESTED_MODE,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build one packet-backed Portkey proof loop without external mutation."""
    started = time.perf_counter()
    request_body = build_portkey_guardrail_probe_payload(
        fixture=fixture,
        requested_mode=requested_mode,
    )
    response = build_portkey_guardrail_response(
        request_body,
        elapsed_ms=0,
        generated_at=generated_at,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response["data"]["elapsed_ms"] = elapsed_ms

    adapter_payload = build_portkey_adapter_payload(fixture=fixture, mode="dry-run")
    data = response["data"]
    packet_reference = data.get("ia_packet_reference") or adapter_payload["ia_packet_reference"]
    safety = data["safety"]

    return {
        "schema_version": PORTKEY_GUARDRAIL_PROOF_LOOP_SCHEMA_VERSION,
        "delivery_mode": PORTKEY_GUARDRAIL_DELIVERY_MODE,
        "fixture": fixture,
        "requested_mode": requested_mode,
        "docs_reference": {
            "guardrail_webhook": PORTKEY_GUARDRAIL_DOC_URL,
            "guardrails_overview": PORTKEY_GUARDRAILS_OVERVIEW_DOC_URL,
            "last_verified": "2026-06-09",
        },
        "portkey_call": {
            "method": "POST",
            "path": "/api/portkey/guardrail",
            "event_type": request_body["eventType"],
            "request_type": request_body["requestType"],
            "auth_required": True,
            "accepted_auth_headers": ["Authorization: Bearer <token>", PORTKEY_GUARDRAIL_TOKEN_HEADER],
            "metadata_sent": request_body["metadata"],
            "response_verdict": response["verdict"],
            "server_elapsed_ms": elapsed_ms,
            "event_recording": {
                "webhook_records_event": True,
                "events_path": "/api/portkey/guardrail/events",
                "preview_written_to_ledger": False,
            },
        },
        "ia_packet_reference": packet_reference,
        "packet_truth": {
            "verdict": response["verdict"],
            "verdict_class": data.get("verdict_class"),
            "reason": data.get("reason"),
            "deny_reasons": data.get("deny_reasons", []),
            "missing_proof": data.get("missing_proof", []),
            "reviewer_routing": data.get("reviewer_routing", []),
            "next_human_action": data.get("next_human_action"),
        },
        "portkey_policy_preview": {
            "mode": adapter_payload["mode"],
            "api_call_made": adapter_payload["api_call_made"],
            "guardrail_response": adapter_payload["portkey_guardrail_response"],
            "usage_policy_plan": adapter_payload["usage_policy_plan"],
            "dry_run_diff": adapter_payload["dry_run_diff"],
        },
        "invariants": {
            "read_only": safety["read_only"],
            "raw_agent_intent_trusted": safety["raw_agent_intent_trusted"],
            "packet_mutation_allowed": safety["packet_mutation_allowed"],
            "portkey_policy_mutation_allowed": safety["portkey_policy_mutation_allowed"],
            "portkey_api_call_made": safety["portkey_api_call_made"],
            "live_portkey_mutation_enabled": False,
            "auth_required": True,
            "no_token_fails_safe": True,
            "packet_remains_authority": True,
            "preview_does_not_write_ledger": True,
        },
        "safety": safety,
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }


def render_portkey_guardrail_proof_loop_markdown(payload: dict[str, Any]) -> str:
    """Render a compact reviewer-facing Portkey proof loop."""
    packet = payload["ia_packet_reference"]
    truth = payload["packet_truth"]
    call = payload["portkey_call"]
    policy = payload["portkey_policy_preview"]
    return "\n".join(
        [
            "# Portkey Guardrail Proof Loop",
            "",
            "Private engine, public proof.",
            "",
            f"- fixture: `{payload['fixture']}`",
            f"- requested mode: `{payload['requested_mode']}`",
            f"- webhook: `{call['method']} {call['path']}`",
            f"- auth required: {call['auth_required']}",
            f"- verdict: {truth['verdict']}",
            f"- reason: `{truth.get('reason')}`",
            f"- packet_id: `{packet['packet_id']}`",
            f"- revision_id: `{packet['revision_id']}`",
            f"- content_hash: `{packet['content_hash']}`",
            f"- verdict_class: `{truth.get('verdict_class')}`",
            f"- server elapsed: `{call['server_elapsed_ms']}ms`",
            f"- policy preview mode: `{policy['mode']}`",
            f"- Portkey API call made: {policy['api_call_made']}",
            f"- usage credit limit: {policy['usage_policy_plan']['request_body']['credit_limit']}",
            f"- next human action: {truth.get('next_human_action')}",
            "",
            "Safety:",
            "- IA returned a packet-backed verdict only.",
            "- IA did not mutate the packet, call Portkey APIs, push policy, execute writes, or trust raw agent intent.",
            "- The live webhook records events only when called with an auth token; this preview writes nothing.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.portkey_guardrail_proof_loop",
        description="Build a read-only Portkey guardrail proof loop from an IA Packet.",
    )
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="Workbench fixture id.")
    parser.add_argument("--requested-mode", default=DEFAULT_REQUESTED_MODE, help="Portkey metadata movement mode.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = build_portkey_guardrail_proof_loop(
            fixture=args.fixture,
            requested_mode=args.requested_mode,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_portkey_guardrail_proof_loop_markdown(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
