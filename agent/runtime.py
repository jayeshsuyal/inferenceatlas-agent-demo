"""Runtime wrapper for the public InferenceAtlas agent demo."""

from __future__ import annotations

import json
from typing import Generator

from .config import AGENT_MAX_STEPS, NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL, SYSTEM_PROMPT
from .tools import TOOL_DISPATCH, TOOL_SCHEMAS, build_decision_packet


def _messages_text(messages: list[dict]) -> str:
    return "\n".join(str(message.get("content", "")) for message in messages)


def _local_fallback(messages: list[dict]) -> str:
    decision = _messages_text(messages).strip() or "Should this agent receive tool access?"
    return build_decision_packet(decision=decision, requested_tools=["GitHub", "Slack", "Jira"])


def _client():
    from openai import OpenAI

    return OpenAI(api_key=NEBIUS_API_KEY, base_url=NEBIUS_BASE_URL)


def run(messages: list[dict]) -> str:
    """Run the agent. Uses Nebius when configured; otherwise returns local packet output."""
    if not NEBIUS_API_KEY:
        return _local_fallback(messages)

    history = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    client = _client()

    for _step in range(AGENT_MAX_STEPS):
        response = client.chat.completions.create(
            model=NEBIUS_MODEL,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        history.append(msg.model_dump(exclude_unset=True))

        if not msg.tool_calls:
            return msg.content or _local_fallback(messages)

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            fn = TOOL_DISPATCH.get(name)
            result = fn(**args) if fn else f"[unknown tool: {name}]"
            history.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})

    return _local_fallback(messages)


def stream(messages: list[dict]) -> Generator[str, None, None]:
    """Simple streaming facade for CLI/demo use."""
    for line in run(messages).splitlines(keepends=True):
        yield line

