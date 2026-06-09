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

        self.assertIn('id="empty-proof-board"', html)
        self.assertIn("Run IA Packet Review", html)
        self.assertIn("<summary>More examples</summary>", html)
        self.assertIn(
            "Downstream systems do not trust raw agent intent. They trust the IA Packet.",
            html,
        )
        self.assertIn(
            "Open one registered AI movement request. IA shows the packet, proof trace, team lenses, and exportable gate without keys or writes.",
            html,
        )
        self.assertIn("<strong>Request:</strong> load one registered AI movement request.", html)
        self.assertIn("<strong>Packet:</strong> review the verdict, proof debt, owners, and hash.", html)
        self.assertIn("<strong>Export:</strong> copy the review brief or Portkey dry-run gate.", html)
        self.assertIn('class="composer-shell first-run-locked"', html)
        self.assertIn("Open one registered AI movement request.", html)
        self.assertIn("Inspect verdict, proof debt, owners, and hash.", html)
        self.assertIn("Copy the review brief or export Portkey gate JSON.", html)
        self.assertIn("Ask IA about this packet", html)
        self.assertIn("Ask IA packet coach", html)
        self.assertIn("Packet-backed decision coach", html)
        self.assertIn("Load an IA Packet, then ask a packet-backed follow-up. IA stays read-only.", html)
        self.assertIn("Open the IA Packet first; Ask IA answers from the packet, not raw agent intent.", html)
        self.assertIn("Can it move?", html)
        self.assertIn("Missing proof", html)
        self.assertIn("Review route", html)
        self.assertIn('rel="icon"', html)
        self.assertRegex(html, r'/static/style\.css\?v=\d+')
        self.assertRegex(html, r'/static/app\.js\?v=\d+')
        self.assertIn("EMPTY_PROOF_TILES", js)
        self.assertIn('["1 · Request", "Open one registered AI movement request."]', js)
        self.assertIn('["2 · Packet", "Inspect verdict, proof debt, owners, and hash."]', js)
        self.assertIn('["3 · Export", "Copy the review brief or export Portkey gate JSON."]', js)
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
        self.assertIn(".composer-shell.first-run-locked .packet-coach-quick-chips", css)
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
        self.assertIn(".advanced-nav", css)
        self.assertIn(".advanced-tab-list", css)
        self.assertIn('const advancedNav = tab.closest(".advanced-nav");', js)
        self.assertIn("advancedNav.open = true", js)
        self.assertIn('["LLM", `${health.llm_provider} · ${health.llm_model}`', js)
        self.assertIn(".empty-proof-board", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css)

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
        self.assertIn("const tavily = run.live_sponsor_proof?.tavily || null;", js)
        self.assertIn("Tavily live evidence", js)
        self.assertIn("source URLs", js)
        self.assertIn("const nebius = run.live_sponsor_proof?.nebius || null;", js)
        self.assertIn("Nebius reviewer narration", js)
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
