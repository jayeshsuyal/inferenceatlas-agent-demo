"""Persistent Mind storage under state/mind/."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from agent.scenarios import ROOT_DIR, SCENARIOS

from .model import Mind


STATE_ROOT = ROOT_DIR / "state" / "mind"


def state_dir() -> Path:
    return STATE_ROOT


def mind_path(scenario: str) -> Path:
    if scenario not in SCENARIOS:
        raise KeyError(f"unknown scenario: {scenario}")
    return STATE_ROOT / f"{scenario}.json"


def load_mind(scenario: str) -> Optional[Mind]:
    path = mind_path(scenario)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Mind.from_dict(data)


def save_mind(mind: Mind) -> Path:
    path = mind_path(mind.scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(mind.to_dict(), indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return path


def load_all_minds() -> dict[str, Mind]:
    minds = {}
    for scenario in SCENARIOS:
        mind = load_mind(scenario)
        if mind is not None:
            minds[scenario] = mind
    return minds
