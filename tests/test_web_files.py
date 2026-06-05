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
        self.assertIn("Production false", html)
        self.assertIn("Composio dry-run", html)
        self.assertIn("no savings guarantee", html)
        self.assertIn('rel="icon"', html)
        self.assertRegex(html, r'/static/style\.css\?v=\d+')
        self.assertRegex(html, r'/static/app\.js\?v=\d+')
        self.assertIn("EMPTY_PROOF_TILES", js)
        self.assertIn("clearEmptyProofBoard", js)
        self.assertIn('["LLM", `${health.llm_provider} · ${health.llm_model}`', js)
        self.assertIn(".empty-proof-board", css)
        self.assertIn("grid-template-columns: repeat(4", css)

    def test_design_partner_walkthrough_api_is_safe_and_export_ready(self) -> None:
        from web.app import design_partner_walkthrough

        data = design_partner_walkthrough()

        self.assertTrue(data["ok"])
        self.assertEqual(data["title"], "Design partner walkthrough")
        self.assertEqual(len(data["steps"]), 5)
        self.assertEqual(data["steps"][-1]["id"], "pilot_memo")
        self.assertIn("support_triage_trial.packet.json", data["packet_reference"]["packet_artifact"])
        self.assertTrue(data["packet_reference"]["content_hash"].startswith("sha256:"))
        self.assertEqual(data["decision"]["verdict_class"], "scoped_validation_only")
        self.assertFalse(data["decision"]["production_access"])
        self.assertFalse(data["decision"]["permission_grants"])
        self.assertFalse(data["decision"]["external_writes"])
        self.assertFalse(data["decision"]["sponsors_can_change_decision"])
        self.assertEqual(data["safety_anchor"], "IA did not approve. The next human action is named above.")
        self.assertIn("Copy Review Brief", data["copy_review_brief"])
        self.assertEqual(len(data["sponsor_roles"]), 4)
        self.assertEqual({item["verb"] for item in data["sponsor_roles"]}, {"finds", "simulates", "narrates", "traces"})
        self.assertTrue(all(not item["can_change_decision"] for item in data["sponsor_roles"]))
        self.assertGreaterEqual(len(data["output_files"]), 6)
        self.assertTrue(any(item["file_id"] for item in data["output_files"]))

    def test_design_partner_walkthrough_ui_is_reachable(self) -> None:
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")

        self.assertIn('data-tab="walkthrough"', html)
        self.assertIn('id="walkthrough-view"', html)
        self.assertIn('id="btn-copy-walkthrough-brief"', html)
        self.assertIn("/api/walkthrough", js)
        self.assertIn("renderWalkthrough", js)
        self.assertIn("copyWalkthroughBrief", js)
        self.assertIn("Clipboard unavailable. Use PilotMemo export.", js)
        self.assertIn('copied = document.execCommand("copy")', js)
        self.assertIn('window.location.pathname === "/walkthrough"', js)
        self.assertIn(".walkthrough-workspace", css)
        self.assertIn(".walkthrough-strip", css)

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
