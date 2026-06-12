"""Coach session, narration, and enrichment tests."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from agent.coach_enrichment import enrich_review_run_coach_answer
from agent.coach_session import (
    append_coach_turn,
    format_coach_session_context,
    load_coach_session,
    record_coach_checkpoint,
)
from agent.review_run import (
    DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    build_review_run_coach_answer,
    create_review_run,
    generate_initial_review_run_packet,
    select_review_run_repo,
)


def _selected_repo() -> dict:
    return {
        "provider": "github",
        "full_name": "acme/demo-support-incidents",
        "source": "demo",
    }


def _indexed_summary() -> dict:
    return {"status": "indexed", "files_indexed": 12}


class CoachEnrichmentTests(TestCase):
    def test_coach_session_records_checkpoints_and_turns(self) -> None:
        with TemporaryDirectory() as tmp:
            store = __import__("pathlib").Path(tmp)
            run_id = "ia-review-run-coach-test"
            record_coach_checkpoint(
                run_id,
                stage="packet_generated",
                revision_id="rev_abc",
                verdict="scoped_validation_only",
                portkey_state="Block",
                trigger="packet_generated",
                summary="Packet generated; proof missing.",
                store_dir=store,
            )
            append_coach_turn(
                run_id,
                prompt="What proof is missing?",
                prompt_kind="proof",
                stage="packet_generated",
                store_dir=store,
            )
            session = load_coach_session(run_id, store_dir=store)
            self.assertEqual(len(session["checkpoints"]), 1)
            self.assertEqual(len(session["turns"]), 1)
            context = format_coach_session_context(run_id, store_dir=store)
            self.assertIn("packet_generated", context)
            self.assertIn("What proof is missing?", context)

    def test_enrich_keeps_deterministic_sections_and_session(self) -> None:
        packet_run = generate_initial_review_run_packet(
            select_review_run_repo(create_review_run(), _selected_repo(), repo_index_summary=_indexed_summary()),
            DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
        )
        base = build_review_run_coach_answer(packet_run, "what next")
        with TemporaryDirectory() as tmp:
            store = __import__("pathlib").Path(tmp)
            with patch("agent.coach_enrichment.config.COACH_SESSION_ENABLED", True), patch(
                "agent.coach_enrichment.config.COACH_LLM_NARRATE", False
            ), patch("agent.coach_enrichment.config.COACH_V1_GOVERNANCE", False):
                enriched = enrich_review_run_coach_answer(
                    packet_run,
                    base,
                    prompt="what next",
                    chip_entities={"reassess_trigger": "packet_generated"},
                    store_dir=store,
                )
        self.assertEqual(enriched["sections"], base["sections"])
        self.assertFalse(enriched["approves_access"])
        self.assertIn("review_run_state_coach", enriched["coach_provider"])
        self.assertTrue(enriched["session_context_included"])
