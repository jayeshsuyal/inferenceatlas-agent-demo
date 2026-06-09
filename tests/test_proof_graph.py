"""ProofGraph schema-only contract tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from agent.proof_graph import (
    PACKET_ONLY_PROOF_FIELDS,
    PROOF_GRAPH_SCHEMA_VERSION,
    build_proof_graph_for_scenario,
)
from agent.scenarios import SCENARIOS
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "proof_graph.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_graph_boundary(graph: dict) -> None:
    assert graph["schema_version"] == PROOF_GRAPH_SCHEMA_VERSION
    assert re.fullmatch(r"ia-proof-graph-.+-[0-9a-f]{16}-public-v0", graph["graph_id"])
    assert re.fullmatch(r"pgr_[0-9a-f]{16}", graph["graph_revision_id"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", graph["content_hash"])
    assert graph["packet_reference"]["packet_id"] == graph["packet_node"]["packet_id"]
    assert graph["packet_reference"]["revision_id"] == graph["packet_node"]["revision_id"]
    assert graph["packet_reference"]["content_hash"] == graph["packet_node"]["content_hash"]
    assert graph["packet_node"]["node_type"] == "packet"
    assert graph["node_counts"] == {
        "packet": 1,
        "proof": len(PACKET_ONLY_PROOF_FIELDS),
        "edge": len(PACKET_ONLY_PROOF_FIELDS),
    }

    safety = graph["safety_boundary"]
    assert safety["approves_access"] is False
    assert safety["grants_permissions"] is False
    assert safety["executes_external_writes"] is False
    assert safety["mutates_packet"] is False
    assert safety["mutates_production"] is False
    assert safety["changes_verdict"] is False
    assert safety["requires_human_review"] is True

    invariants = graph["invariants"]
    assert invariants["packet_remains_authority"] is True
    assert invariants["graph_can_approve"] is False
    assert invariants["graph_can_mutate_packet"] is False
    assert invariants["graph_can_execute_external_write"] is False
    assert invariants["graph_can_change_verdict"] is False
    assert invariants["all_nodes_require_human_review"] is True
    assert invariants["all_nodes_non_mutating"] is True
    assert invariants["all_edges_non_mutating"] is True

    fields = {node["attached_packet_field"] for node in graph["proof_nodes"]}
    assert fields == set(PACKET_ONLY_PROOF_FIELDS)
    for node in graph["proof_nodes"]:
        assert node["node_type"] == "proof"
        assert node["provider"] == "ia_packet"
        assert node["mode"] == "deterministic_packet_authority"
        assert node["api_call_made"] is False
        assert node["fallback_used"] is False
        assert node["external_write_made"] is False
        assert node["can_change_packet_verdict"] is False
        assert node["human_review_required"] is True
        assert node["next_human_action"]

    packet_node_id = graph["packet_node"]["node_id"]
    proof_node_ids = {node["node_id"] for node in graph["proof_nodes"]}
    for edge in graph["proof_edges"]:
        assert edge["from_node_id"] in proof_node_ids
        assert edge["to_node_id"] == packet_node_id
        assert edge["human_review_required"] is True
        assert edge["can_change_packet_verdict"] is False

    assert graph["private_boundary"] == {
        "private_source_exposed": False,
        "principle": "Private engine, public proof.",
    }


def test_proof_graph_schema_file_locks_contract() -> None:
    schema = _load_schema()

    assert schema["properties"]["schema_version"]["const"] == PROOF_GRAPH_SCHEMA_VERSION
    assert "packet_node" in schema["required"]
    assert "proof_nodes" in schema["required"]
    assert "proof_edges" in schema["required"]
    assert schema["$defs"]["proof_node"]["properties"]["provider"]["enum"] == [
        "ia_packet",
        "tavily",
        "composio",
        "openclaw",
        "nebius",
        "portkey",
    ]
    assert schema["$defs"]["proof_node"]["properties"]["external_write_made"]["const"] is False
    assert schema["$defs"]["proof_node"]["properties"]["can_change_packet_verdict"]["const"] is False
    assert schema["$defs"]["proof_node"]["properties"]["human_review_required"]["const"] is True
    assert schema["$defs"]["invariants"]["properties"]["packet_remains_authority"]["const"] is True
    assert schema["$defs"]["invariants"]["properties"]["graph_can_change_verdict"]["const"] is False
    assert schema["$defs"]["safety_boundary"]["properties"]["executes_external_writes"]["const"] is False
    assert schema["$defs"]["private_boundary"]["properties"]["principle"]["const"] == (
        "Private engine, public proof."
    )


def test_packet_only_proof_graph_is_deterministic_and_packet_backed() -> None:
    first = build_proof_graph_for_scenario("support_triage_agent")
    second = build_proof_graph_for_scenario("support_triage_agent")

    assert first == second
    _assert_graph_boundary(first)
    assert first["scenario_name"] == "support_triage_agent"
    assert first["packet_reference"]["packet_id"] == "ia-agent-access-support-triage-v0"


def test_proof_graph_covers_public_access_scenarios_without_keys() -> None:
    expected_locks = {
        "support_triage_agent": "scoped_validation_only",
        "read_only_analytics_agent": "read_only_validation",
        "admin_code_fix_bot": "blocked",
    }
    for scenario_name in SCENARIOS:
        graph = build_proof_graph_for_scenario(scenario_name)

        _assert_graph_boundary(graph)
        assert graph["packet_node"]["decision_lock"] == expected_locks[scenario_name]
        assert graph["mode"] == "offline_deterministic"


def test_proof_graph_cli_is_machine_readable() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent.proof_graph", "admin_code_fix_bot", "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    _assert_graph_boundary(payload)
    assert payload["scenario_name"] == "admin_code_fix_bot"
    assert payload["packet_node"]["decision_lock"] == "blocked"


def test_proof_graph_schema_and_module_preserve_private_boundary() -> None:
    combined = "\n".join(
        [
            SCHEMA_PATH.read_text(encoding="utf-8"),
            (ROOT / "agent" / "proof_graph.py").read_text(encoding="utf-8"),
            json.dumps(build_proof_graph_for_scenario("support_triage_agent"), sort_keys=True),
        ]
    )

    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden not in combined


def test_pr_smoke_checks_proof_graph_schema_and_command() -> None:
    smoke_text = (ROOT / "scripts" / "pr_smoke.sh").read_text(encoding="utf-8")

    assert "schemas/proof_graph.schema.json" in smoke_text
    assert "agent.proof_graph" in smoke_text
