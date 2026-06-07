"""Unified chat orchestration: skills, GitHub, files, connectors, and tools together."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from .chat_answer import (
    ChatAnswer,
    build_access_review_answer,
    build_catalog_answer,
    build_pricing_answer,
    build_product_positioning_answer,
    build_spend_review_answer,
)
from .config import V1_SLOT_FILLER_PROMPT
from .cost_plan import AttachmentRoles, build_cost_plan, fetch_v1_copilot
from .github_repo import build_github_chat_context, get_repo_index_status
from .packet_advisor import (
    build_packet_advisor_answer,
    select_fixture_for_question,
    should_use_packet_advisor,
)
from .google_drive_files import build_drive_chat_context, get_drive_index_status
from .ui_skills import build_skill_context_for_chat, compose_message_with_skills
from .packet import build_support_triage_decision_packet
from .renderers import render_packet_markdown
from .tools import compare_providers, get_catalog_summary, tavily_search
from .workload_parse import is_access_review_question, is_cost_question

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
    direct_reply: str = ""
    direct_reply_source: str = ""
    direct_answer: dict[str, Any] = field(default_factory=dict)
    harness_injected: bool = False


def _message_snippet(message: str, max_len: int = 72) -> str:
    one = " ".join(message.split())
    if len(one) <= max_len:
        return one or "your request"
    return one[: max_len - 1] + "…"


def _normalized(message: str) -> str:
    return " ".join(message.lower().split())


def _is_spend_review_question(message: str) -> bool:
    normalized = _normalized(message)
    spend_terms = (
        "ai budget",
        "budget overrun",
        "spent the",
        "spent my",
        "spent our",
        "finance",
        "procurement",
        "usage cap",
        "cap usage",
        "vendor switch",
        "switch vendors",
        "renegotiate",
        "spend packet",
        "spend review",
    )
    if not any(term in normalized for term in spend_terms):
        return False
    optimizer_terms = (
        "compare_providers",
        "cheapest",
        "top 5",
        "pricing",
        "catalog",
    )
    return not any(term in normalized for term in optimizer_terms)


def _summarize_live_search_evidence(raw_search: str) -> str:
    """Keep demo replies readable while preserving Tavily as the evidence source."""
    if not raw_search.strip():
        return "Live search returned no readable evidence."
    if raw_search.startswith("[") or raw_search == "No results found.":
        return raw_search

    sources: List[str] = []
    for block in raw_search.split("\n\n---\n\n"):
        first_line = block.splitlines()[0].strip() if block.splitlines() else ""
        if first_line.startswith("**") and " — " in first_line:
            title, url = first_line.split(" — ", 1)
            sources.append(f"- {title.strip('*')} — {url.strip()}")
    if not sources:
        return "Live search found evidence, but the result text was too noisy to quote safely."
    return "\n".join(
        [
            "Live search evidence from Tavily:",
            *sources[:3],
            "",
            "Use the linked provider pricing page as the source of truth before any procurement decision.",
        ]
    )


def _direct_answer_tuple(answer: ChatAnswer, source: str) -> tuple[str, str, dict[str, Any]]:
    return answer.reply_markdown, source, answer.to_dict()


def _demo_direct_reply(message: str) -> tuple[str, str, dict[str, Any]]:
    """Deterministic replies for demo-critical questions where LLM improvisation hurts trust."""
    normalized = _normalized(message)
    if "use get_catalog_summary" in normalized:
        return _direct_answer_tuple(build_catalog_answer(get_catalog_summary()), "catalog_example")

    if "support triage agent" in normalized or "tool access review" in normalized:
        return _direct_answer_tuple(build_access_review_answer(message), "access_review_example")

    if _is_spend_review_question(message):
        return _direct_answer_tuple(build_spend_review_answer(), "spend_review")

    if "use tavily_search" in normalized and "mistral" in normalized:
        search = tavily_search("site:mistral.ai pricing Mistral Large API official", max_results=2)
        comparison = compare_providers("llm", top_n=5)
        body = "\n\n".join(
            [
                "### Live evidence",
                _summarize_live_search_evidence(search),
                "### Catalog comparison",
                comparison,
                "Composio remains dry-run; no external write was executed.",
            ]
        )
        return _direct_answer_tuple(
            build_pricing_answer(title="Mistral pricing live check", body=body),
            "pricing_example",
        )

    if (
        "i run 500m tokens/month" in normalized
        and "gpt-4o input+output" in normalized
        and "compare_providers" in normalized
    ):
        comparison = compare_providers("llm", top_n=5)
        body = "\n\n".join(
            [
                "Catalog comparison for `llm` workloads:",
                comparison,
            ]
        )
        return _direct_answer_tuple(
            build_pricing_answer(title="GPT-4o alternative", body=body),
            "pricing_example",
        )

    product_patterns = (
        "what else can u do",
        "what else can you do",
        "what can u do",
        "what can you do",
        "how are u better",
        "how are you better",
        "better than claude",
        "better than chatgpt",
        "why are u better",
        "why are you better",
    )
    if any(pattern in normalized for pattern in product_patterns):
        return _direct_answer_tuple(build_product_positioning_answer(), "product_positioning")

    return "", "", {}


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


def _shell_context_from_message(llm_message: str) -> str:
    """Extract attachment sections for v1 copilot (exclude USER QUESTION)."""
    marker = "--- USER QUESTION ---"
    if marker in llm_message:
        return llm_message.split(marker, 1)[0].strip()
    return llm_message.strip()


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
    current_fixture: str = "",
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
    direct_reply = ""
    direct_reply_source = ""
    direct_answer: dict[str, Any] = {}
    cost = None

    direct_reply, direct_reply_source, direct_answer = _demo_direct_reply(message)
    if direct_reply:
        use_tools = False
    elif should_use_packet_advisor(message, current_fixture=current_fixture):
        fixture = select_fixture_for_question(message, current_fixture)
        advisor_answer = build_packet_advisor_answer(fixture=fixture, question=message)
        direct_reply = advisor_answer["rendered_text"]
        direct_reply_source = "packet_advisor"
        direct_answer = advisor_answer
        use_tools = False

    # Option A: delegate cost questions to v1 E2E copilot when available
    if not direct_reply and is_cost_question(message):
        shell_context = _shell_context_from_message(llm_message)
        copilot_result = fetch_v1_copilot(message, shell_context)
        if copilot_result.ok and copilot_result.reply:
            direct_reply = copilot_result.reply
            direct_reply_source = "inferenceatlas-v1-copilot"
            direct_answer = {}
            engine_source = copilot_result.source
            cost_plan_ok = bool(copilot_result.plans)
            use_tools = False
        else:
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
    elif _wants_tools(message) and not engine_source and not direct_reply:
        use_tools = True

    harness_injected = False
    if direct_reply_source == "access_review_example":
        packet = build_support_triage_decision_packet(mode="live_review_room_demo")
        harness_block = render_packet_markdown(packet)
        llm_message = (
            "--- HARNESS FACTS (auto-injected DecisionPacket — authoritative for access review) ---\n\n"
            + harness_block
            + "\n\n"
            + llm_message
        )
        harness_injected = True
        use_tools = False
    elif (
        is_access_review_question(message)
        and not skills_used
        and not engine_source
        and not direct_reply
    ):
        packet = build_support_triage_decision_packet(message)
        harness_block = render_packet_markdown(packet)
        llm_message = (
            "--- HARNESS FACTS (auto-injected DecisionPacket — authoritative for access review) ---\n\n"
            + harness_block
            + "\n\n"
            + llm_message
        )
        harness_injected = True
        use_tools = False

    has_attachments = bool(skills_used or github_used or drive_used or file_names or harness_injected)
    if not has_attachments and not engine_source and not direct_reply:
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
    if direct_reply:
        if direct_reply_source == "inferenceatlas-v1-copilot":
            thinking.insert(
                1,
                f"InferenceAtlas-v1 copilot E2E — parse → rank → catalog → explain "
                f"({len(copilot_result.plans) if cost_plan_ok else 0} plans; demo LLM skipped)",
            )
        elif direct_reply_source == "product_positioning":
            thinking.insert(
                1,
                "Product positioning question detected — using deterministic IA control-layer answer",
            )
        elif direct_reply_source == "packet_advisor":
            thinking.insert(
                1,
                f"Packet Advisor selected — {direct_answer.get('fixture', {}).get('fixture_id', fixture)} "
                f"→ {direct_answer.get('answer_kind', 'decision')}",
            )
        elif direct_answer:
            thinking.insert(
                1,
                f"Structured ChatAnswer {direct_answer.get('schema_version', 'chat_answer.v0')} "
                f"selected — {direct_answer.get('answer_kind', direct_reply_source)}",
            )
        else:
            thinking.insert(
                1,
                "Known demo prompt detected — using deterministic tool output, demo LLM skipped",
            )
    elif engine_source == "inferenceatlas-v1":
        thinking.insert(
            1,
            f"InferenceAtlas-v1 plan_llm returned {len(cost.plans) if cost and cost_plan_ok else 0} ranked plans — numbers locked",
        )
    elif engine_source == "catalog_fallback":
        thinking.insert(
            1,
            "InferenceAtlas-v1 unreachable — using deterministic catalog fallback (start v1 API for full rank_configs)",
        )
    elif harness_injected:
        thinking.insert(
            1,
            "Access review detected — auto-injected support triage DecisionPacket (no Composio tool loop)",
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
        if engine_source == "inferenceatlas-v1-copilot":
            label = "InferenceAtlas-v1 copilot (E2E)"
        elif engine_source == "inferenceatlas-v1":
            label = "InferenceAtlas-v1 engine"
        else:
            label = "Catalog fallback engine"
        manifest.append(label)
    elif direct_reply_source == "product_positioning":
        manifest.append("InferenceAtlas product positioning")
    elif direct_reply_source == "spend_review":
        manifest.append("ChatAnswer: ai_spend_review")
    elif direct_reply_source == "packet_advisor":
        manifest.append("Packet Advisor: shared CLI/Ask IA answer")
    elif direct_reply_source in {"catalog_example", "pricing_example"}:
        manifest.append("Deterministic catalog example")
    elif direct_reply_source == "access_review_example":
        manifest.append("Deterministic access-review example")
    if harness_injected:
        manifest.append("Harness: auto-injected DecisionPacket")

    user_display = message.strip()
    if not user_display and skills_used:
        user_display = f"[Skills: {', '.join(s['slash_trigger'] for s in skills_used)}]"
    if not user_display and github_used:
        user_display = f"[GitHub: {', '.join(github_used)}]"
    if not user_display and drive_used:
        user_display = f"[Drive: {', '.join(drive_used[:3])}]"
    if not user_display and file_names:
        user_display = f"[Uploads: {', '.join(file_names[:3])}]"

    if direct_reply:
        system_prompt = ""
    elif engine_source:
        system_prompt = V1_SLOT_FILLER_PROMPT
    elif harness_injected or (skills_used and not use_tools):
        system_prompt = ORCHESTRATED_GROUNDED_PROMPT
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
        direct_reply=direct_reply,
        direct_reply_source=direct_reply_source,
        direct_answer=direct_answer,
        harness_injected=harness_injected,
    )


def format_reply_with_manifest(reply: str, manifest: List[str]) -> str:
    if not manifest:
        return reply
    header = "**Context used** — " + " · ".join(manifest)
    return f"{header}\n\n{reply}"
