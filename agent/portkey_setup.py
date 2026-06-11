"""Secret-safe Portkey BYO Guardrail setup artifact.

The setup artifact tells an operator exactly what to paste into Portkey while
keeping the public demo read-only. It does not call Portkey, push policies,
store secrets, or change packet state.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.parse import urlparse

from .portkey_guardrail import PORTKEY_GUARDRAIL_AUTH_ENV
from .workbench import build_workbench_result


PORTKEY_GUARDRAIL_SETUP_SCHEMA_VERSION = "portkey_guardrail_setup.v0"
DEFAULT_FIXTURE = "ai_spend_budget_overrun"
DEFAULT_REQUESTED_MODE = "model_request"
DEFAULT_TIMEOUT_MS = 3000
DEFAULT_IA_LATENCY_BUDGET_MS = 150
PORTKEY_BYO_GUARDRAILS_DOC_URL = "https://docs.portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails"
PORTKEY_GUARDRAILS_DOC_URL = "https://docs.portkey.ai/docs/product/guardrails"
PORTKEY_DOCS_LAST_VERIFIED = "2026-06-11"


def _normalize_public_base_url(public_base_url: str) -> str:
    value = public_base_url.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("public_base_url must be an http(s) URL")
    return value


def _packet_metadata_for_fixture(fixture: str, requested_mode: str) -> dict[str, str]:
    result = build_workbench_result(fixture)
    packet = result["packet_reference"]
    return {
        "ia_fixture": fixture,
        "ia_packet_id": packet["packet_id"],
        "ia_revision_id": packet["revision_id"],
        "ia_requested_mode": requested_mode,
    }


def build_portkey_guardrail_setup(
    *,
    public_base_url: str,
    fixture: str = DEFAULT_FIXTURE,
    requested_mode: str = DEFAULT_REQUESTED_MODE,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ia_latency_budget_ms: int = DEFAULT_IA_LATENCY_BUDGET_MS,
    token_env: str = PORTKEY_GUARDRAIL_AUTH_ENV,
    token_configured: bool | None = None,
) -> dict[str, Any]:
    """Build the dashboard-facing setup artifact without exposing secrets."""
    if timeout_ms <= 0:
        raise ValueError("timeout_ms must be positive")
    if ia_latency_budget_ms <= 0:
        raise ValueError("ia_latency_budget_ms must be positive")

    base_url = _normalize_public_base_url(public_base_url)
    metadata = _packet_metadata_for_fixture(fixture, requested_mode)
    if token_configured is None:
        token_configured = bool(os.getenv(token_env, "").strip())

    webhook_path = "/api/portkey/guardrail"
    webhook_url = f"{base_url}{webhook_path}"
    token_placeholder = f"<{token_env}>"

    return {
        "schema_version": PORTKEY_GUARDRAIL_SETUP_SCHEMA_VERSION,
        "read_only": True,
        "status": "ready_to_configure",
        "public_base_url": base_url,
        "webhook": {
            "method": "POST",
            "path": webhook_path,
            "url": webhook_url,
            "auth_required": True,
            "token_env": token_env,
            "token_configured": token_configured,
        },
        "portkey_dashboard_config": {
            "guardrail_type": "Bring Your Own Guardrail",
            "webhook_url": webhook_url,
            "headers_json": {
                "Authorization": f"Bearer {token_placeholder}",
                "Content-Type": "application/json",
            },
            "timeout_ms": timeout_ms,
            "metadata_json": metadata,
            "expected_response_shape": {
                "verdict": "boolean",
                "data": "optional IA packet reference, deny reasons, safety, and event id",
            },
        },
        "timeout_boundary": {
            "portkey_default_timeout_ms": DEFAULT_TIMEOUT_MS,
            "portkey_timeout_default_verdict": True,
            "configured_timeout_ms": timeout_ms,
            "ia_latency_budget_ms": ia_latency_budget_ms,
            "claim_boundary": (
                "IA fails closed for requests it receives. A Portkey timeout is Portkey behavior, "
                "not an IA approval."
            ),
        },
        "local_verification": {
            "start_command": f'{token_env}="<shared-token>" python3 -m web',
            "probe_command": (
                f'{token_env}="<shared-token>" python3 scripts/portkey_guardrail_probe.py '
                f"--base-url {base_url} --json"
            ),
            "events_url": f"{base_url}/api/portkey/guardrail/events",
        },
        "demo_claim": (
            "Portkey is calling IA live as a BYO Guardrail. IA returns the packet-backed verdict. "
            "No Admin API mutation, no policy push, no writes."
        ),
        "safety": {
            "portkey_api_call_made": False,
            "portkey_policy_mutation_allowed": False,
            "packet_mutation_allowed": False,
            "external_writes": False,
            "secrets_exposed": False,
        },
        "docs_reference": {
            "byo_guardrails": PORTKEY_BYO_GUARDRAILS_DOC_URL,
            "guardrails": PORTKEY_GUARDRAILS_DOC_URL,
            "last_verified": PORTKEY_DOCS_LAST_VERIFIED,
        },
    }


def render_portkey_guardrail_setup_markdown(payload: dict[str, Any]) -> str:
    """Render a compact operator setup sheet."""
    config = payload["portkey_dashboard_config"]
    webhook = payload["webhook"]
    timeout = payload["timeout_boundary"]
    return "\n".join(
        [
            "# Portkey BYO Guardrail Setup",
            "",
            "Private engine, public proof.",
            "",
            f"- webhook URL: `{config['webhook_url']}`",
            f"- method: `{webhook['method']}`",
            f"- token env: `{webhook['token_env']}`",
            f"- token configured locally: `{webhook['token_configured']}`",
            f"- timeout: `{config['timeout_ms']}ms`",
            f"- IA latency budget: `{timeout['ia_latency_budget_ms']}ms`",
            f"- Portkey timeout default verdict: `{str(timeout['portkey_timeout_default_verdict']).lower()}`",
            "",
            "Headers JSON:",
            "```json",
            json.dumps(config["headers_json"], indent=2, sort_keys=True),
            "```",
            "",
            "Metadata JSON:",
            "```json",
            json.dumps(config["metadata_json"], indent=2, sort_keys=True),
            "```",
            "",
            "Expected response:",
            "```json",
            json.dumps(config["expected_response_shape"], indent=2, sort_keys=True),
            "```",
            "",
            "Verification:",
            f"- start IA: `{payload['local_verification']['start_command']}`",
            f"- probe: `{payload['local_verification']['probe_command']}`",
            f"- events: `{payload['local_verification']['events_url']}`",
            "",
            "Safety:",
            "- IA does not call Portkey Admin APIs.",
            "- IA does not push policy, mutate Portkey, mutate packets, expose secrets, or execute writes.",
            f"- {timeout['claim_boundary']}",
            "",
            f"Demo claim: {payload['demo_claim']}",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.portkey_setup",
        description="Build a secret-safe Portkey BYO Guardrail setup artifact.",
    )
    parser.add_argument("--public-base-url", required=True, help="Public IA base URL, such as Render or a tunnel URL.")
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="IA fixture used for local setup metadata.")
    parser.add_argument("--requested-mode", default=DEFAULT_REQUESTED_MODE, help="Portkey movement mode metadata.")
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS, help="Portkey webhook timeout in ms.")
    parser.add_argument(
        "--ia-latency-budget-ms",
        type=int,
        default=DEFAULT_IA_LATENCY_BUDGET_MS,
        help="Maximum target IA processing latency shown in the setup artifact.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = build_portkey_guardrail_setup(
            public_base_url=args.public_base_url,
            fixture=args.fixture,
            requested_mode=args.requested_mode,
            timeout_ms=args.timeout_ms,
            ia_latency_budget_ms=args.ia_latency_budget_ms,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_portkey_guardrail_setup_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
