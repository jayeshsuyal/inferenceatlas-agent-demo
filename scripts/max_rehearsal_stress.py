#!/usr/bin/env python3
"""Bounded max rehearsal stress for the public IA demo.

This runner exercises the local, non-mutating sponsor proof loop under load:

- keyed live-read sponsor rehearsals
- fallback/offline sponsor proof runs
- packet/chat/Portkey/ledger API pressure
- adversarial fail-closed inputs
- cross-run ledger safety invariants

It never prints API keys or secret-shaped values. Run it only against a local
server with a temp ledger directory.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
from pathlib import Path
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from keyed_sponsor_rehearsal import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_REQUEST_PATH,
    RehearsalFailure,
    run_keyed_rehearsal,
)


SCHEMA_VERSION = "max_rehearsal_stress.v0"
DEFAULT_SESSION_ID = "max-rehearsal-stress-session"
DEFAULT_KEYED_RUNS = 20
DEFAULT_FALLBACK_RUNS = 10
DEFAULT_CONCURRENCY = 3
DEFAULT_LOAD_REQUESTS_PER_ROUTE = 12
EXPECTED_SPONSOR_ORDER = ["tavily", "composio", "openclaw", "nebius"]
SECRET_PATTERNS = (
    re.compile(r"sk-proj-[A-Za-z0-9_-]{12,}"),
    re.compile(r"tvly-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ak_[A-Za-z0-9_-]{12,}"),
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bv1\.[A-Za-z0-9_.-]{24,}"),
)


class StressFailure(AssertionError):
    """Max rehearsal stress failed at a product-relevant boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StressFailure(message)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    raw_body: bytes | None = None,
    timeout: float,
) -> tuple[int, Any, float]:
    data = raw_body
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        _url(base_url, path),
        data=data,
        headers=headers,
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
    except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
        raise StressFailure(f"{method} {path} failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000

    try:
        return status, json.loads(raw), elapsed_ms
    except json.JSONDecodeError:
        return status, raw, elapsed_ms


def _json_get(base_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    status, body, _elapsed = _json_request(base_url, path, timeout=timeout)
    _require(status == 200, f"GET {path} returned {status}, expected 200")
    _require(isinstance(body, dict), f"GET {path} did not return a JSON object")
    return body


def _json_post(base_url: str, path: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    status, body, _elapsed = _json_request(base_url, path, method="POST", payload=payload, timeout=timeout)
    _require(status == 200, f"POST {path} returned {status}, expected 200")
    _require(isinstance(body, dict), f"POST {path} did not return a JSON object")
    return body


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((percentile / 100) * len(ordered)) - 1))
    return ordered[index]


def _latency_summary(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "p50_ms": round(_percentile(values, 50), 2),
        "p95_ms": round(_percentile(values, 95), 2),
        "p99_ms": round(_percentile(values, 99), 2),
    }


def _secret_string_count(text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in SECRET_PATTERNS)


def _assert_keyed_summary_safe(summary: dict[str, Any]) -> None:
    _require(summary["status"] == "passed", "keyed rehearsal summary must pass")
    _require(summary["health"]["llm_provider"] == "nebius", "keyed rehearsal must use Nebius")
    _require(summary["health"]["tavily"] is True, "keyed rehearsal must have Tavily")
    _require(summary["health"]["composio"] is True, "keyed rehearsal must have Composio")
    _require(summary["health"]["composio_dry_run"] is True, "Composio must remain dry-run")
    _require(summary["run"]["read_only"] is True, "keyed run must be read-only")
    _require(summary["run"]["live_calls_made"] is True, "keyed run must record live read calls")
    _require(summary["run"]["executes_external_writes"] is False, "keyed run must not write externally")
    _require(summary["run"]["decision_lock_unchanged"] is True, "keyed run must not mutate packet decision lock")
    _require(summary["tavily"]["fallback_used"] is False, "Tavily must not fall back during keyed stress")
    _require(int(summary["tavily"]["live_call_count"]) > 0, "Tavily live call count must be positive")
    _require(summary["nebius"]["fallback_used"] is False, "Nebius must not fall back during keyed stress")
    _require(int(summary["nebius"]["live_call_count"]) > 0, "Nebius live call count must be positive")
    _require(summary["nebius"]["required_anchors_present"] is True, "Nebius safety anchors must be present")
    _require(summary["nebius"]["forbidden_phrases_present"] == [], "Nebius must not emit forbidden phrases")
    _require(summary["composio"]["api_call_made"] is False, "Composio must not call execute API")
    _require(summary["composio"]["execute_allowed"] is False, "Composio execute must stay blocked")
    _require(summary["portkey"]["api_call_made"] is False, "Portkey must not call mutation API")
    _require(summary["portkey"]["guardrail_verdict"] is False, "Portkey guardrail must block movement")
    _require(summary["ledger"]["executes_external_writes"] is False, "ledger record must preserve no writes")


def _assert_fallback_run_safe(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("ok") is True, "fallback sponsor run must return ok=true")
    _require(payload.get("read_only") is True, "fallback sponsor run must stay read-only")
    run = payload["run"]
    _require(run["status"] == "completed", "fallback sponsor run must complete")
    _require([step["sponsor"] for step in run["collector_steps"]] == EXPECTED_SPONSOR_ORDER, "fallback sponsor order drifted")
    _require(run["invariants"]["decision_lock_unchanged"] is True, "fallback run changed decision lock")
    _require(run["invariants"]["portkey_api_call_made"] is False, "fallback run called Portkey API")
    safety = run["safety_boundary"]
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
        _require(safety[key] is False, f"fallback safety_boundary.{key} must stay false")
    record = payload["ledger_record"]
    _require(record["safety_lock"]["live_calls_made"] is False, "fallback ledger record must not record live calls")
    _require(record["safety_lock"]["executes_external_writes"] is False, "fallback ledger record must preserve no writes")
    _require(record["safety_lock"]["decision_lock_unchanged"] is True, "fallback ledger record decision lock drifted")
    return payload


def _run_keyed_loop(base_url: str, *, keyed_runs: int, concurrency: int, timeout: float) -> list[dict[str, Any]]:
    def one_run(index: int) -> dict[str, Any]:
        summary = run_keyed_rehearsal(base_url, timeout=timeout)
        _assert_keyed_summary_safe(summary)
        summary["stress_index"] = index
        return summary

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one_run, index) for index in range(keyed_runs)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RehearsalFailure as exc:
                raise StressFailure(str(exc)) from exc
    return sorted(results, key=lambda item: item["stress_index"])


def _run_fallback_loop(base_url: str, *, fallback_runs: int, concurrency: int, timeout: float) -> list[dict[str, Any]]:
    def one_run(index: int) -> dict[str, Any]:
        payload = _json_post(
            base_url,
            "/api/sponsor-proof-runs",
            {"request_path": DEFAULT_REQUEST_PATH, "composio_dry_run": True},
            timeout=timeout,
        )
        checked = _assert_fallback_run_safe(payload)
        checked["stress_index"] = index
        return checked

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one_run, index) for index in range(fallback_runs)]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item["stress_index"])


def _pressure_requests(session_id: str) -> list[dict[str, Any]]:
    return [
        {"label": "health", "method": "GET", "path": "/api/health"},
        {"label": "packet", "method": "GET", "path": "/api/ia-packet?fixture=mcp_tool_blast_radius"},
        {
            "label": "portkey",
            "method": "GET",
            "path": "/api/packets/ai_spend_budget_overrun/downstream/portkey?mode=dry-run",
        },
        {
            "label": "chat",
            "method": "POST",
            "path": "/api/chat",
            "payload": {
                "session_id": session_id,
                "message": "Can Portkey allow this spend?",
                "current_fixture": "ai_spend_budget_overrun",
            },
        },
        {"label": "ledger", "method": "GET", "path": "/api/sponsor-proof-run-ledger"},
    ]


def _run_endpoint_pressure(
    base_url: str,
    *,
    concurrency: int,
    load_requests_per_route: int,
    session_id: str,
    timeout: float,
) -> dict[str, Any]:
    requests = _pressure_requests(session_id)
    baseline: dict[str, list[float]] = {item["label"]: [] for item in requests}
    loaded: dict[str, list[float]] = {item["label"]: [] for item in requests}

    for item in requests:
        for _ in range(3):
            status, _body, elapsed = _json_request(
                base_url,
                item["path"],
                method=item["method"],
                payload=item.get("payload"),
                timeout=timeout,
            )
            _require(status == 200, f"{item['label']} baseline returned {status}")
            baseline[item["label"]].append(elapsed)

    work_items = [item for item in requests for _ in range(load_requests_per_route)]

    def one_request(item: dict[str, Any]) -> tuple[str, float]:
        status, _body, elapsed = _json_request(
            base_url,
            item["path"],
            method=item["method"],
            payload=item.get("payload"),
            timeout=timeout,
        )
        _require(status == 200, f"{item['label']} load returned {status}")
        return item["label"], elapsed

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one_request, item) for item in work_items]
        for future in as_completed(futures):
            label, elapsed = future.result()
            loaded[label].append(elapsed)

    routes = {}
    for label in baseline:
        baseline_summary = _latency_summary(baseline[label])
        loaded_summary = _latency_summary(loaded[label])
        baseline_p50 = max(baseline_summary["p50_ms"], 1.0)
        ratio = round(loaded_summary["p99_ms"] / baseline_p50, 2)
        routes[label] = {
            "baseline": baseline_summary,
            "under_load": loaded_summary,
            "p99_to_baseline_p50_ratio": ratio,
            "target_ratio_under_3x": ratio < 3,
        }
    return {"routes": routes, "load_requests_per_route": load_requests_per_route, "concurrency": concurrency}


def _run_adversarial_inputs(base_url: str, *, timeout: float, session_id: str) -> list[dict[str, Any]]:
    checks = [
        {
            "label": "missing fixture",
            "method": "GET",
            "path": "/api/ia-packet?fixture=does_not_exist",
            "expected_status": 404,
        },
        {
            "label": "sql-like fixture id",
            "method": "GET",
            "path": "/api/ia-packet?fixture=" + urllib.parse.quote("'; DROP TABLE--"),
            "expected_status": 404,
        },
        {
            "label": "oversized fixture id",
            "method": "GET",
            "path": "/api/ia-packet?fixture=" + ("a" * 1000),
            "expected_status": 404,
        },
        {
            "label": "missing workbench field",
            "method": "POST",
            "path": "/api/workbench/generate",
            "payload": {},
            "expected_status": 422,
        },
        {
            "label": "unknown workbench fixture",
            "method": "POST",
            "path": "/api/workbench/generate",
            "payload": {"fixture_id": "does_not_exist"},
            "expected_status": 404,
        },
        {
            "label": "request path outside public fixtures",
            "method": "POST",
            "path": "/api/sponsor-proof-runs",
            "payload": {"request_path": "README.md"},
            "expected_status": 400,
        },
        {
            "label": "missing sponsor request path",
            "method": "POST",
            "path": "/api/sponsor-proof-runs",
            "payload": {"request_path": "examples/requests/does_not_exist.yml"},
            "expected_status": 404,
        },
        {
            "label": "stale run id",
            "method": "GET",
            "path": "/api/sponsor-proof-runs/not-a-real-run",
            "expected_status": 404,
        },
        {
            "label": "invalid json body",
            "method": "POST",
            "path": "/api/chat",
            "raw_body": b"{not-json",
            "expected_status": 422,
        },
        {
            "label": "oversized chat prompt",
            "method": "POST",
            "path": "/api/chat",
            "payload": {
                "session_id": session_id,
                "message": "x" * 8001,
                "current_fixture": "mcp_tool_blast_radius",
            },
            "expected_status": 422,
        },
        {
            "label": "unicode zero-width prompt",
            "method": "POST",
            "path": "/api/chat",
            "payload": {
                "session_id": session_id,
                "message": "Can this move?\u200b\u200c\u200d",
                "current_fixture": "mcp_tool_blast_radius",
            },
            "expected_status": 200,
            "required_reply": "IA does not approve",
        },
    ]

    results = []
    for check in checks:
        status, body, elapsed = _json_request(
            base_url,
            check["path"],
            method=check["method"],
            payload=check.get("payload"),
            raw_body=check.get("raw_body"),
            timeout=timeout,
        )
        passed = status == check["expected_status"]
        if passed and check.get("required_reply"):
            passed = isinstance(body, dict) and check["required_reply"] in str(body.get("reply", ""))
        results.append(
            {
                "label": check["label"],
                "status": status,
                "expected_status": check["expected_status"],
                "passed": passed,
                "elapsed_ms": round(elapsed, 2),
            }
        )
    failures = [item for item in results if not item["passed"]]
    _require(not failures, f"adversarial checks failed: {failures}")
    return results


def _assert_ledger_invariants(
    ledger_payload: dict[str, Any],
    *,
    keyed_run_ids: set[str],
    fallback_run_ids: set[str],
) -> dict[str, Any]:
    _require(ledger_payload.get("ok") is True, "ledger API must return ok=true")
    _require(ledger_payload.get("read_only") is True, "ledger API must stay read-only")
    ledger = ledger_payload["ledger"]
    _require(ledger["read_only"] is True, "ledger must stay read-only")
    _require(ledger["safety_summary"]["no_external_writes"] is True, "ledger must preserve no external writes")
    _require(
        ledger["safety_summary"]["all_decision_locks_unchanged"] is True,
        "ledger must preserve all decision locks",
    )
    records = ledger.get("runs", [])
    record_ids = {record["run_id"] for record in records}
    _require(keyed_run_ids.issubset(record_ids), "ledger missing keyed run records")
    _require(fallback_run_ids.issubset(record_ids), "ledger missing fallback run records")
    _require(
        not any(
            record["safety_lock"]["live_calls_made"] and record["safety_lock"]["executes_external_writes"]
            for record in records
        ),
        "ledger contains live-call record with external writes",
    )
    _require(
        all(record["safety_lock"]["decision_lock_unchanged"] is True for record in records),
        "ledger contains a changed decision lock",
    )
    _require(
        all(record["safety_lock"]["executes_external_writes"] is False for record in records),
        "ledger contains external writes",
    )
    return {
        "record_count": ledger["record_count"],
        "keyed_records_seen": len(keyed_run_ids),
        "fallback_records_seen": len(fallback_run_ids),
        "no_external_writes": ledger["safety_summary"]["no_external_writes"],
        "all_decision_locks_unchanged": ledger["safety_summary"]["all_decision_locks_unchanged"],
        "no_live_call_with_external_write": True,
    }


def _build_counters(
    keyed: list[dict[str, Any]],
    fallback: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> dict[str, int]:
    live_writes = 0
    approvals = 0
    packet_mutations = 0
    live_calls = 0
    fallback_calls = 0

    for summary in keyed:
        live_calls += int(summary["tavily"]["live_call_count"]) + int(summary["nebius"]["live_call_count"])
        live_writes += int(bool(summary["run"]["executes_external_writes"]))
        live_writes += int(bool(summary["composio"]["api_call_made"]))
        live_writes += int(bool(summary["portkey"]["api_call_made"]))
        approvals += int(bool(summary["portkey"]["guardrail_verdict"]))
        packet_mutations += int(not summary["run"]["decision_lock_unchanged"])

    for payload in fallback:
        safety = payload["run"]["safety_boundary"]
        fallback_calls += 1
        live_writes += int(bool(safety["executes_external_writes"]))
        approvals += sum(
            int(bool(safety[key]))
            for key in ("approves_access", "grants_permissions", "approves_spend", "selects_provider")
        )
        packet_mutations += int(not payload["run"]["invariants"]["decision_lock_unchanged"])

    packet_mutations += int(not ledger["all_decision_locks_unchanged"])
    return {
        "live_writes_attempted": live_writes,
        "approvals_emitted": approvals,
        "packet_mutations_post_seal": packet_mutations,
        "secret_strings_in_output": 0,
        "ledger_runs_total": int(ledger["record_count"]),
        "live_calls_made": live_calls,
        "fallback_runs_made": fallback_calls,
    }


def _assert_pass_conditions(report: dict[str, Any]) -> None:
    counters = report["pass_condition_counters"]
    for key in (
        "live_writes_attempted",
        "approvals_emitted",
        "packet_mutations_post_seal",
        "secret_strings_in_output",
    ):
        _require(counters[key] == 0, f"{key} must be 0")
    _require(report["keyed_loop"]["completed"] == report["keyed_loop"]["requested"], "not all keyed runs completed")
    _require(
        report["fallback_loop"]["completed"] == report["fallback_loop"]["requested"],
        "not all fallback runs completed",
    )
    _require(all(item["passed"] for item in report["adversarial_inputs"]), "adversarial checks must all pass")
    _require(report["ledger_contamination"]["no_external_writes"] is True, "ledger external writes invariant failed")
    _require(
        report["ledger_contamination"]["no_live_call_with_external_write"] is True,
        "ledger live-call/write invariant failed",
    )


def run_max_stress(
    base_url: str,
    *,
    keyed_runs: int = DEFAULT_KEYED_RUNS,
    fallback_runs: int = DEFAULT_FALLBACK_RUNS,
    concurrency: int = DEFAULT_CONCURRENCY,
    load_requests_per_route: int = DEFAULT_LOAD_REQUESTS_PER_ROUTE,
    timeout: float = 45.0,
    session_id: str = DEFAULT_SESSION_ID,
) -> dict[str, Any]:
    _require(keyed_runs >= 1, "keyed_runs must be at least 1")
    _require(fallback_runs >= 1, "fallback_runs must be at least 1")
    _require(concurrency >= 1, "concurrency must be at least 1")
    _require(load_requests_per_route >= 1, "load_requests_per_route must be at least 1")

    started = time.perf_counter()
    health = _json_get(base_url, "/api/health", timeout=timeout)
    _require(health.get("ok") is True, "health must be ok")
    _require(health.get("llm_provider") == "nebius", "max stress requires Nebius live-read server")
    _require(health.get("tavily") is True, "max stress requires Tavily key")
    _require(health.get("composio") is True, "max stress requires Composio key")
    _require(health.get("composio_dry_run") is True, "Composio must remain dry-run")

    keyed_summaries = _run_keyed_loop(base_url, keyed_runs=keyed_runs, concurrency=concurrency, timeout=timeout)
    fallback_payloads = _run_fallback_loop(
        base_url,
        fallback_runs=fallback_runs,
        concurrency=concurrency,
        timeout=timeout,
    )
    latency = _run_endpoint_pressure(
        base_url,
        concurrency=concurrency,
        load_requests_per_route=load_requests_per_route,
        session_id=session_id,
        timeout=timeout,
    )
    adversarial = _run_adversarial_inputs(base_url, timeout=timeout, session_id=session_id)

    keyed_run_ids = {item["run"]["run_id"] for item in keyed_summaries}
    fallback_run_ids = {item["run"]["run_id"] for item in fallback_payloads}
    ledger = _assert_ledger_invariants(
        _json_get(base_url, "/api/sponsor-proof-run-ledger", timeout=timeout),
        keyed_run_ids=keyed_run_ids,
        fallback_run_ids=fallback_run_ids,
    )
    counters = _build_counters(keyed_summaries, fallback_payloads, ledger)

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "base_url": base_url.rstrip("/"),
        "duration_seconds": round(time.perf_counter() - started, 2),
        "health": {
            "llm_provider": health.get("llm_provider"),
            "llm_model": health.get("llm_model"),
            "tavily": bool(health.get("tavily")),
            "composio": bool(health.get("composio")),
            "composio_dry_run": bool(health.get("composio_dry_run")),
        },
        "keyed_loop": {
            "requested": keyed_runs,
            "completed": len(keyed_summaries),
            "concurrency": concurrency,
            "unique_run_ids": len(keyed_run_ids),
            "tavily_live_calls": sum(int(item["tavily"]["live_call_count"]) for item in keyed_summaries),
            "tavily_source_urls": sum(int(item["tavily"]["source_url_count"]) for item in keyed_summaries),
            "nebius_live_calls": sum(int(item["nebius"]["live_call_count"]) for item in keyed_summaries),
            "composio_api_calls": sum(int(bool(item["composio"]["api_call_made"])) for item in keyed_summaries),
            "portkey_api_calls": sum(int(bool(item["portkey"]["api_call_made"])) for item in keyed_summaries),
            "decision_locks_unchanged": all(item["run"]["decision_lock_unchanged"] for item in keyed_summaries),
            "external_writes": any(item["run"]["executes_external_writes"] for item in keyed_summaries),
        },
        "fallback_loop": {
            "requested": fallback_runs,
            "completed": len(fallback_payloads),
            "unique_run_ids": len(fallback_run_ids),
            "live_calls_made": sum(int(item["run"]["safety_boundary"]["live_calls_made"]) for item in fallback_payloads),
            "external_writes": any(item["run"]["safety_boundary"]["executes_external_writes"] for item in fallback_payloads),
        },
        "latency": latency,
        "adversarial_inputs": adversarial,
        "ledger_contamination": ledger,
        "pass_condition_counters": counters,
        "private_boundary": {
            "local_only": base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost"),
            "private_source_exposed": False,
            "secrets_printed": False,
            "principle": "Private engine, public proof.",
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    secret_count = _secret_string_count(rendered)
    report["pass_condition_counters"]["secret_strings_in_output"] = secret_count
    report["private_boundary"]["secrets_printed"] = secret_count > 0
    _assert_pass_conditions(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    counters = report["pass_condition_counters"]
    keyed = report["keyed_loop"]
    fallback = report["fallback_loop"]
    ledger = report["ledger_contamination"]
    lines = [
        "# Stress Test Run",
        "",
        "Private engine, public proof.",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{report['status']}`",
        f"- base_url: `{report['base_url']}`",
        f"- duration_seconds: `{report['duration_seconds']}`",
        "",
        "## Pass Conditions",
        "",
        f"- live_writes_attempted: {counters['live_writes_attempted']}",
        f"- approvals_emitted: {counters['approvals_emitted']}",
        f"- packet_mutations_post_seal: {counters['packet_mutations_post_seal']}",
        f"- secret_strings_in_output: {counters['secret_strings_in_output']}",
        "",
        "## Sponsor Loops",
        "",
        f"- keyed runs: {keyed['completed']} / {keyed['requested']} at concurrency {keyed['concurrency']}",
        f"- Tavily live calls: {keyed['tavily_live_calls']}",
        f"- Tavily source URLs: {keyed['tavily_source_urls']}",
        f"- Nebius live calls: {keyed['nebius_live_calls']}",
        f"- Composio API calls: {keyed['composio_api_calls']}",
        f"- Portkey API calls: {keyed['portkey_api_calls']}",
        f"- fallback runs: {fallback['completed']} / {fallback['requested']}",
        "",
        "## Latency",
        "",
        "| Route | p50 baseline | p99 load | p99/baseline p50 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, item in report["latency"]["routes"].items():
        lines.append(
            "| {label} | {p50}ms | {p99}ms | {ratio}x |".format(
                label=label,
                p50=item["baseline"]["p50_ms"],
                p99=item["under_load"]["p99_ms"],
                ratio=item["p99_to_baseline_p50_ratio"],
            )
        )
    lines.extend(
        [
            "",
            "## Adversarial Inputs",
            "",
        ]
    )
    for item in report["adversarial_inputs"]:
        lines.append(f"- {item['label']}: {item['status']} expected {item['expected_status']} pass={item['passed']}")
    lines.extend(
        [
            "",
            "## Ledger Contamination",
            "",
            f"- ledger records checked: {ledger['record_count']}",
            f"- keyed records seen: {ledger['keyed_records_seen']}",
            f"- fallback records seen: {ledger['fallback_records_seen']}",
            f"- no external writes: {ledger['no_external_writes']}",
            f"- all decision locks unchanged: {ledger['all_decision_locks_unchanged']}",
            f"- no live call with external write: {ledger['no_live_call_with_external_write']}",
            "",
            "## Demo Confidence",
            "",
            "HIGH if this document was produced by the local-only max rehearsal gate and the four pass-condition counters remain zero.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded max rehearsal stress against a local IA server.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Served app URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--keyed-runs", type=int, default=DEFAULT_KEYED_RUNS)
    parser.add_argument("--fallback-runs", type=int, default=DEFAULT_FALLBACK_RUNS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--load-requests-per-route", type=int, default=DEFAULT_LOAD_REQUESTS_PER_ROUTE)
    parser.add_argument("--timeout", type=float, default=45.0, help="Per-request timeout in seconds.")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID)
    parser.add_argument("--json", action="store_true", help="Print safe JSON summary.")
    parser.add_argument("--output-doc", type=Path, help="Optional local markdown result doc path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = run_max_stress(
            args.base_url,
            keyed_runs=args.keyed_runs,
            fallback_runs=args.fallback_runs,
            concurrency=args.concurrency,
            load_requests_per_route=args.load_requests_per_route,
            timeout=args.timeout,
            session_id=args.session_id,
        )
    except StressFailure as exc:
        print(f"Max rehearsal stress failed: {exc}", file=sys.stderr)
        return 1

    if args.output_doc:
        args.output_doc.parent.mkdir(parents=True, exist_ok=True)
        args.output_doc.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
