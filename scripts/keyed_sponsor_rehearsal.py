#!/usr/bin/env python3
"""Keyed sponsor proof rehearsal for the public IA demo.

This script proves the safe live-key path:

- Nebius is configured as the LLM provider.
- Tavily performs live read-only evidence collection.
- Composio remains dry-run/no-execute.
- Portkey remains dry-run/no-mutation.
- The IA Packet decision lock stays unchanged.
- The run is recorded in the local ledger.

It never prints API keys or secret-shaped values.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_REQUEST_PATH = "examples/requests/support_triage_trial.yml"
DEFAULT_PORTKEY_FIXTURE = "ai_spend_budget_overrun"
EXPECTED_SPONSOR_ORDER = ["tavily", "composio", "openclaw", "nebius"]


class RehearsalFailure(AssertionError):
    """Keyed sponsor rehearsal failed at a product-relevant boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalFailure(message)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _json_get(base_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(_url(base_url, path), timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RehearsalFailure(f"GET {path} failed: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RehearsalFailure(f"GET {path} did not return JSON") from exc


def _json_post(base_url: str, path: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _url(base_url, path),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RehearsalFailure(f"POST {path} failed: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RehearsalFailure(f"POST {path} did not return JSON") from exc


def _tavily_source_count(tavily: dict[str, Any]) -> int:
    return sum(
        len(item.get("source_urls", []))
        for item in tavily.get("evidence_candidates", [])
        if isinstance(item, dict)
    )


def _assert_health(health: dict[str, Any]) -> None:
    _require(health.get("ok") is True, "Nebius/LLM health must be ok")
    _require(health.get("llm_provider") == "nebius", "Nebius must be the configured LLM provider")
    _require(bool(health.get("llm_model")), "Nebius model name must be present")
    _require(health.get("tavily") is True, "Tavily key must be configured")
    _require(health.get("composio") is True, "Composio key must be configured")
    _require(health.get("composio_dry_run") is True, "Composio must remain dry-run by default")


def _assert_sponsor_run(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    _require(payload.get("ok") is True, "sponsor proof run API must return ok=true")
    _require(payload.get("read_only") is True, "sponsor proof run API must stay read-only")
    run = payload["run"]
    _require(run["status"] == "completed", "sponsor proof run must complete")
    _require(run["mode"] == "live_read_only_evidence", "sponsor proof run must use live read-only evidence")
    _require(
        [step["sponsor"] for step in run["collector_steps"]] == EXPECTED_SPONSOR_ORDER,
        "sponsor proof order drifted",
    )
    _require(run["invariants"]["decision_lock_unchanged"] is True, "IA Packet decision lock changed")
    _require(run["invariants"]["portkey_api_call_made"] is False, "Portkey mutation API was called")

    safety = run["safety_boundary"]
    _require(safety["read_only"] is True, "sponsor proof run must be read-only")
    _require(safety["live_calls_made"] is True, "keyed rehearsal must make live read calls")
    for key in (
        "approves_access",
        "grants_permissions",
        "executes_external_writes",
        "mutates_production",
        "approves_spend",
        "selects_provider",
        "guarantees_savings",
    ):
        _require(safety[key] is False, f"sponsor proof safety_boundary.{key} must stay false")
    _require(safety["requires_human_review"] is True, "sponsor proof run must require human review")

    tavily = run.get("live_sponsor_proof", {}).get("tavily", {})
    _require(tavily.get("status") == "live_evidence_candidates_fetched", "Tavily must fetch live evidence")
    _require(tavily.get("live_call_attempted") is True, "Tavily live call must be attempted")
    _require(int(tavily.get("live_call_count", 0)) > 0, "Tavily live call count must be greater than zero")
    _require(tavily.get("used_live_key") is True, "Tavily must use the live key")
    _require(tavily.get("fallback_used") is False, "Tavily must not fall back during keyed rehearsal")
    source_count = _tavily_source_count(tavily)
    _require(source_count > 0, "Tavily must return source URLs")

    composio = run.get("dry_run_sponsor_proof", {}).get("composio", {})
    _require(composio.get("status") == "dry_run_permission_diff_built", "Composio dry-run diff must be built")
    _require(composio.get("api_call_made") is False, "Composio must not make a write API call")
    _require(composio.get("composio_execute_allowed") is False, "Composio execute must remain blocked")
    _require(composio.get("human_review_required") is True, "Composio proof must require human review")
    summary = composio.get("permission_diff_summary", {})
    _require(int(summary.get("tool_count", 0)) > 0, "Composio diff must include tools")
    _require(int(summary.get("blocked_write_count", 0)) > 0, "Composio diff must block write actions")
    _require(summary.get("api_call_made") is False, "Composio diff summary must preserve no-write state")

    record = payload["ledger_record"]
    _require(record["run_id"] == run["run_id"], "ledger record run_id must match")
    _require(record["safety_lock"]["read_only"] is True, "ledger record must be read-only")
    _require(record["safety_lock"]["live_calls_made"] is True, "ledger record must capture live calls")
    _require(record["safety_lock"]["decision_lock_unchanged"] is True, "ledger record must preserve decision lock")
    _require(record["safety_lock"]["executes_external_writes"] is False, "ledger record must preserve no writes")

    return run, tavily, composio, source_count


def _assert_portkey_preview(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("ok") is True, "Portkey preview API must return ok=true")
    _require(payload.get("read_only") is True, "Portkey preview must be read-only")
    portkey = payload["portkey"]
    _require(portkey["mode"] == "dry-run", "Portkey preview must stay dry-run")
    _require(portkey["api_call_made"] is False, "Portkey preview must not call mutation API")
    _require(portkey["portkey_guardrail_response"]["verdict"] is False, "Portkey guardrail must block movement")
    _require(
        portkey["usage_policy_plan"]["request_body"]["credit_limit"] == 0,
        "Portkey usage policy preview must cap blocked spend at zero",
    )
    return portkey


def _assert_ledger_contains_run(ledger_payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    _require(ledger_payload.get("ok") is True, "ledger API must return ok=true")
    _require(ledger_payload.get("read_only") is True, "ledger API must stay read-only")
    ledger = ledger_payload["ledger"]
    _require(ledger["read_only"] is True, "ledger must be read-only")
    _require(ledger["record_count"] >= 1, "ledger must contain at least one record")
    matches = [item for item in ledger["runs"] if item["run_id"] == run_id]
    _require(bool(matches), "keyed sponsor run must appear in the ledger")
    match = matches[0]
    _require(match["safety_lock"]["read_only"] is True, "ledger run must stay read-only")
    _require(match["safety_lock"]["live_calls_made"] is True, "ledger run must record live calls")
    _require(match["safety_lock"]["executes_external_writes"] is False, "ledger run must preserve no writes")
    _require(match["safety_lock"]["decision_lock_unchanged"] is True, "ledger run must preserve decision lock")
    _require(ledger["safety_summary"]["no_external_writes"] is True, "ledger summary must preserve no writes")
    _require(
        ledger["safety_summary"]["all_decision_locks_unchanged"] is True,
        "ledger summary must preserve decision locks",
    )
    return match


def run_keyed_rehearsal(
    base_url: str,
    *,
    request_path: str = DEFAULT_REQUEST_PATH,
    timeout: float = 45.0,
) -> dict[str, Any]:
    """Run the server-backed keyed sponsor proof rehearsal and return a safe summary."""
    health = _json_get(base_url, "/api/health", timeout=timeout)
    _assert_health(health)

    run_payload = _json_post(
        base_url,
        "/api/sponsor-proof-runs",
        {
            "request_path": request_path,
            "live_tavily": True,
            "composio_dry_run": True,
        },
        timeout=timeout,
    )
    run, tavily, composio, tavily_source_count = _assert_sponsor_run(run_payload)

    portkey_payload = _json_get(
        base_url,
        f"/api/packets/{urllib.parse.quote(DEFAULT_PORTKEY_FIXTURE)}/downstream/portkey?mode=dry-run",
        timeout=timeout,
    )
    portkey = _assert_portkey_preview(portkey_payload)

    fetched = _json_get(
        base_url,
        "/api/sponsor-proof-runs/" + urllib.parse.quote(run["run_id"]),
        timeout=timeout,
    )
    _require(fetched["run"]["run_id"] == run["run_id"], "created sponsor proof run must reload by run_id")

    ledger_match = _assert_ledger_contains_run(
        _json_get(base_url, "/api/sponsor-proof-run-ledger", timeout=timeout),
        run["run_id"],
    )

    composio_summary = composio.get("permission_diff_summary", {})
    return {
        "schema_version": "keyed_sponsor_rehearsal.v0",
        "status": "passed",
        "base_url": base_url.rstrip("/"),
        "health": {
            "llm_provider": health.get("llm_provider"),
            "llm_model": health.get("llm_model"),
            "tavily": bool(health.get("tavily")),
            "composio": bool(health.get("composio")),
            "composio_dry_run": bool(health.get("composio_dry_run")),
        },
        "run": {
            "run_id": run["run_id"],
            "mode": run["mode"],
            "packet_id": run["packet_reference"]["packet_id"],
            "decision_lock_unchanged": run["invariants"]["decision_lock_unchanged"],
            "read_only": run["safety_boundary"]["read_only"],
            "live_calls_made": run["safety_boundary"]["live_calls_made"],
            "executes_external_writes": run["safety_boundary"]["executes_external_writes"],
        },
        "tavily": {
            "status": tavily.get("status"),
            "live_call_count": tavily.get("live_call_count"),
            "source_url_count": tavily_source_count,
            "fallback_used": tavily.get("fallback_used"),
        },
        "composio": {
            "status": composio.get("status"),
            "api_call_made": composio.get("api_call_made"),
            "execute_allowed": composio.get("composio_execute_allowed"),
            "tool_count": composio_summary.get("tool_count"),
            "blocked_write_count": composio_summary.get("blocked_write_count"),
        },
        "portkey": {
            "mode": portkey["mode"],
            "api_call_made": portkey["api_call_made"],
            "guardrail_verdict": portkey["portkey_guardrail_response"]["verdict"],
            "usage_credit_limit": portkey["usage_policy_plan"]["request_body"]["credit_limit"],
        },
        "ledger": {
            "recorded": True,
            "record_path": ledger_match["record_path"],
            "live_calls_made": ledger_match["safety_lock"]["live_calls_made"],
            "executes_external_writes": ledger_match["safety_lock"]["executes_external_writes"],
            "decision_lock_unchanged": ledger_match["safety_lock"]["decision_lock_unchanged"],
        },
        "private_boundary": {
            "private_source_exposed": False,
            "secrets_printed": False,
            "principle": "Private engine, public proof.",
        },
    }


def render_summary(summary: dict[str, Any]) -> str:
    health = summary["health"]
    run = summary["run"]
    tavily = summary["tavily"]
    composio = summary["composio"]
    portkey = summary["portkey"]
    ledger = summary["ledger"]
    return "\n".join(
        [
            "Keyed sponsor rehearsal passed.",
            "",
            f"- Nebius: {health['llm_provider']} / {health['llm_model']}",
            f"- Tavily: {tavily['status']}; {tavily['live_call_count']} live calls; {tavily['source_url_count']} source URLs; fallback {tavily['fallback_used']}",
            f"- Composio: {composio['status']}; tools {composio['tool_count']}; blocked writes {composio['blocked_write_count']}; api_call_made {composio['api_call_made']}",
            f"- Portkey: {portkey['mode']}; api_call_made {portkey['api_call_made']}; guardrail verdict {portkey['guardrail_verdict']}; credit_limit {portkey['usage_credit_limit']}",
            f"- IA Packet: {run['packet_id']}; decision_lock_unchanged {run['decision_lock_unchanged']}; read_only {run['read_only']}; external_writes {run['executes_external_writes']}",
            f"- Ledger: recorded {ledger['recorded']}; live_calls_made {ledger['live_calls_made']}; external_writes {ledger['executes_external_writes']}",
            "",
            "No sponsor approved, granted, wrote, spent, selected providers, or mutated production.",
        ]
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the keyed, non-mutating sponsor proof rehearsal against a local IA server.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Served app URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--request-path", default=DEFAULT_REQUEST_PATH, help="Request fixture under examples/requests.")
    parser.add_argument("--timeout", type=float, default=45.0, help="Per-request timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print safe JSON summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        summary = run_keyed_rehearsal(
            args.base_url,
            request_path=args.request_path,
            timeout=args.timeout,
        )
    except RehearsalFailure as exc:
        print(f"Keyed sponsor rehearsal failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_summary(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
