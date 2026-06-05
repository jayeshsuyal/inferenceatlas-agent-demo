"""Google Drive file list, attach, and digest for chat (GitHub-style picker)."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .connector_oauth import get_google_access_token, refresh_google_access_token
from .connector_runtime import _now_iso, _raw_connection, load_session, save_session
from .scenarios import GENERATED_DIR, ROOT_DIR

MAX_DIGEST_CHARS = 48_000
MAX_BINARY_BYTES = 2_000_000
TEXT_EXTENSIONS = frozenset(
    {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".html", ".htm", ".log", ".xml"}
)

GOOGLE_EXPORT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

KIND_QUERIES = {
    "all": "trashed = false and mimeType != 'application/vnd.google-apps.folder'",
    "docs": (
        "trashed = false and ("
        "mimeType = 'application/vnd.google-apps.document' or "
        "mimeType = 'application/vnd.google-apps.spreadsheet' or "
        "mimeType = 'application/vnd.google-apps.presentation' or "
        "mimeType contains 'text/' or mimeType = 'application/pdf' or "
        "mimeType = 'application/json' or mimeType = 'text/csv')"
    ),
    "images": "trashed = false and mimeType contains 'image/'",
    "video": "trashed = false and mimeType contains 'video/'",
}


def _drive_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "User-Agent": "InferenceAtlas-Agent-Demo"}


def _drive_get(token: str, path: str, *, accept: Optional[str] = None) -> Any:
    headers = _drive_headers(token)
    if accept:
        headers["Accept"] = accept
    url = f"https://www.googleapis.com/drive/v3{path}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if accept and "text" in accept:
                return raw.decode("utf-8", errors="replace")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Drive API {exc.code}: {detail[:400]}") from exc


def _drive_get_session(session_id: str, path: str, *, accept: Optional[str] = None) -> Any:
    """Drive API GET with automatic token refresh on 401."""
    token = get_google_access_token(session_id)
    try:
        return _drive_get(token, path, accept=accept)
    except RuntimeError as exc:
        if "401" not in str(exc):
            raise
        if refresh_google_access_token(session_id):
            token = get_google_access_token(session_id, force_refresh=False)
            return _drive_get(token, path, accept=accept)
        raise RuntimeError(
            "Google Drive session expired (invalid credentials). "
            "Disconnect Google Drive in Connectors, then Sign in again."
        ) from exc


def _drive_download_bytes(session_id: str, token: str, file_id: str) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    req = urllib.request.Request(url, headers=_drive_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        if refresh_google_access_token(session_id):
            token = get_google_access_token(session_id)
            req = urllib.request.Request(url, headers=_drive_headers(token))
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read()
        raise RuntimeError(
            "Google Drive session expired. Disconnect and Sign in again."
        ) from exc


def _attached_files(session_id: str) -> Dict[str, dict]:
    data = load_session(session_id)
    return data.get("drive_attached", {}) or {}


def _demo_files(kind: str = "all") -> List[dict[str, Any]]:
    brief = GENERATED_DIR / "support_triage_agent.decision_brief.md"
    trial = ROOT_DIR / "examples" / "requests" / "support_triage_trial.yml"
    items = [
        {
            "id": "demo-drive-brief",
            "name": "support_triage_agent.decision_brief.md",
            "mimeType": "text/markdown",
            "modifiedTime": "",
            "size": str(brief.stat().st_size if brief.is_file() else 0),
            "indexed": False,
            "media_kind": "docs",
        },
        {
            "id": "demo-drive-trial",
            "name": "support_triage_trial.yml",
            "mimeType": "application/x-yaml",
            "modifiedTime": "",
            "size": str(trial.stat().st_size if trial.is_file() else 0),
            "indexed": False,
            "media_kind": "docs",
        },
        {
            "id": "demo-drive-screenshot",
            "name": "architecture_diagram.png",
            "mimeType": "image/png",
            "modifiedTime": "",
            "size": "245000",
            "indexed": False,
            "media_kind": "images",
        },
        {
            "id": "demo-drive-walkthrough",
            "name": "access_review_walkthrough.mp4",
            "mimeType": "video/mp4",
            "modifiedTime": "",
            "size": "12000000",
            "indexed": False,
            "media_kind": "video",
        },
    ]
    if kind == "all":
        return items
    return [i for i in items if i.get("media_kind") == kind or kind == "docs" and i["media_kind"] == "docs"]


def _media_kind(mime: str) -> str:
    if mime.startswith("image/"):
        return "images"
    if mime.startswith("video/"):
        return "video"
    return "docs"


def list_drive_files(
    session_id: str,
    *,
    query: str = "",
    kind: str = "all",
    page_size: int = 40,
) -> dict[str, Any]:
    """List Drive files for the signed-in user (searchable, filterable)."""
    conn = _raw_connection(session_id, "google_drive")
    if conn.get("status") != "connected":
        return {"ok": False, "message": "Sign in to Google Drive first.", "files": []}

    attached = _attached_files(session_id)
    kind = kind if kind in KIND_QUERIES else "all"
    q = query.strip().replace("'", "\\'")

    if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
        files = _demo_files(kind)
        if q:
            files = [f for f in files if q.lower() in f["name"].lower()]
        for f in files:
            f["indexed"] = f["id"] in attached
        return {"ok": True, "files": files, "demo": True, "kind": kind}

    drive_q = KIND_QUERIES[kind]
    if q:
        drive_q += f" and name contains '{q}'"

    params = urllib.parse.urlencode(
        {
            "pageSize": min(page_size, 100),
            "fields": "files(id,name,mimeType,modifiedTime,size,thumbnailLink,webViewLink)",
            "orderBy": "modifiedTime desc",
            "q": drive_q,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
    )
    data = _drive_get_session(session_id, f"/files?{params}")
    files: List[dict[str, Any]] = []
    for item in data.get("files", []):
        fid = item.get("id", "")
        if not fid:
            continue
        mime = item.get("mimeType", "")
        files.append(
            {
                "id": fid,
                "name": item.get("name", ""),
                "mimeType": mime,
                "modifiedTime": item.get("modifiedTime", ""),
                "size": item.get("size", ""),
                "thumbnailLink": item.get("thumbnailLink", ""),
                "webViewLink": item.get("webViewLink", ""),
                "media_kind": _media_kind(mime),
                "indexed": fid in attached,
            }
        )
    return {"ok": True, "files": files, "demo": False, "kind": kind}


def _fetch_file_meta(session_id: str, file_id: str) -> dict:
    params = urllib.parse.urlencode(
        {"fields": "id,name,mimeType,size,modifiedTime,webViewLink,thumbnailLink"}
    )
    return _drive_get_session(session_id, f"/files/{file_id}?{params}")


def _extract_text_content(session_id: str, token: str, file_id: str, meta: dict) -> Tuple[str, str]:
    """Return (content_type, text body) for digest."""
    mime = meta.get("mimeType", "")
    name = meta.get("name", file_id)

    if mime in GOOGLE_EXPORT_MIME:
        export_mime = GOOGLE_EXPORT_MIME[mime]
        params = urllib.parse.urlencode({"mimeType": export_mime})
        text = _drive_get_session(
            session_id,
            f"/files/{file_id}/export?{params}",
            accept="text/plain",
        )
        return "google_export", str(text)[:MAX_DIGEST_CHARS]

    if mime.startswith("image/"):
        size = int(meta.get("size") or 0)
        preview = ""
        if size and size < 800_000:
            try:
                raw = _drive_download_bytes(session_id, token, file_id)
                preview = base64.b64encode(raw[:120_000]).decode("ascii")
            except Exception:
                preview = ""
        body = (
            f"[Image file: {name}]\n"
            f"MIME: {mime}\n"
            f"Size: {size} bytes\n"
            f"View: {meta.get('webViewLink', '')}\n"
        )
        if preview:
            body += (
                f"\n(Base64 preview truncated for LLM context — first {len(preview)} chars of encoded data)\n"
                f"data:{mime};base64,{preview[:8000]}…\n"
            )
        else:
            body += "\n(Image too large or not downloaded — use metadata and link only.)\n"
        return "image", body

    if mime.startswith("video/"):
        return "video", (
            f"[Video file: {name}]\n"
            f"MIME: {mime}\n"
            f"Size: {meta.get('size', 'unknown')} bytes\n"
            f"View: {meta.get('webViewLink', '')}\n"
            f"Note: Full video bytes are not inlined. Reference title and link for access-review evidence.\n"
        )

    if mime == "application/pdf":
        return "pdf", (
            f"[PDF: {name}]\n"
            f"Size: {meta.get('size', '')} bytes\n"
            f"View: {meta.get('webViewLink', '')}\n"
            f"Note: PDF text extraction not run in this demo — cite filename and link.\n"
        )

    # Binary / text download
    try:
        raw = _drive_download_bytes(session_id, token, file_id)
    except Exception as exc:
        return "error", f"[Could not download {name}: {exc}]"

    if len(raw) > MAX_BINARY_BYTES:
        return "binary_large", (
            f"[File: {name}]\nMIME: {mime}\nSize: {len(raw)} bytes (too large to inline fully).\n"
        )

    lower = name.lower()
    if mime.startswith("text/") or any(lower.endswith(ext) for ext in TEXT_EXTENSIONS):
        return "text", raw.decode("utf-8", errors="replace")[:MAX_DIGEST_CHARS]

    return "binary", (
        f"[File: {name}]\nMIME: {mime}\nSize: {len(raw)} bytes\n"
        f"(Non-text binary — not fully decoded in digest.)\n"
    )


def _demo_digest(file_id: str, name: str) -> str:
    if file_id == "demo-drive-brief":
        p = GENERATED_DIR / "support_triage_agent.decision_brief.md"
        return p.read_text(encoding="utf-8")[:MAX_DIGEST_CHARS] if p.is_file() else ""
    if file_id == "demo-drive-trial":
        p = ROOT_DIR / "examples" / "requests" / "support_triage_trial.yml"
        return p.read_text(encoding="utf-8")[:MAX_DIGEST_CHARS] if p.is_file() else ""
    if file_id == "demo-drive-screenshot":
        return (
            "# Drive image (demo)\nArchitecture diagram placeholder for access-review evidence.\n"
            "MIME: image/png — use for proof of UI capture in triage workflows.\n"
        )
    if file_id == "demo-drive-walkthrough":
        return (
            "# Drive video (demo)\naccess_review_walkthrough.mp4 — screen recording metadata.\n"
            "Transcript not available in demo; cite filename for human reviewers.\n"
        )
    return f"# Demo Drive file: {name}\n"


def build_file_digest(session_id: str, file_id: str) -> Tuple[str, dict[str, Any]]:
    conn = _raw_connection(session_id, "google_drive")
    if conn.get("status") != "connected":
        raise RuntimeError("Sign in to Google Drive first.")

    if conn.get("mode") in ("demo_session", "demo_oauth") or not conn.get("access_token"):
        demo = next((f for f in _demo_files("all") if f["id"] == file_id), None)
        name = demo["name"] if demo else file_id
        text = _demo_digest(file_id, name)
        meta = {"id": file_id, "name": name, "mimeType": demo.get("mimeType", "") if demo else "", "content_type": "demo"}
        return text, meta

    token = get_google_access_token(session_id)
    meta = _fetch_file_meta(session_id, file_id)
    content_type, body = _extract_text_content(session_id, token, file_id, meta)
    header = (
        f"# Google Drive file: {meta.get('name', file_id)}\n"
        f"MIME: {meta.get('mimeType', '')}\n"
        f"Modified: {meta.get('modifiedTime', '')}\n"
        f"Link: {meta.get('webViewLink', '')}\n\n"
    )
    digest = (header + body)[:MAX_DIGEST_CHARS]
    meta["content_type"] = content_type
    meta["digest_chars"] = len(digest)
    return digest, meta


def _digest_index_meta(digest: str, entry: dict) -> dict[str, Any]:
    return {
        "file_id": entry.get("file_id", ""),
        "name": entry.get("name", ""),
        "mimeType": entry.get("mimeType", ""),
        "media_kind": entry.get("media_kind", "docs"),
        "indexed": bool(digest) and len(digest) > 80,
        "digest_chars": len(digest),
        "content_type": entry.get("content_type", ""),
    }


def attach_drive_file(session_id: str, file_id: str) -> dict[str, Any]:
    from .session_metrics import record_connector_index

    conn = _raw_connection(session_id, "google_drive")
    if conn.get("status") != "connected":
        return {"ok": False, "message": "Sign in to Google Drive first."}

    try:
        digest, meta = build_file_digest(session_id, file_id)
    except Exception as exc:
        return {"ok": False, "message": str(exc)}

    name = meta.get("name", file_id)
    media_kind = _media_kind(meta.get("mimeType", ""))

    data = load_session(session_id)
    attached = data.setdefault("drive_attached", {})
    attached[file_id] = {
        "file_id": file_id,
        "name": name,
        "mimeType": meta.get("mimeType", ""),
        "media_kind": media_kind,
        "content_type": meta.get("content_type", ""),
        "attached_at": _now_iso(),
        "preview": digest[:400].replace("\n", " "),
        "digest": digest,
    }
    index_meta = _digest_index_meta(digest, attached[file_id])
    attached[file_id].update(index_meta)
    save_session(session_id, data)
    record_connector_index("google_drive", session_id)

    return {
        "ok": True,
        "file_id": file_id,
        "name": name,
        "mimeType": meta.get("mimeType", ""),
        "media_kind": media_kind,
        "indexed": index_meta["indexed"],
        "digest_chars": len(digest),
        "content_type": meta.get("content_type", ""),
        "preview": digest[:500],
        "message": (
            f"Indexed Drive file «{name}»: {len(digest):,} chars"
            f" ({media_kind}, {meta.get('content_type', 'text')})"
        ),
    }


def get_drive_index_status(session_id: str, file_id: str) -> dict[str, Any]:
    entry = _attached_files(session_id).get(file_id, {})
    digest = entry.get("digest", "")
    meta = _digest_index_meta(digest, entry)
    meta["attached_at"] = entry.get("attached_at", "")
    meta["preview"] = entry.get("preview", "")[:200]
    return meta


def build_drive_chat_context(session_id: str, file_ids: List[str]) -> Tuple[str, List[str]]:
    used: List[str] = []
    blocks: List[str] = []
    attached = _attached_files(session_id)

    for fid in file_ids[:5]:
        fid = fid.strip()
        if not fid:
            continue
        entry = attached.get(fid)
        if entry and entry.get("digest"):
            digest = entry["digest"]
            label = entry.get("name", fid)
        else:
            result = attach_drive_file(session_id, fid)
            if not result.get("ok"):
                continue
            entry = _attached_files(session_id).get(fid, {})
            digest = entry.get("digest", "")
            label = entry.get("name", fid)
        if digest:
            blocks.append(f"--- GOOGLE DRIVE: {label} ({fid}) ---\n\n{digest}\n")
            used.append(label)

    if not blocks:
        return "", []

    intro = (
        "The user attached Google Drive file context below (docs, sheets, images, or video metadata). "
        "Cite file names and excerpted content. Do not claim you cannot access Drive.\n\n"
    )
    return intro + "\n".join(blocks), used
