"""
OpenClaw runtime integration layer.

OpenClaw is the agent execution runtime — it owns the tool-calling loop,
step limits, message history, and streaming. This module wraps OpenClaw's
interface around the Nebius LLM client and the InferenceAtlas tool set.

If OpenClaw is installed (`pip install openclaw`), it is used directly.
Otherwise we fall back to the built-in agentic loop so the agent is always
runnable during development / without the package.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Generator

from .config import (
    AGENT_MAX_STEPS,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    SKILL_ASSIST_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from .github_repo import GITHUB_CONTEXT_SYSTEM_PROMPT
from .session_metrics import record_demo_llm_usage
from .tools import TOOL_DISPATCH, TOOL_SCHEMAS

logger = logging.getLogger("inference_atlas.agent")


def _track_llm_response(response: Any, *, label: str) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        record_demo_llm_usage(label=label)
        return
    record_demo_llm_usage(
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
        label=label,
    )


def _last_assistant_text(history: list[dict]) -> str:
    for msg in reversed(history):
        if msg.get("role") == "assistant" and msg.get("content"):
            return str(msg["content"])
    return ""


def _summarize_tool_results(tool_results: list[tuple[str, str]]) -> str:
    """Return a useful answer if a tool-calling model never emits final text."""
    if not tool_results:
        return ""

    unique_results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for tool_name, result in tool_results:
        key = (tool_name, result)
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(key)

    lines = [
        "Live tools returned verified output. I am showing the tool result directly "
        "because the model did not produce a final synthesis before the safety limit."
    ]
    for tool_name, result in unique_results[-4:]:
        text = str(result).strip()
        if len(text) > 1200:
            text = text[:1200].rstrip() + "..."
        lines.extend(["", f"## {tool_name}", text or "(empty result)"])
    return "\n".join(lines)


def _llm_client() -> Any:
    if not LLM_API_KEY:
        raise RuntimeError(
            "No LLM API key configured. Set NEBIUS_API_KEY or OPENAI_API_KEY in .env"
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package not installed. Run: pip install -r agent/requirements.txt"
        ) from exc
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


# ---------------------------------------------------------------------------
# OpenClaw integration — primary path
# ---------------------------------------------------------------------------

def _run_with_openclaw(
    messages: list[dict],
    stream: bool = False,
    *,
    system_prompt: str = SYSTEM_PROMPT,
):
    """Run the agent loop using the OpenClaw runtime."""
    try:
        import openclaw  # type: ignore

        runner = openclaw.AgentRunner(
            llm_client=_llm_client(),
            model=LLM_MODEL,
            tools=TOOL_SCHEMAS,
            tool_dispatch=TOOL_DISPATCH,
            system_prompt=system_prompt,
            max_steps=AGENT_MAX_STEPS,
        )
        if stream:
            return runner.stream(messages)
        return runner.run(messages)
    except ModuleNotFoundError:
        logger.debug("openclaw not installed — using built-in fallback loop")
        return None


# ---------------------------------------------------------------------------
# Built-in fallback loop (mirrors OpenClaw's interface)
# ---------------------------------------------------------------------------

def _run_builtin(messages: list[dict], *, system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Minimal tool-calling loop that replicates OpenClaw's behaviour.
    Runs until the model stops calling tools or max_steps is reached.
    """
    client = _llm_client()
    history = [{"role": "system", "content": system_prompt}] + messages
    tool_results: list[tuple[str, str]] = []
    seen_tool_calls: set[tuple[str, str]] = set()

    for step in range(AGENT_MAX_STEPS):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            parallel_tool_calls=False,
        )
        _track_llm_response(response, label="builtin_tool_loop")
        msg = response.choices[0].message
        history.append(msg.model_dump(exclude_unset=True))

        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            fn_name = call.function.name
            fn_args = json.loads(call.function.arguments or "{}")
            signature = (fn_name, json.dumps(fn_args, sort_keys=True))
            if signature in seen_tool_calls and tool_results:
                return _summarize_tool_results(tool_results)
            seen_tool_calls.add(signature)
            logger.info("Tool call [%s/%s]: %s(%s)", step + 1, AGENT_MAX_STEPS, fn_name, fn_args)

            fn = TOOL_DISPATCH.get(fn_name)
            result = fn(**fn_args) if fn else f"[unknown tool: {fn_name}]"
            tool_results.append((fn_name, str(result)))

            history.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    last = _last_assistant_text(history)
    return last or _summarize_tool_results(tool_results) or "[agent] max steps reached without a final answer"


def _stream_builtin(messages: list[dict]) -> Generator[str, None, None]:
    """Streaming variant of the built-in loop — yields text chunks."""
    client = _llm_client()
    history = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    tool_results: list[tuple[str, str]] = []
    seen_tool_calls: set[tuple[str, str]] = set()

    for step in range(AGENT_MAX_STEPS):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            parallel_tool_calls=False,
            stream=True,
        )

        # Collect the streamed response
        tool_calls_buf: dict[int, dict] = {}
        content_buf = ""
        finish_reason = None

        for chunk in response:
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            if delta.content:
                content_buf += delta.content
                yield delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buf:
                        tool_calls_buf[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_buf[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_buf[idx]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_buf[idx]["arguments"] += tc.function.arguments

        if not tool_calls_buf:
            return  # final answer streamed (or empty)

        # Execute tool calls, then loop for the model's follow-up response
        tool_calls_list = []
        for idx in sorted(tool_calls_buf):
            tc = tool_calls_buf[idx]
            tool_calls_list.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            })

        history.append({"role": "assistant", "content": content_buf or None, "tool_calls": tool_calls_list})

        for tc in tool_calls_list:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"] or "{}")
            signature = (fn_name, json.dumps(fn_args, sort_keys=True))
            if signature in seen_tool_calls and tool_results:
                fallback = _summarize_tool_results(tool_results)
                if fallback:
                    yield fallback
                return
            seen_tool_calls.add(signature)
            logger.info("Tool call [%s/%s]: %s(%s)", step + 1, AGENT_MAX_STEPS, fn_name, fn_args)
            fn = TOOL_DISPATCH.get(fn_name)
            result = fn(**fn_args) if fn else f"[unknown tool: {fn_name}]"
            tool_results.append((fn_name, str(result)))
            history.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})

    fallback = _summarize_tool_results(tool_results)
    if fallback:
        yield fallback


# ---------------------------------------------------------------------------
# Public interface — used by InferenceAtlasAgent
# ---------------------------------------------------------------------------

def run_skill_assist(messages: list[dict], *, system_prompt: str = SKILL_ASSIST_SYSTEM_PROMPT) -> str:
    """
    Single-shot LLM answer grounded in attached context — no tools.
    Avoids burning AGENT_MAX_STEPS when context is already in the message.
    """
    client = _llm_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.2,
    )
    _track_llm_response(response, label="skill_assist")
    return response.choices[0].message.content or ""


def run_github_context_assist(messages: list[dict]) -> str:
    return run_skill_assist(messages, system_prompt=GITHUB_CONTEXT_SYSTEM_PROMPT)


def run_orchestrated(
    messages: list[dict],
    *,
    system_prompt: str,
    use_tools: bool,
) -> str:
    """Single path for skills + GitHub + files: tools or grounded assist."""
    if use_tools:
        result = _run_with_openclaw(messages, stream=False, system_prompt=system_prompt)
        if result is not None:
            return result
        return _run_builtin(messages, system_prompt=system_prompt)
    return run_skill_assist(messages, system_prompt=system_prompt)


def run(messages: list[dict]) -> str:
    result = _run_with_openclaw(messages, stream=False)
    if result is not None:
        return result
    return _run_builtin(messages)


def stream(messages: list[dict]) -> Generator[str, None, None]:
    result = _run_with_openclaw(messages, stream=True)
    if result is not None:
        yield from result
        return
    yield from _stream_builtin(messages)
