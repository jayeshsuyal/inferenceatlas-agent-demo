"""Tests for Portkey Governance + Build packet implementation."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent.portkey_packet_build import (
    build_portkey_packet_implementation_plan,
    implement_portkey_packet_build,
)
from agent.review_run import (
    DEFAULT_REVIEW_RUN_ACCESS_REQUEST,
    attach_review_run_proof,
    create_review_run,
    generate_initial_review_run_packet,
    record_review_run_access_request,
    rerun_review_run_packet,
    select_review_run_repo,
)


def _selected_repo() -> dict:
    return {"provider": "github", "full_name": "acme/demo-support-incidents", "source": "demo"}


def _movement() -> dict:
    return {
        "allowed": ["read issues"],
        "review_required": ["comment"],
        "blocked": ["repo admin"],
    }


class PortkeyPacketBuildTests(unittest.TestCase):
    def _ready_run(self):
        run = create_review_run(selected_repo=_selected_repo())
        run = select_review_run_repo(run, _selected_repo())
        run = record_review_run_access_request(run, DEFAULT_REVIEW_RUN_ACCESS_REQUEST)
        run = generate_initial_review_run_packet(run)
        proof_items = [
            {"id": "repo_owner_approval", "label": "Repo owner approval"},
            {"id": "rollback_offswitch", "label": "Rollback/off-switch proof"},
            {"id": "environment_boundary", "label": "Environment boundary"},
        ]
        proofed = attach_review_run_proof(run, proof_items)
        return rerun_review_run_packet(
            proofed,
            revision_id=f"{proofed.packet['revision_id']}-rerun",
            verdict="ready_with_gates",
            movement_classes=_movement(),
            portkey_preview={"portkey_guardrail_response": {"verdict": True}},
        )

    @patch("agent.portkey_packet_build.portkey_plane_b_status")
    def test_build_plan_graph_lists_byok_and_blocked_nodes(self, status: object) -> None:
        status.return_value = {
            "verified": True,
            "connected": True,
            "resolved_model": "@iaagent1/babbage-002",
            "provider_slug": "iaagent1",
        }
        session_id = "packet-build-test-session-01"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                with patch("agent.portkey_packet_build._raw_connection", return_value={}):
                    plan = build_portkey_packet_implementation_plan(
                        self._ready_run(),
                        session_id,
                        public_base_url="http://127.0.0.1:8080",
                    )
        self.assertTrue(plan["ok"])
        nodes = plan["graph"]["nodes"]
        self.assertTrue(any(node["id"] == "metadata_binding" and node["implementable"] for node in nodes))
        self.assertTrue(any(node["id"] == "admin_policy_push" and node["kind"] == "blocked" for node in nodes))
        self.assertGreaterEqual(plan["summary"]["implementable_via_byok"], 4)

    @patch("agent.portkey_packet_build.proxy_portkey_chat")
    @patch("agent.portkey_packet_build.portkey_plane_b_status")
    def test_implement_executes_byok_steps(self, status: object, proxy: object) -> None:
        status.return_value = {"verified": True, "connected": True, "resolved_model": "@iaagent1/babbage-002"}
        proxy.return_value = {"ok": True, "reply": "packet-routed", "model": "@iaagent1/babbage-002"}
        session_id = "packet-build-test-session-02"
        with TemporaryDirectory() as temp_dir:
            with patch("agent.connector_runtime.SESSIONS_DIR", Path(temp_dir)):
                result = implement_portkey_packet_build(
                    self._ready_run(),
                    session_id,
                    public_base_url="http://127.0.0.1:8080",
                )
        self.assertTrue(result["ok"])
        self.assertTrue(result["implementation"]["completed"])
        step_ids = {step["id"] for step in result["implementation"]["steps"]}
        self.assertIn("metadata_binding", step_ids)
        self.assertIn("scoped_inference_probe", step_ids)
        self.assertIn("guardrail_webhook_export", step_ids)

    @patch("agent.portkey_packet_build.portkey_plane_b_status")
    def test_implement_requires_verified_portkey(self, status: object) -> None:
        status.return_value = {"verified": False, "connected": False}
        result = implement_portkey_packet_build(
            self._ready_run(),
            "packet-build-test-session-03",
            public_base_url="http://127.0.0.1:8080",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["needs_sign_in"])
