from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tools.backtranslation.conditions import FixtureRenderer, RecordingMockAdapter, run_one_shot, run_self_refined
from tools.backtranslation.manifest_bridge import (
    CrossRunParent,
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
        cls.renderer = FixtureRenderer({
            "one_shot": cls.fixture.videos["one_shot"],
            "refine_2": cls.fixture.prepared.video_path,
        })
        cls.one_adapter = RecordingMockAdapter([fixture_code("one_shot")])
        cls.one_root = cls.fixture.root / "bridge_one"
        cls.one = run_one_shot(
            pairing_id="fixture-bt-999-r1", prepared_reference=cls.fixture.prepared, run_root=cls.one_root,
            adapter=cls.one_adapter, renderer=cls.renderer, policy=cls.fixture.policy,
        )
        cls.self_adapter = RecordingMockAdapter([fixture_code("compile_error"), fixture_code("refine_2")])
        cls.self_root = cls.fixture.root / "bridge_self"
        cls.refined = run_self_refined(
            pairing_id=cls.one.pairing_id, prepared_reference=cls.fixture.prepared,
            one_shot_code_path=cls.one_root / str(cls.one.rounds[-1].code_path),
            expected_one_shot_hash=cls.one.final_code_hash or "", run_root=cls.self_root,
            adapter=cls.self_adapter, renderer=cls.renderer, policy=cls.fixture.policy,
        )
        cls.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, check=True,
        ).stdout.strip()
        cls.bridge = PaperMediaEvidenceBridge(
            registry_path=REGISTRY_PATH, protocol_path=PROTOCOL_PATH,
            pipeline_repository="https://github.com/colinzhaoust/4blue2brown-progress",
            pipeline_commit=cls.commit,
        )
        cls.results = cls.bridge.emit_pairing(
            human=HumanConditionInput(
                pairing_id=cls.one.pairing_id, prepared_reference=cls.fixture.prepared,
            ),
            one_shot_trace=cls.one, one_shot_root=cls.one_root,
            self_refined_trace=cls.refined, self_refined_root=cls.self_root,
            artifact_root=cls.fixture.root / "bridge_evidence", dry_run=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def human_parent(self) -> CrossRunParent:
        return CrossRunParent(
            run_id=self.results.human.run_id,
            artifact_id=self.results.human.artifact_ids["reference_video"],
            relation="derived_from",
            content_hash="sha256:" + self.fixture.prepared.content_hash,
            canonical_manifest_hash=self.results.human.canonical_manifest_hash,
            evidence_ref=self.results.human.public_manifest_ref,
        )

    def one_shot_parent(self) -> CrossRunParent:
        return CrossRunParent(
            run_id=self.results.one_shot.run_id,
            artifact_id=self.results.one_shot.artifact_ids["final_code"],
            relation="refined_from",
            content_hash="sha256:" + (self.one.final_code_hash or ""),
            canonical_manifest_hash=self.results.one_shot.canonical_manifest_hash,
            evidence_ref=self.results.one_shot.public_manifest_ref,
        )

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
        self.assertIn("3 attempted candidate generations; 1 failed attempts", claim["statement"])
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
        changed_root = self.fixture.root / "too_many_trace"
        shutil.copytree(self.self_root, changed_root)
        (changed_root / "condition_trace.json").write_text(
            json.dumps(changed.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(ManifestBridgeError, "three-revision"):
            self.bridge.emit_backtranslation_run(
                trace=changed, condition_root=changed_root,
                artifact_root=self.fixture.root / "too_many",
                cross_run_parents=[self.one_shot_parent()], dry_run=True,
            )

    def test_bridge_rejects_in_memory_trace_that_differs_from_persisted_ledger(self) -> None:
        changed = copy.deepcopy(self.one)
        changed.failure_codes.append("policy_violation")
        with self.assertRaisesRegex(ManifestBridgeError, "does not exactly match"):
            self.bridge.emit_backtranslation_run(
                trace=changed, condition_root=self.one_root,
                artifact_root=self.fixture.root / "trace_mismatch",
                cross_run_parents=[self.human_parent()], dry_run=True,
            )

    def test_bridge_rejects_traversal_and_symlink_artifact_escapes(self) -> None:
        for mode in ("traversal", "symlink"):
            root = self.fixture.root / f"escape_{mode}"
            shutil.copytree(self.one_root, root)
            changed = copy.deepcopy(self.one)
            original = root / str(changed.rounds[0].code_path)
            outside = self.fixture.root / f"outside_{mode}.py"
            shutil.copyfile(original, outside)
            if mode == "traversal":
                malicious_path = f"../{outside.name}"
            else:
                link = root / "round_0" / "escape.py"
                link.symlink_to(outside)
                malicious_path = "round_0/escape.py"
            changed.rounds[0] = replace(changed.rounds[0], code_path=malicious_path)
            (root / "condition_trace.json").write_text(
                json.dumps(changed.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
            )
            with self.subTest(mode=mode), self.assertRaisesRegex(
                ManifestBridgeError, "traversal|escapes condition_root"
            ):
                self.bridge.emit_backtranslation_run(
                    trace=changed, condition_root=root,
                    artifact_root=self.fixture.root / f"escape_output_{mode}",
                    cross_run_parents=[self.human_parent()], dry_run=True,
                )

    def test_provider_exception_is_preserved_in_self_refined_manifest_denominator(self) -> None:
        failing_root = self.fixture.root / "self_provider_failure"
        failing_adapter = RecordingMockAdapter([])
        trace = run_self_refined(
            pairing_id=self.one.pairing_id,
            prepared_reference=self.fixture.prepared,
            one_shot_code_path=self.one_root / str(self.one.rounds[-1].code_path),
            expected_one_shot_hash=self.one.final_code_hash or "",
            run_root=failing_root,
            adapter=failing_adapter,
            renderer=self.renderer,
            policy=self.fixture.policy,
        )
        self.assertEqual(1, len(failing_adapter.calls))
        self.assertEqual(1, trace.provider_calls)
        self.assertIn("generation_error", trace.failure_codes)
        self.assertNotIn("malformed_code", trace.failure_codes)
        result = self.bridge.emit_backtranslation_run(
            trace=trace, condition_root=failing_root,
            artifact_root=self.fixture.root / "self_provider_failure_evidence",
            cross_run_parents=[self.one_shot_parent()], dry_run=True,
        )
        claim = next(item for item in result.public_manifest["claims"] if item["claim_id"].endswith("attempt-denominator"))
        self.assertIn("2 attempted candidate generations; 1 failed attempts", claim["statement"])

    def test_bridge_validates_local_license_snapshot_files_at_emission(self) -> None:
        source = ROOT / "experiments" / "backtranslation" / "v1" / "licenses"
        for mode in ("missing", "tampered"):
            with tempfile.TemporaryDirectory(prefix=f"license_{mode}_") as raw:
                license_root = Path(raw) / "licenses"
                shutil.copytree(source, license_root)
                target = license_root / "manim-LICENSE.community.txt"
                if mode == "missing":
                    target.unlink()
                else:
                    target.write_text("tampered\n", encoding="utf-8")
                bridge = PaperMediaEvidenceBridge(
                    registry_path=REGISTRY_PATH, protocol_path=PROTOCOL_PATH,
                    pipeline_repository="https://github.com/colinzhaoust/4blue2brown-progress",
                    pipeline_commit=self.commit, license_snapshot_root=license_root,
                )
                with self.subTest(mode=mode), self.assertRaisesRegex(
                    ManifestBridgeError, "license snapshot"
                ):
                    bridge.emit_human_run(
                        human=HumanConditionInput(
                            pairing_id=self.one.pairing_id, prepared_reference=self.fixture.prepared,
                        ),
                        artifact_root=self.fixture.root / f"license_{mode}_evidence",
                    )

    def test_manifest_records_declared_combined_dependency_lock(self) -> None:
        expected = ROOT / "requirements-backtranslation-evidence.txt"
        execution = self.results.one_shot.canonical_manifest["execution"]
        self.assertEqual(expected.name, execution["dependency_lock_ref"])
        self.assertEqual("sha256:" + hashlib.sha256(expected.read_bytes()).hexdigest(), execution["dependency_lock_hash"])

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
            command = [sys.executable, "tools/run_backtranslation.py", "dry-run", "--work-dir", str(work)]
            self.assertEqual(sys.executable, command[0])
            process = subprocess.run(
                command,
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
