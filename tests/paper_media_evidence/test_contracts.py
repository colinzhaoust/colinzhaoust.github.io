from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.paper_media_evidence.completion import derive_completion
from tools.paper_media_evidence.constants import CANONICAL_SCHEMA_PATH, COMPLETION_SCHEMA_PATH, PUBLIC_SCHEMA_PATH
from tools.paper_media_evidence.migration import migrate_legacy_baseline
from tools.paper_media_evidence.projection import project_public_manifest, write_public_manifest_atomic
from tools.paper_media_evidence.validation import ManifestValidationError, validate_canonical, validate_public

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "valid_full.json"
LEGACY = ROOT / "progress_site" / "assets" / "baseline-coverage" / "manifests" / "manifest.json"


def load_valid():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class SchemaTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self):
        for path in (CANONICAL_SCHEMA_PATH, COMPLETION_SCHEMA_PATH, PUBLIC_SCHEMA_PATH):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_valid_full_and_public_projection(self):
        manifest = load_valid()
        validate_canonical(manifest)
        self.assertEqual(derive_completion(manifest), "full")
        public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        validate_public(public)
        self.assertNotIn("execution", public)
        self.assertNotIn("private_path", public["artifacts"][0])

    def test_unknown_field_is_rejected(self):
        manifest = load_valid()
        manifest["unexpected"] = "nope"
        with self.assertRaises(ManifestValidationError):
            validate_canonical(manifest)

    def test_adapted_requires_adapter(self):
        manifest = load_valid()
        manifest["lineage"]["input_contract_mode"] = "adapted"
        with self.assertRaisesRegex(ManifestValidationError, "adapted-without-adapter"):
            validate_canonical(manifest)

    def test_partial_and_placeholder_are_derived(self):
        partial = load_valid()
        partial["stages"][1]["status"] = "not_started"
        partial["stages"][1]["started_at"] = None
        partial["stages"][1]["ended_at"] = None
        partial["completion"]["derived_value"] = "partial"
        self.assertEqual(derive_completion(partial), "partial")
        validate_canonical(partial)

        placeholder = load_valid()
        placeholder["lineage"]["implementation_origin"] = "synthetic_fixture"
        placeholder["artifacts"][0]["lineage"]["implementation_origin"] = "synthetic_fixture"
        placeholder["artifacts"][0]["completion"] = "placeholder"
        placeholder["completion"]["derived_value"] = "placeholder"
        self.assertEqual(derive_completion(placeholder), "placeholder")
        validate_canonical(placeholder)

    def test_manual_completion_mismatch_is_rejected(self):
        manifest = load_valid()
        manifest["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "not-machine-derived"):
            validate_canonical(manifest)

    def test_graph_type_and_review_rules(self):
        manifest = load_valid()
        manifest["graph"]["nodes"] = [
            {"node_id": "node:code", "node_type": "code", "coverage_state": "observed", "aliases": ["old:code"]},
            {"node_id": "node:formula", "node_type": "formula", "coverage_state": "observed", "aliases": []},
        ]
        manifest["graph"]["migrations"] = [
            {"old_id": "old:code", "new_id": "node:code", "reason": "rename", "version": "0.1.0", "migrated_at": "2026-07-15T12:00:00Z"}
        ]
        manifest["graph"]["edges"] = [
            {"edge_id": "edge:implements", "edge_type": "implements", "source_ref": "node:code", "target_ref": "node:formula", "match_state": "confirmed", "evidence_refs": ["artifact:video"], "confidence": 0.9, "review_ref": "review:graph"}
        ]
        manifest["reviews"].append(
            {"review_id": "review:graph", "subject_ref": "edge:implements", "rubric_id": "graph-match/1.0.0", "evaluator": {"type": "human", "id": "reviewer"}, "result": "pass", "evidence_refs": ["artifact:video"], "reviewed_at": "2026-07-15T12:02:00Z", "notes": None}
        )
        validate_canonical(manifest)
        manifest["graph"]["edges"][0]["source_ref"] = "node:formula"
        with self.assertRaisesRegex(ManifestValidationError, "disallowed-types"):
            validate_canonical(manifest)

    def test_cost_gate_fails_closed_on_unknown_projection(self):
        manifest = load_valid()
        manifest["budget"]["paid_stage_gate"]["projected_next_stage_usd"] = None
        with self.assertRaisesRegex(ManifestValidationError, "allowed-with-unknown-projection"):
            validate_canonical(manifest)


class ProjectionTests(unittest.TestCase):
    def test_unsafe_command_leaves_no_output(self):
        manifest = load_valid()
        manifest["execution"]["command"].append("/Users/person/private.py")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "public.json"
            with self.assertRaisesRegex(ManifestValidationError, "unsafe-command"):
                write_public_manifest_atomic(manifest, destination)
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_secret_pii_private_source_and_host_metadata_fail(self):
        mutations = []
        secret = load_valid(); secret["claims"][0]["statement"] = "token=abcdefghijk"; mutations.append(secret)
        pii = load_valid(); pii["claims"][0]["statement"] = "owner@example.com"; mutations.append(pii)
        private = load_valid(); private["input"]["code_snapshot"]["source_visibility"] = "private"; mutations.append(private)
        host = load_valid(); host["execution"]["host_metadata"] = {"hostname": "worker-1"}; mutations.append(host)
        for manifest in mutations:
            with self.subTest(manifest=manifest):
                with self.assertRaises(ManifestValidationError):
                    project_public_manifest(manifest)


class MigrationTests(unittest.TestCase):
    def test_existing_manifest_migrates_deterministically_and_honestly(self):
        raw = LEGACY.read_bytes()
        legacy = json.loads(raw)
        before = copy.deepcopy(legacy)
        kwargs = {"source_path": LEGACY.relative_to(ROOT).as_posix(), "source_hash": "sha256:" + hashlib.sha256(raw).hexdigest()}
        first = migrate_legacy_baseline(legacy, **kwargs)
        second = migrate_legacy_baseline(legacy, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(legacy, before)
        self.assertEqual(len(first), 20)
        self.assertEqual(sum(len(item["artifacts"]) for item in first), 25)
        self.assertEqual(sum(a["completion"] == "placeholder" for m in first for a in m["artifacts"]), 20)
        self.assertEqual(sum(a["completion"] == "partial" for m in first for a in m["artifacts"]), 5)
        transformer_runs = [m for m in first if m["input"]["canonical_topic_family"] == "transformer_attention"]
        self.assertEqual(len(transformer_runs), 5)
        self.assertTrue(all(len(item["artifacts"]) == 2 for item in transformer_runs))
        for manifest in first:
            validate_canonical(manifest)
            self.assertEqual(manifest["status"], "migration_pending")
            self.assertIsNone(manifest["budget"]["measured_usd"])
            with self.assertRaises(ManifestValidationError):
                project_public_manifest(manifest)


class CliTests(unittest.TestCase):
    def test_cli_exit_codes_and_atomic_failure(self):
        python = str(ROOT / ".venv-evidence" / "bin" / "python")
        if not Path(python).exists():
            self.skipTest("isolated evidence runtime not installed")
        valid = subprocess.run([python, "-m", "tools.paper_media_evidence.cli", "validate", str(FIXTURE)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        with tempfile.TemporaryDirectory() as directory:
            unsafe_path = Path(directory) / "unsafe.json"
            unsafe = load_valid(); unsafe["unexpected"] = True
            unsafe_path.write_text(json.dumps(unsafe), encoding="utf-8")
            output = Path(directory) / "public.json"
            failed = subprocess.run([python, "-m", "tools.paper_media_evidence.cli", "project", str(unsafe_path), str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
