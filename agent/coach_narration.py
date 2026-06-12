"""Demo LLM narration over locked ReviewRun coach sections (deterministic skin, LLM bones)."""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from . import config

COACH_NARRATION_FORBIDDEN = (
    "approved for production",
    "permission granted",
    "safe to proceed",
    "access granted",
    "override blocked",
    "bypass review",
)
COACH_NARRATION_REQUIRED = (
    "decision lock",
    "did not approve",
)


def _client() -> Any:
    from openai import OpenAI

    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


def _deterministic_narration(sections: Mapping[str, str]) -> str:
    parts = [
        str(sections.get("current_read") or "").strip(),
        f"What blocks movement: {sections.get('what_blocks_movement', '')}",
        f"Next human action: {sections.get('next_human_action', '')}",
        f"Downstream: {sections.get('downstream_impact', '')}",
        str(sections.get("safety") or "").strip(),
    ]
    return " ".join(part for part in parts if part)


def _validate_narration(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if len(cleaned) < 80:
        raise ValueError("coach narration too short")
    lower = cleaned.lower()
    for phrase in COACH_NARRATION_FORBIDDEN:
        if phrase in lower:
            raise ValueError(f"forbidden phrase: {phrase}")
    missing = [anchor for anchor in COACH_NARRATION_REQUIRED if anchor not in lower]
    if missing:
        raise ValueError(f"missing anchors: {', '.join(missing)}")
    if len(cleaned) > 1200:
        cleaned = cleaned[:1197].rstrip() + "..."
    return cleaned


def narrate_coach_sections(
    answer: Mapping[str, Any],
    *,
    session_context: str = "",
    user_prompt: str = "",
) -> dict[str, Any]:
    """Return narration metadata; sections in answer remain authoritative."""
    sections = answer.get("sections") or {}
    fallback = _deterministic_narration(sections)
    payload = {
        "narration": fallback,
        "narration_source": "deterministic",
        "narration_live": False,
        "narration_fallback_reason": "",
    }
    if not config.COACH_LLM_NARRATE or not config.LLM_API_KEY:
        payload["narration_fallback_reason"] = "coach_llm_narrate_disabled"
        return payload

    locked = {
        "stage": answer.get("stage"),
        "verdict": answer.get("verdict"),
        "portkey_state": answer.get("portkey_state"),
        "packet_revision": answer.get("packet_revision"),
        "sections": dict(sections),
        "movement_classes": answer.get("movement_classes"),
        "safety_boundary": answer.get("safety_boundary"),
    }
    prompt = (
        "You are Ask IA narrating a ReviewRun coach read. The JSON sections are authoritative facts. "
        "Write 3-5 sentences for a human reviewer: explain current read, what blocks movement, "
        "next human action, and Portkey/downstream impact. "
        "You must NOT approve access, grant permissions, override blocked claims, or change verdict. "
        "Include that the decision lock is unchanged and IA did not approve.\n\n"
        f"User question: {user_prompt or '(stage reassessment)'}\n\n"
        f"{session_context}\n\n"
        f"Locked coach JSON:\n{json.dumps(locked, sort_keys=True)}"
    )
    try:
        response = _client().chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return plain prose only. No markdown headings. No JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=400,
        )
        raw = response.choices[0].message.content or ""
        narration = _validate_narration(raw)
    except Exception as exc:
        payload["narration_fallback_reason"] = str(exc).splitlines()[0][:180]
        return payload

    payload.update(
        {
            "narration": narration,
            "narration_source": f"demo_llm_{config.LLM_PROVIDER}",
            "narration_live": True,
            "narration_fallback_reason": "",
        }
    )
    return payload
