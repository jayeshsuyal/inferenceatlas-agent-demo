"""Load project .env before other agent modules read os.environ."""

from __future__ import annotations

from pathlib import Path
import os

_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv() -> None:
    if os.environ.get("IA_DISABLE_DOTENV", "").strip() in {"1", "true", "True"}:
        return
    env_path = _ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv as _load

        _load(env_path, override=True)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key:
                os.environ[key] = value.strip().strip("'\"")
