"""Coach suggestion chip generation tests."""

from __future__ import annotations

from unittest import TestCase

from agent.coach_suggestions import (
    build_intake_suggestions,
    build_packet_advisor_suggestions_from_result,
    build_review_run_suggestions,
    normalize_label,
    review_run_context_from_run,
    suggestions_for_run,
)
from agent.review_run import ReviewRun, create_review_run
from agent.workbench import build_workbench_result


class CoachSuggestionsTests(TestCase):
    def test_normalize_label_truncates(self) -> None:
        long = "A" * 40
        self.assertTrue(normalize_label(long).endswith("…"))
        self.assertLessEqual(len(normalize_label(long)), 28)

    def test_packet_generated_suggestions_reference_missing_proof(self) -> None:
        ctx = review_run_context_from_run(
            ReviewRun.from_dict(
                {
                    **create_review_run(
                        selected_repo={"provider": "github", "full_name": "acme/demo"},
                        repo_index_summary={"status": "indexed"},
                    ).to_dict(),
                    "stage": "packet_generated",
                    "missing_proof": [
                        {"id": "repo_owner_approval", "label": "Repo owner approval"},
                    ],
                    "packet": {
                        "verdict": "scoped_validation_only",
                        "packet_id": "ia-packet-demo",
                        "revision_id": "rev_demo",
                    },
                }
            )
        )
        suggestions = build_review_run_suggestions(ctx)
        self.assertGreaterEqual(len(suggestions), 2)
        first = suggestions[0]
        self.assertIn("label", first)
        self.assertIn("message", first)
        self.assertIn("entities", first)
        self.assertIn("Repo owner approval", first["message"])
        self.assertEqual(first["entities"]["source"], "review_run")

    def test_proof_attached_includes_rerun_chip(self) -> None:
        run = create_review_run(
            selected_repo={"provider": "github", "full_name": "acme/demo"},
            repo_index_summary={"status": "indexed"},
        )
        data = run.to_dict()
        data["stage"] = "proof_attached"
        data["packet"] = {"verdict": "scoped_validation_only", "revision_id": "rev_1"}
        suggestions = suggestions_for_run(ReviewRun.from_dict(data))
        kinds = [item["entities"]["prompt_kind"] for item in suggestions]
        self.assertIn("rerun", kinds)

    def test_packet_advisor_mcp_fixture_has_blast_radius_chip(self) -> None:
        result = build_workbench_result("mcp_tool_blast_radius")
        suggestions = build_packet_advisor_suggestions_from_result(result)
        kinds = [item["entities"]["prompt_kind"] for item in suggestions]
        self.assertIn("blast_radius", kinds)

    def test_intake_suggestions_are_structured(self) -> None:
        suggestions = build_intake_suggestions("mcp_tool_blast_radius")
        self.assertGreaterEqual(len(suggestions), 2)
        for item in suggestions:
            self.assertLessEqual(len(item["label"]), 28)
            self.assertTrue(item["message"])
            self.assertEqual(item["entities"]["source"], "intake")
