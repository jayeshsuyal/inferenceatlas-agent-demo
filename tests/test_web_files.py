"""Web file registry and mind API smoke tests."""

import json
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
        self.assertIn("InferenceAtlas runway", html)
        self.assertIn("What should IA review?", html)
        self.assertIn("Generate the proof packet downstream systems trust before an AI agent moves.", html)
        self.assertIn("Review cockpit", html)
        self.assertIn("Current review step", html)
        self.assertIn("Current step", html)
        self.assertIn("Connect GitHub", html)
        self.assertIn("Use demo repo", html)
        self.assertIn("IA indexes only the repo you select.", html)
        self.assertIn('id="repo-inline-list"', html)
        self.assertIn("Choose one GitHub repository", html)
        self.assertIn("Repo connected", html)
        self.assertIn("Indexed", html)
        self.assertIn("ReviewRun", html)
        self.assertIn("Connect and index one repo before generating a packet.", html)
        self.assertIn("Ask IA Coach", html)
        self.assertIn("Current read", html)
        self.assertIn("Truth source", html)
        self.assertIn("Raw agent intent is not trusted. Proof changes packet state.", html)
        self.assertIn("Review AI spend", html)
        self.assertIn("Review tool access", html)
        self.assertIn("support-triage-bot wants repo access", html)
        self.assertIn("support-triage-bot", html)
        self.assertIn("Choose a GitHub repo first.", html)
        self.assertIn("Review access", html)
        self.assertIn("Next human action", html)
        self.assertIn("ProofGraph", html)
        self.assertIn("Packet authority map", html)
        self.assertIn("Gate preview", html)
        self.assertIn("Advanced", html)
        self.assertIn("Packet and tools", html)
        self.assertIn("Raw packet and workbench surfaces stay behind this advanced drawer.", html)
        self.assertIn("Open ProofGraph", html)
        self.assertIn("Copy review brief", html)
        self.assertIn("Inspect packet", html)
        self.assertIn('id="repo-proof-resolution-card"', html)
        self.assertIn("Attach proof before rerun.", html)
        self.assertIn(
            "Checking proof does not approve access. It marks human evidence as attached and requires a packet rerun.",
            html,
        )
        self.assertIn('class="repo-proof-checklist"', html)
        self.assertIn("Attach checked proof", html)
        self.assertIn('class="repo-review-delta"', html)
        self.assertIn("No proof attached. Verdict unchanged.", html)
        self.assertIn("<summary>More examples</summary>", html)
        self.assertIn(
            "Downstream systems do not trust raw agent intent. They trust the IA Packet.",
            html,
        )
        self.assertIn("<strong>Attach repo:</strong> use the demo GitHub access request.", html)
        self.assertIn("<strong>Run IA:</strong> generate the packet-backed review.", html)
        self.assertIn("<strong>Act:</strong> follow the one named human action.", html)
        self.assertIn('class="composer-shell first-run-locked"', html)
        self.assertIn("Ask IA about this packet", html)
        self.assertIn("Ask IA packet coach", html)
        self.assertIn("Packet-backed decision coach", html)
        self.assertIn("Load an IA Packet, then ask a packet-backed follow-up. IA stays read-only.", html)
        self.assertIn("Run the repo access review first; Ask IA answers from the packet, not raw agent intent.", html)
        self.assertIn("Can it move?", html)
        self.assertIn("Missing proof", html)
        self.assertIn("Review route", html)
        self.assertNotIn("Should this AI agent get repo access?", html)
        self.assertNotIn("Run proof check", html)
        self.assertNotIn("Run IA Packet Review", html)
        self.assertNotIn("Open one registered AI movement request. IA shows the packet", html)
        self.assertNotIn('class="review-lane-grid"', html)
        self.assertNotIn('class="review-lane-card', html)
        self.assertIn('rel="icon"', html)
        self.assertRegex(html, r'/static/style\.css\?v=\d+')
        self.assertRegex(html, r'/static/app\.js\?v=\d+')
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
        self.assertIn("packet generated from the selected ReviewRun", js)
        self.assertIn("proof steps mapped", js)
        self.assertIn("DEFAULT_REVIEW_ACCESS_REQUEST", js)
        self.assertIn("DEFAULT_REVIEW_PROOF_ITEMS", js)
        self.assertIn("support-triage-bot needs to read issues, comment, and create labels.", js)
        self.assertIn('/api/review-runs/${encodeURIComponent(runId)}/packet', js)
        self.assertIn('/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/proof', js)
        self.assertIn('/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/rerun', js)
        self.assertIn("movementLane", js)
        self.assertIn("renderRepoProofResolution", js)
        self.assertIn("attachReviewRunProof", js)
        self.assertIn("rerunReviewRunPacket", js)
        self.assertIn("reviewDeltaRows", js)
        self.assertIn("ready_for_rerun", js)
        self.assertIn("Packet regenerated", js)
        self.assertIn("Portkey can allow with policy", js)
        self.assertIn("Proof attached. Verdict and Portkey state unchanged", js)
        self.assertIn("repo-movement-grid", js)
        self.assertIn("Review required", js)
        self.assertIn("source_of_truth", js)
        self.assertIn("runRepoProofCockpit", js)
        self.assertIn("renderRepoProofCockpit", js)
        self.assertIn("fetchPortkeyProofForFixture", js)
        self.assertIn("fetchRepoSponsorTrace", js)
        self.assertIn('fetch("/api/walkthrough")', js)
        self.assertIn("Copy review brief", html)
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
        self.assertIn('data-ask-prompt="Can Portkey allow this spend?"', html)
        self.assertIn("clearEmptyProofBoard", js)
        self.assertIn("currentPacketFixtureForChat", js)
        self.assertIn("current_fixture: currentPacketFixtureForChat()", js)
        self.assertIn('id="packet-coach-quick-chips"', html)
        self.assertIn('id="packet-coach-status"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("Preview Portkey gate", html)
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
        self.assertIn(".review-cockpit-shell", css)
        self.assertIn(".repo-current-step", css)
        self.assertIn(".repo-ask-coach", css)
        self.assertIn(".repo-coach-state-grid", css)
        self.assertIn(".repo-coach-invariant", css)
        self.assertIn(".repo-ask-coach .packet-coach-quick-chips", css)
        self.assertIn(".repo-ask-coach .packet-coach-status", css)
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
        self.assertIn(".repo-proof-check.attached", css)
        self.assertIn(".repo-proof-attach-action", css)
        self.assertIn(".repo-proof-attach-status", css)
        self.assertIn(".repo-review-delta", css)
        self.assertIn(".repo-proof-grid", css)
        self.assertIn(".repo-proof-accordion", css)
        self.assertIn(".repo-accordion-body", css)
        self.assertIn(".repo-verdict-card.review", css)
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
        self.assertIn('data-tab="start">Start Here</button>', html)
        self.assertIn("<summary>Advanced</summary>", html)
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
