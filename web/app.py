"""FastAPI server for the InferenceAtlas Intelligence Agent."""

import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import InferenceAtlasAgent
from agent.config import (
    COMPOSIO_API_KEY,
    COMPOSIO_DRY_RUN,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    TAVILY_API_KEY,
)
from agent.tools import get_catalog_summary

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="InferenceAtlas Agent", version="1.0.0")

_sessions: Dict[str, InferenceAtlasAgent] = {}
_lock = threading.Lock()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class ResetRequest(BaseModel):
    session_id: str


def _get_or_create_session(session_id: Optional[str]) -> Tuple[str, InferenceAtlasAgent]:
    with _lock:
        if session_id and session_id in _sessions:
            return session_id, _sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        agent = InferenceAtlasAgent()
        _sessions[new_id] = agent
        return new_id, agent


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": bool(LLM_API_KEY),
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "tavily": bool(TAVILY_API_KEY),
        "composio": bool(COMPOSIO_API_KEY),
        "composio_dry_run": COMPOSIO_DRY_RUN,
        "catalog": get_catalog_summary(),
    }


@app.get("/api/examples")
def examples() -> List[dict]:
    return [
        {
            "label": "Catalog overview",
            "message": "Use get_catalog_summary: what does InferenceAtlas track?",
        },
        {
            "label": "Mistral pricing",
            "message": (
                "Use tavily_search for Mistral Large pricing, then compare_providers "
                "for llm workloads in the catalog."
            ),
        },
        {
            "label": "GPT-4o alternative",
            "message": (
                "I run 500M tokens/month on GPT-4o input+output. Use compare_providers "
                "for llm and recommend the cheapest credible alternative."
            ),
        },
        {
            "label": "Tool access review",
            "message": (
                "Should our support triage agent get GitHub issues, Slack incident "
                "channels, and Jira ticket creation access?"
            ),
        },
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="No LLM API key configured. Set NEBIUS_API_KEY or OPENAI_API_KEY in .env",
        )

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id, agent = _get_or_create_session(body.session_id)

    try:
        reply = agent.chat(message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(reply=reply, session_id=session_id)


@app.post("/api/reset")
def reset(body: ResetRequest) -> dict:
    with _lock:
        agent = _sessions.pop(body.session_id, None)
    if agent:
        agent.reset()
    return {"ok": True, "session_id": body.session_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
