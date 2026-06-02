"""Stateful public demo agent."""

from __future__ import annotations

from typing import Generator

from . import runtime


class InferenceAtlasAgent:
    """Small public demo agent that creates reviewable DecisionPackets."""

    def __init__(self) -> None:
        self._history: list[dict] = []

    def run(self, user_message: str) -> str:
        return runtime.run([{"role": "user", "content": user_message}])

    def chat(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})
        response = runtime.run(self._history)
        self._history.append({"role": "assistant", "content": response})
        return response

    def stream(self, user_message: str) -> Generator[str, None, None]:
        yield from runtime.stream([{"role": "user", "content": user_message}])

    def stream_chat(self, user_message: str) -> Generator[str, None, None]:
        self._history.append({"role": "user", "content": user_message})
        chunks: list[str] = []
        for chunk in runtime.stream(self._history):
            chunks.append(chunk)
            yield chunk
        self._history.append({"role": "assistant", "content": "".join(chunks)})

    def reset(self) -> None:
        self._history = []

    @property
    def history(self) -> list[dict]:
        return list(self._history)

