"""Patch-only cortex — LLM proposes structured deltas, never owns verdict fields."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

from agent.config import LLM_API_KEY

from .model import PATCH_ALLOWED_TARGETS, PATCH_LOCKED_TOP_LEVEL, Mind


CORTEX_SYSTEM = """You are the cortex for an InferenceAtlas governance mind.
You do NOT approve access, change verdicts, or edit safety_state.
Return ONLY valid JSON with this shape:
{
  "target": "evidence_notes",
  "ops": [{"op": "append", "value": {"source": "...", "status": "...", "note": "..."}}]
}
Propose at most one evidence note that helps resolve the top tension. No markdown."""


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def propose_patch(mind: Mind) -> Optional[dict]:
    """Ask the LLM for a patch proposal; None if unavailable or parse fails."""
    if not LLM_API_KEY:
        return None

    top = mind.top_tensions(1)
    tension_desc = top[0].to_dict() if top else {}
    user_payload = {
        "scenario": mind.scenario,
        "tick": mind.tick,
        "top_tension": tension_desc,
        "missing_proof_count": len(mind.packet.get("missing_proof", [])),
        "approval_posture": mind.packet.get("approval_posture"),
    }
    prompt = (
        f"{CORTEX_SYSTEM}\n\n"
        f"Current state summary:\n{json.dumps(user_payload, indent=2)}"
    )

    try:
        from agent import InferenceAtlasAgent

        agent = InferenceAtlasAgent()
        raw = agent.run(prompt)
    except Exception:
        return None

    patch = _extract_json(raw)
    if not patch or not _validate_patch_shape(patch):
        return None
    return patch


def _validate_patch_shape(patch: dict) -> bool:
    target = patch.get("target")
    if target not in PATCH_ALLOWED_TARGETS:
        return False
    ops = patch.get("ops")
    if not isinstance(ops, list) or not ops:
        return False
    for op in ops:
        if not isinstance(op, dict) or op.get("op") != "append":
            return False
        if target == "evidence_notes":
            val = op.get("value")
            if not isinstance(val, dict):
                return False
            if not all(k in val for k in ("source", "status", "note")):
                return False
    return True


def apply_patch(packet: dict, patch: dict) -> dict:
    """Apply an allowed patch; reject locked field mutations."""
    for key in patch:
        if key in PATCH_LOCKED_TOP_LEVEL:
            raise ValueError(f"patch cannot target locked field: {key}")

    target = patch.get("target")
    if target not in PATCH_ALLOWED_TARGETS:
        raise ValueError(f"patch target not allowed: {target}")

    result = deepcopy(packet)
    if target == "evidence_notes":
        notes = list(result.get("evidence_notes", []))
        for op in patch.get("ops", []):
            if op.get("op") == "append":
                notes.append(op["value"])
        result["evidence_notes"] = notes
    return result


def apply_patch_for_test(packet: dict, patch: dict) -> dict:
    """Public helper for tests."""
    if not _validate_patch_shape(patch):
        raise ValueError("invalid patch shape")
    return apply_patch(packet, patch)
