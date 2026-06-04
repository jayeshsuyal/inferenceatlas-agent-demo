import json
import unittest
from pathlib import Path

from agent.judge import build_judge_report, render_judge_report_markdown
from tests.public_boundary_terms import FORBIDDEN_PRIVATE_V1_TERMS


ROOT = Path(__file__).resolve().parents[1]


def _read_yaml_list_after(lines: list[str], marker: str, item_prefix: str) -> list[str]:
    for index, line in enumerate(lines):
        if line == marker:
            values = []
            for item in lines[index + 1:]:
                if item.startswith(item_prefix):
                    values.append(item[len(item_prefix):])
                    continue
                if item.strip() == "":
                    continue
                break
            return values
    raise AssertionError(f"missing marker {marker}")


def _read_tool_data_class_union(text: str) -> set[str]:
    lines = text.splitlines()
    values: set[str] = set()
    for index, line in enumerate(lines):
        if line != "      data_classes:":
            continue
        for item in lines[index + 1:]:
            if item.startswith("        - "):
                values.add(item[len("        - "):])
                continue
            if item.strip() == "":
                continue
            break
    return values


class DesignPartnerTrialKitTests(unittest.TestCase):
    def test_trial_kit_doc_names_template_and_sample(self) -> None:
        kit = (ROOT / "docs" / "DESIGN_PARTNER_TRIAL_KIT.md").read_text(encoding="utf-8")

        for expected in [
            "Design Partner Trial Kit",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "python3 -m agent.judge",
            "docs/DESIGN_PARTNER_BRIEF.md",
            "examples/generated/trust_receipt.md",
            "examples/generated/review_room.html",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "policy/agent_access.yml",
            "python3 -m agent.trial examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml",
            "python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml",
            "public offline trial runner",
            "Private engine, public proof.",
        ]:
            self.assertIn(expected, kit)

    def test_trial_request_template_has_required_sections(self) -> None:
        template = (ROOT / "examples" / "requests" / "design_partner_trial.yml").read_text(encoding="utf-8")

        for expected in [
            "schema_version: design_partner_trial_request.v0",
            "status: public_template_no_secrets",
            "redaction_boundary:",
            "candidate_agent:",
            "requested_access:",
            "production_access_requested: false",
            "admin_scopes_requested: false",
            "external_writes_requested: false",
            "proof_debt:",
            "reviewer_routing:",
            "safety_defaults:",
            "access_approval_granted: false",
            "permission_grant_allowed: false",
            "composio_dry_run_default: true",
            "human_approval_required: true",
            "trial_outputs:",
        ]:
            self.assertIn(expected, template)

    def test_trial_request_data_classes_match_tool_union(self) -> None:
        for relative_path in [
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
        ]:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            lines = text.splitlines()
            top_level = set(_read_yaml_list_after(lines, "  data_classes:", "    - "))
            per_tool = _read_tool_data_class_union(text)

            self.assertEqual(
                top_level,
                per_tool,
                msg=f"top-level requested_access.data_classes must equal per-tool union in {relative_path}",
            )

    def test_support_triage_trial_sample_is_concrete_and_safe(self) -> None:
        sample = (ROOT / "examples" / "requests" / "support_triage_trial.yml").read_text(encoding="utf-8")

        for expected in [
            "status: public_sample_no_secrets",
            "name: support_triage_agent",
            "system: GitHub",
            "system: Slack",
            "system: Jira",
            "requested_environment: validation_only",
            "production_access_requested: false",
            "admin_scopes_requested: false",
            "external_writes_requested: false",
            "owner: Engineering",
            "owner: Security/Legal",
            "role: Support Ops",
            "write-enabled Composio actions",
            "sponsor_adapters_remain_dry_run_and_non_approving",
        ]:
            self.assertIn(expected, sample)

    def test_trial_kit_is_in_manifest_and_judge_report(self) -> None:
        manifest = json.loads((ROOT / "AI_JUDGE_MANIFEST.json").read_text(encoding="utf-8"))
        report = build_judge_report(write_artifacts=False)
        markdown = render_judge_report_markdown(report)
        artifact_paths = {item["path"] for item in report["artifact_checklist"]}

        self.assertEqual(manifest["design_partner_trial_kit"], "docs/DESIGN_PARTNER_TRIAL_KIT.md")
        self.assertEqual(manifest["design_partner_trial_template"], "examples/requests/design_partner_trial.yml")
        self.assertEqual(manifest["support_triage_trial_sample"], "examples/requests/support_triage_trial.yml")
        self.assertIn("design partner trial kit", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("design partner trial runner", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("design partner outcome memo", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("sponsor evidence replay", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("trial request templates", manifest["private_v1_boundary"]["public_proof_surface"])
        self.assertIn("proof health", manifest["private_v1_boundary"]["public_proof_surface"])

        for expected in [
            "docs/DESIGN_PARTNER_TRIAL_KIT.md",
            "examples/requests/design_partner_trial.yml",
            "examples/requests/support_triage_trial.yml",
            "examples/generated/support_triage_trial_report.md",
            "examples/generated/support_triage_trial_report.json",
            "examples/generated/support_triage_trial.outcome_memo.md",
            "examples/generated/support_triage_trial.outcome_memo.json",
            "examples/generated/support_triage_trial.evidence_replay.md",
            "examples/generated/support_triage_trial.evidence_replay.json",
            "examples/generated/support_triage_agent.proof_health.md",
            "examples/generated/support_triage_agent.proof_health.json",
        ]:
            self.assertIn(expected, artifact_paths)
            self.assertIn(expected, markdown)

    def test_trial_kit_public_surfaces_do_not_expose_private_schema_names(self) -> None:
        surfaces = [
            ROOT / "docs" / "DESIGN_PARTNER_TRIAL_KIT.md",
            ROOT / "examples" / "requests" / "design_partner_trial.yml",
            ROOT / "examples" / "requests" / "support_triage_trial.yml",
        ]

        for surface in surfaces:
            text = surface.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_PRIVATE_V1_TERMS:
                self.assertNotIn(forbidden, text, msg=f"{forbidden} leaked in {surface}")


if __name__ == "__main__":
    unittest.main()
