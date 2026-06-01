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
from typing import Generator

from openai import OpenAI

from .config import (
    AGENT_MAX_STEPS,
    NEBIUS_API_KEY,
    NEBIUS_BASE_URL,
    NEBIUS_MODEL,
    SYSTEM_PROMPT,
)
from .tools import TOOL_DISPATCH, TOOL_SCHEMAS

logger = logging.getLogger("inference_atlas.agent")


def _nebius_client() -> OpenAI:
    return OpenAI(api_key=NEBIUS_API_KEY, base_url=NEBIUS_BASE_URL)


# ---------------------------------------------------------------------------
# OpenClaw integration — primary path
# ---------------------------------------------------------------------------

def _run_with_openclaw(messages: list[dict], stream: bool = False):
    """Run the agent loop using the OpenClaw runtime."""
    try:
        import openclaw  # type: ignore

        runner = openclaw.AgentRunner(
            llm_client=_nebius_client(),
            model=NEBIUS_MODEL,
            tools=TOOL_SCHEMAS,
            tool_dispatch=TOOL_DISPATCH,
            system_prompt=SYSTEM_PROMPT,
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

def _run_builtin(messages: list[dict]) -> str:
    """
    Minimal tool-calling loop that replicates OpenClaw's behaviour.
    Runs until the model stops calling tools or max_steps is reached.
    """
    client = _nebius_client()
    history = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for step in range(AGENT_MAX_STEPS):
        response = client.chat.completions.create(
            model=NEBIUS_MODEL,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        history.append(msg.model_dump(exclude_unset=True))

        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            fn_name = call.function.name
            fn_args = json.loads(call.function.arguments or "{}")
            logger.info("Tool call [%s/%s]: %s(%s)", step + 1, AGENT_MAX_STEPS, fn_name, fn_args)

            fn = TOOL_DISPATCH.get(fn_name)
            result = fn(**fn_args) if fn else f"[unknown tool: {fn_name}]"

            history.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return "[agent] max steps reached without a final answer"


def _stream_builtin(messages: list[dict]) -> Generator[str, None, None]:
    """Streaming variant of the built-in loop — yields text chunks."""
    client = _nebius_client()
    history = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for step in range(AGENT_MAX_STEPS):
        response = client.chat.completions.create(
            model=NEBIUS_MODEL,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
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

        if finish_reason != "tool_calls" or not tool_calls_buf:
            return  # done

        # Reconstruct assistant message and tool results
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
            logger.info("Tool call [%s/%s]: %s(%s)", step + 1, AGENT_MAX_STEPS, fn_name, fn_args)
            fn = TOOL_DISPATCH.get(fn_name)
            result = fn(**fn_args) if fn else f"[unknown tool: {fn_name}]"
            history.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})


# ---------------------------------------------------------------------------
# Public interface — used by InferenceAtlasAgent
# ---------------------------------------------------------------------------

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
