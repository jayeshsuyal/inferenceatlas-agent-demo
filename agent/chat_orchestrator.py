"""Unified chat orchestration: skills, GitHub, files, connectors, and tools together."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .config import V1_SLOT_FILLER_PROMPT
from .cost_plan import AttachmentRoles, build_cost_plan
from .github_repo import build_github_chat_context, get_repo_index_status
from .google_drive_files import build_drive_chat_context, get_drive_index_status
from .ui_skills import build_skill_context_for_chat, compose_message_with_skills
from .workload_parse import is_cost_question

TOOL_KEYWORDS = (
    "compare_providers",
    "tavily_search",
    "get_catalog_summary",
    "export_report",
    "composio_action",
)

ORCHESTRATED_GROUNDED_PROMPT = """You are the InferenceAtlas assistant. The user attached multiple context sources in ONE message.

Your message is structured in labeled sections:
- HARNESS FACTS (skills) — authoritative for access review, proof debt, policy gates
- GITHUB REPO — real README, tree, and file excerpts from the attached repository
- GOOGLE DRIVE — indexed docs, sheets, images (metadata/preview), or video metadata
- ATTACHED FILES — user-uploaded evidence (local upload, not Drive)
- USER QUESTION — what to answer

Rules (anti-hallucination):
1. Answer the USER QUESTION using ONLY the sections provided. Cite which section you used (e.g. "From GITHUB README…", "Per HARNESS FACTS…").
2. Do NOT invent pricing, repo files, or gate decisions not present in the sections.
3. If the question is about inference **cost** or **compare_providers** but you have no tool results in the message, say you need catalog tool data — do not fabricate provider prices.
4. When GitHub repo context is present, tie recommendations to **specific** README paths, tech stack, or files named in that repo — never generic "given the repository focuses on…" without quoting a fact from the digest.
5. When skills are present, always state production access, scoped validation, and missing proof from HARNESS FACTS.
6. If sections conflict, say so explicitly and prioritize: HARNESS FACTS for access review; tool/catalog for pricing; GITHUB for repo-specific engineering facts.
"""

ORCHESTRATED_TOOLS_PROMPT = """You are the InferenceAtlas Intelligence Agent with **combined attachments** (skills, GitHub repo digest, files) AND live tools.

The user message may include:
- HARNESS FACTS (skills) — authoritative for access review
- GITHUB REPO — README and file excerpts (repo-specific facts only from here)
- GOOGLE DRIVE — indexed file excerpts and media metadata
- ATTACHED FILES — local upload evidence
- USER QUESTION

Tools available:
- compare_providers, tavily_search, get_catalog_summary, export_report, composio_action

Workflow:
1. If the user asks for cost comparison or names compare_providers → call compare_providers (and tavily_search if needed). Ground all prices in tool output.
2. Use HARNESS FACTS for access-review conclusions — never override gates with repo guesses.
3. Use GITHUB sections only for repo-specific engineering context; cite file paths or README lines when relevant.
4. Never give the same generic answer for every question — address the exact USER QUESTION and list which sources you used at the start (3–6 bullets).
"""


@dataclass
class OrchestratedChat:
    """Fully assembled chat turn for the LLM."""

    user_message: str
    llm_message: str
    user_display: str
    skills_used: List[dict] = field(default_factory=list)
    github_used: List[str] = field(default_factory=list)
    github_index: List[dict] = field(default_factory=list)
    drive_used: List[str] = field(default_factory=list)
    drive_index: List[dict] = field(default_factory=list)
    file_names: List[str] = field(default_factory=list)
    attach_warnings: List[str] = field(default_factory=list)
    use_tools: bool = False
    thinking_steps: List[str] = field(default_factory=list)
    system_prompt: str = ORCHESTRATED_GROUNDED_PROMPT
    context_manifest: List[str] = field(default_factory=list)
    engine_source: str = ""
    cost_plan_ok: bool = False


def _message_snippet(message: str, max_len: int = 72) -> str:
    one = " ".join(message.split())
    if len(one) <= max_len:
        return one or "your request"
    return one[: max_len - 1] + "…"


def _wants_tools(message: str) -> bool:
    lower = message.lower()
    if any(kw in lower for kw in TOOL_KEYWORDS):
        return True
    cost_patterns = (
        r"\bcompare\b.*\bprovider",
        r"\bcheapest\b",
        r"\bcost\b.*\btoken",
        r"\bgpt-4",
        r"\bpricing\b",
        r"\bcatalog\b",
        r"\bexport_report\b",
    )
    return any(re.search(p, lower) for p in cost_patterns)


def build_thinking_steps(
    *,
    message: str,
    skills_used: List[dict],
    github_used: List[str],
    github_index: List[dict],
    drive_index: List[dict],
    file_names: List[str],
    use_tools: bool,
    attach_warnings: List[str],
) -> List[str]:
    """Personalized one-liner status lines for the UI."""
    steps: List[str] = []
    snippet = _message_snippet(message)
    steps.append(f"Parsing your question: «{snippet}»")

    if skills_used:
        names = ", ".join(s["slash_trigger"] for s in skills_used[:4])
        steps.append(f"Loading harness skills {names} — DecisionPacket & policy gates")
    else:
        steps.append("No access-review skills attached — skipping harness facts")

    for meta in github_index:
        fn = meta.get("full_name", "repo")
        chars = meta.get("digest_chars", 0)
        readme = "README found" if meta.get("readme_found") else "no README"
        files_n = meta.get("files_included", 0)
        if meta.get("indexed") and chars > 500:
            steps.append(
                f"GitHub {fn}: index OK ({chars:,} chars, {readme}, {files_n} file excerpts)"
            )
        elif meta.get("indexed"):
            steps.append(f"GitHub {fn}: index thin ({chars} chars) — answers may be limited")
        else:
            steps.append(f"GitHub {fn}: not indexed yet — will fetch on send")

    for meta in drive_index:
        name = meta.get("name", "file")
        chars = meta.get("digest_chars", 0)
        kind = meta.get("media_kind", "docs")
        if meta.get("indexed") and chars > 80:
            steps.append(f"Google Drive «{name}»: index OK ({chars:,} chars, {kind})")
        else:
            steps.append(f"Google Drive «{name}»: not indexed — will fetch on send")

    for name in file_names[:3]:
        steps.append(f"Injecting local upload «{name}» into context")
    if len(file_names) > 3:
        steps.append(f"…and {len(file_names) - 3} more attached files")

    if attach_warnings:
        steps.append(f"Warning: {attach_warnings[0]}")

    if use_tools:
        lower = message.lower()
        if "compare_providers" in lower or "cheapest" in lower or "gpt-4" in lower:
            steps.append("Orchestration: cost question → will call compare_providers on catalog")
        elif "tavily" in lower or "pricing" in lower:
            steps.append("Orchestration: live pricing → tavily_search + catalog tools")
        elif "catalog" in lower:
            steps.append("Orchestration: catalog overview → get_catalog_summary")
        else:
            steps.append("Orchestration: enabling InferenceAtlas tools for this question")
    else:
        steps.append("Orchestration: grounded mode — answer only from attached sections (no tools)")

    steps.append("Merging skills + GitHub + Drive + uploads into one prompt — avoiding generic filler")
    steps.append("Generating reply tied to your exact question and cited sources")
    return steps


def build_context_manifest(
    *,
    skills_used: List[dict],
    github_used: List[str],
    github_index: List[dict],
    drive_used: List[str],
    drive_index: List[dict],
    file_names: List[str],
    use_tools: bool,
) -> List[str]:
    manifest: List[str] = []
    if skills_used:
        manifest.append("Skills: " + ", ".join(s["slash_trigger"] for s in skills_used))
    if github_used:
        parts = []
        for fn in github_used:
            meta = next((m for m in github_index if m.get("full_name") == fn), {})
            chars = meta.get("digest_chars", 0)
            parts.append(f"{fn} ({chars:,} chars indexed)" if chars else fn)
        manifest.append("GitHub: " + "; ".join(parts))
    if drive_used:
        parts = []
        for name in drive_used:
            meta = next((m for m in drive_index if m.get("name") == name), {})
            chars = meta.get("digest_chars", 0)
            parts.append(f"{name} ({chars:,} chars)" if chars else name)
        manifest.append("Drive: " + "; ".join(parts))
    if file_names:
        manifest.append("Uploads: " + ", ".join(file_names[:5]))
    if use_tools:
        manifest.append("Tools: enabled (catalog / search)")
    return manifest


def assemble_orchestrated_message(
    *,
    message: str,
    skill_ids: List[str],
    skill_position: str,
    session_id: str,
    github_repos: List[str],
    drive_file_ids: List[str],
    file_blocks: List[Tuple[str, str]],
) -> Tuple[str, List[dict], List[str], List[dict], List[str], List[dict]]:
    """Build a single LLM user message with labeled sections."""
    sections: List[str] = []
    skills_used: List[dict] = []
    github_used: List[str] = []
    github_index: List[dict] = []
    drive_used: List[str] = []
    drive_index: List[dict] = []

    if skill_ids:
        skill_ctx, skills_used = build_skill_context_for_chat(skill_ids)
        if skill_ctx:
            sections.append(
                "--- HARNESS FACTS (skills — authoritative for access review) ---\n\n"
                + skill_ctx
            )

    if github_repos:
        gh_ctx, github_used = build_github_chat_context(session_id, github_repos)
        if gh_ctx:
            sections.append(
                "--- GITHUB REPO (indexed digest — cite paths/README) ---\n\n" + gh_ctx
            )
        for fn in github_used:
            github_index.append(get_repo_index_status(session_id, fn))

    if drive_file_ids:
        dr_ctx, drive_used = build_drive_chat_context(session_id, drive_file_ids)
        if dr_ctx:
            sections.append(
                "--- GOOGLE DRIVE (indexed — cite file names & excerpts) ---\n\n" + dr_ctx
            )
        for fid in drive_file_ids[:5]:
            fid = fid.strip()
            if fid:
                drive_index.append(get_drive_index_status(session_id, fid))

    for fname, text in file_blocks:
        sections.append(
            f"--- ATTACHED FILE: {fname} ---\n\n{text[:12000]}\n"
        )

    question = message.strip()
    if skill_ids and not question:
        question = (
            "Give an executive summary: production access, scoped validation, "
            "top proof gaps, and who must approve next."
        )
    if github_repos and not question and not skill_ids:
        question = "Summarize these repositories for access review and engineering context."
    if drive_file_ids and not question and not skill_ids and not github_repos:
        question = "Summarize these Google Drive files for access review evidence."
    if not question:
        question = "Answer using all attached context above."

    sections.append(f"--- USER QUESTION ---\n\n{question}")

    # Legacy skill wrapper when only skills (no github/files) — still use unified sections
    if skill_ids and len(sections) <= 2:
        wrapped, skills_used = compose_message_with_skills(message, skill_ids, position=skill_position)
        return wrapped, skills_used, github_used, github_index, drive_used, drive_index

    return "\n\n".join(sections), skills_used, github_used, github_index, drive_used, drive_index


def orchestrate_chat(
    *,
    message: str,
    skill_ids: List[str],
    skill_position: str,
    session_id: str,
    github_repos: List[str],
    drive_file_ids: List[str],
    file_blocks: List[Tuple[str, str]],
    attach_warnings: List[str],
) -> OrchestratedChat:
    """Plan and assemble a full chat turn."""
    llm_message, skills_used, github_used, github_index, drive_used, drive_index = (
        assemble_orchestrated_message(
            message=message,
            skill_ids=skill_ids,
            skill_position=skill_position,
            session_id=session_id,
            github_repos=github_repos,
            drive_file_ids=drive_file_ids,
            file_blocks=file_blocks,
        )
    )

    file_names = [n for n, _ in file_blocks]
    use_tools = _wants_tools(message)
    engine_source = ""
    cost_plan_ok = False

    # Option A: InferenceAtlas-v1 engine for cost questions (deterministic numbers)
    if is_cost_question(message):
        roles = AttachmentRoles(
            skills=[s["slash_trigger"] for s in skills_used],
            github=list(github_used),
            drive=list(drive_used),
            uploads=file_names,
        )
        cost = build_cost_plan(message, roles)
        if cost.engine_block:
            llm_message = f"{cost.engine_block}\n\n{llm_message}"
            engine_source = cost.source
            cost_plan_ok = cost.ok
            use_tools = False

    # Pure access-review with only skills and no tool keywords → grounded
    if skills_used and not github_used and not drive_used and not file_names and not use_tools:
        use_tools = False
    elif _wants_tools(message) and not engine_source:
        use_tools = True

    has_attachments = bool(skills_used or github_used or drive_used or file_names)
    if not has_attachments and not engine_source:
        use_tools = True

    thinking = build_thinking_steps(
        message=message,
        skills_used=skills_used,
        github_used=github_used,
        github_index=github_index,
        drive_index=drive_index,
        file_names=file_names,
        use_tools=use_tools,
        attach_warnings=attach_warnings,
    )
    if engine_source == "inferenceatlas-v1":
        thinking.insert(
            1,
            f"InferenceAtlas-v1 plan_llm returned {len(cost.plans) if cost_plan_ok else 0} ranked plans — numbers locked",
        )
    elif engine_source == "catalog_fallback":
        thinking.insert(
            1,
            "InferenceAtlas-v1 unreachable — using deterministic catalog fallback (start v1 API for full rank_configs)",
        )
    elif not has_attachments:
        thinking.insert(
            1,
            "No skills, GitHub, Drive, or uploads attached — using InferenceAtlas catalog tools",
        )

    manifest = build_context_manifest(
        skills_used=skills_used,
        github_used=github_used,
        github_index=github_index,
        drive_used=drive_used,
        drive_index=drive_index,
        file_names=file_names,
        use_tools=use_tools,
    )
    if engine_source:
        label = (
            "InferenceAtlas-v1 engine"
            if engine_source == "inferenceatlas-v1"
            else "Catalog fallback engine"
        )
        manifest.append(label)

    user_display = message.strip()
    if not user_display and skills_used:
        user_display = f"[Skills: {', '.join(s['slash_trigger'] for s in skills_used)}]"
    if not user_display and github_used:
        user_display = f"[GitHub: {', '.join(github_used)}]"
    if not user_display and drive_used:
        user_display = f"[Drive: {', '.join(drive_used[:3])}]"
    if not user_display and file_names:
        user_display = f"[Uploads: {', '.join(file_names[:3])}]"

    if engine_source:
        system_prompt = V1_SLOT_FILLER_PROMPT
    elif use_tools:
        system_prompt = ORCHESTRATED_TOOLS_PROMPT
    else:
        system_prompt = ORCHESTRATED_GROUNDED_PROMPT

    return OrchestratedChat(
        user_message=message,
        llm_message=llm_message,
        user_display=user_display or message,
        skills_used=skills_used,
        github_used=github_used,
        github_index=github_index,
        drive_used=drive_used,
        drive_index=drive_index,
        file_names=file_names,
        attach_warnings=attach_warnings,
        use_tools=use_tools,
        thinking_steps=thinking,
        system_prompt=system_prompt,
        context_manifest=manifest,
        engine_source=engine_source,
        cost_plan_ok=cost_plan_ok,
    )


def format_reply_with_manifest(reply: str, manifest: List[str]) -> str:
    if not manifest:
        return reply
    header = "**Context used** — " + " · ".join(manifest)
    return f"{header}\n\n{reply}"
