#!/usr/bin/env python3
"""Final ReviewRun rehearsal gate for the public cockpit demo.

The regular reviewer smoke covers many public surfaces. This gate is narrower:
it walks the recording path end to end and fails if the ReviewRun cockpit stops
feeling like one run, one packet, one coach.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from reviewer_smoke import (  # noqa: E402
    DEFAULT_BASE_URL,
    SmokeFailure,
    _expect_false,
    _form_post,
    _json_get,
    _json_post,
    _read,
    _require,
)


SCHEMA_VERSION = "review_run_rehearsal_gate.v0"
SESSION_ID = "final-review-run-rehearsal"
ACCESS_REQUEST = "support-triage-bot needs to read issues, comment, and create labels."
EXPECTED_PROOF_ITEMS = (
    {"id": "repo_owner_approval", "label": "Repo owner approval"},
    {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
    {"id": "environment_boundary", "label": "Environment boundary"},
)
EXPECTED_STEPS = (
    "connect/use demo repo",
    "select repo",
    "generate packet",
    "Ask IA next step",
    "attach proof",
    "rerun",
    "Test Portkey guardrail",
    "open ProofGraph",
    "export brief",
)
SCREENSHOT_CHECKPOINTS = (
    "repo_connect",
    "repo_selected_indexed",
    "packet_generated",
    "proof_workbench",
    "rerun_delta",
    "portkey_gate",
    "proofgraph",
    "export_brief",
)
BROWSER_REHEARSALS = (
    "desktop browser rehearsal",
    "mobile browser rehearsal",
)


def _asset_path(html: str, pattern: str) -> str:
    match = re.search(pattern, html)
    _require(bool(match), f"root page missing asset pattern: {pattern}")
    assert match is not None
    return match.group(1)


def _check_first_run_contract(base_url: str, timeout: float) -> dict[str, Any]:
    html = _read(base_url, "/", timeout=timeout)
    app_js = _read(
        base_url,
        _asset_path(html, r'<script src="([^"]*app\.js[^"]*)"></script>'),
        timeout=timeout,
    )
    css = _read(
        base_url,
        _asset_path(html, r'<link rel="stylesheet" href="([^"]*style\.css[^"]*)"'),
        timeout=timeout,
    )

    root_action_count = len(re.findall(r'class="[^"]*\brepo-option-row\b[^"]*"', html))
    _require(root_action_count == 3, f"root must expose exactly three starting actions, got {root_action_count}")
    for expected in (
        "One review. One packet. One coach.",
        "Connect repo",
        "Review AI spend",
        "Test downstream gate",
        'aria-label="Ask IA"',
        'id="repo-coach-thread-scroll"',
        'data-tab="start">ReviewRun</button>',
        '<summary>Advanced</summary>',
        "Ask IA guides this run. It does not approve or write.",
    ):
        _require(expected in html, f"root missing first-run contract text: {expected}")

    primary_nav = html.split('<details class="advanced-nav">', 1)[0]
    for forbidden in ('data-tab="packet"', 'data-tab="walkthrough"', 'data-tab="workbench"'):
        _require(forbidden not in primary_nav, f"old tab still visible in primary nav: {forbidden}")
    advanced_nav = html.split('<details class="advanced-nav">', 1)[1].split("</details>", 1)[0]
    for expected in (
        'data-tab="packet">IA Packet</button>',
        'data-tab="walkthrough">Sponsor Run</button>',
        'data-tab="workbench">Workbench</button>',
        'data-tab="review">Access review</button>',
        'data-tab="metrics">Metrics</button>',
    ):
        _require(expected in advanced_nav, f"advanced nav missing legacy surface: {expected}")
    visible_stage_count = len(re.findall(r'data-stage-screen="[^"]+"(?![^>]*hidden)', html))
    _require(visible_stage_count == 1, f"root must start with one visible stage screen, got {visible_stage_count}")

    for forbidden in (
        'class="review-lane-grid"',
        'class="review-lane-card',
        'id="repo-advanced-card"',
        "Should this AI agent get repo access?",
        "Run IA Packet Review",
    ):
        _require(forbidden not in html, f"root leaked old/confusing surface: {forbidden}")

    for expected in (
        "repo-infra-row:not([open]) .repo-accordion-body",
        ".repo-runway-panel",
        ".repo-ask-floating",
        "position: fixed !important;",
        ".repo-proof-result[hidden]",
        "One-run minimal ReviewRun cockpit",
        ".repo-portkey-revision-flow",
        ".repo-portkey-outcomes",
        ".repo-portkey-live-receipt",
        ".repo-portkey-receipt-grid",
        ".repo-approval-receipt",
        ".repo-approval-receipt-grid",
        ".repo-receipt-actions",
    ):
        _require(expected in css, f"root CSS missing cockpit density guard: {expected}")

    for expected in (
        "askReviewRunCoach",
        "renderReviewRunCoachAnswer",
        "renderReviewRunCoachSuggestions",
        "fetchReviewRunPortkeyGuardrailTest",
        "fetchReviewRunPortkeyReceipt",
        "fetchReviewRunApprovalReceipt",
        "currentReviewRunApprovalReceipt",
        "/approval-receipt",
        "/api/portkey/guardrail/events",
        "fetchReviewRunProofGraph",
        "proofOwnerSummaryForPacket",
        "Use prepared receipt",
        "return [reviewRunActiveScreen(stage)];",
        "focusReviewRunScreen(\"proof_workbench\")",
        "openReviewRunPortkeyStage",
        "repo-rerun-delta",
        "Portable approval receipt",
        "Copy receipt",
        "Copy PR snippet",
        "Open verification",
        "repo-portkey-runway",
        "Packet-consumption runway",
        "repo-portkey-revision-flow",
        "Portkey call receipt",
        "Local tests stay separate.",
        "<span>Event id</span>",
        "<span>Still-blocked scope</span>",
        "<span>Policy mutation</span>",
        "repoPortkeyCard.open = portkeyTested || portkeyRunwayReady",
    ):
        _require(expected in app_js, f"root JS missing ReviewRun flow hook: {expected}")

    for forbidden in (
        'return ["packet_decision", "proof_workbench"]',
        'return ["packet_decision", "proof_workbench", "downstream_outputs"]',
    ):
        _require(forbidden not in app_js, f"root JS leaked stacked stage routing: {forbidden}")

    return {
        "root_action_count": root_action_count,
        "visible_stage_screen_count": visible_stage_count,
        "no_chip_wall": True,
        "no_raw_packet_dump": True,
        "accordions_hide_advanced_detail": True,
        "ask_ia_floating_present": True,
        "ask_ia_suggestions_contract": True,
        "proof_receipts_contract": True,
        "portkey_runway_contract": True,
    }


def _connect_demo_repo(base_url: str, timeout: float) -> tuple[str, dict[str, Any]]:
    review_session = SESSION_ID + "-github"
    popup_html = _form_post(
        base_url,
        "/api/connectors/oauth/popup/github?session_id=" + urllib.parse.quote(review_session),
        {"demo": "1"},
        timeout=timeout,
    )
    _require("connector-oauth" in popup_html, "demo GitHub connector did not complete")

    repos = _json_get(
        base_url,
        "/api/connectors/github/repos?session_id="
        + urllib.parse.quote(review_session)
        + "&q=triage",
        timeout=timeout,
    )
    _require(repos["ok"] is True, "demo repo list failed")
    _require(repos["demo"] is True, "rehearsal must stay in demo GitHub mode")
    _require(repos["repos"], "demo GitHub repo list was empty")
    full_name = repos["repos"][0]["full_name"]

    attached = _json_post(
        base_url,
        "/api/connectors/github/attach",
        {"session_id": review_session, "full_name": full_name},
        timeout=timeout,
    )
    _require(attached["ok"] is True, "selected demo repo did not attach")
    _require(attached["digest_chars"] > 100, "repo index was too small for a meaningful demo")
    return review_session, {
        "provider": "github",
        "full_name": full_name,
        "source": "demo_repo",
        "index": {
            "status": "indexed",
            "indexed_repo_count": 1,
            "digest_chars": attached["digest_chars"],
            "readme_found": attached["readme_found"],
            "files_included": attached["files_included"],
            "paths_in_tree": attached["paths_in_tree"],
            "sample_paths": attached["sample_paths"],
        },
    }


def _run_review_loop(base_url: str, timeout: float) -> dict[str, Any]:
    review_session, repo = _connect_demo_repo(base_url, timeout)
    created = _json_post(
        base_url,
        "/api/review-runs",
        {
            "session_id": review_session,
            "selected_repo": {
                "provider": repo["provider"],
                "full_name": repo["full_name"],
                "source": repo["source"],
            },
            "repo_index_summary": repo["index"],
        },
        timeout=timeout,
    )
    run = created["run"]
    _require(run["stage"] == "repo_selected", "ReviewRun must begin at repo_selected")
    _require(run["selected_repo"]["full_name"] == repo["full_name"], "selected repo drifted")
    _require(run["repo_index_summary"]["indexed_repo_count"] == 1, "must index exactly one repo")

    selected_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "hey"},
        timeout=timeout,
    )
    _require(selected_coach["answer"]["stage"] == "repo_selected", "Ask IA selected-stage answer drifted")
    _require(len(selected_coach["suggestions"]) <= 3, "Ask IA suggestions must stay capped")
    _require(selected_coach["suggestions"][0]["entities"]["run_id"] == run["run_id"], "Ask IA suggestion lost run pin")
    _require("No packet exists yet" in selected_coach["answer"]["sections"]["current_read"], "Ask IA should not dump packet before generation")

    generated = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/packet",
        {"access_request": ACCESS_REQUEST},
        timeout=timeout,
    )
    packet = generated["packet"]
    packet_run = generated["run"]
    _require(packet_run["stage"] == "packet_generated", "packet generation stage drifted")
    _require(packet["packet_reference"]["source_of_truth"] == "ReviewRun", "packet must name ReviewRun as source")
    _require(packet["compact_output"]["allowed"] == ["read issues"], "initial allowed scope drifted")
    _require(packet["compact_output"]["review_required"] == ["comment"], "initial yellow review lane drifted")
    _require(packet["compact_output"]["blocked"] == ["create labels", "repo admin", "org-wide write", "secrets"], "initial blocked scope drifted")
    _expect_false(
        packet["safety_boundary"],
        ["approval_granted", "production_access", "permission_grants", "external_writes"],
        prefix="review_run_rehearsal.packet.safety_boundary",
    )

    proof_lenses = packet["proof_resolution"]["owner_lenses"]
    active_lenses = [lens["lens_id"] for lens in proof_lenses["lenses"] if lens["active"]]
    _require(active_lenses == ["support_ops", "engineering", "security"], "active proof lenses drifted")
    _require(proof_lenses["guardrails"]["proof_attachment_changes_verdict"] is False, "proof lenses cannot approve")

    next_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "idk what to do next"},
        timeout=timeout,
    )
    next_action = next_coach["answer"]["sections"]["next_human_action"]
    for owner in ("Support Ops", "Engineering", "Security"):
        _require(owner in next_action, f"Ask IA next step must name {owner}")
    _require(
        [item["entities"]["prompt_kind"] for item in next_coach["suggestions"]] == ["next_action", "proof", "portkey"],
        "Ask IA packet-stage suggestions drifted",
    )
    _require(next_coach["answer"]["approves_access"] is False, "Ask IA must not approve access")

    proofed = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {"proof_items": list(EXPECTED_PROOF_ITEMS)},
        timeout=timeout,
    )
    proofed_run = proofed["run"]
    proofed_packet = proofed["packet"]
    _require(proofed_run["stage"] == "proof_attached", "proof attach stage drifted")
    _require(proofed_run["packet"]["revision_id"] == packet_run["packet"]["revision_id"], "proof attach changed packet revision")
    _require(proofed_run["packet"]["verdict"] == packet_run["packet"]["verdict"], "proof attach changed verdict")
    _require(proofed_packet["proof_resolution"]["ready_for_rerun"] is True, "proof attach must require rerun")
    _require(proofed_packet["proof_resolution"]["verdict_changed"] is False, "proof attach changed verdict")
    _require(proofed_packet["proof_resolution"]["portkey_changed"] is False, "proof attach changed Portkey")

    proof_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "what next"},
        timeout=timeout,
    )
    _require(proof_coach["answer"]["stage"] == "proof_attached", "Ask IA proof-attached stage drifted")
    _require("Regenerate the packet" in proof_coach["answer"]["sections"]["next_human_action"], "Ask IA must tell human to rerun after proof")

    rerun = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/rerun",
        {"access_request": ACCESS_REQUEST},
        timeout=timeout,
    )
    rerun_run = rerun["run"]
    rerun_packet = rerun["packet"]
    delta = rerun["review_delta"]
    _require(rerun_run["stage"] == "ready_to_export", "rerun must finish at ready_to_export")
    _require(rerun_run["packet"]["revision_number"] == 2, "rerun must create revision 2")
    _require(rerun_run["packet"]["verdict"] == "ready_with_gates", "rerun verdict drifted")
    _require(delta["same_request"] is True, "rerun must preserve raw request")
    _require(delta["portkey_before"] == "Block", "delta must show Portkey block before proof")
    _require(delta["portkey_after"] == "Allow with policy", "delta must show Portkey allow after proof")
    _require(delta["still_blocked"] == ["repo admin", "org-wide write", "secrets"], "hard-blocked scope drifted")
    _require("copy_review_brief" in rerun_packet, "updated packet missing exportable review brief")
    _require("ReviewRun" in rerun_packet["copy_review_brief"], "review brief must name ReviewRun")
    _require("IA did not approve" in rerun_packet["copy_review_brief"], "review brief lost safety anchor")

    receipt_response = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/approval-receipt",
        timeout=timeout,
    )
    approval_receipt = receipt_response["approval_receipt"]
    _require(approval_receipt["schema_version"] == "review_run_approval_receipt.v0", "approval receipt schema drifted")
    _require(approval_receipt["status"] == "ready_to_circulate", "approval receipt must be ready after rerun")
    _require(approval_receipt["can_circulate"] is True, "approval receipt must circulate only after rerun")
    _require(approval_receipt["packet_reference"]["revision_id"] == rerun_run["packet"]["revision_id"], "receipt revision drifted")
    _require(
        approval_receipt["movement"]["allowed_scope"] == ["read issues", "comment", "create labels in selected repo"],
        "receipt allowed scope drifted",
    )
    _require(
        approval_receipt["movement"]["still_blocked_scope"] == ["repo admin", "org-wide write", "secrets"],
        "receipt still-blocked scope drifted",
    )
    _require(
        approval_receipt["approval_summary"]["human_approval_state"] == "recorded_for_scoped_validation",
        "receipt human approval state drifted",
    )
    _require(approval_receipt["safety_boundary"]["ia_approved"] is False, "approval receipt cannot say IA approved")
    _require(
        approval_receipt["safety_boundary"]["ia_mutates_portkey_policy"] is False,
        "approval receipt cannot mutate Portkey policy",
    )
    _require(
        "Humans approve scoped movement" in approval_receipt["safety_anchor"],
        "approval receipt lost safety anchor",
    )

    portkey = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/portkey/guardrail-test",
        {},
        timeout=timeout,
    )
    portkey_test = portkey["portkey_guardrail_test"]
    _require(portkey_test["portkey_state"] == "Allow with policy", "Portkey must allow updated packet with policy")
    _require(portkey_test["packet_reference"]["revision_id"] == rerun_run["packet"]["revision_id"], "Portkey must read updated packet revision")
    _require(portkey_test["still_blocked_scope"] == ["repo admin", "org-wide write", "secrets"], "Portkey still-blocked scope drifted")
    _require(portkey_test["invariants"]["portkey_api_call_made"] is False, "Portkey gate must not call Admin API")
    _require(portkey_test["invariants"]["portkey_policy_mutation_allowed"] is False, "Portkey gate must not mutate policy")

    proofgraph_html = _read(
        base_url,
        "/proofgraph?review_run_id=" + urllib.parse.quote(run["run_id"]),
        timeout=timeout,
    )
    for expected in (
        "InferenceAtlas ReviewRun ProofGraph",
        "Generated from run_id",
        run["run_id"],
        repo["full_name"],
        rerun_run["packet"]["revision_id"],
        "Allow with policy",
        "zero writes",
    ):
        _require(expected in proofgraph_html, f"ProofGraph missing final rehearsal detail: {expected}")

    final_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "what will Portkey do?"},
        timeout=timeout,
    )
    _require(final_coach["answer"]["stage"] == "ready_to_export", "final Ask IA stage drifted")
    _require(final_coach["answer"]["portkey_state"] == "Allow with policy", "final Ask IA Portkey state drifted")
    _require(
        "Still blocked downstream: repo admin, org-wide write, secrets"
        in final_coach["answer"]["sections"]["downstream_impact"],
        "final Ask IA must keep hard-blocked scope visible",
    )

    return {
        "run_id": run["run_id"],
        "selected_repo": repo["full_name"],
        "repo_digest_chars": repo["index"]["digest_chars"],
        "packet_revision_before": packet_run["packet"]["revision_id"],
        "packet_revision_after": rerun_run["packet"]["revision_id"],
        "packet_verdict_before": packet_run["packet"]["verdict"],
        "packet_verdict_after": rerun_run["packet"]["verdict"],
        "proof_lenses": active_lenses,
        "portkey_state_before": "Block",
        "portkey_state_after": portkey_test["portkey_state"],
        "approval_receipt_id": approval_receipt["receipt_id"],
        "approval_receipt_status": approval_receipt["status"],
        "still_blocked_scope": portkey_test["still_blocked_scope"],
        "guardrail_event_id": portkey_test["event_id"],
        "copy_review_brief_ready": True,
        "proofgraph_route": "/proofgraph?review_run_id=" + run["run_id"],
    }


def build_rehearsal_report(base_url: str, timeout: float) -> dict[str, Any]:
    first_run = _check_first_run_contract(base_url, timeout)
    loop = _run_review_loop(base_url, timeout)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "base_url": base_url.rstrip("/"),
        "steps": list(EXPECTED_STEPS),
        "screenshot_checkpoints": list(SCREENSHOT_CHECKPOINTS),
        "browser_rehearsals": list(BROWSER_REHEARSALS),
        "first_run_contract": first_run,
        "review_run": loop,
        "safety": {
            "approval_granted": False,
            "external_writes_enabled": False,
            "portkey_api_call_made": False,
            "portkey_policy_mutation_allowed": False,
            "proof_attachment_changes_verdict": False,
        },
        "recording_ready": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    steps = "\n".join(f"- {step}" for step in report["steps"])
    shots = "\n".join(f"- {item}" for item in report["screenshot_checkpoints"])
    browser = "\n".join(f"- {item}" for item in report.get("browser_rehearsals", ()))
    run = report["review_run"]
    return f"""# ReviewRun Final Rehearsal Gate

Private engine, public proof.

- status: `{report["status"]}`
- base URL: `{report["base_url"]}`
- selected repo: `{run["selected_repo"]}`
- packet: `{run["packet_revision_before"]}` -> `{run["packet_revision_after"]}`
- Portkey: `{run["portkey_state_before"]}` -> `{run["portkey_state_after"]}`
- guardrail event: `{run["guardrail_event_id"]}`
- still blocked: `{", ".join(run["still_blocked_scope"])}`
- copy review brief ready: `{run["copy_review_brief_ready"]}`

## Recording Path

{steps}

## Screenshot Checklist

{shots}

## Browser Rehearsals

{browser}

## Safety

- approval granted: `{report["safety"]["approval_granted"]}`
- external writes enabled: `{report["safety"]["external_writes_enabled"]}`
- Portkey API call made: `{report["safety"]["portkey_api_call_made"]}`
- Portkey policy mutation allowed: `{report["safety"]["portkey_policy_mutation_allowed"]}`
- proof attachment changes verdict: `{report["safety"]["proof_attachment_changes_verdict"]}`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the final ReviewRun rehearsal gate against a local server.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the running local web app.")
    parser.add_argument("--timeout", type=float, default=8.0, help="HTTP timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable rehearsal report.")
    args = parser.parse_args()

    try:
        report = build_rehearsal_report(args.base_url, args.timeout)
    except SmokeFailure as exc:
        print(f"ReviewRun final rehearsal gate failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
