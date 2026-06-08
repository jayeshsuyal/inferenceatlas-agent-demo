#!/usr/bin/env python3
"""Server-backed reviewer smoke for the public IA demo.

This script assumes `python3 -m web` is already running. It exercises the same
served surfaces a first-time reviewer uses, without live keys or external
writes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_SESSION_ID = "reviewer-smoke-session"
EXPECTED_SPONSOR_ORDER = ["tavily", "composio", "openclaw", "nebius"]
EXPECTED_TEAM_LENSES = {
    "product_exec",
    "engineering",
    "security_legal",
    "finance",
    "procurement",
    "ai_platform_ops",
}
PACKET_FIXTURES = [
    "mcp_tool_blast_radius",
    "ai_spend_budget_overrun",
    "miasma_pre_permission_packet",
]


class SmokeFailure(AssertionError):
    """Reviewer smoke failed at a product-relevant boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _read(base_url: str, path: str, *, timeout: float) -> str:
    try:
        with urllib.request.urlopen(_url(base_url, path), timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"GET {path} failed: {exc}") from exc


def _json_get(base_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    raw = _read(base_url, path, timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"GET {path} did not return JSON") from exc


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
        raise SmokeFailure(f"POST {path} failed: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"POST {path} did not return JSON") from exc


def _expect_false(mapping: dict[str, Any], keys: list[str], *, prefix: str) -> None:
    for key in keys:
        _require(mapping.get(key) is False, f"{prefix}.{key} must stay false")


def _check_first_run(base_url: str, timeout: float) -> None:
    html = _read(base_url, "/", timeout=timeout)
    js = _read(base_url, "/static/app.js?v=34", timeout=timeout)
    css = _read(base_url, "/static/style.css?v=21", timeout=timeout)

    for expected in (
        "Review in 90 seconds",
        "Run IA Packet Review",
        "One AI movement request becomes a packet, proof trace, team review",
        "Load one registered AI movement request.",
        "Collect sponsor proof and preview the Portkey dry-run gate.",
        "Sponsor Run",
        "composer-shell first-run-locked",
        "Ask IA about this packet",
        "Open the IA Packet first; Ask IA answers from the packet, not raw agent intent.",
        "Export Portkey gate",
        "Team lenses",
        "Show each team the same packet through its review lens.",
    ):
        _require(expected in html, f"first-run surface missing: {expected}")

    _require("Welcome. Compare AI inference costs" not in js, "old noisy welcome copy returned")
    _require("renderPacketCoachReply" in js, "Ask IA packet coach renderer missing")
    _require("renderPacketTeamLenses" in js, "Team Lenses renderer missing")
    _require("Sponsors collect proof only" in js, "packet sponsor safety line missing")
    _require("Live keys" in js, "packet sponsor live-key flag missing")
    _require("trace ${escapeHtml(trace.trace_id" in js, "packet sponsor trace id missing")
    _require("Packet-backed decision coach" in js, "Ask IA packet coach title missing")
    _require("reply-section-heading" in js, "packet-backed answer section renderer missing")
    _require("renderReplyLines" in js, "packet-backed answer list renderer missing")
    _require("Portkey dry-run gate JSON exported. No API call made." in js, "Portkey gate export missing")
    _require(".composer-shell.first-run-locked" in css, "first-run quick-chip lock CSS missing")
    _require(
        ".composer-shell.first-run-locked .composer" in css,
        "first-run chat composer must stay hidden",
    )
    _require(".reply-section-heading" in css, "reply section heading CSS missing")
    _require(".team-lens-row" in css, "Team Lenses row CSS missing")
    _require(
        "grid-template-columns: repeat(5, minmax(0, 1fr));" in css,
        "first-run proof rail must stay compressed",
    )
    _require(re.search(r"/static/app\.js\?v=\d+", html) is not None, "app.js cache marker missing")
    _require(re.search(r"/static/style\.css\?v=\d+", html) is not None, "style.css cache marker missing")


def _check_packet(base_url: str, fixture: str, timeout: float) -> dict[str, Any]:
    data = _json_get(
        base_url,
        "/api/ia-packet?fixture=" + urllib.parse.quote(fixture),
        timeout=timeout,
    )
    _require(data.get("schema_version") == "ia_packet_detail.v0", f"{fixture} packet schema drifted")
    _require(data.get("ok") is True, f"{fixture} packet did not return ok=true")
    _require(data.get("product_object") == "IA Packet", f"{fixture} product object drifted")
    _require(data["local_verification"]["read_only"] is True, f"{fixture} must be read-only")
    _require(data["local_verification"]["calls_v1"] is False, f"{fixture} must not call v1")
    _expect_false(
        data["decision"],
        ["production_access", "permission_grants", "external_writes", "approval_granted"],
        prefix=f"{fixture}.decision",
    )
    _require(len(data.get("blocked_claims", [])) >= 1, f"{fixture} must expose blocked claims")
    _require(len(data.get("missing_proof", [])) >= 1, f"{fixture} must expose missing proof")
    _require(len(data.get("reviewer_routing", [])) >= 1, f"{fixture} must expose reviewer routing")
    _require(len(data.get("downstream_consumers", [])) >= 5, f"{fixture} must expose downstream consumers")
    _require(data.get("team_lenses_schema_version") == "team_lenses.v0", f"{fixture} team lens schema drifted")
    team_lenses = data.get("team_lenses", {})
    _require(team_lenses.get("schema_version") == "team_lenses.v0", f"{fixture} team lens payload missing")
    _require(team_lenses.get("packet_reference") == data["packet_reference"], f"{fixture} team lenses must read same packet")
    _require(
        {lens["team_id"] for lens in team_lenses.get("lenses", [])} == EXPECTED_TEAM_LENSES,
        f"{fixture} team lens set drifted",
    )
    _require(team_lenses["guardrails"]["read_only"] is True, f"{fixture} team lenses must be read-only")
    _require(team_lenses["guardrails"]["does_not_approve"] is True, f"{fixture} team lenses must not approve")
    _require(team_lenses["guardrails"]["state_mutated"] is False, f"{fixture} team lenses must not mutate")
    for lens in team_lenses["lenses"]:
        _require(lens["packet_reference"] == data["packet_reference"], f"{fixture} {lens['team_id']} packet drifted")
        _require(lens["human_confirmation_required"] is True, f"{fixture} {lens['team_id']} must require humans")
        _require(lens["does_not_approve"] is True, f"{fixture} {lens['team_id']} must not approve")
        _require(lens["can_dispatch_workflow"] is False, f"{fixture} {lens['team_id']} must not dispatch")
        _require(lens["can_mutate_packet"] is False, f"{fixture} {lens['team_id']} must not mutate packet")
        _require(lens["state_mutated"] is False, f"{fixture} {lens['team_id']} mutated state")
    return data


def _check_workbench(base_url: str, timeout: float) -> None:
    registry = _json_get(base_url, "/api/workbench", timeout=timeout)
    _require(registry.get("schema_version") == "packet_workbench.v0", "workbench registry schema drifted")
    _require(registry.get("mode") == "fixture_only", "workbench must remain fixture-only")
    _require(registry.get("default_fixture_id") == "mcp_tool_blast_radius", "workbench default fixture drifted")
    _require(len(registry.get("lanes", [])) >= 4, "workbench lane matrix is too small")

    generated = _json_post(
        base_url,
        "/api/workbench/generate",
        {"fixture_id": "mcp_tool_blast_radius"},
        timeout=timeout,
    )
    _require(generated["fixture"]["fixture_id"] == "mcp_tool_blast_radius", "workbench generated wrong fixture")
    _expect_false(
        generated["decision"],
        ["production_access", "permission_grants", "external_writes", "approval_granted"],
        prefix="workbench.decision",
    )
    _require(len(generated.get("output_files", [])) >= 2, "workbench export files missing")


def _check_walkthrough(base_url: str, timeout: float) -> None:
    data = _json_get(base_url, "/api/walkthrough", timeout=timeout)
    _require(data.get("ok") is True, "walkthrough ok flag missing")
    _require(data.get("mode") == "offline_deterministic", "walkthrough must be offline deterministic")
    _expect_false(
        data["decision"],
        ["production_access", "permission_grants", "external_writes", "sponsors_can_change_decision"],
        prefix="walkthrough.decision",
    )
    trace = data["sponsor_proof_trace"]
    _require(trace["sponsor_order"] == EXPECTED_SPONSOR_ORDER, "walkthrough sponsor order drifted")
    _require(trace["decision_lock_unchanged"] is True, "walkthrough sponsor trace changed decision lock")
    for key in ("all_fallback_used", "all_non_executing", "all_non_approving", "all_non_granting", "all_non_mutating"):
        _require(trace[key] is True, f"walkthrough sponsor invariant must stay true: {key}")
    _require(len(data.get("steps", [])) == 6, "walkthrough step count drifted")
    _require(len(data.get("output_files", [])) >= 2, "walkthrough export files missing")


def _check_portkey_and_chat(base_url: str, timeout: float, session_id: str) -> None:
    preview = _json_get(
        base_url,
        "/api/packets/ai_spend_budget_overrun/downstream/portkey?mode=dry-run",
        timeout=timeout,
    )
    portkey = preview["portkey"]
    _require(preview.get("read_only") is True, "Portkey preview must be read-only")
    _require(portkey["mode"] == "dry-run", "Portkey preview must default to dry-run")
    _require(portkey["api_call_made"] is False, "Portkey preview must not call API")
    _require(portkey["portkey_guardrail_response"]["verdict"] is False, "Portkey preview must block movement")
    _require(
        portkey["usage_policy_plan"]["request_body"]["credit_limit"] == 0,
        "Portkey preview must cap blocked spend at zero",
    )

    chat = _json_post(
        base_url,
        "/api/chat",
        {
            "session_id": session_id,
            "message": "Can Portkey allow this spend?",
            "current_fixture": "ai_spend_budget_overrun",
        },
        timeout=timeout,
    )
    _require(chat["answer"]["schema_version"] == "packet_advisor_answer.v0", "Ask IA answer schema drifted")
    _require(chat["answer"]["subscriber"] == "portkey_model_spend_gate", "Ask IA Portkey subscriber drifted")
    _require(chat["answer"]["downstream_gate"]["requested_action_can_proceed"] is False, "Ask IA allowed movement")
    for expected in ("Portkey cannot allow this request", "IA does not approve", "Preview Portkey gate"):
        _require(expected in chat["reply"], f"Ask IA reply missing: {expected}")


def _check_sponsors(base_url: str, timeout: float) -> None:
    readiness = _json_get(base_url, "/api/sponsor-readiness/matrix", timeout=timeout)
    _require(readiness.get("read_only") is True, "sponsor readiness must be read-only")
    _require([row["provider"] for row in readiness["matrix"]] == EXPECTED_SPONSOR_ORDER, "sponsor readiness order drifted")
    summary = readiness["summary"]
    for key in ("all_fallback_available", "all_dry_run_available", "all_non_executing", "all_non_approving", "all_non_granting", "all_non_mutating"):
        _require(summary[key] is True, f"sponsor readiness summary must stay true: {key}")
    _require(summary["any_live_enabled"] is False, "sponsor readiness must not enable live mode by default")

    run_payload = _json_post(
        base_url,
        "/api/sponsor-proof-runs",
        {"request_path": "examples/requests/support_triage_trial.yml"},
        timeout=timeout,
    )
    run = run_payload["run"]
    _require(run["status"] == "completed", "sponsor proof run did not complete")
    _require(
        [step["sponsor"] for step in run["collector_steps"]] == EXPECTED_SPONSOR_ORDER,
        "sponsor proof run order drifted",
    )
    _require(run["invariants"]["sponsor_order_locked"] is True, "sponsor proof order invariant failed")
    _require(run["invariants"]["decision_lock_unchanged"] is True, "sponsor proof run changed decision lock")
    _require(run["invariants"]["portkey_api_call_made"] is False, "sponsor proof run made Portkey API call")
    _require(run["safety_boundary"]["read_only"] is True, "sponsor proof run must be read-only")
    _expect_false(
        run["safety_boundary"],
        [
            "live_calls_made",
            "approves_access",
            "grants_permissions",
            "executes_external_writes",
            "mutates_production",
            "approves_spend",
            "selects_provider",
            "guarantees_savings",
        ],
        prefix="sponsor_run.safety_boundary",
    )
    record = run_payload["ledger_record"]
    _require(record["run_id"] == run["run_id"], "sponsor proof run must return durable ledger record")
    _require(record["packet_reference"] == run["packet_reference"], "ledger record packet reference drifted")
    _require(record["safety_lock"]["read_only"] is True, "ledger record must stay read-only")
    _require(record["safety_lock"]["live_calls_made"] is False, "ledger record must not record live calls")
    _require(record["safety_lock"]["decision_lock_unchanged"] is True, "ledger record must preserve decision lock")
    _require(record["output_artifacts"]["run_record_json"].endswith(".json"), "ledger record JSON artifact missing")

    fetched = _json_get(base_url, "/api/sponsor-proof-runs/" + urllib.parse.quote(run["run_id"]), timeout=timeout)
    _require(fetched["run"]["run_id"] == run["run_id"], "sponsor proof run detail did not reload by run_id")
    ledger = _json_get(base_url, "/api/sponsor-proof-run-ledger", timeout=timeout)["ledger"]
    _require(ledger["schema_version"] == "sponsor_proof_run_ledger.v0", "sponsor run ledger schema drifted")
    _require(ledger["read_only"] is True, "sponsor run ledger must be read-only")
    _require(ledger["record_count"] >= 1, "sponsor run ledger must include created run")
    _require(any(item["run_id"] == run["run_id"] for item in ledger["runs"]), "created run missing from ledger")
    _require(ledger["safety_summary"]["no_live_calls"] is True, "ledger must preserve no-live-call summary")
    _require(ledger["safety_summary"]["no_external_writes"] is True, "ledger must preserve no-write summary")


def _check_review_cycle(base_url: str, timeout: float) -> None:
    guide = _json_get(base_url, "/api/mind/guide", timeout=timeout)
    _require(guide["expect_blocked"] is True, "review guide must expect blocked production")

    init = _json_post(base_url, "/api/mind/init", {}, timeout=timeout)
    _require(init.get("ok") is True, "mind init failed")
    _require(len(init.get("cycle_results", [])) == 3, "mind init must load three scenarios")

    step = _json_post(base_url, "/api/mind/step", {"no_cortex": True}, timeout=timeout)
    _require(step.get("ok") is True, "mind step failed")
    _require(len(step.get("cycle_results", [])) == 3, "mind step must return three scenario cards")
    for result in step["cycle_results"]:
        live = result["live"]
        _require(live["production_access"] == "blocked", f"{result['scenario']} production must stay blocked")
        _require(live["artifacts"], f"{result['scenario']} review artifacts missing")


def _check_skills_connectors_metrics(base_url: str, timeout: float, session_id: str) -> None:
    skills = _json_get(base_url, "/api/skills", timeout=timeout)
    _require(len(skills.get("skills", [])) >= 10, "skills registry unexpectedly small")
    _require(any(skill["id"] == "reviewer_routing" for skill in skills["skills"]), "reviewer routing skill missing")

    connectors = _json_get(
        base_url,
        "/api/connectors?session_id=" + urllib.parse.quote(session_id),
        timeout=timeout,
    )
    _require(len(connectors.get("connectors", [])) >= 3, "connectors registry unexpectedly small")

    metrics = _json_get(
        base_url,
        "/api/session/metrics?session_id=" + urllib.parse.quote(session_id),
        timeout=timeout,
    )
    _require("session_id" in metrics, "session metrics missing session_id")
    _require("billable" in metrics, "session metrics missing billable counters")
    for key in ("demo_llm", "tavily", "composio", "v1_http", "github_api", "google_drive_api"):
        _require(key in metrics["billable"], f"session metrics missing {key}")


def run_smoke(base_url: str, *, timeout: float, session_id: str) -> list[str]:
    steps: list[tuple[str, Any]] = [
        ("first-run surface", lambda: _check_first_run(base_url, timeout)),
        ("IA Packet fixtures", lambda: [_check_packet(base_url, fixture, timeout) for fixture in PACKET_FIXTURES]),
        ("Workbench", lambda: _check_workbench(base_url, timeout)),
        ("Walkthrough", lambda: _check_walkthrough(base_url, timeout)),
        ("Portkey + Ask IA", lambda: _check_portkey_and_chat(base_url, timeout, session_id)),
        ("Sponsor readiness + proof run", lambda: _check_sponsors(base_url, timeout)),
        ("Access review cycle", lambda: _check_review_cycle(base_url, timeout)),
        ("Skills/connectors/metrics", lambda: _check_skills_connectors_metrics(base_url, timeout, session_id)),
    ]

    passed: list[str] = []
    for label, fn in steps:
        fn()
        passed.append(label)
        print(f"OK {label}")
    return passed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test the served reviewer journey against a running local IA demo.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Served app URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request timeout in seconds.")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID, help="Stable smoke session id.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        passed = run_smoke(args.base_url, timeout=args.timeout, session_id=args.session_id)
    except SmokeFailure as exc:
        print(f"Reviewer smoke failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Reviewer smoke passed: "
        + " -> ".join(passed)
        + " (read-only, no live keys required, no approval/write path)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
