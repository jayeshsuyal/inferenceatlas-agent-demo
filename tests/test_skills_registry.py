import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent.skills import (
    ALLOWED_SAFETY_BOUNDARIES,
    COMMAND_MODULE_RE,
    SKILL_CATEGORIES,
    SKILL_TIERS,
    SKILLS,
    build_skills_report,
    render_skills_markdown,
)
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
AGENT_SKILLS_DOC = ROOT / "docs" / "AGENT_SKILLS.md"


def _all_skill_strings() -> list[str]:
    values: list[str] = []
    for skill in SKILLS:
        values.extend(
            [
                skill.id,
                skill.name,
                skill.what_it_proves,
                skill.command,
                skill.safety_boundary,
                skill.tier,
                skill.category,
            ]
        )
        values.extend(skill.artifacts)
        values.extend(skill.depends_on)
    return values


def _first_diff_line(expected: str, actual: str) -> str:
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    for index in range(max(len(expected_lines), len(actual_lines))):
        expected_line = expected_lines[index] if index < len(expected_lines) else "<missing line>"
        actual_line = actual_lines[index] if index < len(actual_lines) else "<missing line>"
        if expected_line != actual_line:
            return f"line {index + 1}: expected {expected_line!r}, got {actual_line!r}"
    return "no differing line found"


class SkillsRegistryTests(unittest.TestCase):
    def test_skills_are_unique_and_deterministically_ordered(self) -> None:
        ids = [skill.id for skill in SKILLS]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(SKILLS), sorted(SKILLS, key=lambda skill: (skill.category, skill.id)))

    def test_skills_use_safe_public_categories_tiers_and_boundaries(self) -> None:
        for skill in SKILLS:
            self.assertIn(skill.category, SKILL_CATEGORIES)
            self.assertIn(skill.tier, SKILL_TIERS)
            self.assertIn(skill.safety_boundary, ALLOWED_SAFETY_BOUNDARIES)

    def test_skills_preserve_private_boundary(self) -> None:
        for value in _all_skill_strings():
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, value, msg=f"{forbidden} leaked through skills registry")

    def test_generated_agent_skills_doc_preserves_private_boundary(self) -> None:
        doc = AGENT_SKILLS_DOC.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, doc, msg=f"{forbidden} leaked through docs/AGENT_SKILLS.md")

    def test_skill_commands_point_to_importable_public_modules(self) -> None:
        for skill in SKILLS:
            match = COMMAND_MODULE_RE.match(skill.command)
            self.assertIsNotNone(match, msg=f"{skill.id} command is not a python module command")
            assert match is not None
            importlib.import_module(match.group("module"))

    def test_skill_artifacts_exist(self) -> None:
        for skill in SKILLS:
            for artifact in skill.artifacts:
                self.assertTrue((ROOT / artifact).exists(), msg=f"{skill.id} artifact is missing: {artifact}")

    def test_skill_dependencies_are_known_and_acyclic(self) -> None:
        skills_by_id = {skill.id: skill for skill in SKILLS}

        for skill in SKILLS:
            for dependency in skill.depends_on:
                self.assertIn(dependency, skills_by_id, msg=f"{skill.id} depends on unknown skill {dependency}")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(skill_id: str) -> None:
            if skill_id in visited:
                return
            if skill_id in visiting:
                raise AssertionError(f"cycle detected at {skill_id}")
            visiting.add(skill_id)
            for dependency in skills_by_id[skill_id].depends_on:
                visit(dependency)
            visiting.remove(skill_id)
            visited.add(skill_id)

        for skill_id in skills_by_id:
            visit(skill_id)

    def test_generated_agent_skills_doc_matches_registry(self) -> None:
        expected = render_skills_markdown()
        actual = AGENT_SKILLS_DOC.read_text(encoding="utf-8")

        if expected != actual:
            raise AssertionError(
                "docs/AGENT_SKILLS.md has drifted from the registry.\n"
                "Regenerate with: python3 -m scripts.generate_agent_skills_doc\n"
                f"First differing line: {_first_diff_line(expected, actual)}"
            )

    def test_skills_report_is_agent_readable(self) -> None:
        report = build_skills_report()

        self.assertEqual(report["schema_version"], "agent_skills_registry.v0")
        self.assertEqual(report["summary"]["registered_skills"], 13)
        self.assertEqual(report["summary"]["stable_skills"], 13)
        self.assertEqual(report["summary"]["available_stable_skills"], 13)
        self.assertFalse(report["private_boundary"]["private_source_exposed"])
        self.assertFalse(report["safety"]["approves_access"])
        self.assertFalse(report["safety"]["grants_permissions"])
        self.assertFalse(report["safety"]["executes_external_writes"])

    def test_skills_cli_outputs_human_and_json_views(self) -> None:
        text_result = subprocess.run(
            [sys.executable, "-m", "agent.skills"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        json_result = subprocess.run(
            [sys.executable, "-m", "agent.skills", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(text_result.returncode, 0, msg=text_result.stderr)
        self.assertIn("# InferenceAtlas Agent Skills", text_result.stdout)
        self.assertIn("13 / 13 stable skills available", text_result.stdout)
        self.assertIn("Artifact Integrity Verification", text_result.stdout)
        self.assertEqual(json_result.returncode, 0, msg=json_result.stderr)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["summary"]["available_stable_skills"], 13)

if __name__ == "__main__":
    unittest.main()
