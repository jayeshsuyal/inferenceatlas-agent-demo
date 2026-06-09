#!/usr/bin/env python3
"""Adversarial reviewer smoke for public IA demo surfaces.

This script assumes the FastAPI app is already running. It starts with the
normal reviewer smoke, then checks edge selectors and no-key sponsor variants
that a skeptical reviewer or agentic repo scanner is likely to probe.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from reviewer_smoke import (  # noqa: E402
    DEFAULT_BASE_URL,
    EXPECTED_SPONSOR_ORDER,
    PACKET_FIXTURES,
    SmokeFailure,
    _json_get,
    _json_post,
    _read,
    _require,
    run_smoke,
)


DEFAULT_SESSION_ID = "reviewer-stress-session"
STATIC_ROUTES = (
    "/",
    "/workbench",
    "/walkthrough",
    "/packet?fixture=mcp_tool_blast_radius&autorun=1",
    "/packet?fixture=ai_spend_budget_overrun&autorun=1",
    "/packet?fixture=miasma_pre_permission_packet&autorun=1",
)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> tuple[int, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        _url(base_url, path),
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        status = exc.code
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"{method} {path} failed: {exc}") from exc

    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _expect_http_status(
    base_url: str,
    path: str,
    *,
    expected_status: int,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> Any:
    status, body = _json_request(
        base_url,
        path,
        method=method,
        payload=payload,
        timeout=timeout,
    )
    _require(status == expected_status, f"{method} {path} returned {status}, expected {expected_status}")
    return body


def _expect_verification_safe(verification: dict[str, Any], *, selector: str) -> None:
    _require(
        verification["verification_status"] == "valid_review_required",
        f"{selector} verification must stay review-required",
    )
    for key in ("production_access", "external_writes", "permission_grants", "approval_granted"):
        _require(verification[key] is False, f"{selector} verification.{key} must stay false")
    _require(
        verification["private_boundary"]["private_source_exposed"] is False,
        f"{selector} verification must preserve private boundary",
    )


def _check_static_routes(base_url: str, timeout: float) -> None:
    for route in STATIC_ROUTES:
        html = _read(base_url, route, timeout=timeout)
        _require("Private engine, public proof." in html, f"{route} missing public proof framing")
        _require("IA did not approve. The next human action is named above." in html, f"{route} missing safety anchor")


def _check_public_packet_verification(base_url: str, timeout: float) -> None:
    for fixture in PACKET_FIXTURES:
        detail = _json_get(
            base_url,
            "/api/ia-packet?fixture=" + urllib.parse.quote(fixture),
            timeout=timeout,
        )
        packet_ref = detail["packet_reference"]

        by_fixture = _json_get(
            base_url,
            "/api/packets/" + urllib.parse.quote(fixture) + "/verification",
            timeout=timeout,
        )
        by_packet_id = _json_get(
            base_url,
            "/api/packets/" + urllib.parse.quote(packet_ref["packet_id"]) + "/verification",
            timeout=timeout,
        )

        for payload, selector in ((by_fixture, fixture), (by_packet_id, packet_ref["packet_id"])):
            _require(payload["ok"] is True, f"{selector} verification ok flag missing")
            _require(payload["read_only"] is True, f"{selector} verification must be read-only")
            verification = payload["verification"]
            _require(
                verification["packet_id"] == packet_ref["packet_id"],
                f"{selector} verification packet_id drifted",
            )
            _require(
                verification["content_hash"] == packet_ref["content_hash"],
                f"{selector} verification content hash drifted",
            )
            _expect_verification_safe(verification, selector=selector)


def _check_bad_inputs_fail_closed(base_url: str, timeout: float) -> None:
    _expect_http_status(
        base_url,
        "/api/ia-packet?fixture=does_not_exist",
        expected_status=404,
        timeout=timeout,
    )
    _expect_http_status(
        base_url,
        "/api/workbench/generate",
        method="POST",
        payload={"fixture_id": "does_not_exist"},
        expected_status=404,
        timeout=timeout,
    )
    _expect_http_status(
        base_url,
        "/api/sponsor-proof-runs",
        method="POST",
        payload={"request_path": "examples/requests/does_not_exist.yml"},
        expected_status=404,
        timeout=timeout,
    )


def _check_ask_ia_safety(base_url: str, timeout: float, session_id: str) -> None:
    prompts = (
        {
            "message": "Can Portkey allow this spend?",
            "current_fixture": "ai_spend_budget_overrun",
            "answer_kind": "decision",
            "reply_anchor": "Preview Portkey gate",
        },
        {
            "message": "Who reviews this?",
            "current_fixture": "mcp_tool_blast_radius",
            "answer_kind": "reviewer_routing",
            "reply_anchor": "Inspect reviewer routing",
        },
    )

    for prompt in prompts:
        response = _json_post(
            base_url,
            "/api/chat",
            {"session_id": session_id, **prompt},
            timeout=timeout,
        )
        answer = response["answer"]
        safety = answer["safety"]
        _require(answer["schema_version"] == "packet_advisor_answer.v0", "Ask IA answer schema drifted")
        _require(answer["answer_kind"] == prompt["answer_kind"], "Ask IA answer kind drifted")
        _require("IA does not approve" in response["reply"], "Ask IA reply lost safety anchor")
        _require(prompt["reply_anchor"] in response["reply"], f"Ask IA reply missing {prompt['reply_anchor']}")
        _require(safety["executes_external_writes"] is False, "Ask IA must not execute writes")
        _require(safety["mutates_production"] is False, "Ask IA must not mutate production")
        _require(safety["requires_human_review"] is True, "Ask IA must require human review")


def _check_portkey_preview(base_url: str, timeout: float) -> None:
    preview = _json_get(
        base_url,
        "/api/packets/ai_spend_budget_overrun/downstream/portkey?mode=dry-run",
        timeout=timeout,
    )
    portkey = preview["portkey"]
    _require(preview["read_only"] is True, "Portkey preview must be read-only")
    _require(portkey["mode"] == "dry-run", "Portkey preview must stay dry-run")
    _require(portkey["api_call_made"] is False, "Portkey preview must not call API")
    _require(portkey["portkey_guardrail_response"]["verdict"] is False, "Portkey preview must block movement")


def _expect_sponsor_run_safe(run: dict[str, Any], *, label: str) -> None:
    _require(run["status"] == "completed", f"{label} sponsor proof run did not complete")
    _require([step["sponsor"] for step in run["collector_steps"]] == EXPECTED_SPONSOR_ORDER, f"{label} sponsor order drifted")
    _require(run["invariants"]["decision_lock_unchanged"] is True, f"{label} decision lock changed")
    _require(run["invariants"]["portkey_api_call_made"] is False, f"{label} made Portkey API call")
    safety = run["safety_boundary"]
    _require(safety["read_only"] is True, f"{label} run must be read-only")
    for key in (
        "live_calls_made",
        "approves_access",
        "grants_permissions",
        "executes_external_writes",
        "mutates_production",
        "approves_spend",
        "selects_provider",
        "guarantees_savings",
    ):
        _require(safety[key] is False, f"{label} safety_boundary.{key} must stay false")


def _check_sponsor_variants(base_url: str, timeout: float) -> None:
    composio_payload = _json_post(
        base_url,
        "/api/sponsor-proof-runs",
        {"request_path": "examples/requests/support_triage_trial.yml", "composio_dry_run": True},
        timeout=timeout,
    )
    composio_run = composio_payload["run"]
    _expect_sponsor_run_safe(composio_run, label="composio_dry_run")
    composio = composio_run["dry_run_sponsor_proof"]["composio"]
    _require(composio["api_call_made"] is False, "Composio dry-run must not call API")
    _require(composio["composio_execute_allowed"] is False, "Composio dry-run must not execute")

    tavily_payload = _json_post(
        base_url,
        "/api/sponsor-proof-runs",
        {"request_path": "examples/requests/support_triage_trial.yml", "live_tavily": True},
        timeout=timeout,
    )
    tavily_run = tavily_payload["run"]
    _expect_sponsor_run_safe(tavily_run, label="live_tavily_no_key")
    tavily = tavily_run["live_sponsor_proof"]["tavily"]
    _require(tavily["live_requested"] is True, "Tavily opt-in marker missing")
    _require(tavily["live_call_attempted"] is False, "Tavily no-key path must not attempt a live call")
    _require(tavily["live_call_count"] == 0, "Tavily no-key path must make zero live calls")
    _require(tavily["fallback_used"] is True, "Tavily no-key path must use fallback")
    _require(tavily["fallback_reason"] == "tavily_api_key_missing", "Tavily fallback reason drifted")

    ledger = _json_get(base_url, "/api/sponsor-proof-run-ledger", timeout=timeout)["ledger"]
    _require(ledger["read_only"] is True, "sponsor run ledger must be read-only")
    _require(ledger["safety_summary"]["no_external_writes"] is True, "ledger write safety summary drifted")
    _require(
        ledger["safety_summary"]["all_decision_locks_unchanged"] is True,
        "ledger decision-lock summary drifted",
    )
    created_run_ids = {composio_run["run_id"], tavily_run["run_id"]}
    created_records = [item for item in ledger["runs"] if item["run_id"] in created_run_ids]
    _require(len(created_records) == 2, "stress-created sponsor runs missing from ledger")
    _require(
        all(item["safety_lock"]["live_calls_made"] is False for item in created_records),
        "stress-created no-key runs must not record live calls",
    )
    for run in (composio_payload, tavily_payload):
        record = run["ledger_record"]
        _require(record["safety_lock"]["read_only"] is True, "ledger record must stay read-only")
        _require(record["safety_lock"]["live_calls_made"] is False, "ledger record live-call lock drifted")
        _require(record["safety_lock"]["decision_lock_unchanged"] is True, "ledger record decision lock drifted")
        _require(record["safety_lock"]["executes_external_writes"] is False, "ledger record write lock drifted")


def run_stress(base_url: str, *, timeout: float, session_id: str) -> list[str]:
    baseline = run_smoke(base_url, timeout=timeout, session_id=session_id)
    steps: list[tuple[str, Any]] = [
        ("static route stress", lambda: _check_static_routes(base_url, timeout)),
        ("public packet verification selectors", lambda: _check_public_packet_verification(base_url, timeout)),
        ("bad inputs fail closed", lambda: _check_bad_inputs_fail_closed(base_url, timeout)),
        ("Portkey dry-run preview", lambda: _check_portkey_preview(base_url, timeout)),
        ("Ask IA safety variants", lambda: _check_ask_ia_safety(base_url, timeout, session_id)),
        ("sponsor proof variants", lambda: _check_sponsor_variants(base_url, timeout)),
    ]

    passed = [f"baseline:{item}" for item in baseline]
    for label, fn in steps:
        fn()
        passed.append(label)
        print(f"OK {label}")
    return passed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stress-test the served reviewer journey and packet verification edges.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Served app URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request timeout in seconds.")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID, help="Stable stress session id.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        passed = run_stress(args.base_url, timeout=args.timeout, session_id=args.session_id)
    except SmokeFailure as exc:
        print(f"Reviewer stress failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Reviewer stress passed: "
        + " -> ".join(passed)
        + " (public packet selectors verified, no live keys required, no approval/write path)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
