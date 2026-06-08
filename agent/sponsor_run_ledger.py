"""Durable local ledger for agentic sponsor proof runs.

The ledger persists public proof-run records under ignored local state. It does
not approve, grant, write to external systems, call live providers, or mutate
the IA Packet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .scenarios import ROOT_DIR
from .sponsor_proof_trace import SPONSOR_ORDER


SPONSOR_PROOF_RUN_LEDGER_SCHEMA_VERSION = "sponsor_proof_run_ledger.v0"
SPONSOR_PROOF_RUN_RECORD_SCHEMA_VERSION = "sponsor_proof_run_record.v0"
DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR = ROOT_DIR / "state" / "sponsor_proof_runs"

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _public_dict(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_public_dict(item) for item in value]
    if isinstance(value, list):
        return [_public_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _public_dict(item) for key, item in value.items()}
    return value


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else path)


def _safe_run_id(run_id: str) -> str:
    if not run_id or not _RUN_ID_RE.match(run_id):
        raise ValueError("invalid sponsor proof run_id")
    return run_id


def _record_path(run_id: str, ledger_dir: Path) -> Path:
    return ledger_dir / f"{_safe_run_id(run_id)}.json"


def _step_summary(run: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "order": step["order"],
            "sponsor": step["sponsor"],
            "status": step["status"],
            "verb": step["verb"],
            "used_live_key": step["used_live_key"],
            "fallback_used": step["fallback_used"],
            "would_execute": step["would_execute"],
            "can_approve_access": step["can_approve_access"],
            "can_grant_permissions": step["can_grant_permissions"],
            "can_mutate_external_state": step["can_mutate_external_state"],
            "human_review_required": step["human_review_required"],
            "output_hash": step["output_hash"],
        }
        for step in run["collector_steps"]
    ]


def _fallback_flags(run: dict[str, Any]) -> dict[str, bool]:
    return {
        step["sponsor"]: bool(step["fallback_used"])
        for step in run["collector_steps"]
    }


def _live_key_flags(run: dict[str, Any]) -> dict[str, bool]:
    return {
        step["sponsor"]: bool(step["used_live_key"])
        for step in run["collector_steps"]
    }


def _output_artifacts(run: dict[str, Any], record_path: Path) -> dict[str, str]:
    surfaces = dict(run.get("source_surfaces", {}))
    surfaces.update(
        {
            "run_record_json": _relative(record_path),
            "packet_advisor_answer": "embedded:run.packet_advisor_answer",
            "portkey_preview": "embedded:run.downstream_previews.portkey_model_spend_gate",
            "safety_lock": "embedded:run.safety_boundary",
        }
    )
    return surfaces


def build_sponsor_proof_run_record(
    run: dict[str, Any],
    *,
    ledger_dir: Path = DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR,
) -> dict[str, Any]:
    """Build the durable record for one SponsorProofCollector run."""
    ledger_dir = ledger_dir.resolve()
    run_id = _safe_run_id(str(run["run_id"]))
    record_path = _record_path(run_id, ledger_dir)
    safety = run["safety_boundary"]
    invariants = run["invariants"]

    return {
        "schema_version": SPONSOR_PROOF_RUN_RECORD_SCHEMA_VERSION,
        "run_id": run_id,
        "record_path": _relative(record_path),
        "generated_at": run["generated_at"],
        "mode": run["mode"],
        "status": run["status"],
        "run_type": run["run_type"],
        "request": {
            "request_path": run["request_path"],
            "scenario_name": run["scenario_name"],
            "lane": run["lane"],
            "downstream_fixture": run["packet_advisor_answer"]["fixture"]["fixture_id"],
            "subscriber": run["packet_advisor_answer"]["subscriber"],
            "question": run["packet_advisor_answer"]["question"],
        },
        "packet_reference": run["packet_reference"],
        "trace_reference": run["trace_reference"],
        "sponsor_steps": _step_summary(run),
        "fallback_used": _fallback_flags(run),
        "live_key_used": _live_key_flags(run),
        "output_artifacts": _output_artifacts(run, record_path),
        "safety_lock": {
            "read_only": safety["read_only"],
            "live_calls_made": safety["live_calls_made"],
            "approves_access": safety["approves_access"],
            "grants_permissions": safety["grants_permissions"],
            "executes_external_writes": safety["executes_external_writes"],
            "mutates_production": safety["mutates_production"],
            "approves_spend": safety["approves_spend"],
            "selects_provider": safety["selects_provider"],
            "guarantees_savings": safety["guarantees_savings"],
            "requires_human_review": safety["requires_human_review"],
            "decision_lock_unchanged": invariants["decision_lock_unchanged"],
            "packet_mutation_allowed": invariants["packet_mutation_allowed"],
            "downstream_can_override_packet": invariants["downstream_can_override_packet"],
        },
        "invariants": invariants,
        "private_boundary": run["private_boundary"],
        "run": run,
    }


def sponsor_proof_run_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Return the list-safe record summary without duplicating the full run."""
    return {
        "schema_version": record["schema_version"],
        "run_id": record["run_id"],
        "record_path": record["record_path"],
        "generated_at": record["generated_at"],
        "mode": record["mode"],
        "status": record["status"],
        "run_type": record["run_type"],
        "request": record["request"],
        "packet_reference": record["packet_reference"],
        "trace_reference": record["trace_reference"],
        "sponsor_steps": record["sponsor_steps"],
        "fallback_used": record["fallback_used"],
        "live_key_used": record["live_key_used"],
        "output_artifacts": record["output_artifacts"],
        "safety_lock": record["safety_lock"],
        "invariants": record["invariants"],
        "private_boundary": record["private_boundary"],
    }


def write_sponsor_proof_run_record(
    run: dict[str, Any],
    *,
    ledger_dir: Path = DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR,
) -> dict[str, Any]:
    """Persist one run record and return it."""
    record = build_sponsor_proof_run_record(run, ledger_dir=ledger_dir)
    path = _record_path(record["run_id"], ledger_dir.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_public_dict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def load_sponsor_proof_run_record(
    run_id: str,
    *,
    ledger_dir: Path = DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR,
) -> dict[str, Any] | None:
    """Load one persisted run record by id."""
    path = _record_path(run_id, ledger_dir.resolve())
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sponsor_proof_run_records(
    *,
    ledger_dir: Path = DEFAULT_SPONSOR_PROOF_RUN_LEDGER_DIR,
) -> list[dict[str, Any]]:
    """Load all persisted run records newest-first by file mtime."""
    ledger_dir = ledger_dir.resolve()
    if not ledger_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(ledger_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if record.get("schema_version") == SPONSOR_PROOF_RUN_RECORD_SCHEMA_VERSION:
            records.append(record)
    return records


def build_sponsor_proof_run_ledger(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the read-only run ledger response."""
    summaries = [sponsor_proof_run_record_summary(record) for record in records]
    return {
        "schema_version": SPONSOR_PROOF_RUN_LEDGER_SCHEMA_VERSION,
        "mode": "local_durable_read_model",
        "read_only": True,
        "record_count": len(summaries),
        "sponsor_order": list(SPONSOR_ORDER),
        "runs": summaries,
        "safety_summary": {
            "all_read_only": all(item["safety_lock"]["read_only"] for item in summaries),
            "no_live_calls": all(not item["safety_lock"]["live_calls_made"] for item in summaries),
            "no_approvals": all(not item["safety_lock"]["approves_access"] for item in summaries),
            "no_grants": all(not item["safety_lock"]["grants_permissions"] for item in summaries),
            "no_external_writes": all(not item["safety_lock"]["executes_external_writes"] for item in summaries),
            "no_production_mutation": all(not item["safety_lock"]["mutates_production"] for item in summaries),
            "no_spend_approval": all(not item["safety_lock"]["approves_spend"] for item in summaries),
            "no_provider_selection": all(not item["safety_lock"]["selects_provider"] for item in summaries),
            "no_savings_guarantee": all(not item["safety_lock"]["guarantees_savings"] for item in summaries),
            "all_require_human_review": all(item["safety_lock"]["requires_human_review"] for item in summaries),
            "all_decision_locks_unchanged": all(
                item["safety_lock"]["decision_lock_unchanged"] for item in summaries
            ),
        },
        "private_boundary": {
            "private_source_exposed": False,
            "principle": "Private engine, public proof.",
        },
    }
