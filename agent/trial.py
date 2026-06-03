"""Design-partner trial runner for public agent-access requests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .access_request import AccessRequest, ToolRequest
from .decision_brief import build_agent_access_decision_brief, brief_to_pretty_json
from .packet import build_decision_packet, packet_to_pretty_json
from .renderers import render_decision_brief_markdown, render_packet_markdown
from .scenarios import GENERATED_DIR, ROOT_DIR


TRIAL_REQUEST_SCHEMA_VERSION = "design_partner_trial_request.v0"
TRIAL_REPORT_SCHEMA_VERSION = "design_partner_trial_report.v0"
DEFAULT_TRIAL_REQUEST = ROOT_DIR / "examples" / "requests" / "support_triage_trial.yml"

PRIVATE_BOUNDARY_TERMS = (
    "ask_ia",
    "living_document",
    "advanced_workspace",
    "mcp_agent_tool_access",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_./+=-]{12,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}"),
)


class TrialRequestError(ValueError):
    """Raised when a public trial request cannot be parsed."""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise TrialRequestError(f"expected key/value line: {text}")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise TrialRequestError(f"missing key in line: {text}")
    return key, value.strip()


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _preprocess_folded_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.endswith(": >") or stripped.endswith(": |"):
            base_indent = _indent(line)
            key = stripped[:-2].strip()
            index += 1
            parts: list[str] = []
            while index < len(lines):
                child = lines[index]
                if child.strip() and _indent(child) <= base_indent:
                    break
                if child.strip():
                    parts.append(child.strip())
                index += 1
            output.append(f"{' ' * base_indent}{key} {' '.join(parts)}")
            continue
        output.append(line)
        index += 1
    return output


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    parsed = []
    for line in _preprocess_folded_blocks(text):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed.append((_indent(line), stripped))
    return parsed


def _looks_like_inline_dict_item(text: str) -> bool:
    return ":" in text and not text.startswith(("http://", "https://"))


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    if lines[index][0] < indent:
        return {}, index
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise TrialRequestError(f"unexpected indentation near: {text}")
        if text.startswith("- "):
            break

        key, value = _split_key_value(text)
        index += 1
        if value:
            data[key] = _parse_scalar(value)
            continue
        if index < len(lines) and lines[index][0] > current_indent:
            nested, index = _parse_block(lines, index, lines[index][0])
            data[key] = nested
        else:
            data[key] = {}
    return data, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent or not text.startswith("- "):
            break

        content = text[2:].strip()
        index += 1
        if not content:
            if index < len(lines) and lines[index][0] > current_indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
        elif _looks_like_inline_dict_item(content):
            key, value = _split_key_value(content)
            item = {key: _parse_scalar(value)} if value else {key: {}}
            if not value and index < len(lines) and lines[index][0] > current_indent:
                nested, index = _parse_block(lines, index, lines[index][0])
                item[key] = nested
            if index < len(lines) and lines[index][0] > current_indent:
                nested, index = _parse_dict(lines, index, lines[index][0])
                item.update(nested)
        else:
            item = _parse_scalar(content)
        items.append(item)
    return items, index


def parse_public_trial_yaml(text: str) -> dict[str, Any]:
    """Parse the small public YAML subset used by trial request files."""
    lines = _yaml_lines(text)
    payload, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise TrialRequestError(f"could not parse request near: {lines[index][1]}")
    if not isinstance(payload, dict):
        raise TrialRequestError("trial request must parse to a mapping")
    return payload


def load_trial_request(path: Path) -> dict[str, Any]:
    """Load a public trial request from disk."""
    return parse_public_trial_yaml(path.read_text(encoding="utf-8"))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value).strip().lower() == "true"


def _placeholder_warnings(value: Any, path: str = "request") -> list[str]:
    warnings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            warnings.extend(_placeholder_warnings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            warnings.extend(_placeholder_warnings(item, f"{path}[{index}]"))
    elif isinstance(value, str) and "replace_with_" in value:
        warnings.append(f"{path} still contains a template placeholder")
    return warnings


def _secret_scan_errors(text: str) -> list[str]:
    errors = []
    for term in PRIVATE_BOUNDARY_TERMS:
        if term in text:
            errors.append(f"private boundary term leaked: {term}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"possible secret matched pattern: {pattern.pattern}")
    return errors


def validate_trial_request(payload: dict[str, Any], *, source_text: str = "") -> dict[str, list[str]]:
    """Validate the public trial request safety contract."""
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("schema_version") != TRIAL_REQUEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {TRIAL_REQUEST_SCHEMA_VERSION}")

    for key in ("candidate_agent", "requested_access", "proof_debt", "reviewer_routing", "safety_defaults"):
        if key not in payload:
            errors.append(f"missing required section: {key}")

    candidate = _as_dict(payload.get("candidate_agent"))
    for key in ("name", "purpose", "requested_environment"):
        if not candidate.get(key):
            errors.append(f"candidate_agent.{key} is required")

    requested_access = _as_dict(payload.get("requested_access"))
    if not _as_list(requested_access.get("tools")):
        errors.append("requested_access.tools must include at least one tool")

    safety = _as_dict(payload.get("safety_defaults"))
    expected_safety = {
        "access_approval_granted": False,
        "permission_grant_allowed": False,
        "external_writes_enabled": False,
        "production_mutation_allowed": False,
        "packet_state_mutation_allowed": False,
        "composio_dry_run_default": True,
        "human_approval_required": True,
    }
    for key, expected in expected_safety.items():
        if _bool(safety.get(key)) is not expected:
            errors.append(f"safety_defaults.{key} must remain {expected}")

    warnings.extend(_placeholder_warnings(payload))
    errors.extend(_secret_scan_errors(source_text))
    return {"errors": errors, "warnings": warnings}


def _humanize_agent_name(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def _environment(payload: dict[str, Any]) -> str:
    requested_access = _as_dict(payload.get("requested_access"))
    candidate = _as_dict(payload.get("candidate_agent"))
    requested_environment = str(candidate.get("requested_environment", "")).lower()
    if _bool(requested_access.get("production_access_requested")) or "prod" in requested_environment:
        return "prod"
    if "stage" in requested_environment or "validation" in requested_environment:
        return "stage"
    return "dev"


def _raw_prompt(payload: dict[str, Any]) -> str:
    candidate = _as_dict(payload.get("candidate_agent"))
    requested_access = _as_dict(payload.get("requested_access"))
    tools = _as_list(requested_access.get("tools"))
    systems = [str(tool.get("system", "unknown system")) for tool in tools if isinstance(tool, dict)]
    actions = [
        action
        for tool in tools
        if isinstance(tool, dict)
        for action in _as_list(tool.get("requested_actions"))
    ]
    return (
        "Should this {agent} get {systems} access? It will {actions}. "
        "Requested environment: {environment}. Current approval path: {approval_path}."
    ).format(
        agent=_humanize_agent_name(str(candidate.get("name", "candidate agent"))),
        systems=", ".join(systems) if systems else "the requested tools",
        actions="; ".join(str(action) for action in actions) if actions else str(candidate.get("purpose", "perform the requested workflow")),
        environment=candidate.get("requested_environment", "unspecified"),
        approval_path=candidate.get("current_approval_path", "unspecified"),
    )


def trial_request_to_access_request(payload: dict[str, Any]) -> AccessRequest:
    """Convert a public trial request into the deterministic engine input."""
    candidate = _as_dict(payload.get("candidate_agent"))
    requested_access = _as_dict(payload.get("requested_access"))
    risk_scopes = []
    if _bool(requested_access.get("admin_scopes_requested")):
        risk_scopes.append("admin scope requested")
    if _bool(requested_access.get("production_access_requested")):
        risk_scopes.append("production access requested")
    if _bool(requested_access.get("external_writes_requested")):
        risk_scopes.append("external write requested")

    tools = []
    for tool in _as_list(requested_access.get("tools")):
        tool_data = _as_dict(tool)
        actions = tuple(str(action) for action in _as_list(tool_data.get("requested_actions")))
        scopes = tuple(str(item) for item in _as_list(tool_data.get("data_classes")) + risk_scopes)
        tools.append(
            ToolRequest(
                system=str(tool_data.get("system", "unknown system")),
                requested_actions=actions or ("unspecified requested action",),
                scopes=scopes or ("named allowlisted resources only",),
            )
        )

    data_classes = tuple(str(item) for item in _as_list(requested_access.get("data_classes")))
    return AccessRequest(
        agent_name=_humanize_agent_name(str(candidate.get("name", "candidate agent"))),
        purpose=str(candidate.get("purpose", "unspecified agent-access workflow")),
        environment=_environment(payload),  # type: ignore[arg-type]
        requested_tools=tuple(tools),
        data_classes=data_classes or ("role_level_data_class",),
        raw_prompt=_raw_prompt(payload),
    )


def _highest_risk(packet: dict[str, Any]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    risks = [item["risk_level"] for item in packet["requested_capability"]]
    return max(risks, key=lambda risk: order.get(risk, 1))


def _requested_risk_flags(payload: dict[str, Any]) -> dict[str, Any]:
    requested_access = _as_dict(payload.get("requested_access"))
    flags = {
        "production_access_requested": _bool(requested_access.get("production_access_requested")),
        "admin_scopes_requested": _bool(requested_access.get("admin_scopes_requested")),
        "external_writes_requested": _bool(requested_access.get("external_writes_requested")),
    }
    return {
        **flags,
        "risk_flags_present": [key for key, enabled in flags.items() if enabled],
    }


def _trial_speed_lane(packet: dict[str, Any], brief: dict[str, Any], requested_flags: dict[str, Any]) -> dict[str, Any]:
    highest_risk = _highest_risk(packet)
    validation_allowed = brief["go_no_go"]["scoped_validation_review"]
    if requested_flags["risk_flags_present"] or highest_risk == "critical" or not validation_allowed:
        lane = "blocked_fast"
        reason = "Admin, production, external-write, or critical access is blocked before validation."
        user_impact = "prevents_slow_unsafe_escalation"
    elif highest_risk == "low":
        lane = "fast_lane_scoped_validation"
        reason = "Low-risk read-only access can move to scoped validation after owner scope confirmation."
        user_impact = "accelerates_safe_validation"
    else:
        lane = "proof_routed_scoped_validation"
        reason = "Medium/high-risk access gets a scoped validation path while proof debt is routed to named owners."
        user_impact = "replaces_back_and_forth_with_owner_routing"
    return {
        "lane": lane,
        "decision_time": "immediate",
        "reason": reason,
        "user_impact": user_impact,
        "highest_risk": highest_risk,
        "safe_next_step": packet["decision"]["review_posture"],
        "production_access": False,
        "scoped_validation_review": validation_allowed and lane != "blocked_fast",
    }


def _reviewer_roles(payload: dict[str, Any]) -> dict[str, list[str]]:
    routing = _as_dict(payload.get("reviewer_routing"))
    return {
        "required": [str(item.get("role", "unknown reviewer")) for item in _as_list(routing.get("required_reviewers")) if isinstance(item, dict)],
        "conditional": [str(item.get("role", "unknown reviewer")) for item in _as_list(routing.get("conditional_reviewers")) if isinstance(item, dict)],
    }


def build_trial_bundle(request_path: Path) -> dict[str, Any]:
    """Build the trial report plus derived packet and brief."""
    source_text = request_path.read_text(encoding="utf-8")
    payload = parse_public_trial_yaml(source_text)
    validation = validate_trial_request(payload, source_text=source_text)
    access_request = trial_request_to_access_request(payload)
    packet = build_decision_packet(access_request)
    brief = build_agent_access_decision_brief(packet)
    requested_flags = _requested_risk_flags(payload)
    speed_lane = _trial_speed_lane(packet, brief, requested_flags)
    candidate = _as_dict(payload.get("candidate_agent"))
    proof_debt = _as_dict(payload.get("proof_debt"))
    safety = _as_dict(payload.get("safety_defaults"))

    report = {
        "schema_version": TRIAL_REPORT_SCHEMA_VERSION,
        "generated_by": "inferenceatlas-agent-demo",
        "mode": "offline_deterministic",
        "request_path": str(request_path.relative_to(ROOT_DIR) if request_path.is_relative_to(ROOT_DIR) else request_path),
        "request_schema_version": payload.get("schema_version"),
        "request_status": payload.get("status"),
        "request_readiness": "ready_for_scoped_trial" if not validation["errors"] and not validation["warnings"] else "needs_review",
        "validation": validation,
        "candidate_agent": {
            "name": candidate.get("name", "candidate agent"),
            "business_owner": candidate.get("business_owner", "unspecified"),
            "purpose": candidate.get("purpose", "unspecified"),
            "requested_environment": candidate.get("requested_environment", "unspecified"),
            "current_approval_path": candidate.get("current_approval_path", "unspecified"),
        },
        "requested_risk_flags": requested_flags,
        "access_speed_lane": speed_lane,
        "packet_summary": {
            "packet_id": packet["packet_id"],
            "verdict": packet["decision"]["verdict"],
            "review_posture": packet["decision"]["review_posture"],
            "approval_posture": packet["approval_posture"],
            "requested_systems": [item["system"] for item in packet["requested_capability"]],
            "missing_proof_count": len(packet["missing_proof"]),
            "blocked_claim_count": len(packet["blocked_claims"]),
        },
        "decision_brief_summary": {
            "brief_id": brief["brief_id"],
            "recommended_next_step": brief["decision"]["recommended_next_step"],
            "next_validation": brief["go_no_go"]["next_validation"],
            "scoped_validation_review": brief["go_no_go"]["scoped_validation_review"],
            "production_access": brief["go_no_go"]["production_access"],
        },
        "proof_debt": {
            "request_missing_proof": _as_list(proof_debt.get("missing_proof")),
            "request_unsupported_claims": _as_list(proof_debt.get("unsupported_claims")),
            "derived_missing_proof": packet["missing_proof"],
            "derived_blocked_claims": packet["blocked_claims"],
        },
        "reviewer_routing": {
            "request_roles": _reviewer_roles(payload),
            "derived_reviewer_owners": packet["reviewer_owners"],
            "derived_action_items": packet["reviewer_action_items"],
        },
        "safety": {
            "input_defaults": safety,
            "public_runner_approves_access": False,
            "public_runner_grants_permissions": False,
            "public_runner_executes_external_writes": False,
            "public_runner_mutates_production": False,
            "composio_dry_run_default": True,
            "requires_human_approval": True,
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
        "written_artifacts": [],
    }
    return {"report": report, "packet": packet, "brief": brief}


def build_trial_report(request_path: Path = DEFAULT_TRIAL_REQUEST) -> dict[str, Any]:
    """Build a machine-readable design-partner trial report."""
    return build_trial_bundle(request_path)["report"]


def _bullet(items: list[Any], *, empty: str = "- None") -> str:
    lines = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("item") or item.get("claim") or item.get("owner") or item.get("role") or "item"
            label = str(label).rstrip(".")
            detail = item.get("unblocks") or item.get("reason") or item.get("action") or item.get("review_area") or ""
            lines.append(f"- {label}" + (f": {detail}" if detail else ""))
        else:
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else empty


def render_trial_report_markdown(report: dict[str, Any]) -> str:
    """Render the design-partner trial report as Markdown."""
    lane = report["access_speed_lane"]
    safety = report["safety"]
    lines = [
        "# Design Partner Trial Report",
        "",
        "Private engine, public proof.",
        "",
        f"Request: `{report['request_path']}`",
        "",
        "## Verdict",
        "",
        f"- readiness: {report['request_readiness']}",
        f"- packet verdict: {report['packet_summary']['verdict']}",
        f"- recommended next step: {report['decision_brief_summary']['recommended_next_step']}",
        f"- production access: {report['decision_brief_summary']['production_access']}",
        f"- scoped validation review: {report['decision_brief_summary']['scoped_validation_review']}",
        "",
        "## Access Speed Lane",
        "",
        f"- lane: {lane['lane']}",
        f"- decision time: {lane['decision_time']}",
        f"- highest risk: {lane['highest_risk']}",
        f"- reason: {lane['reason']}",
        f"- safe next step: {lane['safe_next_step']}",
        "",
        "## Candidate Agent",
        "",
        f"- name: {report['candidate_agent']['name']}",
        f"- owner: {report['candidate_agent']['business_owner']}",
        f"- environment: {report['candidate_agent']['requested_environment']}",
        f"- current approval path: {report['candidate_agent']['current_approval_path']}",
        "",
        "## Requested Risk Flags",
        "",
        f"- production access requested: {report['requested_risk_flags']['production_access_requested']}",
        f"- admin scopes requested: {report['requested_risk_flags']['admin_scopes_requested']}",
        f"- external writes requested: {report['requested_risk_flags']['external_writes_requested']}",
        "",
        "## Proof Debt",
        "",
        _bullet(report["proof_debt"]["derived_missing_proof"]),
        "",
        "## Blocked Claims",
        "",
        _bullet(report["proof_debt"]["derived_blocked_claims"]),
        "",
        "## Reviewer Routing",
        "",
        _bullet(report["reviewer_routing"]["derived_action_items"]),
        "",
        "## Safety Boundary",
        "",
        f"- approves access: {safety['public_runner_approves_access']}",
        f"- grants permissions: {safety['public_runner_grants_permissions']}",
        f"- executes external writes: {safety['public_runner_executes_external_writes']}",
        f"- mutates production: {safety['public_runner_mutates_production']}",
        f"- Composio dry-run default: {safety['composio_dry_run_default']}",
        f"- requires human approval: {safety['requires_human_approval']}",
        "",
        "## Validation",
        "",
        "Errors:",
        "",
        _bullet(report["validation"]["errors"]),
        "",
        "Warnings:",
        "",
        _bullet(report["validation"]["warnings"]),
        "",
        "## Written Artifacts",
        "",
        _bullet([f"`{item}`" for item in report["written_artifacts"]]),
        "",
    ]
    return "\n".join(lines)


def trial_report_to_pretty_json(report: dict[str, Any]) -> str:
    """Render a trial report as stable JSON."""
    return json.dumps(report, indent=2, sort_keys=True)


def write_trial_artifacts(
    request_path: Path = DEFAULT_TRIAL_REQUEST,
    output_dir: Path = GENERATED_DIR,
) -> list[Path]:
    """Write the report, packet, and brief for one public trial request."""
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_trial_bundle(request_path)
    report = bundle["report"]
    packet = bundle["packet"]
    brief = bundle["brief"]
    stem = request_path.stem
    paths = [
        output_dir / f"{stem}_report.md",
        output_dir / f"{stem}_report.json",
        output_dir / f"{stem}.packet.md",
        output_dir / f"{stem}.packet.json",
        output_dir / f"{stem}.decision_brief.md",
        output_dir / f"{stem}.decision_brief.json",
    ]
    report["written_artifacts"] = [f"examples/generated/{path.name}" for path in paths]
    paths[0].write_text(render_trial_report_markdown(report), encoding="utf-8")
    paths[1].write_text(trial_report_to_pretty_json(report) + "\n", encoding="utf-8")
    paths[2].write_text(render_packet_markdown(packet), encoding="utf-8")
    paths[3].write_text(packet_to_pretty_json(packet) + "\n", encoding="utf-8")
    paths[4].write_text(render_decision_brief_markdown(brief), encoding="utf-8")
    paths[5].write_text(brief_to_pretty_json(brief) + "\n", encoding="utf-8")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent.trial",
        description="Run a public design-partner trial request through the offline access-review harness.",
    )
    parser.add_argument(
        "request_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TRIAL_REQUEST,
        help="Public trial request YAML file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the trial report as machine-readable JSON.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write report, packet, and brief artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help="Directory for generated trial artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request_path = args.request_path
    if not request_path.is_absolute():
        request_path = ROOT_DIR / request_path

    if args.write:
        paths = write_trial_artifacts(request_path, args.output_dir)
        if args.json:
            report = json.loads(paths[1].read_text(encoding="utf-8"))
            print(trial_report_to_pretty_json(report))
        else:
            for path in paths:
                print(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)
        report = json.loads(paths[1].read_text(encoding="utf-8"))
    else:
        report = build_trial_report(request_path)
        print(trial_report_to_pretty_json(report) if args.json else render_trial_report_markdown(report))

    return 1 if report["validation"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
