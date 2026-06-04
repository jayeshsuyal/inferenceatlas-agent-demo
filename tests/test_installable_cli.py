import importlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SCRIPTS = {
    "ia-adapters": "agent.adapters.__main__:main",
    "ia-contract": "agent.contract:main",
    "ia-gate": "agent.gate:main",
    "ia-judge": "agent.judge:main",
    "ia-outcome-memo": "agent.outcome_memo:main",
    "ia-packet-diff": "agent.packet_diff:main",
    "ia-proof-health": "agent.proof_health:main",
    "ia-review": "agent.review:main",
    "ia-review-room": "agent.review_room:main",
    "ia-skills": "agent.skills:main",
    "ia-sponsor-readiness": "agent.sponsor_readiness:main",
    "ia-trial": "agent.trial:main",
    "ia-trial-outcome-memo": "agent.trial_outcome_memo:main",
    "ia-trust": "agent.trust:main",
    "ia-verify-artifacts": "agent.verify_artifacts:main",
    "ia-mind": "agent.mind.__main__:main",
}


def _load_pyproject_text() -> str:
    path = ROOT / "pyproject.toml"
    if not path.is_file():
        raise AssertionError("pyproject.toml is missing")
    return path.read_text(encoding="utf-8")


def _toml_string(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\"]+)\"", text, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"missing TOML string key: {key}")
    return match.group(1)


def _script_entries(text: str) -> dict[str, str]:
    match = re.search(r"^\[project\.scripts\]\n(?P<body>.*?)(?:\n\[|\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise AssertionError("missing [project.scripts] section")
    entries: dict[str, str] = {}
    for line in match.group("body").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, target = line.partition("=")
        entries[name.strip()] = target.strip().strip('"')
    return entries


class InstallableCliTests(unittest.TestCase):
    def test_pyproject_defines_public_console_scripts(self) -> None:
        pyproject = _load_pyproject_text()

        self.assertEqual(_toml_string(pyproject, "name"), "inferenceatlas-agent-demo")
        self.assertEqual(_toml_string(pyproject, "version"), "0.1.0")

        self.assertEqual(_script_entries(pyproject), EXPECTED_SCRIPTS)

    def test_console_script_targets_are_importable(self) -> None:
        for script_name, target in EXPECTED_SCRIPTS.items():
            module_name, function_name = target.split(":", 1)
            module = importlib.import_module(module_name)
            self.assertTrue(
                callable(getattr(module, function_name)),
                msg=f"{script_name} target {target} must be callable",
            )

    def test_readme_and_ci_exercise_installed_judge_command(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")

        self.assertIn("pip install -e .", readme)
        self.assertIn("ia-judge", readme)
        self.assertIn("ia-skills", readme)
        self.assertIn("ia-packet-diff", readme)
        self.assertIn("ia-outcome-memo", readme)
        self.assertIn("ia-proof-health", readme)
        self.assertIn("ia-sponsor-readiness", readme)
        self.assertIn("ia-review --list", readme)
        self.assertIn("ia-contract --all", readme)
        self.assertIn("ia-trial examples/requests/support_triage_trial.yml", readme)
        self.assertIn("ia-trial-outcome-memo examples/requests/support_triage_trial.yml", readme)
        self.assertIn("ia-verify-artifacts", readme)
        self.assertIn("python -m pip install -e .", workflow)
        self.assertIn("ia-judge --no-write", workflow)
        self.assertIn("ia-skills", workflow)
        self.assertIn("ia-packet-diff --no-write", workflow)
        self.assertIn("ia-outcome-memo --no-write", workflow)
        self.assertIn("ia-proof-health --no-write", workflow)
        self.assertIn("ia-sponsor-readiness --no-write", workflow)
        self.assertIn("ia-trial examples/requests/support_triage_trial.yml", workflow)
        self.assertIn("ia-trial-outcome-memo examples/requests/support_triage_trial.yml", workflow)
        self.assertIn("ia-verify-artifacts", workflow)


if __name__ == "__main__":
    unittest.main()
