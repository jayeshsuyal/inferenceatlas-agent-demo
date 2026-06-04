"""Generate docs/AGENT_SKILLS.md and web/static/skills-registry.json from agent/skills.py."""

from __future__ import annotations

import json

from agent.scenarios import ROOT_DIR
from agent.skills import render_skills_markdown
from agent.ui_skills import build_ui_skills_payload


OUTPUT_PATH = ROOT_DIR / "docs" / "AGENT_SKILLS.md"
SKILLS_JSON_PATH = ROOT_DIR / "web" / "static" / "skills-registry.json"


def main() -> None:
    OUTPUT_PATH.write_text(render_skills_markdown(), encoding="utf-8")
    SKILLS_JSON_PATH.write_text(
        json.dumps(build_ui_skills_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH.relative_to(ROOT_DIR))
    print(SKILLS_JSON_PATH.relative_to(ROOT_DIR))


if __name__ == "__main__":
    main()
