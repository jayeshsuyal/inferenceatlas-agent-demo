"""UI skills — web harness picker sourced from AGENT_SKILLS registry."""

import json
import unittest
from pathlib import Path

from agent.skills import SKILLS
from agent.ui_skills import (
    SLASH_BY_SKILL_ID,
    _executive_review_summary,
    build_skill_context_for_chat,
    build_ui_skills,
    build_ui_skills_payload,
    compose_message_with_skills,
    find_ui_skill,
    skill_suggested_questions,
)


class UISkillsTests(unittest.TestCase):
    def test_every_registry_skill_has_slash(self) -> None:
        self.assertEqual(len(SLASH_BY_SKILL_ID), len(SKILLS))
        for skill in SKILLS:
            self.assertIn(skill.id, SLASH_BY_SKILL_ID)

    def test_ui_skill_count(self) -> None:
        self.assertEqual(len(build_ui_skills()), len(SKILLS) + 1)

    def test_find_by_slash(self) -> None:
        found = find_ui_skill("packet")
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.id, "decision_packet_generation")

    def test_payload_matches_doc_source(self) -> None:
        payload = build_ui_skills_payload()
        self.assertEqual(payload["source"], "docs/AGENT_SKILLS.md")
        self.assertEqual(payload["count"], 13)
        self.assertEqual(len(payload["skills"]), 13)

    def test_compose_message_with_skills(self) -> None:
        text, used = compose_message_with_skills(
            "What blocks production?",
            ["decision_packet_generation", "policy_gate_evaluation"],
        )
        self.assertIn("QUESTION", text)
        self.assertIn("What blocks production?", text)
        self.assertEqual(len(used), 2)
        self.assertIn("HARNESS FACTS", text)
        self.assertLess(len(text), 12000)

    def test_build_skill_context_nonempty(self) -> None:
        ctx, used = build_skill_context_for_chat(["proof_debt_extraction"])
        self.assertTrue(used)
        self.assertIn("Proof debt", ctx)
        self.assertIn("Production access", ctx)

    def test_executive_summary_compact(self) -> None:
        summary = _executive_review_summary()
        self.assertIn("Production access: False", summary)
        self.assertLess(len(summary), 2500)

    def test_skill_suggested_questions(self) -> None:
        hints = skill_suggested_questions(["policy_gate_evaluation"])
        self.assertTrue(any("gate" in h.lower() for h in hints))

    def test_static_skills_registry_json(self) -> None:
        root = Path(__file__).resolve().parents[1]
        path = root / "web" / "static" / "skills-registry.json"
        self.assertTrue(path.is_file(), "run: python3 -m scripts.generate_agent_skills_doc")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["count"], 13)


if __name__ == "__main__":
    unittest.main()
