"""Access-review path relevance scoring and stage-triggered fetch patterns."""

from __future__ import annotations

import re
from typing import Any

TEXT_EXTENSIONS = frozenset(
    {
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".csv",
        ".sql",
        ".sh",
        ".env.example",
    }
)

PRIORITY_FILENAMES = (
    "README.md",
    "readme.md",
    "README",
    "AGENTS.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
)

SKIP_PREFIXES = (
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    ".git/",
    "__pycache__/",
    ".venv/",
    "venv/",
)

SKIP_SUFFIXES = (".min.js", ".min.css", ".lock", ".png", ".jpg", ".gif", ".woff", ".woff2")

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("manifest", ("package.json", "pyproject.toml", "go.mod", "cargo.toml", "requirements.txt"), 95),
    ("readme", ("readme", "agents.md", "contributing"), 100),
    ("ci_cd", (".github/workflows", ".gitlab-ci", "jenkinsfile", "circleci"), 88),
    ("iac", ("terraform", "cloudformation", "kubernetes", "k8s", "helm", "pulumi"), 82),
    ("auth", ("auth", "permission", "rbac", "oauth", "scope", "acl", "iam"), 78),
    ("agent_tools", ("mcp", "composio", "agent", "tool", "skill", "prompt"), 72),
    ("config", (".env.example", "config.", "settings."), 55),
    ("docs", ("/docs/", "/doc/", "security", "policy"), 48),
)

STAGE_FETCH_PATTERNS: dict[str, list[str]] = {
    "packet_generated": [
        "permission",
        "scope",
        "auth",
        "github",
        "issue",
        "label",
        "workflow",
    ],
    "proof_attached": [
        "rollback",
        "workflow",
        "deploy",
        "ci",
        "environment",
        "off-switch",
        "boundary",
    ],
    "portkey_tested": [
        "guardrail",
        "gateway",
        "portkey",
        "spend",
        "budget",
        "model",
    ],
    "coach_stream": [
        "readme",
        "agent",
        "mcp",
        "permission",
    ],
}


def path_extension(path: str) -> str:
    dot = path.rfind(".")
    return path[dot:].lower() if dot > path.rfind("/") else ""


def categorize_path(path: str) -> str:
    lower = path.lower()
    for category, needles, _score in CATEGORY_RULES:
        if any(needle in lower for needle in needles):
            return category
    if any(lower.endswith(ext) for ext in TEXT_EXTENSIONS):
        return "source"
    return "other"


def score_path(path: str) -> int:
    lower = path.lower()
    if any(lower.startswith(prefix) for prefix in SKIP_PREFIXES):
        return -100
    if any(lower.endswith(suffix) for suffix in SKIP_SUFFIXES):
        return -50
    if path in PRIORITY_FILENAMES or lower.endswith("/readme.md") or lower == "agents.md":
        return 150
    score = 10
    depth = path.count("/")
    if depth <= 1:
        score += 25
    elif depth <= 3:
        score += 10
    else:
        score -= min(depth * 2, 20)
    for _category, needles, boost in CATEGORY_RULES:
        if any(needle in lower for needle in needles):
            score += boost
            break
    if any(lower.endswith(ext) for ext in TEXT_EXTENSIONS):
        score += 15
    return score


def pick_scored_paths(
    paths: list[str],
    *,
    limit: int,
    exclude: set[str] | None = None,
    min_score: int = 20,
) -> list[dict[str, Any]]:
    """Return top paths with score and category metadata."""
    excluded = exclude or set()
    ranked: list[dict[str, Any]] = []
    for path in paths:
        if path in excluded:
            continue
        score = score_path(path)
        if score < min_score:
            continue
        ranked.append(
            {
                "path": path,
                "score": score,
                "category": categorize_path(path),
                "extension": path_extension(path),
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["path"]))
    return ranked[:limit]


def patterns_for_stage(trigger: str, stage: str = "") -> list[str]:
    key = trigger or stage
    return list(STAGE_FETCH_PATTERNS.get(key, STAGE_FETCH_PATTERNS.get(stage, [])))


def path_matches_patterns(path: str, patterns: list[str]) -> bool:
    lower = path.lower()
    return any(re.search(re.escape(pat.lower()), lower) for pat in patterns if pat)
