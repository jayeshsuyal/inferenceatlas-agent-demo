"""Web upload/download helpers — text files only, scoped under state/web_io/."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.scenarios import ROOT_DIR

WEB_IO_ROOT = ROOT_DIR / "state" / "web_io"
UPLOADS_DIR = WEB_IO_ROOT / "uploads"
OUTPUTS_DIR = WEB_IO_ROOT / "outputs"
BY_ID_DIR = WEB_IO_ROOT / "by_id"
MANIFEST_PATH = WEB_IO_ROOT / "manifest.json"

MAX_BYTES = 512_000
ALLOWED_SUFFIXES = frozenset(
    {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".log", ".xml", ".html", ".htm", ""}
)


def ensure_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    BY_ID_DIR.mkdir(parents=True, exist_ok=True)


def _load_manifest() -> Dict[str, Any]:
    ensure_dirs()
    if not MANIFEST_PATH.is_file():
        return {"files": {}}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}


def _save_manifest(data: Dict[str, Any]) -> None:
    ensure_dirs()
    MANIFEST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _safe_name(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]+", "_", base)
    return base[:120] or "file.txt"


def _normalize_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in ALLOWED_SUFFIXES:
        return suffix
    return ".txt"


def register_download(
    path: Path,
    *,
    label: str,
    mime: str = "text/plain; charset=utf-8",
) -> str:
    """Register an on-disk file for download by opaque id."""
    ensure_dirs()
    file_id = str(uuid.uuid4())
    data = _load_manifest()
    rel = path.resolve()
    if not rel.is_file():
        raise FileNotFoundError(path)
    data["files"][file_id] = {
        "path": str(rel),
        "label": label,
        "mime": mime,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    _save_manifest(data)
    return file_id


def resolve_download(file_id: str) -> Optional[Tuple[Path, str, str]]:
    """Return (path, label, mime) for a registered file."""
    entry = _load_manifest().get("files", {}).get(file_id)
    if not entry:
        return None
    path = Path(entry["path"])
    if not path.is_file():
        return None
    try:
        path.resolve().relative_to(WEB_IO_ROOT.resolve())
    except ValueError:
        try:
            path.resolve().relative_to(ROOT_DIR.resolve())
        except ValueError:
            return None
    return path, entry.get("label", path.name), entry.get("mime", "text/plain")


def save_upload(
    *,
    scope: str,
    filename: str,
    data: bytes,
) -> Tuple[str, str, str]:
    """Store upload; return (file_id, safe_name, text_preview)."""
    ensure_dirs()
    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large (max {MAX_BYTES // 1024} KB)")
    suffix = _normalize_suffix(filename)
    if suffix and suffix not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"Unsupported type {suffix}. Allowed: {', '.join(sorted(ALLOWED_SUFFIXES - {''}))}"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text files are supported") from exc

    file_id = str(uuid.uuid4())
    safe = _safe_name(filename)
    if not Path(safe).suffix:
        safe = f"{safe}.txt"
    folder = UPLOADS_DIR / scope
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{file_id}__{safe}"
    path.write_text(text, encoding="utf-8")
    preview = text[:400] + ("…" if len(text) > 400 else "")
    return file_id, safe, preview


def load_upload(scope: str, file_id: str) -> Optional[Tuple[str, str]]:
    """Return (filename, full_text) for a prior upload in scope."""
    folder = UPLOADS_DIR / scope
    if not folder.is_dir():
        return None
    for path in folder.glob(f"{file_id}__*"):
        name = path.name.split("__", 1)[-1] if "__" in path.name else path.name
        return name, path.read_text(encoding="utf-8")
    return None


def format_attachment_block(filename: str, text: str) -> str:
    return (
        f"\n\n--- Attached file: {filename} ---\n"
        f"{text.strip()}\n"
        f"--- End attachment ---"
    )


def save_output(
    *,
    scope: str,
    filename: str,
    content: str,
    subfolder: str = "",
    use_timestamp: bool = True,
) -> Path:
    ensure_dirs()
    safe = _safe_name(filename)
    folder = OUTPUTS_DIR / scope
    if subfolder:
        folder = folder / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    if use_timestamp:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = folder / f"{ts}_{safe}"
    else:
        path = folder / safe
    path.write_text(content, encoding="utf-8")
    return path


def save_output_registered(
    *,
    scope: str,
    filename: str,
    content: str,
    label: str,
    subfolder: str = "",
    use_timestamp: bool = False,
) -> dict:
    path = save_output(
        scope=scope,
        filename=filename,
        content=content,
        subfolder=subfolder,
        use_timestamp=use_timestamp,
    )
    file_id = register_download(path, label=label)
    return {"file_id": file_id, "label": label, "name": path.name}


def list_outputs(scope: str, subfolder: str = "") -> List[dict]:
    ensure_dirs()
    folder = OUTPUTS_DIR / scope
    if subfolder:
        folder = folder / subfolder
    if not folder.is_dir():
        return []
    items = []
    for path in sorted(folder.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        if not path.is_file():
            continue
        items.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    return items


def resolve_output_path(scope: str, name: str, subfolder: str = "") -> Optional[Path]:
    folder = OUTPUTS_DIR / scope
    if subfolder:
        folder = folder / subfolder
    if not folder.is_dir():
        return None
    safe = _safe_name(name)
    candidate = folder / safe
    if candidate.is_file():
        return candidate
    for path in folder.glob(f"*_{safe}"):
        if path.is_file():
            return path
    for path in folder.glob(f"*{safe}"):
        if path.is_file():
            return path
    return None
