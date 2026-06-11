"""Web file registry and mind API smoke tests."""

import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from web.files_io import load_upload, register_download, resolve_download, save_output, save_upload


ROOT = Path(__file__).resolve().parents[1]


class WebFilesTests(unittest.TestCase):
    def test_upload_load_roundtrip(self) -> None:
        scope = "test_scope"
        file_id, name, _ = save_upload(
            scope=scope,
            filename="note.txt",
            data=b"hello evidence",
        )
        loaded = load_upload(scope, file_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded[0], name)
        self.assertIn("hello", loaded[1])

    def test_register_download(self) -> None:
        path = save_output(scope="test_dl", filename="x.md", content="# hi", use_timestamp=False)
        file_id = register_download(path, label="Hi")
        resolved = resolve_download(file_id)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertTrue(resolved[0].is_file())

    def test_mind_init_and_step_handlers(self) -> None:
        from web.app import mind_init, mind_step

        init_data = mind_init()
        self.assertTrue(init_data.get("cycle_results"))
        self.assertEqual(len(init_data["minds"]), 3)
        step_data = mind_step(type("B", (), {"scenario": None, "no_cortex": False})())
        self.assertTrue(step_data.get("cycle_results"))
        self.assertGreaterEqual(len(step_data["cycle_results"]), 3)
        arts = step_data["cycle_results"][0]["live"]["artifacts"]
        self.assertTrue(any(a.get("file_id") for a in arts))

    def test_live_evidence_rehearsal_handler(self) -> None:
        from web.app import run_live_evidence_rehearsal

        data = run_live_evidence_rehearsal()

        self.assertTrue(data["ok"])
        self.assertTrue(data["summary"]["sanitized_evidence_attached"])
        self.assertTrue(data["summary"]["decision_locked_after_rehearsal"])
        self.assertEqual(data["live_evidence_rehearsal"]["sanitized_provider_count"], 4)
        self.assertEqual(len(data["providers"]), 4)
        self.assertFalse(data["decision_lock"]["production_access"])
        self.assertFalse(data["decision_lock"]["permission_grants"])
        self.assertFalse(data["decision_lock"]["external_writes"])
        self.assertFalse(data["decision_lock"]["can_sponsor_change_decision"])
        self.assertTrue(all(provider["evidence_attached"] for provider in data["providers"]))
        self.assertTrue(all(not provider["would_execute"] for provider in data["providers"]))
        self.assertTrue(any(item["file_id"] for item in data["output_files"]))

    def test_example_cards_have_deterministic_tool_replies(self) -> None:
        from web.app import _deterministic_example_reply

        catalog = _deterministic_example_reply(
            "Use get_catalog_summary: what does InferenceAtlas track?"
        )
        self.assertIsNotNone(catalog)
        assert catalog is not None
        self.assertIn("InferenceAtlas Catalog", catalog)

        alternative = _deterministic_example_reply(
            "I run 500M tokens/month on GPT-4o input+output. "
            "Use compare_providers for llm and recommend the cheapest credible alternative."
        )
        self.assertIsNotNone(alternative)
        assert alternative is not None
        self.assertIn("Catalog comparison", alternative)
        self.assertIn("procurement shortlist", alternative)

        with patch("web.app.tavily_search", return_value="Mistral live result") as tavily:
            mistral = _deterministic_example_reply(
                "Use tavily_search for Mistral Large pricing, then compare_providers "
                "for llm workloads in the catalog."
            )
        tavily.assert_called_once_with(
            "site:mistral.ai pricing Mistral Large API official", max_results=2
        )
        self.assertIsNotNone(mistral)
        assert mistral is not None
        self.assertIn("Mistral live result", mistral)
        self.assertIn("Catalog comparison", mistral)
        self.assertIn("Composio remains dry-run", mistral)

        access_review = _deterministic_example_reply(
            "Should our support triage agent get GitHub issues, Slack incident channels, "
            "and Jira ticket creation access?"
        )
        self.assertIsNotNone(access_review)
        assert access_review is not None
        self.assertIn("Tool access review", access_review)
        self.assertIn("Do not grant production access.", access_review)
        self.assertIn("scoped validation review", access_review)
        self.assertIn("Runtime Permission Boundary", access_review)
        self.assertIn("Composio remains dry-run", access_review)

    def test_live_evidence_rehearsal_ui_is_reachable(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btn-run-rehearsal"', html)
        self.assertIn('id="custom-evidence-file"', html)
        self.assertIn('id="btn-run-uploaded-rehearsal"', html)
        self.assertIn("Run sponsor rehearsal", html)
        self.assertIn("Run uploaded rehearsal", html)
        self.assertIn("/api/rehearsal/live-evidence", js)
        self.assertIn("/api/rehearsal/custom-evidence", js)
        self.assertIn("renderRehearsalCard", js)

    def test_chat_empty_state_surfaces_locked_proof_state(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")

        self.assertIn('id="repo-proof-cockpit"', html)
        self.assertIn('data-fixture="support_triage_agent"', html)
        self.assertIn("ReviewRun", html)
        self.assertIn("One review. One packet. One coach.", html)
        self.assertIn("Connect a repo, generate the IA Packet, then let downstream gates read the packet before movement.", html)
        self.assertIn("Review cockpit", html)
        self.assertIn('class="repo-runway-panel"', html)
        self.assertIn('class="repo-stage-status"', html)
        self.assertIn('id="repo-stage-repo-status"', html)
        self.assertIn('id="repo-stage-packet-status"', html)
        self.assertIn('id="repo-stage-proof-status"', html)
        self.assertIn('id="repo-stage-portkey-status"', html)
        self.assertIn('class="repo-option-stack"', html)
        self.assertIn('data-stage-screen="repo_setup"', html)
        self.assertIn('data-stage-screen="packet_decision"', html)
        self.assertIn('data-stage-screen="proof_workbench"', html)
        self.assertIn('data-stage-screen="packet_rerun"', html)
        self.assertIn('data-stage-screen="portkey_gate"', html)
        self.assertEqual(len(re.findall(r'data-stage-screen="[^"]+"(?![^>]*hidden)', html)), 1)
        self.assertIn('aria-label="Connect repo"', html)
        self.assertIn('aria-current="step"', html)
        self.assertIn("Repo access", html)
        self.assertIn("Connect GitHub", html)
        self.assertIn("Use demo repo", html)
        self.assertIn("Connect repo", html)
        self.assertIn("IA indexes only that repo for this ReviewRun.", html)
        self.assertIn('id="repo-inline-list"', html)
        self.assertIn("Choose one GitHub repository", html)
        self.assertIn("Selected repo", html)
        self.assertIn("Index", html)
        self.assertIn("ReviewRun", html)
        self.assertIn("Connect and index one repo before generating a packet.", html)
        self.assertIn("Ask IA", html)
        self.assertIn("Chat coach", html)
        self.assertIn("ensureCoachThreadWelcome", js)
        self.assertIn('class="repo-ask-sidecar repo-ask-floating"', html)
        self.assertIn('role="dialog"', html)
        self.assertIn('data-coach-mode="floating"', html)
        self.assertIn('id="repo-coach-toggle"', html)
        self.assertIn("Minimize Ask IA chat", html)
        self.assertIn('id="repo-coach-stage"', html)
        self.assertIn('id="review-flow-steps"', html)
        self.assertIn('id="review-run-rail"', html)
        self.assertIn('id="repo-coach-thread-scroll"', html)
        self.assertIn('id="repo-coach-thread"', html)
        self.assertIn('id="repo-coach-followup-chips"', html)
        self.assertIn('id="repo-coach-resize-corner"', html)
        self.assertIn('id="repo-coach-maximize"', html)
        self.assertIn('id="repo-index-tracker"', html)
        self.assertIn("Ask what to do next...", html)
        self.assertIn("Ask IA guides this run. It does not approve or write.", html)
        self.assertIn("Review AI spend", html)
        self.assertIn("Test downstream gate", html)
        self.assertIn("support-triage-bot wants repo access", html)
        self.assertIn("support-triage-bot", html)
        self.assertIn("Choose a GitHub repo first.", html)
        self.assertIn("Review access", html)
        self.assertIn("Next human action", html)
        self.assertIn("ProofGraph", html)
        self.assertIn("Waiting for packet", html)
        self.assertIn("Portkey", html)
        self.assertIn("repo-infra-rows", html)
        self.assertIn("Open ProofGraph", html)
        self.assertIn('id="repo-rerun-card"', html)
        self.assertIn("Same request. New proof. Updated packet.", html)
        self.assertIn('id="repo-proof-resolution-card"', html)
        self.assertIn("Use prepared proof before rerun.", html)
        self.assertIn(
            "Review prepared human proof receipts. Using them attaches evidence only; it does not approve access.",
            html,
        )
        self.assertIn('class="repo-proof-checklist"', html)
        self.assertIn("Use prepared proof for demo", html)
        self.assertNotIn("Attach checked proof", html)
        self.assertIn('class="repo-review-delta"', html)
        self.assertIn("No prepared proof used yet. Verdict unchanged.", html)
        self.assertIn("<summary>More examples</summary>", html)
        self.assertIn(
            "Downstream systems do not trust raw agent intent. They trust the IA Packet.",
            html,
        )
        self.assertIn("<strong>Attach repo:</strong> use the demo GitHub access request.", html)
        self.assertIn("<strong>Run IA:</strong> generate the packet-backed review.", html)
        self.assertIn("<strong>Act:</strong> follow the one named human action.", html)
        self.assertIn('class="composer-shell first-run-locked"', html)
        self.assertIn("Ask IA packet coach", html)
        self.assertIn("Packet-backed decision coach", html)
        self.assertIn("Load an IA Packet, then ask a packet-backed follow-up. IA stays read-only.", html)
        self.assertIn('class="repo-ask-sidecar repo-ask-floating"', html)
        self.assertIn('id="repo-coach-form"', html)
        self.assertIn("What now?", html)
        self.assertIn("Missing proof", html)
        self.assertIn("Review route", html)
        self.assertNotIn("Should this AI agent get repo access?", html)
        self.assertNotIn("Run proof check", html)
        self.assertNotIn("Run IA Packet Review", html)
        self.assertNotIn("Open one registered AI movement request. IA shows the packet", html)
        self.assertNotIn('class="review-lane-grid"', html)
        self.assertNotIn('class="review-lane-card', html)
        self.assertNotIn('class="repo-proof-grid"', html)
        self.assertNotIn('id="repo-advanced-card"', html)
        self.assertIn('rel="icon"', html)
        self.assertRegex(html, r'/static/style\.css\?v=\d+')
        self.assertRegex(html, r'/static/app\.js\?v=\d+')
        self.assertIn('/static/style.css?v=58', html)
        self.assertIn('/static/app.js?v=80', html)
        self.assertIn("REPO_PROOF_FIXTURE", js)
        self.assertIn('const REPO_PROOF_FIXTURE = "support_triage_agent";', js)
        self.assertIn("btnRootConnectGithub", js)
        self.assertIn("btnRootDemoGithub", js)
        self.assertIn("loadReviewRepoList", js)
        self.assertIn("attachReviewRepo", js)
        self.assertIn("createReviewRunForIndexedRepo", js)
        self.assertIn('fetch("/api/review-runs"', js)
        self.assertIn('status: repo.digest_chars ? "indexed" : "ready"', js)
        self.assertIn("currentReviewRun.stage === \"repo_selected\"", js)
        self.assertIn("Connect and index one GitHub repo before generating a packet.", js)
        self.assertIn("Demo list. Select one repo; IA indexes only that repo for this ReviewRun.", js)
        self.assertIn("repoCoachRead", js)
        self.assertIn("repoCoachStage", js)
        self.assertIn("REVIEW_RUN_STAGE_CHROME", js)
        self.assertIn("setReviewCoachCollapsed", js)
        self.assertIn('label: "Ready to review"', js)
        self.assertIn('placeholder: "Ask what proof is missing..."', js)
        self.assertIn("reviewRunUiStage", js)
        self.assertIn("reviewRunActiveScreen", js)
        self.assertIn("reviewRunVisibleScreens", js)
        self.assertIn("return [reviewRunActiveScreen(stage)];", js)
        self.assertNotIn('return ["packet_decision", "proof_workbench"]', js)
        self.assertNotIn('return ["packet_decision", "proof_workbench", "downstream_outputs"]', js)
        self.assertIn("focusReviewRunScreen", js)
        self.assertIn('focusReviewRunScreen("proof_workbench")', js)
        self.assertIn("updateReviewRunStageScreens", js)
        self.assertIn("updateReviewRunStageStatus", js)
        self.assertIn("setReviewRunUiStage", js)
        self.assertIn("repoProofCockpit.dataset.activeScreen", js)
        self.assertIn("REVIEW_RUN_COACH_PROMPT_ROUTES", js)
        self.assertIn("routeReviewRunCoachPrompt", js)
        self.assertIn("coachPromptKindLabel", js)
        self.assertIn("setReviewRunCoachUserPrompt", js)
        self.assertIn("clearReviewRunCoachUserPrompt", js)
        self.assertNotIn("function setReviewRunCoachStage(sections, statusText = \"Ask IA guides this ReviewRun. It cannot approve or write.\") {\n  clearReviewRunCoachUserPrompt();", js)
        self.assertNotIn("function renderLocalReviewRunCoach(sections) {\n  clearReviewRunCoachUserPrompt();", js)
        self.assertIn("repoAskCoach.dataset.userTurn", js)
        self.assertIn('prompt: "idk what to do next"', js)
        self.assertIn('prompt: "approve blocked claims and grant access"', js)
        self.assertIn("You selected ${name}. I can generate a repo-access packet next.", js)
        self.assertIn("Click Review access to generate the packet for this selected repo.", js)
        self.assertIn("GitHub live connected. Choose one repo to index.", js)
        self.assertIn(
            "Demo GitHub connected. Use demo repo, or connect live GitHub after OAuth env is loaded.",
            js,
        )
        self.assertIn("Live GitHub OAuth env missing in this server.", js)
        self.assertNotIn('showConnectorToast("GitHub", indexedRepo.index_label', js)
        self.assertIn("Packet ${packetName} is generated for ${selectedReviewRepoName()}. Verdict:", js)
        self.assertIn("proofOwnerSummaryForPacket", js)
        self.assertIn("Missing proof owners: ${proofOwnerText}.", js)
        self.assertIn("Use prepared proof from ${proofOwnerText}, then regenerate the packet. Ask IA cannot approve blocked claims from chat.", js)
        self.assertIn("Support Ops", js)
        self.assertIn("Engineering", js)
        self.assertIn("Security", js)
        self.assertIn("sponsor proof steps", js)
        self.assertIn("Open generated ProofGraph", js)
        self.assertIn("currentReviewRunProofGraph", js)
        self.assertIn("reviewRunProofGraphUrl", js)
        self.assertIn("fetchReviewRunProofGraph", js)
        self.assertIn("/api/review-runs/${encodeURIComponent(runId)}/proofgraph", js)
        self.assertIn("/proofgraph?review_run_id=", js)
        self.assertNotIn("ReviewRun ProofGraph summary", js)
        self.assertNotIn("repo-proofgraph-map", js)
        self.assertIn("Generated from run_id", js)
        self.assertIn("Packet remains authority. Sponsors contribute proof only. No approval / no writes / no mutation.", js)
        self.assertIn("zero writes", js)
        self.assertIn("sponsor_proof_trace: sponsorTrace || undefined", js)
        self.assertIn("DEFAULT_REVIEW_ACCESS_REQUEST", js)
        self.assertIn("DEFAULT_REVIEW_PROOF_ITEMS", js)
        self.assertIn("support-triage-bot needs to read issues, comment, and create labels.", js)
        self.assertIn('/api/review-runs/${encodeURIComponent(runId)}/packet', js)
        self.assertIn('/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/proof', js)
        self.assertIn('/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/rerun', js)
        self.assertIn("movementLane", js)
        self.assertIn("renderRepoProofResolution", js)
        self.assertIn("proofLensesForPacket", js)
        self.assertIn("proofReceiptTimestamp", js)
        self.assertIn("proofReceiptSafetyPills", js)
        self.assertIn("owner_lenses", js)
        self.assertIn("data-owner-lens", js)
        self.assertIn("data-proof-owner", js)
        self.assertIn("data-proof-receipt", js)
        self.assertIn("data-proof-timestamp", js)
        self.assertIn("Prepared receipt", js)
        self.assertIn("Attached receipt", js)
        self.assertIn("Use prepared receipt", js)
        self.assertIn("Supplied by: ${escapeHtml(ownerGroup)}", js)
        self.assertIn("Timestamp: ${escapeHtml(receiptTimestamp)}", js)
        self.assertIn("not approval", js)
        self.assertIn("no writes", js)
        self.assertIn("rerun required", js)
        self.assertIn("prepared proof receipt${checked.length === 1 ? \"\" : \"s\"} selected", js)
        self.assertIn("attachReviewRunProof", js)
        self.assertIn("rerunReviewRunPacket", js)
        self.assertIn("reviewDeltaRows", js)
        self.assertIn('delta.same_request ? "unchanged" : "changed"', js)
        self.assertNotIn('["Same request", delta.same_request ? "true" : "false"]', js)
        self.assertIn("ready_for_rerun", js)
        self.assertIn("Packet regenerated", js)
        self.assertIn("Portkey can allow with policy", js)
        self.assertIn("Proof attached. Verdict and Portkey state unchanged", js)
        self.assertIn("Use prepared proof for demo", js)
        self.assertIn("No prepared proof used yet. Verdict unchanged.", js)
        self.assertNotIn("Attach checked proof", js)
        self.assertIn("repo-movement-grid", js)
        self.assertIn("Review required", js)
        self.assertIn("source_of_truth", js)
        self.assertIn("runRepoProofCockpit", js)
        self.assertIn("renderRepoProofCockpit", js)
        self.assertIn("fetchPortkeyProofForFixture", js)
        self.assertIn("fetchReviewRunPortkeyGuardrailTest", js)
        self.assertIn('/portkey/guardrail-test', js)
        self.assertIn("Test Portkey guardrail", js)
        self.assertIn("repo-portkey-runway", js)
        self.assertIn("<span>IA Packet</span>", js)
        self.assertIn("<span>BYO Guardrail</span>", js)
        self.assertIn("<span>Portkey</span>", js)
        self.assertIn("portkeyRunwayReady", js)
        self.assertIn("btnOpenPortkeyStage", js)
        self.assertIn("openReviewRunPortkeyStage", js)
        self.assertIn('wantsPortkeyStage = /\\bportkey\\b/i.test(routedMessage)', js)
        self.assertIn("repo-rerun-delta", js)
        self.assertIn("effectivePortkeyDecisionLabel", js)
        self.assertIn('effectivePortkeyVerdict ? "Allow with policy" : "Block"', js)
        self.assertIn("Packet-consumption runway", js)
        self.assertIn("repo-portkey-revision-flow", js)
        self.assertIn("portkeyRevisionBefore", js)
        self.assertIn("portkeyStateAfter", js)
        self.assertIn("<span>Event id</span>", js)
        self.assertIn("<span>Still-blocked scope</span>", js)
        self.assertIn("<span>Policy mutation</span>", js)
        self.assertIn("Portkey consumes packet metadata from this ReviewRun", js)
        self.assertIn("No Portkey Admin API mutation, no live policy push.", js)
        self.assertIn("API mutation: ${escapeHtml(String(portkeyApiMutation))}. Policy mutation: ${escapeHtml(String(portkeyPolicyMutation))}.", js)
        self.assertEqual(
            js.count("<span>Verdict</span><strong>${escapeHtml(effectivePortkeyDecisionLabel)}</strong></div>"),
            1,
        )
        self.assertNotIn("<span>Verdict</span><strong>${escapeHtml(String(effectivePortkeyVerdict))}</strong></div>", js)
        self.assertIn("Portkey guardrail test recorded locally. No approval, no writes.", js)
        self.assertIn("Portkey received packet metadata only. IA did not approve, write, mutate policy, or call a Portkey Admin API.", js)
        self.assertIn("fetchRepoSponsorTrace", js)
        self.assertIn('fetch("/api/walkthrough")', js)
        self.assertIn("EMPTY_PROOF_TILES", js)
        self.assertIn('["1 · Attach repo", "Use demo-support-incidents."]', js)
        self.assertIn('["2 · Run IA", "Generate the packet-backed review."]', js)
        self.assertIn('["3 · Act", "Follow the one named human action."]', js)
        self.assertIn("packetPortkeyProofLoopPath", js)
        self.assertIn("Portkey asks IA before movement", js)
        self.assertIn("Portkey receives a packet-backed verdict", js)
        self.assertIn("FIRST_RUN_PACKET_URL", js)
        self.assertIn("FIRST_RUN_HEADING", js)
        self.assertIn("renderFirstRunWelcome", js)
        self.assertIn("parsePacketCoachReply", js)
        self.assertIn("renderPacketCoachReply", js)
        self.assertIn("renderCoachFact", js)
        self.assertIn("askPacketInlineCoach", js)
        self.assertIn("packetInlineCoachPrompts", js)
        self.assertIn("askReviewRunCoach", js)
        self.assertIn("renderReviewRunCoachAnswer", js)
        self.assertIn("upsertCoachContextBubble", js)
        self.assertIn("appendCoachThreadSystemMessage", js)
        self.assertIn("navigateReviewRunScreen", js)
        self.assertIn("refreshReviewRunRail", js)
        self.assertIn("/api/sessions/", js)
        self.assertIn("repo-coach-thread-scroll", js)
        self.assertIn("renderReviewRunCoachSuggestions", js)
        self.assertIn("safeCoachSuggestions", js)
        self.assertIn("refreshReviewRunCoachSuggestions", js)
        self.assertIn("currentReviewRunCoachSuggestions", js)
        self.assertIn("button.dataset.suggestionIndex = String(index)", js)
        self.assertIn("message: routedMessage", js)
        self.assertIn("body.entities = entities", js)
        self.assertIn("body.chip_entities = entities", js)
        self.assertIn("chip?.entities || null", js)
        self.assertIn("slice(0, 3)", js)
        self.assertIn("/coach/stream", js)
        self.assertIn("/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/coach", js)
        self.assertIn('window.open(data.redirect_url, "ia_oauth", "width=520,height=720")', js)
        self.assertNotIn("width=520,height=720,noopener", js)
        self.assertIn("handleConnectorOAuthReturn", js)
        self.assertIn('localStorage.getItem("ia_connector_oauth_result")', js)
        self.assertIn('params.get("connector_oauth")', js)
        self.assertIn('params.get("session_id")', js)
        self.assertIn("payload.session_id && payload.session_id !== sessionId", js)
        self.assertIn('if (connectorId === "github")', js)
        self.assertIn('await loadReviewRepoList("");', js)
        self.assertIn('document.body.dataset.activeTab = "start"', js)
        self.assertIn("document.body.dataset.activeTab = id", js)
        self.assertIn("Packet-backed answer rendered. Decision lock unchanged.", js)
        self.assertIn("packet-coach-bubble", js)
        self.assertIn("Packet-backed decision coach", js)
        self.assertIn("Read-only", js)
        self.assertIn("No approval", js)
        self.assertIn("No write", js)
        self.assertIn("reply-section-heading", js)
        self.assertIn("Sponsors collect proof only", js)
        self.assertIn("Live keys", js)
        self.assertIn("trace ${escapeHtml(trace.trace_id", js)
        self.assertIn("packet ${escapeHtml(trace.packet_id", js)
        self.assertIn("renderReplyLines", js)
        self.assertIn("lockPacketCoach", js)
        self.assertIn("unlockPacketCoach", js)
        self.assertNotIn("Welcome. Compare AI inference costs", js)
        self.assertNotIn("btn-start-portkey-preview", html)
        self.assertNotIn("btnStartPortkeyPreview", js)
        self.assertIn('data-ask-prompt="What now?"', html)
        self.assertIn('data-ask-prompt="What proof is missing?"', html)
        self.assertIn('data-ask-prompt="What will Portkey do?"', html)
        self.assertIn("clearEmptyProofBoard", js)
        self.assertIn("currentPacketFixtureForChat", js)
        self.assertIn("current_fixture: currentPacketFixtureForChat()", js)
        self.assertIn('id="packet-coach-quick-chips"', html)
        self.assertIn('id="packet-coach-status"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('class="repo-coach-composer"', html)
        self.assertIn('aria-label="Ask IA"', html)
        self.assertIn("packetCoachQuickChips", js)
        self.assertIn("packetCoachStatus", js)
        self.assertIn('packetCoachQuickChips.setAttribute("aria-busy", String(loading))', js)
        self.assertIn('packetCoachQuickChips.dataset.busy = String(loading)', js)
        self.assertIn("button.disabled = loading", js)
        self.assertIn('button.setAttribute("aria-disabled", String(loading))', js)
        self.assertIn("Answering... packet-backed quick prompts are paused.", js)
        self.assertIn(".composer-shell.first-run-locked .composer-toolbar", css)
        self.assertIn(".composer-shell.first-run-locked .composer", css)
        self.assertIn('body[data-active-tab="start"] .stack', css)
        self.assertIn('body[data-active-tab="start"] #btn-reset', css)
        self.assertIn("display: none;", css)
        self.assertIn(".packet-coach-quick-chips", css)
        self.assertIn(".packet-coach-status", css)
        self.assertIn('.packet-coach-quick-chips[data-busy="true"] button', css)
        self.assertIn(".packet-coach-label", css)
        self.assertIn(".packet-coach-bubble", css)
        self.assertIn(".packet-coach-answer", css)
        self.assertIn(".coach-current-read", css)
        self.assertIn(".coach-inspect-link", css)
        self.assertIn(".coach-safety-anchor", css)
        self.assertIn(".coach-source-details", css)
        self.assertIn(".packet-inline-coach", css)
        self.assertIn(".packet-inline-coach-prompts", css)
        self.assertIn(".packet-inline-coach-output", css)
        self.assertIn('body[data-active-tab="packet"] .layout', css)
        self.assertIn('body[data-active-tab="packet"] .walkthrough-workspace', css)
        self.assertIn(".reply-section-heading", css)
        self.assertIn(".reply-list", css)
        self.assertIn(".after-review-details", css)
        self.assertIn(".first-run-actions", css)
        self.assertIn(".first-run-cta", css)
        self.assertIn(".first-run-start-link", css)
        self.assertIn(".repo-proof-cockpit", css)
        self.assertIn(".repo-runway-panel", css)
        self.assertIn(".repo-stage-status", css)
        self.assertIn(".repo-stage-screen[hidden]", css)
        self.assertIn('data-active-screen="packet_decision"', css)
        self.assertIn('data-active-screen="portkey_gate"', css)
        self.assertIn(".repo-option-stack", css)
        self.assertIn(".repo-option-row", css)
        self.assertIn(".repo-infra-rows", css)
        self.assertIn(".repo-infra-row", css)
        self.assertIn(".repo-infra-row:not([open]) .repo-accordion-body", css)
        self.assertIn(".repo-portkey-handoff", css)
        self.assertIn(".repo-portkey-runway", css)
        self.assertIn(".repo-portkey-stage-title", css)
        self.assertIn(".repo-portkey-revision-flow", css)
        self.assertIn(".repo-portkey-outcomes", css)
        self.assertIn(".repo-portkey-test-action", css)
        self.assertIn(".repo-ask-coach", css)
        self.assertIn(".repo-coach-state-grid", css)
        self.assertIn(".repo-coach-invariant", css)
        self.assertIn(".repo-ask-coach .packet-coach-quick-chips", css)
        self.assertIn(".repo-ask-coach .packet-coach-status", css)
        self.assertIn(".repo-coach-toggle", css)
        self.assertIn(".repo-coach-stage-line", css)
        self.assertIn(".repo-ask-floating", css)
        self.assertIn("position: fixed !important;", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) !important;", css)
        self.assertIn('.repo-ask-floating[data-coach-collapsed="true"]', css)
        self.assertIn(".repo-coach-thread-scroll", css)
        self.assertIn(".repo-coach-thread", css)
        self.assertIn("consumeCoachStream", js)
        self.assertIn("autoReassessReviewRunCoach", js)
        self.assertIn("renderCoachChips", js)
        self.assertIn("/coach/stream", js)
        self.assertIn("chip_entities", js)
        self.assertIn(".coach-thread-system", css)
        self.assertIn(".repo-coach-composer", css)
        self.assertIn("min-height: 20rem;", css)
        self.assertIn(".repo-coach-assistant-head", css)
        self.assertIn('data-prompt-kind="approval_override"', css)
        self.assertIn('data-user-turn="true"', css)
        self.assertIn('data-suggestion-mode="contract"', css)
        self.assertIn(".repo-coach-answer", css)
        self.assertIn(".repo-coach-answer-row", css)
        self.assertIn("PR 137: recording-ready visual polish", css)
        self.assertIn("calc(100vh - 9rem)", css)
        self.assertIn(".repo-review-delta-item", css)
        self.assertIn(".repo-secondary-link-row", css)
        self.assertIn(".repo-movement-grid", css)
        self.assertIn(".repo-movement-lane.allowed", css)
        self.assertIn(".repo-movement-lane.review", css)
        self.assertIn(".repo-movement-lane.blocked", css)
        self.assertNotIn(".review-lane-grid", css)
        self.assertNotIn(".review-lane-card", css)
        self.assertIn(".repo-connect-panel", css)
        self.assertIn(".repo-connect-actions", css)
        self.assertIn(".repo-inline-picker", css)
        self.assertIn(".repo-inline-item", css)
        self.assertIn(".repo-index-summary", css)
        self.assertIn(".repo-primary-action:disabled", css)
        self.assertIn(".repo-review-request", css)
        self.assertIn(".repo-proof-result[hidden]", css)
        self.assertIn(".repo-proof-resolution-card", css)
        self.assertIn(".repo-proof-checklist", css)
        self.assertIn(".repo-proof-lens", css)
        self.assertIn(".repo-proof-lens-head", css)
        self.assertIn(".repo-proof-receipt", css)
        self.assertIn(".repo-proof-receipt-head", css)
        self.assertIn(".repo-proof-receipt-meta", css)
        self.assertIn(".repo-proof-receipt-safety", css)
        self.assertIn(".repo-proof-check.attached", css)
        self.assertIn(".repo-proof-attach-action", css)
        self.assertIn(".repo-proof-attach-status", css)
        self.assertIn(".repo-review-delta", css)
        self.assertIn(".repo-proof-accordion", css)
        self.assertIn(".repo-accordion-body", css)
        self.assertIn(".repo-verdict-card.review", css)
        self.assertIn("One-run minimal ReviewRun cockpit", css)
        self.assertIn("--gloss-panel", css)
        self.assertIn("body:not([data-active-tab]) .permission-pill", css)
        self.assertIn("body:not([data-active-tab]) .btn-primary", css)
        self.assertIn("#050506", css)
        self.assertIn(".repo-outcome.blocked", css)
        self.assertIn(".permission-pill.allowed", css)
        self.assertIn(".permission-pill.blocked", css)
        self.assertIn(".advanced-nav", css)
        self.assertIn(".advanced-tab-list", css)
        self.assertIn('const advancedNav = tab.closest(".advanced-nav");', js)
        self.assertIn("advancedNav.open = true", js)
        self.assertIn('["LLM", `${health.llm_provider} · ${health.llm_model}`', js)
        self.assertIn(".empty-proof-board", css)
        self.assertIn("grid-template-columns: 1fr;", css)

    def test_oauth_callback_supports_same_tab_return(self) -> None:
        from agent.connector_oauth import oauth_close_html

        html = oauth_close_html("github", True, "Connected!", session_id="sess-return")

        self.assertIn("window.opener.postMessage", html)
        self.assertIn('localStorage.setItem("ia_connector_oauth_result"', html)
        self.assertIn('window.location.replace("/?" + qs.toString())', html)
        self.assertIn('connector_oauth: "github"', html)
        self.assertIn('session_id:"sess-return"', html)
        self.assertIn('qs.set("session_id", "sess-return")', html)

    def test_chat_api_surfaces_structured_chat_answer_v0(self) -> None:
        from web.app import ChatRequest, _execute_chat

        with patch("web.app._chat_validate", return_value=None):
            response = _execute_chat(
                ChatRequest(
                    session_id="chat-answer-contract",
                    message=(
                        "Our AI budget was blown in Q1. What should Finance and "
                        "Procurement review?"
                    ),
                )
            )

        self.assertIn("Context used", response.reply)
        self.assertEqual(response.answer["schema_version"], "chat_answer.v0")
        self.assertEqual(response.answer["answer_kind"], "ai_spend_review")
        self.assertFalse(response.answer["safety"]["approves_spend"])
        self.assertFalse(response.answer["safety"]["selects_provider"])
        self.assertFalse(response.answer["safety"]["guarantees_savings"])
        self.assertIn("Finance and Procurement review packet", response.reply)

    def test_chat_api_uses_packet_advisor_from_current_fixture(self) -> None:
        from web.app import ChatRequest, _execute_chat

        with patch("web.app._chat_validate", side_effect=AssertionError("Packet Advisor must stay no-key")):
            response = _execute_chat(
                ChatRequest(
                    session_id="packet-advisor-chat-contract",
                    current_fixture="ai_spend_budget_overrun",
                    message="Can Portkey allow this spend?",
                )
            )

        self.assertIn("Context used", response.reply)
        self.assertEqual(response.answer["schema_version"], "packet_advisor_answer.v0")
        self.assertEqual(response.answer["answer_kind"], "decision")
        self.assertEqual(response.answer["subscriber"], "portkey_model_spend_gate")
        self.assertEqual(
            response.answer["packet_reference"]["packet_id"],
            "ia-spend-review-ai_spend_budget_overrun-v0",
        )
        self.assertFalse(response.answer["downstream_gate"]["requested_action_can_proceed"])
        self.assertIn("Portkey cannot allow this request", response.reply)
        self.assertIn("Top blocker", response.reply)
        self.assertIn("Preview Portkey gate", response.reply)
        self.assertIn("Packet-backed", response.reply)
        self.assertEqual(
            response.answer["chat_salience"]["destination_surface"],
            "portkey_adapter_preview",
        )
        self.assertFalse(
            response.answer["chat_salience"]["portkey_adapter_preview"]["portkey_guardrail_response"]["verdict"]
        )
        self.assertIn("does not approve", response.reply.lower())

    def test_chat_api_greeting_uses_intake_not_packet_dump(self) -> None:
        from web.app import ChatRequest, _execute_chat

        with patch("web.app._chat_validate", side_effect=AssertionError("Greeting must stay no-key")):
            response = _execute_chat(
                ChatRequest(
                    session_id="ask-ia-greeting-contract",
                    current_fixture="mcp_tool_blast_radius",
                    message="hey",
                )
            )

        self.assertIn("Context used", response.reply)
        self.assertIn("Ask IA intake", response.reply)
        self.assertEqual(response.answer["schema_version"], "ask_ia_intake.v0")
        self.assertFalse(response.answer["invariants"]["raw_packet_dumped"])
        self.assertFalse(response.answer["invariants"]["uses_packet_advisor"])
        self.assertFalse(response.use_tools)
        self.assertIn("Can this move?", response.reply)
        self.assertIn("What proof is missing?", response.reply)
        self.assertNotIn("Top blocker", response.reply)
        self.assertNotIn("packet_id", response.reply)

    def test_design_partner_walkthrough_api_is_safe_and_export_ready(self) -> None:
        from web.app import design_partner_walkthrough

        data = design_partner_walkthrough()

        self.assertTrue(data["ok"])
        self.assertEqual(data["title"], "Design partner walkthrough")
        self.assertEqual(len(data["steps"]), 6)
        self.assertEqual(
            [step["id"] for step in data["steps"]],
            ["request", "packet", "sponsor_proof_trace", "sponsor_replay", "review_cycle", "pilot_memo"],
        )
        self.assertEqual(data["steps"][-1]["id"], "pilot_memo")
        self.assertEqual(data["steps"][2]["title"], "Collect sponsor proof")
        self.assertEqual(
            data["sponsor_proof_trace"]["blast_radius"]["summary"]["blocked_action_count"],
            9,
        )
        self.assertEqual(
            data["sponsor_proof_trace"]["blast_radius"]["summary"]["max_risk_level"],
            "critical",
        )
        self.assertFalse(data["sponsor_proof_trace"]["blast_radius"]["summary"]["would_execute"])
        self.assertIn("support_triage_trial.packet.json", data["packet_reference"]["packet_artifact"])
        self.assertTrue(data["packet_reference"]["content_hash"].startswith("sha256:"))
        self.assertEqual(data["decision"]["verdict_class"], "scoped_validation_only")
        self.assertFalse(data["decision"]["production_access"])
        self.assertFalse(data["decision"]["permission_grants"])
        self.assertFalse(data["decision"]["external_writes"])
        self.assertFalse(data["decision"]["sponsors_can_change_decision"])
        self.assertEqual(data["safety_anchor"], "IA did not approve. The next human action is named above.")
        self.assertIn("Copy Review Brief", data["copy_review_brief"])
        self.assertEqual(
            data["packet_authority"]["headline"],
            "The packet authority layer downstream systems trust before AI moves.",
        )
        self.assertEqual(
            data["packet_authority"]["verification_endpoint"],
            "/api/packets/ia-agent-access-support-triage-v0/verification",
        )
        self.assertTrue(data["packet_authority"]["read_only"])
        self.assertEqual(data["packet_authority"]["subscriber_count"], 6)
        self.assertEqual(
            set(data["packet_authority"]["categories"]),
            {"gateway", "ci", "spend", "review", "observability"},
        )
        self.assertEqual(len(data["subscriber_rows"]), 6)
        self.assertEqual(
            {item["category"] for item in data["subscriber_rows"]},
            {"gateway", "ci", "spend", "review", "observability"},
        )
        for item in data["subscriber_rows"]:
            self.assertFalse(item["can_approve_access"])
            self.assertFalse(item["can_grant_permissions"])
            self.assertFalse(item["can_mutate_packet"])
            self.assertFalse(item["can_override_verdict"])
            self.assertFalse(item["executes_external_writes"])
            self.assertTrue(item["requires_human_review"])
        self.assertEqual(len(data["sponsor_roles"]), 4)
        self.assertEqual({item["verb"] for item in data["sponsor_roles"]}, {"finds", "simulates", "narrates", "traces"})
        self.assertTrue(all(not item["can_change_decision"] for item in data["sponsor_roles"]))
        trace = data["sponsor_proof_trace"]
        self.assertEqual(trace["sponsor_order"], ["tavily", "composio", "openclaw", "nebius"])
        self.assertEqual(trace["step_count"], 4)
        self.assertTrue(trace["decision_lock_unchanged"])
        self.assertTrue(trace["access_evidence_present"])
        self.assertTrue(trace["spend_evidence_present"])
        self.assertTrue(trace["all_fallback_used"])
        self.assertTrue(trace["all_non_executing"])
        self.assertTrue(trace["all_non_approving"])
        self.assertTrue(trace["all_non_granting"])
        self.assertTrue(trace["all_non_mutating"])
        self.assertFalse(trace["approves_access"])
        self.assertFalse(trace["approves_spend"])
        self.assertFalse(trace["selects_provider"])
        self.assertFalse(trace["guarantees_savings"])
        self.assertIn("support_triage_trial.sponsor_proof_trace.md", trace["artifact"])
        self.assertGreaterEqual(len(data["output_files"]), 8)
        self.assertTrue(any(item["file_id"] for item in data["output_files"]))

    def test_design_partner_walkthrough_ui_is_reachable(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")

        self.assertIn("<title>InferenceAtlas — Packet Authority Review</title>", html)
        self.assertIn("Packet authority for AI access and spend review", html)
        self.assertIn('data-tab="start">ReviewRun</button>', html)
        self.assertIn("<summary>Advanced</summary>", html)
        primary_nav = html.split('<details class="advanced-nav">', 1)[0]
        self.assertNotIn('data-tab="packet"', primary_nav)
        self.assertNotIn('data-tab="walkthrough"', primary_nav)
        self.assertNotIn('data-tab="workbench"', primary_nav)
        advanced_nav = html.split('<details class="advanced-nav">', 1)[1].split("</details>", 1)[0]
        self.assertIn('data-tab="packet">IA Packet</button>', advanced_nav)
        self.assertIn('data-tab="walkthrough">Sponsor Run</button>', advanced_nav)
        self.assertIn('data-tab="workbench">Workbench</button>', html)
        self.assertIn('data-tab="walkthrough"', html)
        self.assertIn("Sponsor Run", html)
        self.assertIn('id="walkthrough-view"', html)
        self.assertIn("Private engine, public proof.", html)
        self.assertRegex(html, r"/static/app\.js\?v=\d+")
        self.assertIn('id="btn-collect-sponsor-proof"', html)
        self.assertIn("Collect sponsor proof", html)
        self.assertIn('id="btn-copy-walkthrough-brief"', html)
        self.assertIn('id="walkthrough-subscriber-card"', html)
        self.assertIn("/api/walkthrough", js)
        self.assertIn("renderWalkthrough", js)
        self.assertIn("renderSubscriberCard", js)
        self.assertIn("renderSponsorCard", js)
        self.assertIn("selectWalkthroughStepById", js)
        self.assertIn("collectSponsorProof", js)
        self.assertIn("/api/sponsor-proof-runs", js)
        self.assertIn('traceAction.addEventListener("click", () => collectSponsorProof());', js)
        self.assertIn('traceAction.setAttribute("aria-label", "Collect non-mutating sponsor proof run");', js)
        self.assertIn("composio_dry_run: true", js)
        self.assertIn("const liveTavily = Boolean(runtimeHealth?.tavily);", js)
        self.assertIn("live_tavily: liveTavily", js)
        self.assertIn("sponsor_proof_run", js)
        self.assertIn("Latest collected run", js)
        self.assertIn("renderSponsorProofLoop", js)
        self.assertIn("renderBlastRadiusGraph", js)
        self.assertIn("IA Blast Radius Graph", js)
        self.assertIn("proofGraphUrl", js)
        self.assertIn("Open ProofGraph", js)
        self.assertIn("Shows the full packet authority map", js)
        self.assertIn("IA created this graph from sponsor proof.", js)
        self.assertIn("Sponsors provide signals. IA builds the blast-radius graph", js)
        self.assertIn("One local IA API call orchestrates sponsor proof.", js)
        self.assertIn("const tavily = run?.live_sponsor_proof?.tavily || null;", js)
        self.assertIn("Tavily live evidence", js)
        self.assertIn("source URLs", js)
        self.assertIn("const nebius = run?.live_sponsor_proof?.nebius || null;", js)
        self.assertIn("Nebius reviewer narration", js)
        self.assertIn("Nebius evidence synthesis", js)
        self.assertIn("nebius_evidence_synthesis", js)
        self.assertIn("Live source synthesis", js)
        self.assertIn("Tavily only", js)
        self.assertIn("No new URLs", js)
        self.assertIn("live_nebius: liveNebius", js)
        self.assertIn('const liveNebius = runtimeHealth?.llm_provider === "nebius";', js)
        self.assertIn("const composioSummary = composio?.permission_diff_summary || {};", js)
        self.assertIn("Composio permission diffs generated", js)
        self.assertIn("write actions remain blocked", js)
        self.assertIn("Decision lock unchanged.", js)
        self.assertIn("Downstream consumers", js)
        self.assertIn("Systems trust the packet", js)
        self.assertIn("copyWalkthroughBrief", js)
        self.assertIn("Clipboard unavailable. Use PilotMemo export.", js)
        self.assertIn('copied = document.execCommand("copy")', js)
        self.assertIn('window.location.pathname === "/walkthrough"', js)
        self.assertIn(".walkthrough-workspace", css)
        self.assertIn(".walkthrough-proof", css)
        self.assertIn(".sponsor-run-card", css)
        self.assertIn(".sponsor-proof-loop", css)
        self.assertIn(".sponsor-proof-step", css)
        self.assertIn(".sponsor-source-panel", css)
        self.assertIn(".sponsor-source-links", css)
        self.assertIn(".trace-metrics.compact", css)
        self.assertIn(".walkthrough-strip", css)
        self.assertIn(".subscriber-grid", css)
        self.assertIn(".subscriber-row", css)
        self.assertIn(".trace-metrics", css)
        self.assertIn(".trace-step-row", css)

    def test_uploaded_evidence_rehearsal_accepts_sanitized_bundle(self) -> None:
        from web.app import CustomEvidenceRehearsalRequest, run_custom_evidence_rehearsal

        fixture_dir = ROOT / "examples" / "evidence" / "support_triage_trial"
        bundle = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(fixture_dir.glob("*.json"))
        }
        file_id, _name, _preview = save_upload(
            scope="review_uploaded_safe",
            filename="provider_bundle.json",
            data=json.dumps(bundle).encode("utf-8"),
        )

        data = run_custom_evidence_rehearsal(
            CustomEvidenceRehearsalRequest(
                storage_scope="review_uploaded_safe",
                attachment_ids=[file_id],
            )
        )

        self.assertTrue(data["ok"])
        self.assertEqual(data["title"], "Uploaded sponsor evidence rehearsal")
        self.assertEqual(data["live_evidence_rehearsal"]["sanitized_provider_count"], 4)
        self.assertEqual(len(data["accepted_files"]), 4)
        self.assertTrue(all(provider["evidence_attached"] for provider in data["providers"]))
        self.assertFalse(data["decision_lock"]["production_access"])
        self.assertFalse(data["decision_lock"]["can_sponsor_change_decision"])
        self.assertTrue(any(item["file_id"] for item in data["output_files"]))

    def test_uploaded_evidence_rehearsal_rejects_unsafe_claims(self) -> None:
        from fastapi import HTTPException

        from web.app import CustomEvidenceRehearsalRequest, run_custom_evidence_rehearsal

        file_id, _name, _preview = save_upload(
            scope="review_uploaded_unsafe",
            filename="tavily.json",
            data=json.dumps(
                {
                    "provider": "tavily",
                    "api_key": "do-not-accept",
                    "evidence_candidates": [],
                }
            ).encode("utf-8"),
        )

        with self.assertRaises(HTTPException) as context:
            run_custom_evidence_rehearsal(
                CustomEvidenceRehearsalRequest(
                    storage_scope="review_uploaded_unsafe",
                    attachment_ids=[file_id],
                )
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("sensitive key", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
