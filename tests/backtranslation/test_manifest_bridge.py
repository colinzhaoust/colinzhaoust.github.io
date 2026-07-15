from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.conditions import FixtureRenderer, RecordingMockAdapter, run_one_shot, run_self_refined
from tools.backtranslation.manifest_bridge import (
    HumanConditionInput,
    ManifestBridgeError,
    PaperMediaEvidenceBridge,
)
from tools.paper_media_evidence import ManifestValidationError, project_public_manifest, validate_canonical, validate_public

from helpers import OfflineFixture, PROTOCOL_PATH, REGISTRY_PATH, ROOT, fixture_code, load_json


class ManifestBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = OfflineFixture()
        renderer = FixtureRenderer({
            "one_shot": cls.fixture.videos["one_shot"],
            "refine_2": cls.fixture.prepared.video_path,
        })
        cls.one_adapter = RecordingMockAdapter([fixture_code("one_shot")])
        cls.one_root = cls.fixture.root / "bridge_one"
        cls.one = run_one_shot(
            pairing_id="fixture-bt-999-r1", case_id="bt-999",
            reference_video=cls.fixture.prepared.video_path, run_root=cls.one_root,
            adapter=cls.one_adapter, renderer=renderer, policy=cls.fixture.policy,
        )
        cls.self_adapter = RecordingMockAdapter([fixture_code("compile_error"), fixture_code("refine_2")])
        cls.self_root = cls.fixture.root / "bridge_self"
        cls.refined = run_self_refined(
            pairing_id=cls.one.pairing_id, case_id=cls.one.case_id,
            reference_video=cls.fixture.prepared.video_path,
            one_shot_code_path=cls.one_root / str(cls.one.rounds[-1].code_path),
            expected_one_shot_hash=cls.one.final_code_hash or "", run_root=cls.self_root,
            adapter=cls.self_adapter, renderer=renderer, policy=cls.fixture.policy,
        )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, check=True,
        ).stdout.strip()
        cls.bridge = PaperMediaEvidenceBridge(
            registry_path=REGISTRY_PATH, protocol_path=PROTOCOL_PATH,
            pipeline_repository="https://github.com/colinzhaoust/4blue2brown-progress",
            pipeline_commit=commit,
        )
        cls.results = cls.bridge.emit_pairing(
            human=HumanConditionInput(
                pairing_id=cls.one.pairing_id, case_id=cls.one.case_id,
                reference_video=cls.fixture.prepared.video_path,
            ),
            one_shot_trace=cls.one, one_shot_root=cls.one_root,
            self_refined_trace=cls.refined, self_refined_root=cls.self_root,
            artifact_root=cls.fixture.root / "bridge_evidence", dry_run=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def test_valid_three_cell_pairing_uses_q5_validation_and_projection(self) -> None:
        manifests = (self.results.human, self.results.one_shot, self.results.self_refined)
        self.assertEqual({"human", "one_shot", "self_refined"}, {item.condition for item in manifests})
        self.assertEqual({self.one.pairing_id}, {item.pairing_id for item in manifests})
        for result in manifests:
            validate_canonical(result.canonical_manifest)
            validate_public(result.public_manifest)
            self.assertEqual(self.one.pairing_id, result.public_manifest["pairing_id"])
            self.assertEqual("placeholder", result.public_manifest["completion"]["derived_value"])
            self.assertTrue(result.manifest_path.is_file())
            self.assertTrue(result.public_manifest_path.is_file())

    def test_exact_one_shot_parent_hash_and_canonical_manifest_hash(self) -> None:
        parent = self.results.self_refined.canonical_manifest["lineage"]["parent_artifact_refs"][0]
        self.assertEqual("refined_from", parent["relation"])
        self.assertEqual("sha256:" + (self.one.final_code_hash or ""), parent["content_hash"])
        self.assertEqual(self.results.one_shot.canonical_manifest_hash, parent["canonical_manifest_hash"])
        self.assertEqual(self.results.one_shot.run_id, parent["run_id"])
        round_zero = next(
            item for item in self.results.self_refined.canonical_manifest["artifacts"]
            if item["artifact_id"].endswith(":round:0:code")
        )
        self.assertEqual(parent, round_zero["lineage"]["parent_artifact_refs"][0])

    def test_broken_cross_run_lineage_is_rejected_by_q5(self) -> None:
        manifest = copy.deepcopy(self.results.self_refined.canonical_manifest)
        manifest["external_lineage"][0]["canonical_manifest_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ManifestValidationError, "unresolved-external-parent"):
            validate_canonical(manifest)

    def test_missing_repository_or_gallery_license_is_rejected(self) -> None:
        for source_type in ("repository", "example_gallery"):
            manifest = copy.deepcopy(self.results.human.canonical_manifest)
            manifest["license_ledger"] = [
                item for item in manifest["license_ledger"] if item["resource_type"] != source_type
            ]
            with self.subTest(source_type=source_type), self.assertRaisesRegex(
                ManifestValidationError, "source-coverage"
            ):
                validate_canonical(manifest)

    def test_failed_attempt_is_retained_in_denominator_and_repair_chain(self) -> None:
        manifest = self.results.self_refined.canonical_manifest
        claim = next(item for item in manifest["claims"] if item["claim_id"].endswith("attempt-denominator"))
        self.assertIn("3 retained candidate attempts; 1 failed attempts", claim["statement"])
        self.assertIn("compile_error", self.refined.failure_codes)
        self.assertEqual(2, len(manifest["repair_events"]))
        self.assertEqual(2, self.results.self_refined.public_manifest["repair_summary"]["event_count"])

    def test_dry_run_has_zero_billable_provider_calls_and_zero_cost(self) -> None:
        self.assertEqual(0, self.one.billable_provider_calls)
        self.assertEqual(0, self.refined.billable_provider_calls)
        for result in (self.results.human, self.results.one_shot, self.results.self_refined):
            self.assertEqual(0, result.canonical_manifest["budget"]["measured_usd"])
            self.assertEqual([], result.canonical_manifest["budget"]["reservations"])
        provider_claim = next(
            item for item in self.results.self_refined.public_manifest["claims"]
            if item["claim_id"].endswith("provider-calls")
        )
        self.assertIn("billable provider calls: 0", provider_claim["statement"])

    def test_bridge_rejects_more_than_three_revision_calls(self) -> None:
        changed = copy.deepcopy(self.refined)
        changed.provider_calls = 4
        with self.assertRaisesRegex(ManifestBridgeError, "three-revision"):
            self.bridge.emit_pairing(
                human=HumanConditionInput(
                    pairing_id=self.one.pairing_id, case_id=self.one.case_id,
                    reference_video=self.fixture.prepared.video_path,
                ),
                one_shot_trace=self.one, one_shot_root=self.one_root,
                self_refined_trace=changed, self_refined_root=self.self_root,
                artifact_root=self.fixture.root / "too_many", dry_run=True,
            )

    def test_source_vault_claim_fails_closed_before_public_projection(self) -> None:
        manifest = copy.deepcopy(self.results.one_shot.canonical_manifest)
        manifest["claims"][0]["statement"] = "copied from source-vault draft"
        validate_canonical(manifest)
        with self.assertRaises(ManifestValidationError):
            project_public_manifest(manifest)


class CanonicalCliDryRunTests(unittest.TestCase):
    def test_cli_dry_run_exercises_three_manifest_bridge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="backtranslation_bridge_cli_") as raw:
            work = Path(raw) / "work"
            process = subprocess.run(
                [str(ROOT / ".venv-evidence" / "bin" / "python"), "tools/run_backtranslation.py", "dry-run",
                 "--work-dir", str(work)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(0, process.returncode, process.stderr)
            result = load_json(work / "dry_run_result.json")
            self.assertEqual(0, result["provider_calls"]["billable"])
            self.assertEqual({"human", "one_shot", "self_refined"}, set(result["canonical_manifests"]))
            for item in result["canonical_manifests"].values():
                self.assertEqual("placeholder", item["completion"])
                self.assertTrue(Path(item["canonical"]).is_file())
                self.assertTrue(Path(item["public"]).is_file())


if __name__ == "__main__":
    unittest.main()
