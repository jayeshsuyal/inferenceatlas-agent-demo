#!/usr/bin/env python3
"""Build /tmp/mem0_import.json from OpenClaw workspace + InferenceAtlas project memory."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_DIR = WORKSPACE / "memory"
ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/tmp/mem0_import.json")
WORD_LIMIT = 2000
WORKSPACE_FILES = ("SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md")
SKIP_FILES = {"AGENTS.md", "BOOTSTRAP.md", "HEARTBEAT.md", "TOOLS.md"}
PROJECT_DOC_FILES = (
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "REVIEW_60_PATH.md",
    ROOT / "docs" / "AGENT_SKILLS.md",
)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def split_by_heading(text: str, source: str) -> list[dict]:
    if word_count(text) <= WORD_LIMIT:
        return [{"memory": text.strip(), "metadata": {"source": source, "kind": "document"}}]
    parts = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)
    items: list[dict] = []
    for idx, part in enumerate(parts):
        body = part.strip()
        if not body:
            continue
        title = body.splitlines()[0].lstrip("# ").strip() if body.startswith("#") else f"section-{idx + 1}"
        items.append(
            {
                "memory": body[:12000],
                "metadata": {"source": source, "kind": "section", "title": title},
            }
        )
    return items


def coach_session_items() -> list[dict]:
    items: list[dict] = []
    coach_dir = ROOT / "state" / "coach_sessions"
    if not coach_dir.is_dir():
        return items
    for path in sorted(coach_dir.glob("*.json"))[-20:]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        run_id = str(data.get("run_id") or path.stem)
        checkpoints = data.get("checkpoints") or []
        turns = data.get("turns") or []
        summary_bits = []
        for cp in checkpoints[-3:]:
            summary_bits.append(
                f"ReviewRun {run_id} checkpoint [{cp.get('stage')}]: {cp.get('summary') or cp.get('trigger')}"
            )
        for turn in turns[-2:]:
            summary_bits.append(f"Coach turn on {run_id}: {turn.get('prompt') or turn.get('prompt_kind')}")
        if not summary_bits:
            continue
        items.append(
            {
                "memory": "\n".join(summary_bits)[:4000],
                "metadata": {"source": f"coach_session:{run_id}", "kind": "review_run_coach"},
            }
        )
    return items


def main() -> None:
    found_files: list[str] = []
    items: list[dict] = []

    for name in WORKSPACE_FILES:
        path = WORKSPACE / name
        if path.is_file():
            found_files.append(str(path))
            items.extend(split_by_heading(path.read_text(encoding="utf-8"), str(path)))

    if MEMORY_DIR.is_dir():
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for path in sorted(MEMORY_DIR.glob("*.md")):
            match = re.match(r"^(\d{4}-\d{2}-\d{2})\.md$", path.name)
            if not match:
                continue
            day = datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if day < cutoff:
                continue
            found_files.append(str(path))
            items.extend(split_by_heading(path.read_text(encoding="utf-8"), str(path)))

    for path in PROJECT_DOC_FILES:
        if path.is_file():
            found_files.append(str(path))
            items.extend(split_by_heading(path.read_text(encoding="utf-8"), str(path)))

    items.extend(coach_session_items())

    items.append(
        {
            "memory": (
                "InferenceAtlas ReviewRun memory policy: IA Packet is authoritative; coach and session hub "
                "store per-run context only unless Mem0 is enabled. User prefers tiered repo indexing, "
                "collapsible session/run hub, and structured index presentation with charts on Show summary."
            ),
            "metadata": {"source": "inferenceatlas-agent-demo", "kind": "preferences"},
        }
    )

    OUT.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "found_files": found_files, "items": len(items)}, indent=2))


if __name__ == "__main__":
    main()
