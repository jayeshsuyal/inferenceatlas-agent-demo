"""ReviewRun flow context and session queue helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.review_context import list_review_runs_for_session, record_flow_event


class ReviewRunFlowTests(unittest.TestCase):
    def test_list_review_runs_for_session_returns_newest_first(self) -> None:
        session_id = "reviewer-smoke-session-flow"
        payload = {
            "session_id": session_id,
            "review_contexts": {
                "ia-review-run-aaa": {
                    "run_id": "ia-review-run-aaa",
                    "repo_full_name": "org/repo-a",
                    "stage": "packet_generated",
                    "updated_at": "2026-06-11T12:00:00Z",
                },
                "ia-review-run-bbb": {
                    "run_id": "ia-review-run-bbb",
                    "repo_full_name": "org/repo-b",
                    "stage": "repo_selected",
                    "updated_at": "2026-06-11T11:00:00Z",
                },
            },
        }
        with patch("agent.review_context.load_session", return_value=payload):
            runs = list_review_runs_for_session(session_id)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["run_id"], "ia-review-run-aaa")
        self.assertEqual(runs[1]["run_id"], "ia-review-run-bbb")
        self.assertIn("summary", runs[0])
        self.assertIn("tools_used", runs[0])
        self.assertIn("context_used", runs[0])

    def test_record_flow_event_appends_context(self) -> None:
        session_id = "reviewer-smoke-session-flow-2"
        store: dict = {"session_id": session_id, "review_contexts": {}}

        def fake_load(sid: str) -> dict:
            return store if sid == session_id else {"session_id": sid, "review_contexts": {}}

        def fake_save(sid: str, data: dict) -> None:
            if sid == session_id:
                store["review_contexts"] = data.get("review_contexts", {})
                store["updated_at"] = data.get("updated_at", "")

        with patch("agent.review_context.load_session", side_effect=fake_load):
            with patch("agent.review_context.save_session", side_effect=fake_save):
                record_flow_event(
                    session_id,
                    "ia-review-run-ccc",
                    stage="repo_indexed",
                    previous_stage="repo_selected",
                    trigger="repo_indexed",
                    summary="Indexed demo repo",
                    repo_full_name="org/demo",
                )
        ctx = store["review_contexts"]["ia-review-run-ccc"]
        self.assertEqual(ctx["stage"], "repo_indexed")
        self.assertEqual(ctx["repo_full_name"], "org/demo")
        self.assertEqual(len(ctx["flow_events"]), 1)


if __name__ == "__main__":
    unittest.main()
