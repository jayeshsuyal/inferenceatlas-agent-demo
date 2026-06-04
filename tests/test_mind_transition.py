"""Tests for Mind state-transition runtime."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.mind.cortex import apply_patch_for_test, propose_patch
from agent.mind.model import PATCH_LOCKED_TOP_LEVEL, Mind
from agent.mind.project import project_mind
from agent.mind.store import STATE_ROOT, load_mind, save_mind
from agent.mind.transition import init_mind, step
from agent.public_contract import validate_public_review_artifacts
from agent.scenarios import SCENARIOS


class MindTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._state_patch = patch("agent.mind.store.STATE_ROOT", Path(self._tmpdir))
        self._state_patch.start()

    def tearDown(self) -> None:
        self._state_patch.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_init_all_scenarios(self) -> None:
        for scenario in SCENARIOS:
            mind = init_mind(scenario)
            self.assertEqual(mind.tick, 0)
            self.assertIn("missing_proof", mind.packet)

    def test_two_steps_create_tensions_with_proof_debt(self) -> None:
        for scenario in SCENARIOS:
            mind = init_mind(scenario)
            mind = step(mind, allow_cortex=False)
            mind = step(mind, allow_cortex=False)
            tensions = mind.internal.get("tensions", [])
            if mind.packet.get("missing_proof"):
                self.assertGreater(len(tensions), 0, scenario)
            self.assertGreater(mind.tick, 0)

    def test_e2e_contract_offline(self) -> None:
        out = Path(self._tmpdir) / "project"
        for scenario in SCENARIOS:
            mind = init_mind(scenario)
            mind = step(mind, allow_cortex=False)
            mind = step(mind, allow_cortex=False)
            _, errors = project_mind(mind, out)
            self.assertEqual(errors, [], f"{scenario}: {errors}")

    def test_persist_and_reload(self) -> None:
        mind = init_mind("support_triage_agent")
        mind = step(mind, allow_cortex=False)
        save_mind(mind)
        loaded = load_mind("support_triage_agent")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.tick, mind.tick)

    def test_patch_append_evidence_only(self) -> None:
        mind = init_mind("support_triage_agent")
        before_len = len(mind.packet["evidence_notes"])
        patch = {
            "target": "evidence_notes",
            "ops": [
                {
                    "op": "append",
                    "value": {
                        "source": "test",
                        "status": "synthetic",
                        "note": "unit test evidence",
                    },
                }
            ],
        }
        mind.packet = apply_patch_for_test(mind.packet, patch)
        self.assertEqual(len(mind.packet["evidence_notes"]), before_len + 1)
        brief = __import__(
            "agent.decision_brief", fromlist=["build_agent_access_decision_brief"]
        ).build_agent_access_decision_brief(mind.packet)
        errors = validate_public_review_artifacts(mind.packet, brief)
        self.assertEqual(errors, [])

    def test_reject_locked_field_in_patch_shape(self) -> None:
        mind = init_mind("support_triage_agent")
        verdict_before = mind.packet["decision"]["verdict"]
        bad_patch = {
            "target": "evidence_notes",
            "ops": [{"op": "append", "value": {"source": "x", "status": "y", "note": "z"}}],
            "verdict": "approved",
        }
        for key in bad_patch:
            if key in PATCH_LOCKED_TOP_LEVEL:
                continue
        with patch("agent.mind.cortex.propose_patch", return_value=bad_patch):
            mind = step(mind, allow_cortex=True)
        self.assertEqual(mind.packet["decision"]["verdict"], verdict_before)

    def test_propose_patch_without_api_key_returns_none(self) -> None:
        mind = init_mind("support_triage_agent")
        with patch("agent.mind.cortex.LLM_API_KEY", ""):
            self.assertIsNone(propose_patch(mind))


class MindE2ECliTests(unittest.TestCase):
    def test_main_e2e_exits_zero(self) -> None:
        from agent.mind.__main__ import main

        code = main(["e2e"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
