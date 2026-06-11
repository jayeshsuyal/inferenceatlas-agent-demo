#!/usr/bin/env python3
"""Portkey BYO Guardrails live-probe harness.

This script sends a Portkey-shaped webhook payload to the local IA guardrail
endpoint and verifies that IA returns a packet-backed verdict without mutating
the packet, Portkey policy, or production state.

It never prints the shared guardrail token or any secret-shaped values.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_FIXTURE = "ai_spend_budget_overrun"
DEFAULT_REQUESTED_MODE = "model_request"
DEFAULT_EXPECT_VERDICT = False
PORTKEY_GUARDRAIL_TOKEN_ENV = "PORTKEY_GUARDRAIL_TOKEN"
PORTKEY_GUARDRAIL_TOKEN_HEADER = "x-ia-portkey-guardrail-token"
PORTKEY_REHEARSAL_MODE_HEADER = "X-IA-Rehearsal-Mode"
PORTKEY_DOC_URL = "https://portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails"
PORTKEY_DOCS_LAST_CHECKED = "2026-06-09"


class PortkeyProbeFailure(AssertionError):
    """Portkey guardrail probe failed at a product-relevant boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PortkeyProbeFailure(message)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> tuple[int, Any, float]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        _url(base_url, path),
        data=data,
        headers=request_headers,
        method=method,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except urllib.error.URLError as exc:
        raise PortkeyProbeFailure(f"{method} {path} failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000

    try:
        return status, json.loads(raw), elapsed_ms
    except json.JSONDecodeError:
        return status, raw, elapsed_ms


def build_portkey_probe_payload(
    *,
    fixture: str = DEFAULT_FIXTURE,
    requested_mode: str = DEFAULT_REQUESTED_MODE,
    review_run_id: str | None = None,
    packet_id: str | None = None,
    revision_id: str | None = None,
) -> dict[str, Any]:
    """Build a Portkey BYO Guardrails beforeRequestHook payload."""
    metadata = {
        "ia_fixture": fixture,
        "ia_requested_mode": requested_mode,
    }
    if review_run_id:
        metadata = {
            "ia_review_run_id": review_run_id,
            "ia_packet_id": packet_id or "",
            "ia_revision_id": revision_id or "",
            "ia_requested_mode": requested_mode,
            "ia_source_of_truth": "ReviewRun",
        }
    return {
        "eventType": "beforeRequestHook",
        "provider": "openai",
        "requestType": "chatComplete",
        "metadata": metadata,
        "request": {
            "metadata": metadata,
            "json": {
                "model": "demo-model",
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": "IA Portkey guardrail probe: can this packet-backed request move?",
                    }
                ],
            },
            "text": "IA Portkey guardrail probe: can this packet-backed request move?",
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


def _auth_headers(
    token: str,
    *,
    header_mode: str,
    rehearsal_token: str | None = None,
) -> dict[str, str]:
    if header_mode == "authorization":
        headers = {"Authorization": f"Bearer {token}"}
    elif header_mode == "x-ia":
        headers = {PORTKEY_GUARDRAIL_TOKEN_HEADER: token}
    else:
        raise PortkeyProbeFailure(f"unsupported header mode: {header_mode}")
    if rehearsal_token:
        headers[PORTKEY_REHEARSAL_MODE_HEADER] = rehearsal_token
    return headers


def _assert_response_safe(
    response: dict[str, Any],
    *,
    expect_verdict: bool,
    max_response_ms: int,
) -> tuple[dict[str, Any], str]:
    _require(response.get("verdict") is expect_verdict, "Portkey verdict did not match expected packet outcome")
    _require("transformedData" not in response, "IA guardrail probe must not transform Portkey request/response")
    data = response.get("data")
    _require(isinstance(data, dict), "Portkey guardrail response must include data")
    _require(data.get("delivery_mode") == "live_guardrail_webhook", "delivery mode drifted")
    _require(int(data.get("elapsed_ms", 999999)) <= max_response_ms, "guardrail response exceeded latency budget")

    event = data.get("guardrail_event")
    _require(isinstance(event, dict), "guardrail event reference missing")
    event_id = str(event.get("event_id") or "")
    _require(event_id.startswith("portkey-guardrail-"), "guardrail event id missing")

    packet_ref = data.get("ia_packet_reference")
    _require(isinstance(packet_ref, dict), "IA packet reference missing")
    _require(bool(packet_ref.get("packet_id")), "packet_id missing")
    _require(bool(packet_ref.get("revision_id")), "revision_id missing")
    _require(str(packet_ref.get("content_hash", "")).startswith("sha256:"), "content_hash missing")

    safety = data.get("safety")
    _require(isinstance(safety, dict), "safety payload missing")
    for key in (
        "read_only",
        "packet_mutation_allowed",
        "portkey_policy_mutation_allowed",
        "portkey_api_call_made",
        "approves_access",
        "approves_spend",
        "executes_external_writes",
        "mutates_production",
        "raw_agent_intent_trusted",
    ):
        _require(key in safety, f"safety.{key} missing")
    _require(safety["read_only"] is True, "guardrail must stay read-only")
    _require(safety["packet_mutation_allowed"] is False, "guardrail must not mutate packet")
    _require(safety["portkey_policy_mutation_allowed"] is False, "guardrail must not mutate Portkey policy")
    _require(safety["portkey_api_call_made"] is False, "guardrail must not call Portkey API")
    _require(safety["executes_external_writes"] is False, "guardrail must not execute external writes")
    _require(safety["raw_agent_intent_trusted"] is False, "raw agent intent must not be trusted")
    return data, event_id


def _assert_event_recorded(base_url: str, event_id: str, *, timeout: float) -> dict[str, Any]:
    status, body, _elapsed = _json_request(base_url, "/api/portkey/guardrail/events", timeout=timeout)
    _require(status == 200, f"guardrail events endpoint returned {status}")
    _require(isinstance(body, dict), "guardrail events endpoint must return JSON")
    _require(body.get("read_only") is True, "guardrail events endpoint must be read-only")
    events = body.get("events", [])
    _require(isinstance(events, list), "guardrail events must be a list")
    matches = [item for item in events if item.get("event_id") == event_id]
    _require(bool(matches), "guardrail probe event was not recorded")
    event = matches[0]
    _require(event.get("read_only") is True, "recorded guardrail event must be read-only")
    _require(event.get("verdict") in {True, False}, "recorded guardrail event verdict missing")
    return event


def run_portkey_guardrail_probe(
    base_url: str,
    *,
    fixture: str = DEFAULT_FIXTURE,
    requested_mode: str = DEFAULT_REQUESTED_MODE,
    expect_verdict: bool = DEFAULT_EXPECT_VERDICT,
    timeout: float = 10.0,
    max_response_ms: int = 150,
    header_mode: str = "authorization",
    review_run_id: str | None = None,
    packet_id: str | None = None,
    revision_id: str | None = None,
    rehearsal_token_env: str | None = None,
) -> dict[str, Any]:
    """Run the Portkey-shaped webhook probe and return a safe summary."""
    token = os.getenv(PORTKEY_GUARDRAIL_TOKEN_ENV, "").strip()
    _require(bool(token), f"{PORTKEY_GUARDRAIL_TOKEN_ENV} must be configured for the Portkey probe")

    rehearsal_token = ""
    if rehearsal_token_env:
        rehearsal_token = os.getenv(rehearsal_token_env, "").strip()
        _require(bool(rehearsal_token), f"{rehearsal_token_env} must be configured for rehearsal mode")

    payload = build_portkey_probe_payload(
        fixture=fixture,
        requested_mode=requested_mode,
        review_run_id=review_run_id,
        packet_id=packet_id,
        revision_id=revision_id,
    )
    status, response, client_elapsed_ms = _json_request(
        base_url,
        "/api/portkey/guardrail",
        method="POST",
        payload=payload,
        headers=_auth_headers(token, header_mode=header_mode, rehearsal_token=rehearsal_token or None),
        timeout=timeout,
    )
    _require(status == 200, f"guardrail webhook returned {status}, expected 200")
    _require(isinstance(response, dict), "guardrail webhook must return JSON")
    data, event_id = _assert_response_safe(
        response,
        expect_verdict=expect_verdict,
        max_response_ms=max_response_ms,
    )
    event = _assert_event_recorded(base_url, event_id, timeout=timeout)

    packet_ref = data["ia_packet_reference"]
    return {
        "schema_version": "portkey_guardrail_probe.v0",
        "status": "passed",
        "base_url": base_url.rstrip("/"),
        "docs_reference": {
            "portkey_byo_guardrails": PORTKEY_DOC_URL,
            "last_checked": PORTKEY_DOCS_LAST_CHECKED,
        },
        "probe": {
            "event_type": payload["eventType"],
            "fixture": fixture,
            "review_run_id": review_run_id,
            "requested_mode": requested_mode,
            "header_mode": header_mode,
            "rehearsal_header_sent": bool(rehearsal_token),
            "client_elapsed_ms": round(client_elapsed_ms, 2),
            "server_elapsed_ms": data["elapsed_ms"],
            "expected_verdict": expect_verdict,
            "actual_verdict": response["verdict"],
            "transformed_data_returned": False,
        },
        "packet_reference": {
            "packet_id": packet_ref["packet_id"],
            "revision_id": packet_ref["revision_id"],
            "content_hash": packet_ref["content_hash"],
            "verdict_class": data["verdict_class"],
        },
        "guardrail_event": {
            "event_id": event_id,
            "recorded": True,
            "recorded_verdict": event["verdict"],
            "read_only": event["read_only"],
            "kind": event.get("kind"),
            "review_run_id": event.get("review_run_id"),
        },
        "safety": {
            "read_only": True,
            "packet_mutation_allowed": False,
            "portkey_policy_mutation_allowed": False,
            "portkey_api_call_made": False,
            "executes_external_writes": False,
            "raw_agent_intent_trusted": False,
            "secrets_printed": False,
        },
    }


def render_summary(summary: dict[str, Any]) -> str:
    probe = summary["probe"]
    packet = summary["packet_reference"]
    event = summary["guardrail_event"]
    return "\n".join(
        [
            "# Portkey BYO Guardrail Probe",
            "",
            "Private engine, public proof.",
            "",
            f"- status: `{summary['status']}`",
            f"- event type: `{probe['event_type']}`",
            f"- fixture: `{probe['fixture']}`",
            f"- requested mode: `{probe['requested_mode']}`",
            f"- verdict: `{str(probe['actual_verdict']).lower()}`",
            f"- packet_id: `{packet['packet_id']}`",
            f"- revision_id: `{packet['revision_id']}`",
            f"- verdict_class: `{packet['verdict_class']}`",
            f"- server elapsed: `{probe['server_elapsed_ms']}ms`",
            f"- event recorded: `{event['event_id']}`",
            "",
            "Safety: IA returned a packet-backed verdict only. It did not mutate the packet, call Portkey APIs, "
            "push policy, execute writes, or trust raw agent intent.",
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe the IA Portkey BYO Guardrails webhook with a Portkey-shaped payload."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Local or public IA web base URL.")
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE, help="IA fixture to attach as Portkey metadata.")
    parser.add_argument("--requested-mode", default=DEFAULT_REQUESTED_MODE, help="Requested movement mode metadata.")
    parser.add_argument("--review-run-id", default=None, help="Optional ReviewRun id for current-packet probing.")
    parser.add_argument("--packet-id", default=None, help="Expected IA packet id for ReviewRun probing.")
    parser.add_argument("--revision-id", default=None, help="Expected IA revision id for ReviewRun probing.")
    parser.add_argument(
        "--rehearsal-token-env",
        default=None,
        help="Optional env var whose value is sent as X-IA-Rehearsal-Mode.",
    )
    parser.add_argument(
        "--expect-verdict",
        choices=("true", "false"),
        default="false",
        help="Expected Portkey guardrail verdict for this fixture and requested mode.",
    )
    parser.add_argument(
        "--header-mode",
        choices=("authorization", "x-ia"),
        default="authorization",
        help="Header shape to send. Portkey UI commonly uses Authorization: Bearer <token>.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    parser.add_argument("--max-response-ms", type=int, default=150, help="Maximum IA webhook processing time.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = run_portkey_guardrail_probe(
            args.base_url,
            fixture=args.fixture,
            requested_mode=args.requested_mode,
            expect_verdict=args.expect_verdict == "true",
            timeout=args.timeout,
            max_response_ms=args.max_response_ms,
            header_mode=args.header_mode,
            review_run_id=args.review_run_id,
            packet_id=args.packet_id,
            revision_id=args.revision_id,
            rehearsal_token_env=args.rehearsal_token_env,
        )
    except PortkeyProbeFailure as exc:
        print(f"Portkey guardrail probe failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
