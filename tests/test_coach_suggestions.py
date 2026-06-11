"""ReviewRun coach suggestion contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase

from agent.coach_suggestions import (
    COACH_SUGGESTION_SCHEMA_VERSION,
    MAX_COACH_SUGGESTIONS,
    normalize_suggestion_label,
    suggestions_for_review_run,
)
from agent.review_run import (
    DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    attach_review_run_proof,
    create_review_run,
    generate_initial_review_run_packet,
    generate_proof_resolved_review_run_packet,
    select_review_run_repo,
)


ROOT = Path(__file__).resolve().parents[1]


def _selected_repo() -> dict:
    return {"provider": "github", "full_name": "inferenceatlas/support-triage-trial"}


def _indexed_summary() -> dict:
    return {"status": "indexed", "indexed_repo_count": 1, "digest_chars": 16}


class CoachSuggestionsTests(TestCase):
    def assertSuggestionShape(self, suggestion: dict, *, run_id: str, stage: str) -> None:
        self.assertEqual(suggestion["schema_version"], COACH_SUGGESTION_SCHEMA_VERSION)
        self.assertLessEqual(len(suggestion["label"]), 28)
        self.assertTrue(suggestion["message"])
        entities = suggestion["entities"]
        self.assertEqual(entities["source"], "review_run")
        self.assertEqual(entities["run_id"], run_id)
        self.assertEqual(entities["stage"], stage)
        self.assertEqual(entities["subscriber"], "cto")
        self.assertIn("prompt_kind", entities)
        self.assertNotIn("approve access", suggestion["message"].lower())
        self.assertNotIn("grant permissions", suggestion["message"].lower())

    def test_schema_documents_required_entities(self) -> None:
        schema = json.loads((ROOT / "schemas" / "coach_suggestion.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], COACH_SUGGESTION_SCHEMA_VERSION)
        required = set(schema["properties"]["entities"]["required"])
        self.assertEqual(required, {"source", "prompt_kind", "run_id", "stage", "subscriber"})
        self.assertEqual(schema["properties"]["entities"]["properties"]["subscriber"]["const"], "cto")

    def test_normalize_suggestion_label_keeps_chips_short(self) -> None:
        label = normalize_suggestion_label("A very long label that should never become a chip wall")
        self.assertLessEqual(len(label), 28)
        self.assertTrue(label.endswith("..."))

    def test_packet_generated_suggestions_are_stage_specific_and_entity_pinned(self) -> None:
        run = generate_initial_review_run_packet(
            select_review_run_repo(create_review_run(), _selected_repo(), repo_index_summary=_indexed_summary()),
            DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
        )
        suggestions = suggestions_for_review_run(run)

        self.assertLessEqual(len(suggestions), MAX_COACH_SUGGESTIONS)
        kinds = [item["entities"]["prompt_kind"] for item in suggestions]
        self.assertEqual(kinds, ["next_action", "proof", "portkey"])
        for item in suggestions:
            self.assertSuggestionShape(item, run_id=run.run_id, stage="packet_generated")
            self.assertEqual(item["entities"]["repo_full_name"], "inferenceatlas/support-triage-trial")
            self.assertEqual(item["entities"]["packet_id"], run.packet["packet_id"])
            self.assertEqual(item["entities"]["revision_id"], run.packet["revision_id"])
            self.assertEqual(
                item["entities"]["missing_proof_ids"],
                ["repo_owner_approval", "rollback_offswitch", "environment_boundary"],
            )

    def test_proof_and_export_stages_return_next_safe_actions(self) -> None:
        packet_run = generate_initial_review_run_packet(
            select_review_run_repo(create_review_run(), _selected_repo(), repo_index_summary=_indexed_summary()),
            DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
        )
        proof_run = attach_review_run_proof(
            packet_run,
            [
                {"id": "repo_owner_approval"},
                {"id": "rollback_offswitch"},
                {"id": "environment_boundary"},
            ],
        )
        proof_suggestions = suggestions_for_review_run(proof_run)
        self.assertEqual(proof_suggestions[0]["label"], "Regenerate packet")
        self.assertEqual(proof_suggestions[0]["entities"]["prompt_kind"], "next_action")

        export_run = generate_proof_resolved_review_run_packet(proof_run, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
        export_suggestions = suggestions_for_review_run(export_run)
        self.assertEqual([item["entities"]["prompt_kind"] for item in export_suggestions], ["next_action", "movement", "portkey"])
        for item in export_suggestions:
            self.assertSuggestionShape(item, run_id=export_run.run_id, stage="ready_to_export")
