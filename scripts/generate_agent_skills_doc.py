"""Generate docs/AGENT_SKILLS.md from the canonical skills registry."""

from __future__ import annotations

from agent.scenarios import ROOT_DIR
from agent.skills import render_skills_markdown


OUTPUT_PATH = ROOT_DIR / "docs" / "AGENT_SKILLS.md"


def main() -> None:
    OUTPUT_PATH.write_text(render_skills_markdown(), encoding="utf-8")
    print(OUTPUT_PATH.relative_to(ROOT_DIR))


if __name__ == "__main__":
    main()
