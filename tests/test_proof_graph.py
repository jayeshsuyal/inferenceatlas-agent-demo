"""ProofGraph schema-only contract tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from agent.adapters.core import ADAPTER_CONTRACT_VERSION
from agent.composio_dry_run_diff import COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION
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
    assert schema["properties"]["composio_blast_radius"]["$ref"] == (
        "#/$defs/composio_blast_radius"
    )
    assert schema["$defs"]["composio_blast_radius"]["properties"]["schema_version"]["const"] == (
        COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION
    )
    assert schema["$defs"]["composio_blast_radius"]["properties"]["api_call_made"]["const"] is False
    assert schema["$defs"]["composio_blast_radius"]["properties"]["would_execute"]["const"] is False
    assert schema["properties"]["openclaw_runtime_trace"]["$ref"] == (
        "#/$defs/openclaw_runtime_trace"
    )
    assert schema["$defs"]["openclaw_runtime_trace"]["properties"]["schema_version"]["const"] == (
        ADAPTER_CONTRACT_VERSION
    )
    assert schema["$defs"]["openclaw_runtime_trace"]["properties"]["api_call_made"]["const"] is False
    assert schema["$defs"]["openclaw_runtime_trace"]["properties"]["runtime_write_attempted"]["const"] is False
    assert schema["$defs"]["openclaw_runtime_trace"]["properties"]["would_execute"]["const"] is False
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
    assert "composio_blast_radius" not in first
    assert "openclaw_runtime_trace" not in first


def test_composio_blast_radius_graph_layer_is_opt_in_and_non_mutating() -> None:
    graph = build_proof_graph_for_scenario(
        "support_triage_agent",
        include_composio_blast_radius=True,
    )

    assert graph["scenario_name"] == "support_triage_agent"
    assert graph["packet_reference"]["packet_id"] == "ia-agent-access-support-triage-v0"
    assert graph["invariants"] == {
        "packet_remains_authority": True,
        "graph_can_approve": False,
        "graph_can_mutate_packet": False,
        "graph_can_execute_external_write": False,
        "graph_can_change_verdict": False,
        "all_nodes_require_human_review": True,
        "all_nodes_non_mutating": True,
        "all_edges_non_mutating": True,
    }

    composio_summary = graph["composio_blast_radius"]
    assert composio_summary["schema_version"] == COMPOSIO_DRY_RUN_DIFF_SCHEMA_VERSION
    assert composio_summary["provider"] == "composio"
    assert composio_summary["mode"] == "deterministic_fallback"
    assert composio_summary["dry_run_enforced"] is True
    assert composio_summary["api_call_made"] is False
    assert composio_summary["composio_execute_allowed"] is False
    assert composio_summary["fallback_used"] is True
    assert composio_summary["tool_count"] == 3
    assert composio_summary["blocked_action_count"] == 9
    assert composio_summary["write_like_action_count"] == 5
    assert composio_summary["admin_like_action_count"] == 4
    assert composio_summary["required_proof_count"] == 9
    assert composio_summary["max_risk_level"] == "critical"
    assert composio_summary["all_blocked_before_execution"] is True
    assert composio_summary["all_write_or_admin_blocked"] is True
    assert composio_summary["would_execute"] is False
    assert composio_summary["candidate_action_slugs"] == [
        "GITHUB_LIST_ISSUES",
        "SLACK_FETCH_CONVERSATION_HISTORY",
        "JIRA_CREATE_ISSUE",
    ]

    composio_nodes = [node for node in graph["proof_nodes"] if node["provider"] == "composio"]
    assert len(composio_nodes) == (
        composio_summary["tool_count"]
        + composio_summary["blocked_action_count"]
        + composio_summary["required_proof_count"]
    )
    assert graph["node_counts"] == {
        "packet": 1,
        "proof": len(PACKET_ONLY_PROOF_FIELDS) + len(composio_nodes),
        "edge": len(graph["proof_edges"]),
    }

    tool_nodes = {
        node["node_id"]: node
        for node in composio_nodes
        if node["node_id"].startswith("proof:composio:tool_scope:")
    }
    assert set(tool_nodes) == {
        "proof:composio:tool_scope:github",
        "proof:composio:tool_scope:slack",
        "proof:composio:tool_scope:jira",
    }
    for node in composio_nodes:
        assert node["mode"] == "deterministic_fallback"
        assert node["api_call_made"] is False
        assert node["fallback_used"] is True
        assert node["external_write_made"] is False
        assert node["can_change_packet_verdict"] is False
        assert node["human_review_required"] is True
        assert node["attached_packet_field"] in {"tool_scope", "missing_proof"}

    composio_node_ids = {node["node_id"] for node in composio_nodes}
    packet_node_id = graph["packet_node"]["node_id"]
    composio_packet_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"] in composio_node_ids and edge["to_node_id"] == packet_node_id
    ]
    blocked_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"].startswith("proof:composio:blocked_action:")
        and edge["edge_type"] == "blocks_action"
    ]
    required_proof_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"].startswith("proof:composio:required_proof:")
        and edge["edge_type"] == "requires_human_owner"
    ]

    assert len(composio_packet_edges) == len(composio_nodes)
    assert len(blocked_edges) == composio_summary["blocked_action_count"]
    assert len(required_proof_edges) == composio_summary["required_proof_count"]
    for edge in graph["proof_edges"]:
        assert edge["human_review_required"] is True
        assert edge["can_change_packet_verdict"] is False


def test_openclaw_runtime_trace_graph_layer_is_opt_in_and_non_mutating() -> None:
    graph = build_proof_graph_for_scenario(
        "support_triage_agent",
        include_openclaw_runtime_trace=True,
    )

    assert graph["scenario_name"] == "support_triage_agent"
    assert graph["packet_reference"]["packet_id"] == "ia-agent-access-support-triage-v0"
    assert graph["invariants"] == {
        "packet_remains_authority": True,
        "graph_can_approve": False,
        "graph_can_mutate_packet": False,
        "graph_can_execute_external_write": False,
        "graph_can_change_verdict": False,
        "all_nodes_require_human_review": True,
        "all_nodes_non_mutating": True,
        "all_edges_non_mutating": True,
    }

    trace_summary = graph["openclaw_runtime_trace"]
    assert trace_summary["schema_version"] == ADAPTER_CONTRACT_VERSION
    assert trace_summary["provider"] == "openclaw"
    assert trace_summary["mode"] == "deterministic_fallback"
    assert trace_summary["status"] == "trace_contract_planned"
    assert trace_summary["api_call_made"] is False
    assert trace_summary["fallback_used"] is True
    assert trace_summary["checkpoint_count"] == 3
    assert trace_summary["attempted_action_count"] == 9
    assert trace_summary["blocked_event_count"] == 9
    assert trace_summary["write_like_blocked_count"] == 5
    assert trace_summary["admin_like_blocked_count"] == 4
    assert trace_summary["high_or_critical_action_count"] == 9
    assert trace_summary["all_attempted_actions_blocked"] is True
    assert trace_summary["runtime_write_attempted"] is False
    assert trace_summary["human_review_boundary_preserved"] is True
    assert trace_summary["would_execute"] is False
    assert trace_summary["safety_impact"] == "none"

    openclaw_nodes = [node for node in graph["proof_nodes"] if node["provider"] == "openclaw"]
    assert len(openclaw_nodes) == (
        trace_summary["checkpoint_count"]
        + trace_summary["attempted_action_count"]
        + trace_summary["blocked_event_count"]
    )
    assert graph["node_counts"] == {
        "packet": 1,
        "proof": len(PACKET_ONLY_PROOF_FIELDS) + len(openclaw_nodes),
        "edge": len(graph["proof_edges"]),
    }

    checkpoint_nodes = [
        node for node in openclaw_nodes if node["node_id"].startswith("proof:openclaw:checkpoint:")
    ]
    attempted_nodes = [
        node
        for node in openclaw_nodes
        if node["node_id"].startswith("proof:openclaw:attempted_action:")
    ]
    blocked_nodes = [
        node for node in openclaw_nodes if node["node_id"].startswith("proof:openclaw:blocked_event:")
    ]
    assert len(checkpoint_nodes) == trace_summary["checkpoint_count"]
    assert len(attempted_nodes) == trace_summary["attempted_action_count"]
    assert len(blocked_nodes) == trace_summary["blocked_event_count"]

    for node in openclaw_nodes:
        assert node["mode"] == "deterministic_fallback"
        assert node["api_call_made"] is False
        assert node["fallback_used"] is True
        assert node["external_write_made"] is False
        assert node["can_change_packet_verdict"] is False
        assert node["human_review_required"] is True
        assert node["attached_packet_field"] == "runtime_trace"

    openclaw_node_ids = {node["node_id"] for node in openclaw_nodes}
    packet_node_id = graph["packet_node"]["node_id"]
    openclaw_packet_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"] in openclaw_node_ids and edge["to_node_id"] == packet_node_id
    ]
    observed_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"].startswith("proof:openclaw:attempted_action:")
        and edge["edge_type"] == "observed_by_downstream"
    ]
    blocked_edges = [
        edge
        for edge in graph["proof_edges"]
        if edge["from_node_id"].startswith("proof:openclaw:blocked_event:")
        and edge["edge_type"] == "blocks_action"
    ]

    assert len(openclaw_packet_edges) == len(openclaw_nodes)
    assert len(observed_edges) == trace_summary["attempted_action_count"]
    assert len(blocked_edges) == trace_summary["blocked_event_count"]
    for edge in graph["proof_edges"]:
        assert edge["human_review_required"] is True
        assert edge["can_change_packet_verdict"] is False


def test_sponsor_graph_layers_compose_without_changing_authority() -> None:
    graph = build_proof_graph_for_scenario(
        "support_triage_agent",
        include_composio_blast_radius=True,
        include_openclaw_runtime_trace=True,
    )

    assert graph["packet_reference"]["packet_id"] == "ia-agent-access-support-triage-v0"
    assert graph["composio_blast_radius"]["provider"] == "composio"
    assert graph["openclaw_runtime_trace"]["provider"] == "openclaw"
    assert {node["provider"] for node in graph["proof_nodes"]} == {
        "ia_packet",
        "composio",
        "openclaw",
    }
    assert graph["invariants"]["packet_remains_authority"] is True
    assert graph["invariants"]["graph_can_approve"] is False
    assert graph["invariants"]["graph_can_execute_external_write"] is False
    assert graph["invariants"]["graph_can_change_verdict"] is False


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


def test_proof_graph_cli_can_include_composio_blast_radius_layer() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.proof_graph",
            "support_triage_agent",
            "--include-composio-blast-radius",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["composio_blast_radius"]["provider"] == "composio"
    assert payload["composio_blast_radius"]["api_call_made"] is False
    assert payload["composio_blast_radius"]["would_execute"] is False
    assert {node["provider"] for node in payload["proof_nodes"]} == {"ia_packet", "composio"}


def test_proof_graph_cli_can_include_openclaw_runtime_trace_layer() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.proof_graph",
            "support_triage_agent",
            "--include-openclaw-runtime-trace",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["openclaw_runtime_trace"]["provider"] == "openclaw"
    assert payload["openclaw_runtime_trace"]["api_call_made"] is False
    assert payload["openclaw_runtime_trace"]["runtime_write_attempted"] is False
    assert payload["openclaw_runtime_trace"]["would_execute"] is False
    assert {node["provider"] for node in payload["proof_nodes"]} == {"ia_packet", "openclaw"}


def test_proof_graph_schema_and_module_preserve_private_boundary() -> None:
    combined = "\n".join(
        [
            SCHEMA_PATH.read_text(encoding="utf-8"),
            (ROOT / "agent" / "proof_graph.py").read_text(encoding="utf-8"),
            json.dumps(build_proof_graph_for_scenario("support_triage_agent"), sort_keys=True),
            json.dumps(
                build_proof_graph_for_scenario(
                    "support_triage_agent",
                    include_openclaw_runtime_trace=True,
                ),
                sort_keys=True,
            ),
        ]
    )

    for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
        assert forbidden not in combined


def test_pr_smoke_checks_proof_graph_schema_and_command() -> None:
    smoke_text = (ROOT / "scripts" / "pr_smoke.sh").read_text(encoding="utf-8")

    assert "schemas/proof_graph.schema.json" in smoke_text
    assert "agent.proof_graph" in smoke_text
