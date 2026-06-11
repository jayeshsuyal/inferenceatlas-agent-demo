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


def _json_post(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    expected_status: int = 200,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _url(base_url, path),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != expected_status:
                raise SmokeFailure(f"POST {path} returned {response.status}, expected {expected_status}")
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        if exc.code != expected_status:
            raise SmokeFailure(f"POST {path} failed: HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"POST {path} failed: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"POST {path} did not return JSON") from exc


def _form_post(base_url: str, path: str, payload: dict[str, str], *, timeout: float) -> str:
    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        _url(base_url, path),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"POST {path} failed: {exc}") from exc


def _expect_false(mapping: dict[str, Any], keys: list[str], *, prefix: str) -> None:
    for key in keys:
        _require(mapping.get(key) is False, f"{prefix}.{key} must stay false")


def _check_first_run(base_url: str, timeout: float) -> None:
    html = _read(base_url, "/", timeout=timeout)
    js = _read(base_url, "/static/app.js?v=76", timeout=timeout)
    css = _read(base_url, "/static/style.css?v=58", timeout=timeout)

    for expected in (
        "ReviewRun",
        "One review. One packet. One coach.",
        "Connect a repo, generate the IA Packet, then let downstream gates read the packet before movement.",
        "Review cockpit",
        "repo-runway-panel",
        "repo-stage-status",
        "repo-stage-repo-status",
        "repo-stage-packet-status",
        "repo-stage-proof-status",
        "repo-stage-portkey-status",
        "repo-option-stack",
        "data-stage-screen=\"repo_setup\"",
        "data-stage-screen=\"packet_decision\"",
        "data-stage-screen=\"proof_workbench\"",
        "data-stage-screen=\"packet_rerun\"",
        "data-stage-screen=\"portkey_gate\"",
        "data-tab=\"start\">ReviewRun</button>",
        "<summary>Advanced</summary>",
        "Repo access",
        "Connect GitHub",
        "Use demo repo",
        "Connect repo",
        "IA indexes only that repo for this ReviewRun.",
        "Selected repo",
        "Index",
        "ReviewRun",
        "Choose one GitHub repository",
        "Connect and index one repo before generating a packet.",
        "Ask IA",
        "Chat coach",
        "I am watching this ReviewRun. Choose one repo and I will keep the next human action, blocked scope, and Portkey impact in sync.",
        "Minimize Ask IA chat",
        'data-coach-mode="floating"',
        "repo-coach-chat",
        "repo-coach-last-user",
        "You asked",
        "Ask what to do next...",
        "Review AI spend",
        "Test downstream gate",
        "support-triage-bot wants repo access",
        "Choose a GitHub repo first.",
        "support-triage-bot",
        "Review access",
        "Next human action",
        "Missing proof",
        "Use prepared proof before rerun.",
        "Review prepared human proof receipts. Using them attaches evidence only; it does not approve access.",
        "Use prepared proof for demo",
        "No prepared proof used yet. Verdict unchanged.",
        "Review delta",
        "ProofGraph",
        "Waiting for packet",
        "Portkey",
        "repo-infra-rows",
        "Open ProofGraph",
        "Sponsor Run",
        "composer-shell first-run-locked",
        "Ask IA guides this run. It does not approve or write.",
        "Export Portkey gate",
        "Team lenses",
    ):
        _require(expected in html, f"first-run surface missing: {expected}")
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
    _require(visible_stage_count == 1, f"first-run must expose one visible ReviewRun stage, got {visible_stage_count}")

    _require('aria-label="Connect repo"' in html, "repo access row must be the selected entry point")
    _require('aria-current="step"' in html, "repo access row must show selected step state")
    _require('class="repo-ask-sidecar repo-ask-floating"' in html, "Ask IA must be a floating chat coach")
    _require('role="dialog"' in html, "Ask IA floating chat must expose dialog semantics")
    _require('class="repo-ask-coach repo-infra-row"' not in html, "Ask IA returned to downstream drawer")
    _require("Should this AI agent get repo access?" not in html, "old cockpit-first heading returned")
    _require("Run proof check" not in html, "old cockpit-first CTA returned")
    _require("Run IA Packet Review" not in html, "old packet-document-first CTA returned")
    _require("Open one registered AI movement request. IA shows the packet" not in html, "old first-run body returned")
    _require('class="review-lane-grid"' not in html, "old root lane selector returned")
    _require('class="review-lane-card' not in html, "old root lane cards returned")
    _require('class="repo-proof-grid"' not in html, "root proof card grid returned")
    _require('id="repo-advanced-card"' not in html, "root advanced drawer returned")
    _require("Welcome. Compare AI inference costs" not in js, "old noisy welcome copy returned")
    _require('const REPO_PROOF_FIXTURE = "support_triage_agent";' in js, "repo proof fixture is not locked")
    _require("loadReviewRepoList" in js, "root GitHub repo list loader missing")
    _require("attachReviewRepo" in js, "root GitHub repo attach handler missing")
    _require("createReviewRunForIndexedRepo" in js, "ReviewRun creation from selected repo missing")
    _require('fetch("/api/review-runs"' in js, "root flow must create ReviewRun from selected repo")
    _require("reviewRunActiveScreen" in js, "ReviewRun active screen router missing")
    _require("reviewRunVisibleScreens" in js, "ReviewRun visible screen contract missing")
    _require("updateReviewRunStageScreens" in js, "ReviewRun stage screen swapper missing")
    _require("updateReviewRunStageStatus" in js, "ReviewRun compact stage status updater missing")
    _require("repoProofCockpit.dataset.activeScreen" in js, "root stage router must set active screen")
    _require("currentReviewRun.stage === \"repo_selected\"" in js, "repo review must wait for repo_selected ReviewRun")
    _require(
        "Connect and index one GitHub repo before generating a packet." in js,
        "repo proof runner must fail closed before indexing",
    )
    _require("DEFAULT_REVIEW_ACCESS_REQUEST" in js, "root review request constant missing")
    _require("DEFAULT_REVIEW_PROOF_ITEMS" in js, "root proof checklist constant missing")
    _require(
        "/api/review-runs/${encodeURIComponent(runId)}/packet" in js,
        "root flow must generate packet from ReviewRun",
    )
    _require(
        "/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/proof" in js,
        "root flow must attach proof from ReviewRun",
    )
    _require(
        "/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/rerun" in js,
        "root flow must rerun ReviewRun after proof",
    )
    _require(
        "/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/coach" in js,
        "root Ask IA must answer from ReviewRun coach endpoint",
    )
    _require(
        'window.open(data.redirect_url, "ia_oauth", "width=520,height=720")' in js,
        "OAuth popup must keep opener so callback can notify the app",
    )
    _require(
        "width=520,height=720,noopener" not in js,
        "OAuth popup cannot use noopener; it breaks callback postMessage",
    )
    _require("handleConnectorOAuthReturn" in js, "same-tab OAuth return handler missing")
    _require(
        'localStorage.getItem("ia_connector_oauth_result")' in js,
        "same-tab OAuth localStorage fallback missing",
    )
    _require('params.get("connector_oauth")' in js, "same-tab OAuth URL fallback missing")
    _require('params.get("session_id")' in js, "same-tab OAuth session handoff missing")
    _require(
        "payload.session_id && payload.session_id !== sessionId" in js,
        "same-tab OAuth must adopt callback session id",
    )
    _require('if (connectorId === "github")' in js, "OAuth poll must special-case GitHub repo loading")
    _require('await loadReviewRepoList("");' in js, "OAuth poll must load repo list after GitHub connects")
    _require(
        "/api/review-runs/${encodeURIComponent(runId)}/proofgraph" in js,
        "root flow must fetch dynamic ReviewRun ProofGraph",
    )
    _require("fetchReviewRunProofGraph" in js, "ReviewRun ProofGraph fetcher missing")
    _require("reviewRunProofGraphUrl" in js, "ReviewRun ProofGraph URL helper missing")
    _require("/proofgraph?review_run_id=" in js, "ProofGraph link must carry review_run_id")
    _require("repo-proofgraph-map" not in js, "ProofGraph cockpit summary returned as text panel")
    _require("Generated from run_id" in js, "ProofGraph cockpit must show run_id source")
    _require("zero writes" in js, "ProofGraph cockpit must show zero writes")
    _require("Open generated ProofGraph" in js, "ProofGraph must stay behind generated graph action")
    _require("sponsor_proof_trace: sponsorTrace || undefined" in js, "ReviewRun packet must preserve sponsor trace when available")
    _require("movementLane" in js, "movement lane renderer missing")
    _require("renderRepoProofResolution" in js, "proof resolution renderer missing")
    _require("proofReceiptTimestamp" in js, "proof receipt timestamp helper missing")
    _require("proofReceiptSafetyPills" in js, "proof receipt safety helper missing")
    _require("proofLensesForPacket" in js, "proof owner lens renderer missing")
    _require("owner_lenses" in js, "proof owner lens payload missing")
    _require("data-owner-lens" in js, "proof owner lens DOM hook missing")
    _require("data-proof-owner" in js, "proof owner attach metadata missing")
    _require("data-proof-receipt" in js, "proof receipts must expose receipt metadata")
    _require("data-proof-timestamp" in js, "proof receipts must expose timestamp metadata")
    _require("Prepared receipt" in js, "prepared receipt label missing")
    _require("Attached receipt" in js, "attached receipt label missing")
    _require("Use prepared receipt" in js, "proof receipt selection copy missing")
    _require("Supplied by: ${escapeHtml(ownerGroup)}" in js, "proof receipt supplier metadata missing")
    _require("Timestamp: ${escapeHtml(receiptTimestamp)}" in js, "proof receipt timestamp metadata missing")
    _require("not approval" in js, "proof receipt no-approval safety chip missing")
    _require("no writes" in js, "proof receipt no-writes safety chip missing")
    _require("rerun required" in js, "proof receipt rerun safety chip missing")
    _require("prepared proof receipt${checked.length === 1 ? \"\" : \"s\"} selected" in js, "proof selected-count feedback missing")
    for owner in ("Support Ops", "Engineering", "Security"):
        _require(owner in js, f"proof owner lens missing: {owner}")
    _require("attachReviewRunProof" in js, "proof attach handler missing")
    _require("rerunReviewRunPacket" in js, "proof rerun handler missing")
    _require("askReviewRunCoach" in js, "ReviewRun Ask IA coach handler missing")
    _require("renderReviewRunCoachAnswer" in js, "ReviewRun Ask IA answer renderer missing")
    _require('includeCurrentRead ? ["Current read", sections.current_read] : null' in js, "Ask IA user-turn answer must include current read")
    _require("repoCoachInput?.blur();" in js, "Ask IA user-turn answer must release input focus")
    _require("window.requestAnimationFrame(() =>" in js, "Ask IA user-turn answer must pin chat scroll")
    _require("renderReviewRunCoachSuggestions" in js, "Ask IA smart suggestion renderer missing")
    _require("safeCoachSuggestions" in js, "Ask IA suggestion cap/sanitizer missing")
    _require("refreshReviewRunCoachSuggestions" in js, "Ask IA suggestion refresh missing")
    _require("currentReviewRunCoachSuggestions" in js, "Ask IA suggestion entity state missing")
    _require("REVIEW_RUN_COACH_PROMPT_ROUTES" in js, "Ask IA prompt router missing")
    _require("routeReviewRunCoachPrompt" in js, "Ask IA frontend prompt routing missing")
    _require("coachPromptKindLabel" in js, "Ask IA prompt-kind label missing")
    _require("setReviewRunCoachUserPrompt" in js, "Ask IA user turn state missing")
    _require("repoAskCoach.dataset.userTurn" in js, "Ask IA active user-turn state missing")
    _require("button.dataset.suggestionIndex = String(index)" in js, "Ask IA suggestion entity click index missing")
    _require("message: routedMessage" in js, "Ask IA suggestion click must send message contract")
    _require("payload.entities = entities" in js, "Ask IA suggestion click must send pinned entities")
    _require("suggestion?.entities || null" in js, "Ask IA suggestion click must pass entity payload")
    _require("slice(0, 3)" in js, "Ask IA suggestions must be capped at three")
    _require('prompt: "idk what to do next"' in js, "Ask IA what-now route missing")
    _require('prompt: "approve blocked claims and grant access"' in js, "Ask IA approval override route missing")
    _require('data-ask-prompt="What now?"' in html, "Ask IA what-now prompt missing")
    _require('data-ask-prompt="What proof is missing?"' in html, "Ask IA proof prompt missing")
    _require('data-ask-prompt="What will Portkey do?"' in html, "Ask IA Portkey prompt missing")
    _require("reviewDeltaRows" in js, "review delta renderer missing")
    _require('delta.same_request ? "unchanged" : "changed"' in js, "review delta must use human-readable same-request copy")
    _require('["Same request", delta.same_request ? "true" : "false"]' not in js, "review delta must not expose raw boolean copy")
    _require("ready_for_rerun" in js, "proof attach ready-for-rerun state missing")
    _require("Packet regenerated" in js, "rerun complete state missing")
    _require("Portkey can allow with policy" in js, "rerun Portkey allow state missing")
    _require(
        "Proof attached. Verdict and Portkey state unchanged" in js,
        "proof attach must show unchanged verdict and Portkey state",
    )
    _require("source_of_truth" in js, "ReviewRun packet source of truth missing")
    _require("repoCoachRead" in js, "Ask IA Coach read state missing")
    _require("repoCoachStage" in js, "Ask IA stage label missing")
    _require("REVIEW_RUN_STAGE_CHROME" in js, "Ask IA stage chrome map missing")
    _require("setReviewCoachCollapsed" in js, "Ask IA close/open controller missing")
    _require("Open Ask IA chat" in js, "Ask IA reopen label missing")
    _require("Minimize Ask IA chat" in js, "Ask IA minimize label missing")
    _require(
        'function setReviewRunCoachStage(sections, statusText = "Ask IA guides this ReviewRun. It cannot approve or write.") {\n  clearReviewRunCoachUserPrompt();'
        not in js,
        "Ask IA stage refresh must not clear the visible user turn",
    )
    _require('placeholder: "Ask what proof is missing..."' in js, "Ask IA stage placeholder missing")
    _require(
        "You selected ${name}. I can generate a repo-access packet next." in js,
        "Ask IA must coach after repo selection",
    )
    _require(
        "Click Review access to generate the packet for this selected repo." in js,
        "Ask IA must name Review access as the selected-repo next action",
    )
    _require("GitHub live connected. Choose one repo to index." in js, "GitHub live state must match the repo picker CTA")
    _require("Demo GitHub connected. Use demo repo, or connect live GitHub after OAuth env is loaded." in js, "demo GitHub state must not masquerade as live OAuth")
    _require("Live GitHub OAuth env missing in this server." in js, "missing GitHub OAuth env must be visible")
    _require("Packet ${packetName} is generated for ${selectedReviewRepoName()}. Verdict:" in js, "Ask IA must coach after packet generation")
    _require("proofOwnerSummaryForPacket" in js, "Ask IA must summarize proof owners")
    _require(
        "Use prepared proof from ${proofOwnerText}, then regenerate the packet. Ask IA cannot approve blocked claims from chat." in js,
        "Ask IA must explain owner-lensed proof resolution without approving",
    )
    _require("sponsor proof steps" in js, "ProofGraph reveal copy must preserve sponsor proof count")
    _require("Use prepared proof for demo" in js, "proof action must disclose prepared proof behavior")
    _require("Attach checked proof" not in js, "misleading proof attach label returned")
    _require("runRepoProofCockpit" in js, "repo proof cockpit runner missing")
    _require("fetchPortkeyProofForFixture" in js, "Portkey proof fetch helper missing")
    _require("fetchReviewRunPortkeyGuardrailTest" in js, "ReviewRun Portkey guardrail test helper missing")
    _require("fetchReviewRunPortkeyReceipt" in js, "ReviewRun Portkey receipt helper missing")
    _require("/api/portkey/guardrail/events" in js, "ReviewRun Portkey receipt endpoint missing in UI")
    _require("/portkey/guardrail-test" in js, "ReviewRun Portkey guardrail endpoint missing in UI")
    _require("Test Portkey guardrail" in js, "ReviewRun Portkey test CTA missing")
    _require("repo-portkey-runway" in js, "Portkey runway strip missing")
    _require("<span>IA Packet</span>" in js, "Portkey runway must start from IA Packet")
    _require("<span>BYO Guardrail</span>" in js, "Portkey runway must show BYO Guardrail")
    _require("<span>Portkey</span>" in js, "Portkey runway must end at Portkey")
    _require("portkeyRunwayReady" in js, "Portkey runway readiness flag missing")
    _require("openReviewRunPortkeyStage" in js, "Ask IA Portkey prompt must focus the Portkey stage")
    _require("wantsPortkeyStage = /\\bportkey\\b/i.test(routedMessage)" in js, "Ask IA must detect Portkey prompts")
    _require(
        "repoPortkeyCard.open = portkeyTested || portkeyRunwayReady" in js,
        "Portkey row must open after rerun or test",
    )
    _require("effectivePortkeyDecisionLabel" in js, "Portkey verdict display label missing")
    _require(
        'effectivePortkeyVerdict ? "Allow with policy" : "Block"' in js,
        "Portkey verdict must render as a user-facing decision label",
    )
    for expected in (
        "Packet-consumption runway",
        "repo-portkey-revision-flow",
        "portkeyRevisionBefore",
        "portkeyStateAfter",
        "<span>Event id</span>",
        "<span>Still-blocked scope</span>",
        "<span>Policy mutation</span>",
        "Portkey consumes packet metadata from this ReviewRun",
        "No Portkey Admin API mutation, no live policy push.",
        "API mutation: ${escapeHtml(String(portkeyApiMutation))}. Policy mutation: ${escapeHtml(String(portkeyPolicyMutation))}.",
        "Portkey call receipt",
        "Live BYO webhook",
        "Rehearsal webhook",
        "Local tests stay separate.",
    ):
        _require(expected in js, f"Portkey final runway missing: {expected}")
    _require(
        js.count("<span>Verdict</span><strong>${escapeHtml(effectivePortkeyDecisionLabel)}</strong></div>") == 1,
        "Portkey verdict outcome must render once",
    )
    _require(
        "<span>Verdict</span><strong>${escapeHtml(String(effectivePortkeyVerdict))}</strong></div>" not in js,
        "Portkey verdict must not expose raw boolean text",
    )
    _require(
        "Portkey guardrail test recorded locally. No approval, no writes." in js,
        "ReviewRun Portkey test must disclose local read-only event",
    )
    _require("fetchRepoSponsorTrace" in js, "repo sponsor trace fetch helper missing")
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
    _require(".repo-proof-cockpit" in css, "repo proof cockpit CSS missing")
    _require(".repo-runway-panel" in css, "one-run runway panel CSS missing")
    _require(".repo-stage-status" in css, "compact ReviewRun stage status CSS missing")
    _require(".repo-stage-screen[hidden]" in css, "inactive stage screens must be hidden")
    _require('data-active-screen="packet_decision"' in css, "packet decision screen CSS missing")
    _require('data-active-screen="portkey_gate"' in css, "Portkey gate screen CSS missing")
    _require(".repo-option-stack" in css, "review option stack CSS missing")
    _require(".repo-option-row" in css, "Render-style option row CSS missing")
    _require(".repo-infra-rows" in css, "downstream infrastructure rows CSS missing")
    _require(".repo-infra-row" in css, "downstream infrastructure row CSS missing")
    _require(
        ".repo-infra-row:not([open]) .repo-accordion-body" in css,
        "downstream infrastructure rows must stay collapsed until opened",
    )
    _require(".repo-portkey-handoff" in css, "ReviewRun Portkey handoff CSS missing")
    _require(".repo-portkey-runway" in css, "ReviewRun Portkey runway CSS missing")
    _require(".repo-portkey-stage-title" in css, "ReviewRun Portkey stage title CSS missing")
    _require(".repo-portkey-revision-flow" in css, "ReviewRun Portkey revision flow CSS missing")
    _require(".repo-portkey-outcomes" in css, "ReviewRun Portkey outcome CSS missing")
    _require(".repo-portkey-live-receipt" in css, "ReviewRun Portkey receipt CSS missing")
    _require(".repo-portkey-receipt-grid" in css, "ReviewRun Portkey receipt grid CSS missing")
    _require(".repo-portkey-test-action" in css, "ReviewRun Portkey test action CSS missing")
    _require(".repo-ask-floating" in css, "Ask IA floating CSS missing")
    _require("position: fixed !important;" in css, "Ask IA must float above the stage")
    _require("grid-template-columns: minmax(0, 1fr) !important;" in css, "runway must not reserve a sidecar rail")
    _require(".repo-coach-chat" in css, "Ask IA chat wrapper CSS missing")
    _require(".repo-coach-last-user" in css, "Ask IA user bubble CSS missing")
    _require('.repo-ask-sidecar[data-user-turn="true"] .repo-coach-current-read' in css, "Ask IA user-turn duplicate current read must hide")
    _require('.repo-ask-sidecar[data-user-turn="true"] .repo-coach-chat' in css, "Ask IA user-turn transcript height CSS missing")
    _require("min-height: 20rem;" in css, "Ask IA user-turn transcript must reserve answer space")
    _require(".repo-coach-assistant-head" in css, "Ask IA assistant header CSS missing")
    _require('data-prompt-kind="approval_override"' in css, "Ask IA safety correction state CSS missing")
    _require('data-user-turn="true"' in css, "Ask IA active user-turn CSS missing")
    _require('data-suggestion-mode="contract"' in css, "Ask IA smart suggestions must persist after a user turn")
    _require(".repo-coach-answer" in css, "Ask IA answer surface CSS missing")
    _require(".repo-coach-answer-row" in css, "Ask IA answer row CSS missing")
    _require(".repo-coach-toggle" in css, "Ask IA close/open CSS missing")
    _require(".repo-coach-stage-line" in css, "Ask IA stage line CSS missing")
    _require('.repo-ask-floating[data-coach-collapsed="true"]' in css, "Ask IA collapsed floating CSS missing")
    _require(".repo-ask-sidecar .packet-coach-quick-chips" in css, "Ask IA prompts must live in coach CSS")
    _require("max-height: min(18.5rem, calc(100vh - 1.7rem));" in css, "Ask IA floating chat must stay compact")
    _require("PR 137: recording-ready visual polish" in css, "recording polish CSS missing")
    _require("calc(100vh - 9rem)" in css, "loaded ReviewRun recording viewport guard missing")
    _require(".repo-secondary-link-row" in css, "advanced link row CSS missing")
    _require(".repo-movement-grid" in css, "movement class grid CSS missing")
    _require(".repo-movement-lane.allowed" in css, "allowed movement lane CSS missing")
    _require(".repo-movement-lane.review" in css, "review-required movement lane CSS missing")
    _require(".repo-movement-lane.blocked" in css, "blocked movement lane CSS missing")
    _require(".review-lane-grid" not in css, "dead review lane selector CSS returned")
    _require(".review-lane-card" not in css, "dead review lane card CSS returned")
    _require(".repo-connect-panel" in css, "root repo connect panel CSS missing")
    _require(".repo-inline-picker" in css, "root repo picker CSS missing")
    _require(".repo-index-summary" in css, "repo index summary CSS missing")
    _require(".repo-primary-action:disabled" in css, "repo review CTA disabled state missing")
    _require(".repo-review-request" in css, "repo review request CSS missing")
    _require(".repo-proof-result[hidden]" in css, "repo proof result hidden state CSS missing")
    _require(".repo-proof-resolution-card" in css, "repo proof resolution card CSS missing")
    _require(".repo-proof-checklist" in css, "repo proof checklist CSS missing")
    _require(".repo-proof-lens" in css, "repo proof owner lens CSS missing")
    _require(".repo-proof-lens-head" in css, "repo proof owner lens heading CSS missing")
    _require(".repo-proof-receipt" in css, "repo proof receipt CSS missing")
    _require(".repo-proof-receipt-head" in css, "repo proof receipt heading CSS missing")
    _require(".repo-proof-receipt-meta" in css, "repo proof receipt metadata CSS missing")
    _require(".repo-proof-receipt-safety" in css, "repo proof receipt safety CSS missing")
    _require(".repo-proof-check.attached" in css, "repo proof attached item CSS missing")
    _require(".repo-proof-attach-action" in css, "repo proof attach CTA CSS missing")
    _require(".repo-proof-attach-status" in css, "repo proof attach status CSS missing")
    _require(".repo-review-delta" in css, "review delta CSS missing")
    _require(".repo-proof-accordion" in css, "repo proof accordion CSS missing")
    _require(".repo-accordion-body" in css, "repo accordion body CSS missing")
    _require(".repo-verdict-card.review" in css, "repo review verdict CSS missing")
    _require("One-run minimal ReviewRun cockpit" in css, "one-run cockpit contract missing")
    _require("--gloss-panel" in css, "glossy cockpit variables missing")
    _require(
        "body:not([data-active-tab]) .permission-pill" in css,
        "permission pills must use the dark cockpit treatment",
    )
    _require(
        "body:not([data-active-tab]) .btn-primary" in css and "#050506" in css,
        "primary cockpit action must be glossy black",
    )
    _require('data-repo-selected="true"' not in html, "repo selected state must be runtime-only")
    _require('body[data-active-tab="start"] .stack' in css, "start tab must hide status pill cluster")
    _require('body[data-active-tab="start"] #btn-reset' in css, "start tab must hide reset button")
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


def _check_proofgraph_visual(base_url: str, timeout: float) -> None:
    html = _read(base_url, "/proofgraph", timeout=timeout)
    for expected in (
        "InferenceAtlas ProofGraph",
        "The packet authority layer downstream systems trust before AI moves.",
        "80",
        "proof nodes",
        "141",
        "edges",
        "zero",
        "writes",
        "Tavily",
        "Composio",
        "OpenClaw",
        "Nebius",
        "IA Packet Authority",
        "Portkey Gate",
        "Sponsors contribute proof only - IA keeps the packet locked - no approval - no writes - no verdict mutation",
    ):
        _require(expected in html, f"ProofGraph visual missing: {expected}")
    _require("77 proof nodes" not in html, "ProofGraph visual returned stale 77-node screenshot count")
    _require("136 edges" not in html, "ProofGraph visual returned stale 136-edge screenshot count")


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
    created_runs = [item for item in ledger["runs"] if item["run_id"] == run["run_id"]]
    _require(created_runs, "created run missing from ledger")
    _require(
        all(item["safety_lock"]["live_calls_made"] is False for item in created_runs),
        "created smoke run must preserve no-live-call safety lock",
    )
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


def _check_review_run_github_connect(base_url: str, timeout: float, session_id: str) -> None:
    review_session = session_id + "-reviewrun"
    popup_html = _form_post(
        base_url,
        "/api/connectors/oauth/popup/github?session_id=" + urllib.parse.quote(review_session),
        {"demo": "1"},
        timeout=timeout,
    )
    _require("connector-oauth" in popup_html, "demo GitHub sign-in popup did not complete")

    status = _json_get(
        base_url,
        "/api/connectors/status?session_id="
        + urllib.parse.quote(review_session)
        + "&connector_id=github",
        timeout=timeout,
    )
    connection = status["connection"]
    _require(connection["status"] == "connected", "demo GitHub session did not connect")
    _require("access_token" not in connection, "public connector status leaked access token")

    repos = _json_get(
        base_url,
        "/api/connectors/github/repos?session_id="
        + urllib.parse.quote(review_session)
        + "&q=triage",
        timeout=timeout,
    )
    _require(repos["ok"] is True, "GitHub repo list failed after demo sign-in")
    _require(repos["demo"] is True, "demo GitHub session should return demo repo list")
    _require(len(repos["repos"]) >= 1, "demo GitHub repo list empty")
    full_name = repos["repos"][0]["full_name"]

    attached = _json_post(
        base_url,
        "/api/connectors/github/attach",
        {"session_id": review_session, "full_name": full_name},
        timeout=timeout,
    )
    _require(attached["ok"] is True, "selected GitHub repo did not attach")
    _require(attached["digest_chars"] > 100, "selected GitHub repo did not index enough context")

    created = _json_post(
        base_url,
        "/api/review-runs",
        {
            "session_id": review_session,
            "selected_repo": {
                "provider": "github",
                "full_name": full_name,
                "source": "demo_repo",
            },
            "repo_index_summary": {
                "status": "indexed",
                "indexed_repo_count": 1,
                "digest_chars": attached["digest_chars"],
                "readme_found": attached["readme_found"],
                "files_included": attached["files_included"],
                "paths_in_tree": attached["paths_in_tree"],
                "sample_paths": attached["sample_paths"],
            },
        },
        timeout=timeout,
    )
    _require(created["ok"] is True, "ReviewRun create failed for selected repo")
    _require(created["read_only"] is True, "ReviewRun create must be read-only")
    run = created["run"]
    _require(run["stage"] == "repo_selected", "ReviewRun must stop at repo_selected before request entry")
    _require(run["selected_repo"]["full_name"] == full_name, "ReviewRun selected repo drifted")
    _require(run["repo_index_summary"]["indexed_repo_count"] == 1, "ReviewRun must index exactly one repo")
    _require(run["access_request"] == {}, "ReviewRun PR126 must not pre-generate access request")
    _expect_false(
        run["safety_invariants"],
        ["approval_granted", "spend_approved", "permissions_granted", "external_writes_enabled"],
        prefix="review_run.safety_invariants",
    )

    fetched = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]),
        timeout=timeout,
    )
    _require(fetched["run"]["run_id"] == run["run_id"], "ReviewRun did not reload by run_id")
    _require(fetched["record"]["stage"] == "repo_selected", "ReviewRun record stage drifted")

    waiting_graph = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proofgraph",
        timeout=timeout,
    )
    _require(waiting_graph["ok"] is True, "ReviewRun ProofGraph failed before packet")
    _require(waiting_graph["read_only"] is True, "ReviewRun ProofGraph must be read-only")
    _require(waiting_graph["proofgraph"]["graph_state"] == "waiting_for_packet", "ProofGraph before packet state drifted")
    _require(
        waiting_graph["proofgraph"]["generated_from_run_id"] == run["run_id"],
        "ProofGraph before packet missing run_id source",
    )
    _require(waiting_graph["proofgraph"]["portkey_state"] == "No packet", "ProofGraph before packet Portkey state drifted")
    _require(waiting_graph["proofgraph"]["zero_writes"] is True, "ProofGraph before packet must show zero writes")
    _expect_false(
        waiting_graph["proofgraph"]["safety_boundary"],
        [
            "approval_granted",
            "approves_access",
            "permissions_granted",
            "external_writes",
            "mutates_production",
            "portkey_api_call_made",
            "portkey_policy_mutation_allowed",
            "raw_agent_intent_trusted",
        ],
        prefix="review_run_proofgraph_waiting.safety_boundary",
    )

    portkey_before_packet = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/portkey/guardrail-test",
        {},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "no generated packet" in portkey_before_packet.get("detail", ""),
        "Portkey test before packet must fail closed",
    )

    selected_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "hey"},
        timeout=timeout,
    )
    _require(selected_coach["ok"] is True, "ReviewRun coach failed before packet")
    _require(selected_coach["read_only"] is True, "ReviewRun coach must stay read-only")
    _require(selected_coach["answer"]["schema_version"] == "review_run_coach_answer.v0", "coach schema drifted")
    _require(selected_coach["answer"]["prompt_kind"] == "greeting", "coach greeting was not classified")
    _require(selected_coach["answer"]["stage"] == "repo_selected", "coach selected stage drifted")
    _require(len(selected_coach["suggestions"]) <= 3, "coach suggestions must stay capped")
    _require(selected_coach["suggestions"][0]["schema_version"] == "coach_suggestion.v0", "coach suggestion schema drifted")
    _require(selected_coach["suggestions"][0]["label"], "coach suggestion label missing")
    _require(selected_coach["suggestions"][0]["message"], "coach suggestion message missing")
    _require(selected_coach["suggestions"][0]["entities"]["run_id"] == run["run_id"], "coach suggestion run pin missing")
    _require(selected_coach["suggestions"][0]["entities"]["stage"] == "repo_selected", "coach suggestion stage pin missing")
    _require(selected_coach["suggestions"][0]["entities"]["subscriber"] == "cto", "coach suggestion subscriber pin missing")
    _require("No packet exists yet" in selected_coach["answer"]["sections"]["current_read"], "coach selected read drifted")
    _expect_false(
        selected_coach["answer"]["safety_boundary"],
        [
            "approval_granted",
            "approves_access",
            "permissions_granted",
            "external_writes",
            "packet_mutated_without_rerun",
            "raw_packet_dumped",
            "raw_agent_intent_trusted",
            "portkey_api_call_made",
            "portkey_policy_mutation_allowed",
        ],
        prefix="review_run_coach.safety_boundary",
    )

    generated = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/packet",
        {"access_request": "support-triage-bot needs to read issues, comment, and create labels."},
        timeout=timeout,
    )
    _require(generated["ok"] is True, "ReviewRun packet generation failed")
    _require(generated["read_only"] is True, "ReviewRun packet generation must stay read-only")
    packet_run = generated["run"]
    packet = generated["packet"]
    _require(packet_run["stage"] == "packet_generated", "ReviewRun packet did not move to packet_generated")
    _require(packet_run["packet"]["source_run_id"] == run["run_id"], "packet must be tied to run_id")
    _require(packet["schema_version"] == "review_run_packet.v0", "ReviewRun packet schema drifted")
    _require(packet["packet_reference"]["run_id"] == run["run_id"], "packet reference missing run_id")
    _require(packet["packet_reference"]["source_of_truth"] == "ReviewRun", "packet source of truth drifted")
    _require(packet["compact_output"]["allowed"] == ["read issues"], "read issues must be allowed")
    _require(packet["compact_output"]["review_required"] == ["comment"], "comment must stay review/yellow")
    _require("create labels" in packet["compact_output"]["blocked"], "create labels must stay blocked")
    _require("repo admin" in packet["compact_output"]["blocked"], "repo admin must stay blocked")
    _require("org-wide write" in packet["compact_output"]["blocked"], "org-wide write must stay blocked")
    _require("secrets" in packet["compact_output"]["blocked"], "secrets must stay blocked")
    _expect_false(
        packet["safety_boundary"],
        ["approval_granted", "production_access", "permission_grants", "external_writes"],
        prefix="review_run_packet.safety_boundary",
    )
    proof_lenses = packet["proof_resolution"]["owner_lenses"]
    _require(proof_lenses["schema_version"] == "review_run_proof_lenses.v0", "ReviewRun proof lens schema drifted")
    _require(proof_lenses["packet_reference"] == packet["packet_reference"], "proof lenses must read same packet reference")
    active_lenses = {lens["lens_id"] for lens in proof_lenses["lenses"] if lens["active"]}
    inactive_lenses = {lens["lens_id"] for lens in proof_lenses["lenses"] if not lens["active"]}
    _require(active_lenses == {"support_ops", "engineering", "security"}, "active proof owner lenses drifted")
    _require(inactive_lenses == {"finance_procurement", "legal"}, "dormant proof owner lenses drifted")
    _require(proof_lenses["guardrails"]["does_not_approve"] is True, "proof lenses must not approve")
    _require(
        proof_lenses["guardrails"]["proof_attachment_changes_verdict"] is False,
        "proof lenses cannot let proof attachment change verdict",
    )
    for lens in proof_lenses["lenses"]:
        for item in lens["prepared_proof_items"]:
            _require(item["approves_access"] is False, f"{lens['lens_id']} prepared proof approved access")
            _require(item["grants_permissions"] is False, f"{lens['lens_id']} prepared proof granted permissions")
            _require(
                item["mutates_downstream_policy"] is False,
                f"{lens['lens_id']} prepared proof mutated downstream policy",
            )

    rev1_graph = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proofgraph",
        timeout=timeout,
    )["proofgraph"]
    _require(rev1_graph["graph_state"] == "packet_generated", "ProofGraph rev_1 state drifted")
    _require(
        rev1_graph["packet_reference"]["revision_id"] == packet_run["packet"]["revision_id"],
        "ProofGraph rev_1 revision mismatch",
    )
    _require(rev1_graph["selected_repo"] == full_name, "ProofGraph selected repo drifted")
    _require(rev1_graph["portkey_state"] == "Block", "ProofGraph rev_1 Portkey state drifted")
    _require(rev1_graph["proof_counts"]["missing"] == 3, "ProofGraph rev_1 missing proof count drifted")
    _require(rev1_graph["zero_writes"] is True, "ProofGraph rev_1 must show zero writes")
    rev1_graph_hash = rev1_graph["content_hash"]

    rev1_portkey = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/portkey/guardrail-test",
        {},
        timeout=timeout,
    )
    rev1_portkey_test = rev1_portkey["portkey_guardrail_test"]
    _require(rev1_portkey["read_only"] is True, "ReviewRun Portkey test must be read-only")
    _require(rev1_portkey_test["stage"] == "packet_generated", "rev_1 Portkey test stage drifted")
    _require(rev1_portkey_test["portkey_state"] == "Block", "rev_1 Portkey test must block")
    _require(rev1_portkey_test["verdict"] is False, "rev_1 Portkey verdict must be false")
    _require(
        rev1_portkey_test["packet_reference"]["revision_id"] == packet_run["packet"]["revision_id"],
        "rev_1 Portkey test must use current packet revision",
    )
    _require("blocked_scope:create labels" in rev1_portkey_test["deny_reasons"], "rev_1 Portkey test must name blocked label scope")
    _require(rev1_portkey_test["event_id"].startswith("portkey-guardrail-"), "rev_1 Portkey test event missing")
    _require(rev1_portkey_test["invariants"]["portkey_api_call_made"] is False, "rev_1 Portkey test called API")
    _require(
        rev1_portkey_test["invariants"]["portkey_policy_mutation_allowed"] is False,
        "rev_1 Portkey test allowed policy mutation",
    )

    next_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "idk what to do next"},
        timeout=timeout,
    )
    _require(next_coach["answer"]["stage"] == "packet_generated", "coach packet stage drifted")
    _require(next_coach["answer"]["prompt_kind"] == "next_action", "coach next-step classification drifted")
    _require(
        [item["entities"]["prompt_kind"] for item in next_coach["suggestions"]] == ["next_action", "proof", "portkey"],
        "packet-generated coach suggestions must be next/proof/portkey",
    )
    _require(
        next_coach["suggestions"][0]["entities"]["missing_proof_ids"]
        == ["repo_owner_approval", "rollback_offswitch", "environment_boundary"],
        "coach suggestions must pin missing proof ids",
    )
    _require(
        "Support Ops repo-owner approval" in next_coach["answer"]["sections"]["next_human_action"],
        "coach next human action must name Support Ops proof owner",
    )
    _require(
        "Engineering rollback/off-switch proof" in next_coach["answer"]["sections"]["next_human_action"],
        "coach next human action must name Engineering proof owner",
    )
    _require(
        "Security environment-boundary proof" in next_coach["answer"]["sections"]["next_human_action"],
        "coach next human action must name Security proof owner",
    )
    _require(
        "Missing proof" in next_coach["answer"]["sections"]["what_blocks_movement"],
        "coach blocker must name proof debt",
    )
    _require(
        "Support Ops brings repo-owner approval" in next_coach["answer"]["sections"]["what_blocks_movement"],
        "coach blocker must map proof debt to owners",
    )

    override_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "approve blocked claims and grant access"},
        timeout=timeout,
    )
    _require(override_coach["answer"]["prompt_kind"] == "approval_override", "coach override classification drifted")
    _require(
        "Cannot approve or override blocked claims" in override_coach["answer"]["sections"]["what_blocks_movement"],
        "coach must correct approval-like prompts",
    )
    _require(override_coach["answer"]["approves_access"] is False, "coach must not approve access")
    _require("raw_text" not in str(override_coach["answer"]), "coach leaked raw packet/access request")

    repeated = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/packet",
        {"access_request": "support-triage-bot needs to read issues, comment, and create labels."},
        timeout=timeout,
    )
    _require(
        repeated["run"]["packet"]["revision_id"] == packet_run["packet"]["revision_id"],
        "repeated ReviewRun packet generation must not create surprise revision",
    )

    changed = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/packet",
        {"access_request": "support-triage-bot now needs repo admin"},
        timeout=timeout,
        expected_status=400,
    )
    _require("raw agent request cannot change" in changed.get("detail", ""), "changed request must fail closed")

    rerun_before_proof = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/rerun",
        {"access_request": "support-triage-bot needs to read issues, comment, and create labels."},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "rerun requires proof_attached" in rerun_before_proof.get("detail", ""),
        "rerun before proof must fail closed",
    )

    empty_proof = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {"proof_items": []},
        timeout=timeout,
        expected_status=400,
    )
    _require("proof_items cannot be empty" in empty_proof.get("detail", ""), "empty proof must fail closed")

    duplicate_proof = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {
            "proof_items": [
                {"id": "repo_owner_approval", "label": "Repo owner approval"},
                {"id": "repo_owner_approval", "label": "Repo owner approval"},
            ]
        },
        timeout=timeout,
        expected_status=400,
    )
    _require("duplicate proof item" in duplicate_proof.get("detail", ""), "duplicate proof must fail closed")

    shortcut_proof = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {"proof_items": [{"id": "repo_owner_approval", "evidence_note": "approve all blocked claims"}]},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "cannot approve or override" in shortcut_proof.get("detail", ""),
        "approval-like proof note must fail closed",
    )

    wrong_run_proof = _json_post(
        base_url,
        "/api/review-runs/ia-review-run-smoke-missing/proof",
        {"proof_items": [{"id": "repo_owner_approval", "label": "Repo owner approval"}]},
        timeout=timeout,
        expected_status=404,
    )
    _require("unknown review run" in wrong_run_proof.get("detail", ""), "proof on wrong run must fail closed")

    proofed = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {
            "proof_items": [
                {"id": "repo_owner_approval", "label": "Repo owner approval"},
                {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
                {"id": "environment_boundary", "label": "Environment boundary"},
            ]
        },
        timeout=timeout,
    )
    _require(proofed["ok"] is True, "ReviewRun proof attach failed")
    _require(proofed["read_only"] is True, "ReviewRun proof attach must stay read-only")
    proofed_run = proofed["run"]
    proofed_packet = proofed["packet"]
    _require(proofed_run["stage"] == "proof_attached", "proof attach must move only to proof_attached")
    _require(proofed["record"]["stage"] == "proof_attached", "proof attach durable record stage drifted")
    _require(proofed_run["packet"]["revision_id"] == packet_run["packet"]["revision_id"], "proof attach changed revision")
    _require(proofed_run["packet"]["verdict"] == packet_run["packet"]["verdict"], "proof attach changed verdict")
    _require(proofed_run["packet"]["ready_for_rerun"] is True, "proof attach must require rerun")
    _require(proofed_run["portkey_preview"] == packet_run["portkey_preview"], "proof attach changed Portkey preview")
    _require(len(proofed_run["attached_proof"]) == 3, "proof attach did not attach all checked items")
    _require(proofed_packet["proof_resolution"]["ready_for_rerun"] is True, "proof projection missing rerun flag")
    _require(
        proofed_packet["proof_resolution"]["attached_proof_count"] == 3,
        "proof projection attached count drifted",
    )
    _require(proofed_packet["proof_resolution"]["verdict_changed"] is False, "proof projection changed verdict")
    _require(proofed_packet["proof_resolution"]["portkey_changed"] is False, "proof projection changed Portkey")
    proofed_lenses = proofed_packet["proof_resolution"]["owner_lenses"]
    _require(
        {lens["lens_id"] for lens in proofed_lenses["lenses"] if lens["active"]} == {"support_ops", "engineering", "security"},
        "proofed active proof owner lenses drifted",
    )
    for lens in proofed_lenses["lenses"]:
        if lens["active"]:
            _require(len(lens["missing_proof"]) == 0, f"{lens['lens_id']} did not clear missing proof after attach")
            _require(len(lens["attached_proof"]) == 1, f"{lens['lens_id']} did not show attached proof")
    _require(
        proofed_lenses["guardrails"]["proof_attachment_changes_verdict"] is False,
        "proofed lenses allowed proof attachment to change verdict",
    )
    _require(
        proofed_packet["compact_output"]["ready_for_rerun"] is True,
        "compact output missing ready_for_rerun",
    )
    _expect_false(
        proofed_packet["safety_boundary"],
        [
            "approval_granted",
            "production_access",
            "permission_grants",
            "external_writes",
            "packet_mutated_without_rerun",
            "proof_attachment_changes_verdict",
            "portkey_api_call_made",
            "portkey_policy_mutation_allowed",
            "raw_agent_intent_trusted",
        ],
        prefix="review_run_proof.safety_boundary",
    )

    proof_graph = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proofgraph",
        timeout=timeout,
    )["proofgraph"]
    _require(
        proof_graph["graph_state"] == "proof_attached_rerun_required",
        "ProofGraph proof-attached state drifted",
    )
    _require(
        proof_graph["packet_reference"]["revision_id"] == packet_run["packet"]["revision_id"],
        "ProofGraph proof attach changed packet revision",
    )
    _require(proof_graph["proof_counts"]["attached"] == 3, "ProofGraph proof attached count drifted")
    _require(proof_graph["proof_counts"]["missing"] == 0, "ProofGraph proof missing count drifted")
    _require(proof_graph["portkey_state"] == "Block", "ProofGraph proof Portkey state drifted")

    proof_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "what next"},
        timeout=timeout,
    )
    _require(proof_coach["answer"]["stage"] == "proof_attached", "coach proof stage drifted")
    _require(
        "Regenerate the packet" in proof_coach["answer"]["sections"]["next_human_action"],
        "coach must tell human to rerun after proof",
    )

    repeated_proof = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proof",
        {"proof_items": [{"id": "repo_owner_approval", "label": "Repo owner approval"}]},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "proof attachment requires generated packet state" in repeated_proof.get("detail", ""),
        "second proof attach must fail closed until rerun",
    )

    changed_rerun = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/rerun",
        {"access_request": "support-triage-bot now needs repo admin"},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "raw agent request cannot change before rerun" in changed_rerun.get("detail", ""),
        "rerun with changed raw request must fail closed",
    )

    rerun = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/rerun",
        {"access_request": "support-triage-bot needs to read issues, comment, and create labels."},
        timeout=timeout,
    )
    _require(rerun["ok"] is True, "ReviewRun rerun failed")
    _require(rerun["read_only"] is True, "ReviewRun rerun must stay read-only")
    rerun_run = rerun["run"]
    rerun_packet = rerun["packet"]
    rerun_delta = rerun["review_delta"]
    _require(rerun_run["stage"] == "ready_to_export", "rerun must move to ready_to_export")
    _require(rerun_run["packet"]["previous_revision_id"] == proofed_run["packet"]["revision_id"], "rerun previous revision drifted")
    _require(rerun_run["packet"]["revision_id"] != proofed_run["packet"]["revision_id"], "rerun did not create new revision")
    _require(rerun_run["packet"]["revision_number"] == 2, "rerun must create packet revision 2")
    _require(rerun_run["packet"]["verdict"] == "ready_with_gates", "rerun verdict must be ready_with_gates")
    _require(rerun_run["packet"]["ready_for_rerun"] is False, "rerun must clear ready_for_rerun")
    _require(
        rerun_packet["compact_output"]["allowed"] == ["read issues", "comment", "create labels in selected repo"],
        "rerun allowed movement drifted",
    )
    _require(rerun_packet["compact_output"]["review_required"] == [], "rerun review lane should be clear")
    _require(
        rerun_packet["compact_output"]["blocked"] == ["repo admin", "org-wide write", "secrets"],
        "rerun still-blocked movement drifted",
    )
    _require(rerun_delta["same_request"] is True, "rerun must preserve raw request")
    _require(rerun_delta["packet_changed"] is True, "rerun must show packet changed")
    _require(rerun_delta["packet_revision_before"] == proofed_run["packet"]["revision_id"], "rerun delta before revision drifted")
    _require(rerun_delta["packet_revision_after"] == rerun_run["packet"]["revision_id"], "rerun delta after revision drifted")
    _require(rerun_delta["portkey_before"] == "Block", "rerun delta must start from Portkey block")
    _require(rerun_delta["portkey_after"] == "Allow with policy", "rerun delta must end with Portkey allow with policy")
    _require(rerun_delta["still_blocked"] == ["repo admin", "org-wide write", "secrets"], "rerun delta still-blocked drifted")
    _require(rerun["portkey"]["state"] == "Allow with policy", "rerun Portkey state must allow with policy")
    _require(rerun["portkey"]["portkey_guardrail_response"]["verdict"] is True, "rerun Portkey guardrail must allow")
    _require(rerun["portkey"]["api_call_made"] is False, "rerun must not call Portkey API")
    _require(rerun["portkey"]["policy_mutation_allowed"] is False, "rerun must not mutate Portkey policy")
    _expect_false(
        rerun_packet["safety_boundary"],
        [
            "approval_granted",
            "production_access",
            "permission_grants",
            "external_writes",
            "packet_mutated_without_rerun",
            "proof_attachment_changes_verdict",
            "portkey_api_call_made",
            "portkey_policy_mutation_allowed",
            "raw_agent_intent_trusted",
        ],
        prefix="review_run_rerun.safety_boundary",
    )

    rev2_graph = _json_get(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/proofgraph",
        timeout=timeout,
    )["proofgraph"]
    _require(rev2_graph["graph_state"] == "updated_packet_ready", "ProofGraph rev_2 state drifted")
    _require(rev2_graph["revision_changed"] is True, "ProofGraph rev_2 must mark revision changed")
    _require(
        rev2_graph["packet_reference"]["previous_revision_id"] == proofed_run["packet"]["revision_id"],
        "ProofGraph rev_2 previous revision mismatch",
    )
    _require(
        rev2_graph["packet_reference"]["revision_id"] == rerun_run["packet"]["revision_id"],
        "ProofGraph rev_2 revision mismatch",
    )
    _require(rev2_graph["portkey_state"] == "Allow with policy", "ProofGraph rev_2 Portkey state drifted")
    _require(rev2_graph["content_hash"] != rev1_graph_hash, "ProofGraph content hash did not change from rev_1 to rev_2")
    _require(rev2_graph["zero_writes"] is True, "ProofGraph rev_2 must show zero writes")

    rev2_portkey = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/portkey/guardrail-test",
        {},
        timeout=timeout,
    )
    rev2_portkey_test = rev2_portkey["portkey_guardrail_test"]
    _require(rev2_portkey_test["stage"] == "ready_to_export", "rev_2 Portkey test stage drifted")
    _require(rev2_portkey_test["portkey_state"] == "Allow with policy", "rev_2 Portkey test must allow with policy")
    _require(rev2_portkey_test["verdict"] is True, "rev_2 Portkey verdict must be true")
    _require(rev2_portkey_test["deny_reasons"] == [], "rev_2 Portkey test must have no deny reasons")
    _require(
        rev2_portkey_test["packet_reference"]["revision_id"] == rerun_run["packet"]["revision_id"],
        "rev_2 Portkey test must use updated packet revision",
    )
    _require(
        rev2_portkey_test["allowed_scope"] == ["read issues", "comment", "create labels in selected repo"],
        "rev_2 Portkey allowed scope drifted",
    )
    _require(
        rev2_portkey_test["still_blocked_scope"] == ["repo admin", "org-wide write", "secrets"],
        "rev_2 Portkey still-blocked scope drifted",
    )
    _require(rev2_portkey_test["invariants"]["packet_remains_authority"] is True, "rev_2 Portkey test lost packet authority")
    _require(rev2_portkey_test["invariants"]["portkey_api_call_made"] is False, "rev_2 Portkey test called API")
    _require(
        rev2_portkey_test["invariants"]["portkey_policy_mutation_allowed"] is False,
        "rev_2 Portkey test allowed policy mutation",
    )

    proofgraph_html = _read(
        base_url,
        "/proofgraph?review_run_id=" + urllib.parse.quote(run["run_id"]),
        timeout=timeout,
    )
    for expected in (
        "InferenceAtlas ReviewRun ProofGraph",
        "Generated from run_id",
        run["run_id"],
        full_name,
        rerun_run["packet"]["revision_id"],
        "Allow with policy",
        "Packet remains authority",
        "Sponsors contribute proof only",
        "zero writes",
    ):
        _require(expected in proofgraph_html, f"dynamic ProofGraph visual missing: {expected}")

    portkey_coach = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/coach",
        {"prompt": "what will Portkey do?"},
        timeout=timeout,
    )
    _require(portkey_coach["answer"]["stage"] == "ready_to_export", "coach rerun stage drifted")
    _require(portkey_coach["answer"]["portkey_state"] == "Allow with policy", "coach Portkey state drifted")
    _require(
        "Still blocked downstream: repo admin, org-wide write, secrets"
        in portkey_coach["answer"]["sections"]["downstream_impact"],
        "coach must keep hard blocked scopes visible",
    )

    repeated_rerun = _json_post(
        base_url,
        "/api/review-runs/" + urllib.parse.quote(run["run_id"]) + "/rerun",
        {"access_request": "support-triage-bot needs to read issues, comment, and create labels."},
        timeout=timeout,
        expected_status=400,
    )
    _require(
        "rerun requires proof_attached" in repeated_rerun.get("detail", ""),
        "second rerun must fail closed",
    )


def run_smoke(base_url: str, *, timeout: float, session_id: str) -> list[str]:
    steps: list[tuple[str, Any]] = [
        ("first-run surface", lambda: _check_first_run(base_url, timeout)),
        ("GitHub repo select ReviewRun", lambda: _check_review_run_github_connect(base_url, timeout, session_id)),
        ("IA Packet fixtures", lambda: [_check_packet(base_url, fixture, timeout) for fixture in PACKET_FIXTURES]),
        ("Workbench", lambda: _check_workbench(base_url, timeout)),
        ("Walkthrough", lambda: _check_walkthrough(base_url, timeout)),
        ("Portkey + Ask IA", lambda: _check_portkey_and_chat(base_url, timeout, session_id)),
        ("ProofGraph visual", lambda: _check_proofgraph_visual(base_url, timeout)),
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
