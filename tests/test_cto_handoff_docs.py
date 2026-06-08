import json
import unittest
from pathlib import Path

from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


class CtoHandoffDocsTests(unittest.TestCase):
    def test_cto_handoff_docs_exist(self) -> None:
        for path in [
            "docs/CTO_HANDOFF.md",
            "docs/ARCHITECTURE.md",
            "docs/LIVE_INTEGRATION_CONTRACT.md",
        ]:
            self.assertTrue((ROOT / path).exists(), msg=f"missing {path}")

    def test_cto_handoff_names_stable_and_transitional_modules(self) -> None:
        handoff = (ROOT / "docs" / "CTO_HANDOFF.md").read_text(encoding="utf-8")
        for expected in [
            "agent/demo.py",
            "agent/chat_answer.py",
            "agent/skills.py",
            "agent/packet.py",
            "agent/evidence_receipts.py",
            "agent/packet_diff.py",
            "agent/outcome_memo.py",
            "agent/trial_outcome_memo.py",
            "agent/trial_evidence_replay.py",
            "agent/decision_brief.py",
            "agent/proof_health.py",
            "agent/spend.py",
            "agent/renderers.py",
            "agent/sponsor_readiness.py",
            "agent/config.py",
            "agent/tools.py",
            "What Is Stable",
            "What Is Transitional",
        ]:
            self.assertIn(expected, handoff)

    def test_live_contract_preserves_safety_defaults(self) -> None:
        contract = (ROOT / "docs" / "LIVE_INTEGRATION_CONTRACT.md").read_text(encoding="utf-8")
        for expected in [
            "COMPOSIO_DRY_RUN",
            "would_execute",
            "false",
            "production access is still blocked",
            "live integrations do not auto-approve access",
            "no external writes in the default public path",
            "Proof Health reports drift and reviewer refresh work without approving access",
            "Sponsor Live Readiness",
        ]:
            self.assertIn(expected, contract)

    def test_readme_links_cto_build_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in [
            "CTO Handoff",
            "Architecture",
            "Live Integration Contract",
            "Proof Health",
        ]:
            self.assertIn(expected, readme)

    def test_readme_top_fold_frames_public_harness(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first_screen = "\n".join(readme.splitlines()[:24])
        first_minute = "\n".join(readme.splitlines()[:60])
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(readme.splitlines()[0], "# InferenceAtlas — Public Agent-Access Review Harness")
        self.assertLessEqual(len(readme.splitlines()), 85)
        self.assertIn("Private engine, public proof.", first_screen)
        self.assertIn("docs/assets/ia_packet_surface.png", first_screen)
        self.assertTrue((ROOT / "docs" / "assets" / "ia_packet_surface.png").is_file())
        self.assertIn("bash scripts/review_60.sh", first_screen)
        self.assertNotIn("bash scripts/run.sh", first_screen)
        self.assertIn("not a private v1 code dump", first_screen)
        self.assertIn("This public harness does not approve access.", first_screen)
        self.assertIn("Downstream systems do not trust raw agent intent", first_screen)
        self.assertIn("Who Uses It", first_minute)
        self.assertIn("Upstream Packet Authority", first_minute)
        self.assertIn("flowchart LR", first_minute)
        self.assertIn("Evidence enrichment", first_minute)
        self.assertIn("search / dry-run tools / narration / trace", first_minute)
        self.assertIn("Verification API", first_minute)
        self.assertIn("MCP / Gateway Controls", first_minute)
        self.assertIn("AI Spend Controls", first_minute)
        self.assertIn("Review Queues", first_minute)
        self.assertIn("docs/COMMAND_REFERENCE.md", readme)
        self.assertIn("docs/ARTIFACT_MAP.md", readme)
        self.assertNotIn("Trust Receipt, DecisionPacket, Packet Diff", first_minute)
        self.assertNotIn("Tavily / Composio / Nebius / OpenClaw", first_minute)
        self.assertNotIn("python3 -m agent.demo", readme)
        self.assertNotIn("ia-judge", readme)
        self.assertIn("tests-passing", first_screen)
        self.assertIn("CI-smoke%20green", first_screen)
        self.assertIn("public%20contract-v0", first_screen)
        self.assertIn("safety-dry--run%20default", first_screen)
        self.assertEqual(manifest["default_run_command"], "bash scripts/run.sh")
        self.assertEqual(manifest["readme_headline"], "InferenceAtlas — Public Agent-Access Review Harness")
        self.assertEqual(
            manifest["readme_badges"],
            ["tests passing", "CI green", "public contract v0", "safety: dry-run default"],
        )

    def test_readme_links_public_contract_without_v1_schema_names(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "CONTRACT.md").read_text(encoding="utf-8")

        self.assertIn("Public Conformance Contract", readme)
        self.assertIn("Private engine, public proof.", readme)
        self.assertIn("Private engine, public proof.", contract)
        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, contract)

    def test_v1_capability_passport_uses_public_safe_terms(self) -> None:
        passport = (ROOT / "docs" / "V1_CAPABILITY_PASSPORT.md").read_text(encoding="utf-8")

        self.assertIn("Status: public redacted capability map", passport)
        self.assertIn("private engine, public proof", passport)
        self.assertIn("request profile", passport)
        self.assertIn("evidence pack", passport)
        self.assertIn("artifact projection", passport)
        for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
            self.assertNotIn(forbidden, passport, msg=f"{forbidden} leaked in docs/V1_CAPABILITY_PASSPORT.md")

    def test_readme_and_manifest_point_to_judge_fast_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertIn("CLI fallback", readme)
        self.assertIn("docs/PRODUCT_TOUR.md", readme)
        self.assertIn("docs/JUDGE_REVIEW_GUIDE.md", readme)
        self.assertIn("AGENTS.md", readme)
        self.assertIn("docs/COMMAND_REFERENCE.md", readme)
        self.assertIn("docs/ARTIFACT_MAP.md", readme)
        self.assertEqual(manifest["agent_reviewer_instructions"], "AGENTS.md")
        self.assertEqual(manifest["agentic_review_expected_output"], "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md")
        self.assertEqual(manifest["reviewer_entrypoint"], "docs/JUDGE_REVIEW_GUIDE.md")
        self.assertEqual(manifest["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertEqual(manifest["agent_skills"], "docs/AGENT_SKILLS.md")
        self.assertEqual(manifest["command_reference"], "docs/COMMAND_REFERENCE.md")
        self.assertEqual(manifest["artifact_map"], "docs/ARTIFACT_MAP.md")
        self.assertEqual(manifest["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(manifest["judge_harness_command"], "python3 -m agent.judge")
        self.assertEqual(manifest["judge_harness_json_command"], "python3 -m agent.judge --json")
        self.assertIn("bash scripts/run.sh", manifest["five_minute_review_commands"])
        self.assertEqual(manifest["agent_skills_command"], "python3 -m agent.skills")
        self.assertEqual(manifest["agent_skills_json_command"], "python3 -m agent.skills --json")
        self.assertEqual(manifest["artifact_integrity_command"], "python3 -m agent.verify_artifacts")
        self.assertEqual(manifest["artifact_integrity_json_command"], "python3 -m agent.verify_artifacts --json")
        self.assertIn("60 generated artifacts byte-compared", manifest["artifact_integrity_gate"])
        self.assertEqual(
            manifest["sponsor_proof_trace_command"],
            "python3 -m agent.sponsor_proof_trace examples/requests/support_triage_trial.yml",
        )
        self.assertEqual(manifest["tavily_live_evidence_module"], "agent/tavily_live_evidence.py")
        self.assertEqual(
            manifest["tavily_live_evidence_json_command"],
            "python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write --live-tavily --json",
        )
        self.assertEqual(manifest["composio_dry_run_diff_module"], "agent/composio_dry_run_diff.py")
        self.assertEqual(
            manifest["composio_dry_run_diff_json_command"],
            "python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write --composio-dry-run --json",
        )
        self.assertEqual(manifest["ai_spend_review_request"], "examples/requests/ai_spend_budget_overrun.yml")
        self.assertEqual(
            manifest["ai_spend_review_command"],
            "python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write",
        )
        self.assertEqual(
            manifest["ai_spend_review_json_command"],
            "python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write --json",
        )
        self.assertIn("python3 -m agent.judge", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.skills", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.packet_diff", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.evidence_receipts", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.packet_authority", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.verification --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.downstream_gate --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.outcome_memo", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.contract --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.gate --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.adapters --all", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.sponsor_readiness", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.trust", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.review_room", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.proof_health", manifest["five_minute_review_commands"])
        self.assertIn(
            "python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write",
            manifest["five_minute_review_commands"],
        )
        self.assertIn("python3 -m agent.trial examples/requests/support_triage_trial.yml", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml", manifest["five_minute_review_commands"])
        self.assertIn("python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml", manifest["five_minute_review_commands"])
        self.assertIn(
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial",
            manifest["five_minute_review_commands"],
        )
        self.assertIn("python3 -m agent.verify_artifacts", manifest["five_minute_review_commands"])
        self.assertIn("docs/PRODUCT_TOUR.md", manifest["product_review_path"])
        self.assertIn("docs/AGENT_SKILLS.md", manifest["product_review_path"])
        self.assertIn("bash scripts/run.sh", manifest["product_review_path"])
        self.assertIn("python3 -m agent.skills", manifest["product_review_path"])
        self.assertIn("examples/generated/packet_diff.md", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.evidence_receipts.md", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.evidence_receipts.json", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.snapshot.json", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.verification.json", manifest["product_review_path"])
        self.assertIn("python3 -m agent.downstream_gate --all", manifest["product_review_path"])
        self.assertIn("/api/downstream-gates/{subscriber}/decision", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.outcome_memo.md", manifest["product_review_path"])
        self.assertIn("python3 -m agent.verify_artifacts", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_agent.proof_health.md", manifest["product_review_path"])
        self.assertIn("examples/requests/ai_spend_budget_overrun.yml", manifest["product_review_path"])
        self.assertIn(
            "python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write",
            manifest["product_review_path"],
        )
        self.assertIn("examples/generated/ai_spend_budget_overrun.spend_packet.md", manifest["product_review_path"])
        self.assertIn("examples/generated/sponsor_live_readiness.md", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_trial.outcome_memo.md", manifest["product_review_path"])
        self.assertIn("python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml", manifest["product_review_path"])
        self.assertIn(
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial",
            manifest["product_review_path"],
        )
        self.assertIn("examples/evidence/support_triage_trial", manifest["product_review_path"])
        self.assertIn("examples/generated/support_triage_trial.evidence_replay.md", manifest["product_review_path"])
        self.assertEqual(manifest["policy_gate_command"], "python3 -m agent.gate --all")
        self.assertEqual(manifest["sponsor_adapter_command"], "python3 -m agent.adapters --all")
        self.assertEqual(manifest["sponsor_live_readiness_command"], "python3 -m agent.sponsor_readiness")
        self.assertEqual(
            manifest["sponsor_live_readiness_json_command"],
            "python3 -m agent.sponsor_readiness --no-write --json",
        )
        self.assertEqual(
            manifest["design_partner_trial_runner_command"],
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
        )
        self.assertEqual(
            manifest["design_partner_outcome_memo_command"],
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
        )
        self.assertEqual(
            manifest["design_partner_outcome_memo_json_command"],
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml --no-write --json",
        )
        self.assertEqual(
            manifest["design_partner_evidence_replay_command"],
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
        )
        self.assertEqual(
            manifest["design_partner_evidence_replay_json_command"],
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --json",
        )
        self.assertEqual(
            manifest["design_partner_evidence_replay_surface"],
            "examples/generated/support_triage_trial.evidence_replay.md and examples/generated/support_triage_trial.evidence_replay.json",
        )
        self.assertEqual(
            manifest["live_evidence_rehearsal_command"],
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial",
        )
        self.assertEqual(
            manifest["live_evidence_rehearsal_json_command"],
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --no-write --evidence-dir examples/evidence/support_triage_trial --json",
        )
        self.assertEqual(manifest["trust_receipt_command"], "python3 -m agent.trust")
        self.assertEqual(manifest["review_room_html_command"], "python3 -m agent.review_room")
        self.assertEqual(manifest["proof_health_command"], "python3 -m agent.proof_health")
        self.assertEqual(manifest["proof_health_json_command"], "python3 -m agent.proof_health --no-write --json")
        self.assertEqual(manifest["packet_diff_command"], "python3 -m agent.packet_diff")
        self.assertEqual(manifest["packet_diff_json_command"], "python3 -m agent.packet_diff --no-write --json")
        self.assertEqual(manifest["evidence_receipt_ledger_command"], "python3 -m agent.evidence_receipts")
        self.assertEqual(
            manifest["evidence_receipt_ledger_json_command"],
            "python3 -m agent.evidence_receipts --no-write --json",
        )
        self.assertEqual(manifest["downstream_gate_command"], "python3 -m agent.downstream_gate --all")
        self.assertEqual(manifest["downstream_gate_json_command"], "python3 -m agent.downstream_gate --all --json")
        self.assertEqual(manifest["downstream_gate_surface"], "/api/downstream-gates/{subscriber}/decision")
        self.assertEqual(
            manifest["packet_advisor_json_command"],
            'python3 -m agent.packet_advisor --fixture ai_spend_budget_overrun --subscriber portkey_model_spend_gate --question "Can Portkey allow this spend?" --json',
        )
        self.assertEqual(manifest["packet_advisor_surface"], "agent/packet_advisor.py")
        self.assertEqual(
            manifest["portkey_adapter_json_command"],
            "python3 -m agent.portkey_adapter --fixture ai_spend_budget_overrun --mode dry-run --json",
        )
        self.assertEqual(
            manifest["portkey_adapter_surface"],
            "agent/portkey_adapter.py and /api/packets/{fixture}/downstream/portkey",
        )
        self.assertEqual(manifest["packet_outcome_memo_command"], "python3 -m agent.outcome_memo")
        self.assertEqual(
            manifest["packet_outcome_memo_json_command"],
            "python3 -m agent.outcome_memo --no-write --json",
        )
        self.assertIn("python3 -m agent.verify_artifacts", manifest["verification"]["artifact_integrity"])
        self.assertIn("python3 -m agent.verify_artifacts --json", manifest["verification"]["artifact_integrity"])
        self.assertIn("python3 -m agent.skills", manifest["verification"]["agent_skills"])
        self.assertIn("python3 -m agent.skills --json", manifest["verification"]["agent_skills"])
        self.assertIn("python3 -m agent.evidence_receipts", manifest["verification"]["evidence_receipt_ledger"])
        self.assertIn(
            "python3 -m agent.evidence_receipts --no-write --json",
            manifest["verification"]["evidence_receipt_ledger"],
        )
        self.assertIn("python3 -m agent.verify_artifacts", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_trial.outcome_memo.md", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml", manifest["judge_review_path"])
        self.assertIn("examples/generated/support_triage_trial.evidence_replay.md", manifest["judge_review_path"])
        self.assertIn("docs/AGENT_SKILLS.md", manifest["judge_review_path"])
        self.assertIn("python3 -m agent.skills", manifest["judge_review_path"])
        self.assertIn("agent skills registry", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("chat answer contract", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("chat salience surface", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("packet advisor", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("Portkey dry-run adapter", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("evidence receipt ledger", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("downstream gate decisions", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("artifact integrity gate", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("design partner outcome memo", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("sponsor evidence replay", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("live evidence rehearsal", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("sanitized evidence fixtures", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertEqual(
            manifest["proof_health_surface"],
            "examples/generated/support_triage_agent.proof_health.md and examples/generated/support_triage_agent.proof_health.json",
        )
        self.assertEqual(manifest["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")
        self.assertEqual(manifest["primary_artifacts"]["trust_receipt_markdown"], "examples/generated/trust_receipt.md")
        self.assertEqual(
            manifest["primary_artifacts"]["sponsor_live_readiness_markdown"],
            "examples/generated/sponsor_live_readiness.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["sponsor_live_readiness_json"],
            "examples/generated/sponsor_live_readiness.json",
        )
        self.assertEqual(manifest["primary_artifacts"]["product_tour"], "docs/PRODUCT_TOUR.md")
        self.assertEqual(manifest["primary_artifacts"]["agent_skills"], "docs/AGENT_SKILLS.md")
        self.assertEqual(manifest["primary_artifacts"]["agent_skills_registry"], "agent/skills.py")
        self.assertEqual(manifest["primary_artifacts"]["chat_answer_contract"], "agent/chat_answer.py")
        self.assertEqual(manifest["primary_artifacts"]["chat_salience_surface"], "agent/chat_salience.py")
        self.assertEqual(manifest["primary_artifacts"]["packet_advisor"], "agent/packet_advisor.py")
        self.assertEqual(manifest["primary_artifacts"]["portkey_adapter"], "agent/portkey_adapter.py")
        self.assertEqual(manifest["primary_artifacts"]["review_room_html"], "examples/generated/review_room.html")
        self.assertEqual(
            manifest["primary_artifacts"]["proof_health_markdown"],
            "examples/generated/support_triage_agent.proof_health.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["proof_health_json"],
            "examples/generated/support_triage_agent.proof_health.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["ai_spend_review_packet_markdown"],
            "examples/generated/ai_spend_budget_overrun.spend_packet.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["ai_spend_review_packet_json"],
            "examples/generated/ai_spend_budget_overrun.spend_packet.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["ai_spend_finance_receipt_json"],
            "examples/generated/ai_spend_budget_overrun.finance_receipt.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["ai_spend_procurement_memo_json"],
            "examples/generated/ai_spend_budget_overrun.procurement_memo.json",
        )
        self.assertEqual(manifest["primary_artifacts"]["packet_diff_markdown"], "examples/generated/packet_diff.md")
        self.assertEqual(manifest["primary_artifacts"]["packet_diff_json"], "examples/generated/packet_diff.json")
        self.assertEqual(
            manifest["primary_artifacts"]["evidence_receipt_ledger_markdown"],
            "examples/generated/support_triage_agent.evidence_receipts.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["evidence_receipt_ledger_json"],
            "examples/generated/support_triage_agent.evidence_receipts.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["packet_outcome_memo_markdown"],
            "examples/generated/support_triage_agent.outcome_memo.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["packet_outcome_memo_json"],
            "examples/generated/support_triage_agent.outcome_memo.json",
        )
        self.assertEqual(manifest["primary_artifacts"]["review_room_walkthrough"], "docs/REVIEW_ROOM_WALKTHROUGH.md")
        self.assertEqual(manifest["primary_artifacts"]["review_room_screenshot"], "examples/generated/review_room.desktop.jpg")
        self.assertEqual(
            manifest["primary_artifacts"]["agentic_review_expected_output"],
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
        )
        self.assertEqual(manifest["primary_artifacts"]["design_partner_brief"], "docs/DESIGN_PARTNER_BRIEF.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["primary_artifacts"]["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["primary_artifacts"]["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_report_markdown"],
            "examples/generated/support_triage_trial_report.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_outcome_memo_markdown"],
            "examples/generated/support_triage_trial.outcome_memo.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_outcome_memo_json"],
            "examples/generated/support_triage_trial.outcome_memo.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_evidence_replay_markdown"],
            "examples/generated/support_triage_trial.evidence_replay.md",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_evidence_replay_json"],
            "examples/generated/support_triage_trial.evidence_replay.json",
        )
        self.assertEqual(
            manifest["primary_artifacts"]["support_triage_trial_evidence_fixture"],
            "examples/evidence/support_triage_trial",
        )
        self.assertEqual(manifest["primary_artifacts"]["policy_gate"], "policy/agent_access.yml")
        self.assertEqual(manifest["primary_artifacts"]["sponsor_adapters"], "agent/adapters/")

    def test_judge_review_guide_preserves_private_boundary(self) -> None:
        guide = (ROOT / "docs" / "JUDGE_REVIEW_GUIDE.md").read_text(encoding="utf-8")

        for expected in [
            "Five-Minute Path",
            "docs/PRODUCT_TOUR.md",
            "docs/AGENT_SKILLS.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "python3 -m agent.demo",
            "python3 -m agent.skills",
            "python3 -m agent.packet_diff",
            "python3 -m agent.evidence_receipts",
            "python3 -m agent.outcome_memo",
            "python3 -m agent.verify_artifacts",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.sponsor_readiness",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m agent.proof_health",
            "python3 -m agent.spend examples/requests/ai_spend_budget_overrun.yml --no-write",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "examples/generated/trust_receipt.md",
            "examples/generated/packet_diff.md",
            "examples/generated/support_triage_agent.evidence_receipts.md",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "examples/generated/ai_spend_budget_overrun.spend_packet.md",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/sponsor_live_readiness.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "policy/agent_access.yml",
            "What This Does Not Expose",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, guide)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, guide)

    def test_agents_file_guides_ai_review_without_secrets(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for expected in [
            "Agent Reviewer Instructions",
            "Do not request secrets",
            "docs/PRODUCT_TOUR.md",
            "docs/AGENT_SKILLS.md",
            "docs/AGENTIC_REVIEW_EXPECTED_OUTPUT.md",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "python3 -m agent.demo",
            "python3 -m agent.review --list",
            "python3 -m agent.skills",
            "python3 -m agent.packet_diff",
            "python3 -m agent.evidence_receipts",
            "python3 -m agent.outcome_memo",
            "python3 -m agent.verify_artifacts",
            "python3 -m agent.contract --all",
            "python3 -m agent.gate --all",
            "python3 -m agent.adapters --all",
            "python3 -m agent.sponsor_readiness",
            "python3 -m agent.trust",
            "python3 -m agent.review_room",
            "python3 -m agent.proof_health",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "examples/generated/trust_receipt.md",
            "examples/generated/packet_diff.md",
            "examples/generated/support_triage_agent.evidence_receipts.md",
            "examples/generated/support_triage_agent.outcome_memo.md",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/sponsor_live_readiness.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "docs/REVIEW_ROOM_WALKTHROUGH.md",
            "examples/generated/review_room.desktop.jpg",
            "policy/agent_access.yml",
            "python3 -m unittest discover -s tests",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, agents)

        for forbidden in ["ask_ia", "living_document", "advanced_workspace", "mcp_agent_tool_access"]:
            self.assertNotIn(forbidden, agents)


if __name__ == "__main__":
    unittest.main()
