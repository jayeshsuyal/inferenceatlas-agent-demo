#!/usr/bin/env python3
"""No-key smoke check for the buyer-facing walkthrough surface."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_STEPS = [
    "request",
    "packet",
    "sponsor_proof_trace",
    "sponsor_replay",
    "review_cycle",
    "pilot_memo",
]
EXPECTED_SPONSOR_ORDER = ["tavily", "composio", "openclaw", "nebius"]


def _fail(message: str) -> None:
    raise AssertionError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _read_static(name: str) -> str:
    return (ROOT / "web" / "static" / name).read_text(encoding="utf-8")


def _assert_walkthrough_payload(payload: dict[str, Any]) -> None:
    step_ids = [step["id"] for step in payload.get("steps", [])]
    _require(step_ids == EXPECTED_STEPS, f"unexpected walkthrough steps: {step_ids}")
    _require(payload.get("mode") == "offline_deterministic", "walkthrough must stay no-key deterministic")

    decision = payload["decision"]
    for field in ("production_access", "permission_grants", "external_writes", "sponsors_can_change_decision"):
        _require(decision[field] is False, f"decision field must stay false: {field}")

    authority = payload["packet_authority"]
    _require(authority["read_only"] is True, "packet authority must be read-only")
    _require(authority["subscriber_count"] >= 6, "walkthrough must show downstream subscriber categories")

    trace = payload["sponsor_proof_trace"]
    _require(trace["sponsor_order"] == EXPECTED_SPONSOR_ORDER, "SponsorProofTrace order drifted")
    _require(trace["step_count"] == 4, "SponsorProofTrace must show all four sponsor steps")
    _require(trace["decision_lock_unchanged"] is True, "SponsorProofTrace changed the decision lock")
    _require(trace["access_evidence_present"] is True, "SponsorProofTrace must show access evidence")
    _require(trace["spend_evidence_present"] is True, "SponsorProofTrace must show spend evidence")

    for field in ("all_fallback_used", "all_non_executing", "all_non_approving", "all_non_granting", "all_non_mutating"):
        _require(trace[field] is True, f"SponsorProofTrace invariant must stay true: {field}")

    for field in ("approves_access", "approves_spend", "selects_provider", "guarantees_savings"):
        _require(trace[field] is False, f"SponsorProofTrace must not move authority: {field}")


def _assert_static_walkthrough_contract() -> None:
    html = _read_static("index.html")
    js = _read_static("app.js")
    css = _read_static("style.css")

    _require('id="walkthrough-view"' in html, "walkthrough view missing from HTML")
    _require('id="btn-collect-sponsor-proof"' in html, "Collect sponsor proof button missing")
    _require('id="btn-collect-sponsor-proof" disabled' not in html, "Collect sponsor proof must be directly usable")
    _require("Collect sponsor proof" in html, "button label drifted")
    _require(re.search(r"/static/app\.js\?v=\d+", html) is not None, "app.js cache version missing")
    _require(re.search(r"/static/style\.css\?v=\d+", html) is not None, "style.css cache version missing")

    for expected in (
        "collectSponsorProof",
        "selectWalkthroughStepById",
        "Sponsor Proof Trace selected. Decision lock unchanged.",
        "sponsor_proof_trace",
        "renderSponsorCard",
    ):
        _require(expected in js, f"walkthrough JS missing {expected}")

    for forbidden in ("Run live sponsor agent", "Approve sponsor proof", "Grant sponsor access"):
        _require(forbidden not in html + js, f"unsafe walkthrough label present: {forbidden}")

    for expected in (
        ".trace-metrics",
        ".trace-step-list",
        ".trace-step-row",
        "grid-template-columns: repeat(auto-fit",
    ):
        _require(expected in css, f"walkthrough CSS missing {expected}")


def main() -> int:
    try:
        from web.app import design_partner_walkthrough

        payload = design_partner_walkthrough()
        _assert_walkthrough_payload(payload)
        _assert_static_walkthrough_contract()
    except Exception as exc:
        print(f"Walkthrough smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Walkthrough smoke passed: request -> packet -> sponsor_proof_trace -> sponsor_replay -> review_cycle -> pilot_memo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
