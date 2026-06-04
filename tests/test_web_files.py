"""Web file registry and mind API smoke tests."""

import json
import unittest
from pathlib import Path

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
