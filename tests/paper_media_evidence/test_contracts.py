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
from tools.paper_media_evidence.constants import CANONICAL_SCHEMA_PATH, COMPLETION_SCHEMA_PATH, PROJECTION_POLICY_PATH, PUBLIC_SCHEMA_PATH
from tools.paper_media_evidence.migration import migrate_legacy_baseline, migrate_legacy_file
from tools.paper_media_evidence.projection import _scan_projected, project_public_manifest, write_public_manifest_atomic
from tools.paper_media_evidence.validation import ManifestValidationError, validate_canonical, validate_public

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "valid_full.json"
LEGACY = ROOT / "progress_site" / "assets" / "baseline-coverage" / "manifests" / "manifest.json"


def load_valid():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def no_cost(manifest):
    manifest["budget"]["reservations"] = []
    manifest["budget"]["paid_stage_gate"] = {"next_stage_id": None, "reservation_id": None, "projected_next_stage_usd": None, "decision": "not_applicable"}
    manifest["budget"]["measured_usd"] = 0
    manifest["budget"]["estimated_usd"] = 0
    manifest["stages"][1]["billing_class"] = "free"


def load_backtranslation():
    manifest = load_valid()
    manifest["thread"] = "backtranslation"
    manifest["input"] = {
        "canonical_topic_family": "scene:attention-example",
        "granularity": "clip",
        "source_snapshots": [
            {"availability": "available", "source_id": "input:manim", "source_type": "repository", "source_url": "https://github.com/ManimCommunity/manim", "revision": "1234567890abcdef1234567890abcdef12345678", "retrieved_at": "2026-07-15T11:00:00Z", "content_hash": "sha256:" + "1" * 64, "source_visibility": "public", "publication_decision": "allowed"},
            {"availability": "available", "source_id": "input:gallery", "source_type": "example_gallery", "source_url": "https://example.org/manim-gallery", "revision": "gallery-v1", "retrieved_at": "2026-07-15T11:00:00Z", "content_hash": "sha256:" + "2" * 64, "source_visibility": "public", "publication_decision": "allowed"},
        ],
    }
    repository_license = copy.deepcopy(manifest["license_ledger"][1])
    repository_license.update({"item_id": "license:manim", "source_ref": "input:manim", "source_url": "https://github.com/ManimCommunity/manim", "source_revision": "1234567890abcdef1234567890abcdef12345678", "content_hash": "sha256:" + "1" * 64})
    gallery_license = copy.deepcopy(manifest["license_ledger"][0])
    gallery_license.update({"item_id": "license:gallery", "source_ref": "input:gallery", "resource_type": "example_gallery", "source_url": "https://example.org/manim-gallery", "source_revision": "gallery-v1", "content_hash": "sha256:" + "2" * 64, "declared_spdx": "MIT"})
    manifest["license_ledger"] = [repository_license, gallery_license]
    return manifest


class SchemaTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self):
        for path in (CANONICAL_SCHEMA_PATH, COMPLETION_SCHEMA_PATH, PUBLIC_SCHEMA_PATH):
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_valid_full_and_expanded_public_projection(self):
        manifest = load_valid()
        validate_canonical(manifest)
        self.assertEqual("full", derive_completion(manifest))
        public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        validate_public(public)
        for key in ("input", "condition", "validations", "graph", "repair_summary", "publication_validator_version"):
            self.assertIn(key, public)
        self.assertNotIn("execution", public)
        self.assertNotIn("private_path", public["artifacts"][0])
        self.assertGreater(public["redaction_summary"]["omitted_fields"], 0)

    def test_backtranslation_uses_repository_and_gallery_without_fake_paper(self):
        manifest = load_backtranslation()
        validate_canonical(manifest)
        public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        self.assertEqual({"repository", "example_gallery"}, {item["source_type"] for item in public["input"]["source_snapshots"]})
        self.assertNotIn("paper_snapshot", json.dumps(public))

    def test_backtranslation_requires_bound_repository_and_gallery_licenses(self):
        for missing_ref in ("input:manim", "input:gallery"):
            manifest = load_backtranslation()
            manifest["license_ledger"] = [item for item in manifest["license_ledger"] if item["source_ref"] != missing_ref]
            with self.subTest(missing_ref=missing_ref), self.assertRaisesRegex(ManifestValidationError, "source-coverage"):
                validate_canonical(manifest)

    def test_paper_threads_still_require_paper_and_repository_sources(self):
        for missing_type in ("paper", "repository"):
            manifest = load_valid()
            removed_ids = {item["source_id"] for item in manifest["input"]["source_snapshots"] if item["source_type"] == missing_type}
            manifest["input"]["source_snapshots"] = [item for item in manifest["input"]["source_snapshots"] if item["source_type"] != missing_type]
            manifest["license_ledger"] = [item for item in manifest["license_ledger"] if item["source_ref"] not in removed_ids]
            with self.subTest(missing_type=missing_type), self.assertRaisesRegex(ManifestValidationError, "thread-minimum-coverage"):
                validate_canonical(manifest)

    def test_legacy_paper_code_source_shape_remains_compatible(self):
        manifest = load_valid()
        del manifest["input"]["source_snapshots"]
        manifest["license_ledger"] = [item for item in manifest["license_ledger"] if item["resource_type"] in {"paper", "repository"}]
        repository_license = next(item for item in manifest["license_ledger"] if item["resource_type"] == "repository")
        repository_license.update({
            "source_url": manifest["input"]["code_snapshot"]["source_url"],
            "source_revision": manifest["input"]["code_snapshot"]["revision"],
            "content_hash": manifest["input"]["code_snapshot"]["content_hash"],
        })
        validate_canonical(manifest)
        public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        self.assertEqual({"paper", "repository"}, {item["source_type"] for item in public["input"]["source_snapshots"]})

    def test_pairing_id_is_schema_checked_and_preserved(self):
        manifest = load_backtranslation()
        manifest["pairing_id"] = "pair:attention-example:r1"
        validate_canonical(manifest)
        public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        self.assertEqual(manifest["pairing_id"], public["pairing_id"])
        manifest["pairing_id"] = " invalid pairing "
        with self.assertRaises(ManifestValidationError):
            validate_canonical(manifest)

    def test_unknown_field_and_missing_pin_at_run_fields_are_rejected(self):
        manifest = load_valid(); manifest["unexpected"] = "nope"
        with self.assertRaises(ManifestValidationError):
            validate_canonical(manifest)
        for field in ("prompt_bundle_hash", "tool_policy_hash", "random_seed", "container_digest", "renderer_versions", "hardware", "environment"):
            manifest = load_valid(); del manifest["execution"][field]
            with self.subTest(field=field), self.assertRaises(ManifestValidationError):
                validate_canonical(manifest)

    def test_exact_artifact_validation_binding_is_bidirectional(self):
        manifest = load_valid(); manifest["validations"][0]["subject_ref"] = "artifact:missing"
        with self.assertRaisesRegex(ManifestValidationError, "validation-subject|not-bound-by-subject"):
            validate_canonical(manifest)
        manifest = load_valid(); manifest["artifacts"][0]["validation_refs"] = []
        manifest["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "not-bound-by-subject"):
            validate_canonical(manifest)

    def test_graph_review_evidence_and_policy_are_edge_bound(self):
        mutations = []
        wrong_subject = load_valid(); wrong_subject["reviews"][1]["subject_ref"] = "artifact:video"; mutations.append((wrong_subject, "review-not-bound"))
        wrong_rubric = load_valid(); wrong_rubric["reviews"][1]["rubric_id"] = "other-rubric/1.0.0"; mutations.append((wrong_rubric, "review-policy"))
        missing_evidence = load_valid(); missing_evidence["graph"]["edges"][0]["evidence_refs"] = ["artifact:missing"]; mutations.append((missing_evidence, "unresolved-evidence"))
        mismatched_result = load_valid(); mismatched_result["reviews"][1]["result"] = "fail"; mutations.append((mismatched_result, "review-evidence-or-result"))
        for manifest, error in mutations:
            with self.subTest(error=error), self.assertRaisesRegex(ManifestValidationError, error):
                validate_canonical(manifest)

    def test_local_and_external_parent_identity(self):
        local = load_valid()
        local["lineage"]["parent_artifact_refs"] = [{
            "scope": "local", "run_id": local["run_id"], "artifact_id": "artifact:video", "relation": "derived_from",
            "content_hash": local["artifacts"][0]["content_hash"], "canonical_manifest_hash": None,
        }]
        validate_canonical(local)
        local["lineage"]["parent_artifact_refs"][0]["content_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ManifestValidationError, "unresolved-local-parent"):
            validate_canonical(local)

        external = load_valid()
        parent = {"scope": "external", "run_id": "run.parent", "artifact_id": "artifact:parent", "relation": "refined_from", "content_hash": "sha256:" + "1" * 64, "canonical_manifest_hash": "sha256:" + "2" * 64}
        external["lineage"]["parent_artifact_refs"] = [parent]
        external["external_lineage"] = [{"run_id": "run.parent", "artifact_id": "artifact:parent", "content_hash": parent["content_hash"], "canonical_manifest_hash": parent["canonical_manifest_hash"], "evidence_ref": "evidence/parents/run-parent.json", "source_visibility": "public"}]
        validate_canonical(external)
        external["external_lineage"][0]["canonical_manifest_hash"] = "sha256:" + "3" * 64
        with self.assertRaisesRegex(ManifestValidationError, "unresolved-external-parent"):
            validate_canonical(external)

    def test_completion_matrix_and_contradictions(self):
        self.assertEqual("full", derive_completion(load_valid()))

        partial = load_valid(); partial["status"] = "stopped"; partial["completion_contract"]["smoke_stages"] = []; partial["completion"]["derived_value"] = "partial"
        self.assertEqual("partial", derive_completion(partial)); validate_canonical(partial)

        running = load_valid(); running["status"] = "running"; running["ended_at"] = None; running["completion_contract"]["smoke_stages"] = []; running["completion"]["derived_value"] = "partial"
        self.assertEqual("partial", derive_completion(running)); validate_canonical(running)

        failed = load_valid(); failed["status"] = "failed"; failed["completion"]["derived_value"] = "failed"
        self.assertEqual("failed", derive_completion(failed)); validate_canonical(failed)

        placeholder = load_valid(); placeholder["lineage"]["implementation_origin"] = "synthetic_fixture"; placeholder["artifacts"][0]["lineage"]["implementation_origin"] = "synthetic_fixture"; placeholder["artifacts"][0]["completion"] = "placeholder"; placeholder["completion"]["derived_value"] = "placeholder"
        self.assertEqual("placeholder", derive_completion(placeholder)); validate_canonical(placeholder)

        smoke = load_valid(); smoke["artifacts"] = []; smoke["validations"] = []; smoke["claims"] = []; smoke["reviews"] = []; smoke["graph"] = {"nodes": [], "edges": [], "migrations": []}; smoke["stages"][1].update({"status": "not_started", "started_at": None, "ended_at": None, "evidence_refs": []}); no_cost(smoke); smoke["completion"]["derived_value"] = "smoke"
        self.assertEqual("smoke", derive_completion(smoke)); validate_canonical(smoke)

        real_smoke = load_valid(); real_smoke["artifacts"][0]["completion"] = "smoke"; real_smoke["stages"][1].update({"status": "not_started", "started_at": None, "ended_at": None, "evidence_refs": []}); no_cost(real_smoke); real_smoke["completion"]["derived_value"] = "smoke"
        self.assertEqual("smoke", derive_completion(real_smoke)); validate_canonical(real_smoke)

        for status in ("running", "failed"):
            manifest = load_valid(); manifest["status"] = status; manifest["ended_at"] = None if status == "running" else manifest["ended_at"]
            with self.subTest(status=status), self.assertRaisesRegex(ManifestValidationError, "not-machine-derived|nonterminal-or-failed-full"):
                validate_canonical(manifest)

    def test_artifact_completion_cannot_contradict_evidence(self):
        manifest = load_valid(); manifest["validations"][0]["result"] = "fail"; manifest["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "full-without-evidence"):
            validate_canonical(manifest)
        manifest = load_valid(); manifest["artifacts"][0]["completion"] = "placeholder"; manifest["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "placeholder-origin"):
            validate_canonical(manifest)

    def test_cost_atomic_identity_reconciliation_and_limits(self):
        mutations = []
        identity = load_valid(); identity["budget"]["reservations"][0]["cell_id"] = "other:cell"; mutations.append((identity, "identity-mismatch"))
        measured = load_valid(); measured["budget"]["measured_usd"] = 1.2; mutations.append((measured, "measured-total-contradiction"))
        unknown = load_valid(); unknown["budget"]["rate_card"] = {"availability": "unavailable", "reason": "unknown"}; mutations.append((unknown, "paid-without-rate-card|allowed-with-unknown-projection"))
        limit = load_valid(); limit["budget"]["cell_spend_before_usd"] = 14.5; mutations.append((limit, "cell-limit-exceeded"))
        projected_limit = load_valid(); projected_limit["budget"]["reservations"][0]["projected_usd"] = 16; projected_limit["budget"]["paid_stage_gate"]["projected_next_stage_usd"] = 16; mutations.append((projected_limit, "cell-reservation-over-limit"))
        unreconciled = load_valid(); unreconciled["budget"]["reservations"][0].update({"status": "active", "reconciled_at": None, "reconciled_usd": None, "usage_evidence_ref": None}); unreconciled["budget"]["measured_usd"] = None; mutations.append((unreconciled, "terminal-paid-stage-unreconciled"))
        for manifest, error in mutations:
            with self.subTest(error=error), self.assertRaisesRegex(ManifestValidationError, error):
                validate_canonical(manifest)

    def test_zero_spend_released_and_expired_terminal_paid_stages(self):
        for reservation_status, run_status in (("released", "failed"), ("expired", "stopped")):
            manifest = load_valid()
            manifest["status"] = run_status
            manifest["stages"][1].update({"status": "failed", "stop_reason": "provider rejected the request"})
            manifest["budget"]["reservations"][0].update({
                "status": reservation_status,
                "reconciled_at": "2026-07-15T12:02:00Z",
                "reconciled_usd": 0,
                "usage_evidence_ref": "evidence/cost/zero-spend.json",
            })
            manifest["budget"]["measured_usd"] = 0
            if run_status == "stopped":
                manifest["artifacts"][0]["completion"] = "smoke"
            manifest["completion"]["derived_value"] = derive_completion(manifest)
            with self.subTest(status=reservation_status):
                validate_canonical(manifest)
                public = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
                self.assertEqual(reservation_status, public["cost"]["reservation_state"])

        nonzero = load_valid(); nonzero["status"] = "failed"; nonzero["stages"][1].update({"status": "failed", "stop_reason": "failed"}); nonzero["budget"]["reservations"][0].update({"status": "released", "reconciled_usd": 0.1}); nonzero["budget"]["measured_usd"] = 0.1; nonzero["completion"]["derived_value"] = "failed"
        with self.assertRaisesRegex(ManifestValidationError, "released-or-expired-nonzero"):
            validate_canonical(nonzero)

        incomplete = load_valid(); incomplete["status"] = "failed"; incomplete["stages"][1].update({"status": "failed", "stop_reason": "failed"}); incomplete["budget"]["reservations"][0].update({"status": "expired", "reconciled_at": None, "reconciled_usd": None, "usage_evidence_ref": None}); incomplete["budget"]["measured_usd"] = 0; incomplete["completion"]["derived_value"] = "failed"
        with self.assertRaisesRegex(ManifestValidationError, "incomplete-zero-spend-finalization"):
            validate_canonical(incomplete)

    def test_license_ledger_is_typed_and_reviewed(self):
        manifest = load_valid(); del manifest["license_ledger"][0]["reviewer"]
        with self.assertRaises(ManifestValidationError):
            validate_canonical(manifest)
        manifest = load_valid(); manifest["license_ledger"][0]["resource_type"] = "unknown"
        with self.assertRaises(ManifestValidationError):
            validate_canonical(manifest)

    def test_stage_and_failed_artifact_terminal_semantics(self):
        stage = load_valid(); stage["stages"][1]["ended_at"] = None; stage["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "terminal-timestamps"):
            validate_canonical(stage)
        artifact = load_valid(); artifact["artifacts"][0]["completion"] = "failed"; artifact["completion"]["derived_value"] = "partial"
        with self.assertRaisesRegex(ManifestValidationError, "failed-with-passing-evidence"):
            validate_canonical(artifact)


class ProjectionTests(unittest.TestCase):
    def test_dependency_closure_fails_for_private_or_missing_dependencies(self):
        private_validation = load_valid(); private_validation["validations"][0]["publishable"] = False
        private_node = load_valid(); private_node["graph"]["nodes"][0]["publishable"] = False
        private_review = load_valid(); private_review["reviews"][1]["publishable"] = False
        for manifest in (private_validation, private_node, private_review):
            with self.subTest(), self.assertRaisesRegex(ManifestValidationError, "closure"):
                project_public_manifest(manifest)
        public = project_public_manifest(load_valid(), generated_at="2026-07-15T13:00:00Z")
        public["claims"][0]["evidence_refs"] = ["artifact:missing"]
        with self.assertRaisesRegex(ManifestValidationError, "evidence-closure"):
            validate_public(public)

    def test_policy_rejects_paths_usernames_source_vault_and_sensitive_keys(self):
        unsafe_values = [
            "Stored at /Users/alice/run.json", "Stored at /home/bob/run.json", "Stored at C:\\Users\\alice\\run.json",
            "Read ../private/run.json", "Read /opt/internal/run.json", "username=alice", "copied from source-vault draft",
        ]
        for value in unsafe_values:
            manifest = load_valid(); manifest["claims"][0]["statement"] = value
            with self.subTest(value=value), self.assertRaises(ManifestValidationError):
                project_public_manifest(manifest)
        policy = json.loads(PROJECTION_POLICY_PATH.read_text(encoding="utf-8"))
        self.assertIn("publication:forbidden-projected-key", _scan_projected({"api_key": "redacted"}, policy))

    def test_private_unknown_repository_and_publication_decision_fail_closed(self):
        private = load_valid(); private["pipeline"]["repository_visibility"] = "private"
        unknown = load_valid(); unknown["pipeline"]["repository_visibility"] = "unknown"
        blocked = load_valid(); blocked["publication"]["decision"] = "blocked"
        source = load_valid(); next(item for item in source["input"]["source_snapshots"] if item["source_type"] == "repository")["publication_decision"] = "pending"
        for manifest in (private, unknown, blocked, source):
            with self.subTest(), self.assertRaises(ManifestValidationError):
                project_public_manifest(manifest)

    def test_redaction_summary_is_derived_from_actual_omissions(self):
        baseline = project_public_manifest(load_valid(), generated_at="2026-07-15T13:00:00Z")["redaction_summary"]
        manifest = load_valid()
        hidden = copy.deepcopy(manifest["artifacts"][0]); hidden.update({"artifact_id": "artifact:hidden", "private_path": "/private/hidden.mp4", "public_path": None, "content_hash": {"availability": "unavailable", "reason": "not retained"}, "completion": "failed", "validation_refs": [], "publishable": False})
        manifest["artifacts"].append(hidden)
        projected = project_public_manifest(manifest, generated_at="2026-07-15T13:00:00Z")
        self.assertEqual(baseline["omitted_artifacts"] + 1, projected["redaction_summary"]["omitted_artifacts"])
        self.assertGreater(projected["redaction_summary"]["omitted_fields"], baseline["omitted_fields"])

    def test_atomic_no_output_on_every_publication_failure(self):
        manifest = load_valid(); manifest["claims"][0]["statement"] = "token=abcdefghijk"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "public.json"
            with self.assertRaises(ManifestValidationError):
                write_public_manifest_atomic(manifest, destination)
            self.assertFalse(destination.exists())
            self.assertEqual([], list(Path(directory).iterdir()))


class MigrationTests(unittest.TestCase):
    def test_existing_manifest_migrates_deterministically_and_honestly(self):
        raw = LEGACY.read_bytes(); legacy = json.loads(raw); before = copy.deepcopy(legacy)
        source_location = {"kind": "repo_relative", "path": LEGACY.relative_to(ROOT).as_posix()}
        kwargs = {"source_location": source_location, "source_hash": "sha256:" + hashlib.sha256(raw).hexdigest()}
        first = migrate_legacy_baseline(legacy, **kwargs); second = migrate_legacy_baseline(legacy, **kwargs)
        self.assertEqual(first, second); self.assertEqual(legacy, before); self.assertEqual(20, len(first))
        self.assertEqual(25, sum(len(item["artifacts"]) for item in first))
        self.assertEqual(20, sum(a["completion"] == "placeholder" for m in first for a in m["artifacts"]))
        self.assertEqual(5, sum(a["completion"] == "partial" for m in first for a in m["artifacts"]))
        for manifest in first:
            validate_canonical(manifest)
            with self.assertRaises(ManifestValidationError):
                project_public_manifest(manifest)

    def test_absolute_path_migration_normalizes_or_hashes_private_location(self):
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "legacy.json"; external.write_bytes(LEGACY.read_bytes())
            manifests = migrate_legacy_file(external, repo_root=ROOT)
            location = manifests[0]["migration"]["source_location"]
            self.assertEqual("private_external", location["kind"])
            self.assertEqual("legacy.json", location["basename"])
            self.assertNotIn(directory, json.dumps(manifests))
            validate_canonical(manifests[0])
        in_repo = migrate_legacy_file(LEGACY.resolve(), repo_root=ROOT)
        self.assertEqual("repo_relative", in_repo[0]["migration"]["source_location"]["kind"])


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python = str(ROOT / ".venv-evidence" / "bin" / "python")
        if not Path(cls.python).exists():
            raise unittest.SkipTest("isolated evidence runtime not installed")

    def test_validate_project_failure_and_atomic_no_output(self):
        valid = subprocess.run([self.python, "-m", "tools.paper_media_evidence.cli", "validate", str(FIXTURE)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, valid.returncode, valid.stderr)
        with tempfile.TemporaryDirectory() as directory:
            unsafe_path = Path(directory) / "unsafe.json"; unsafe = load_valid(); unsafe["unexpected"] = True; unsafe_path.write_text(json.dumps(unsafe), encoding="utf-8")
            output = Path(directory) / "public.json"
            failed = subprocess.run([self.python, "-m", "tools.paper_media_evidence.cli", "project", str(unsafe_path), str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(2, failed.returncode); self.assertFalse(output.exists())

    def test_derive_completion_ignores_incorrect_stored_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.json"; manifest = load_valid(); manifest["completion"]["derived_value"] = "partial"; path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run([self.python, "-m", "tools.paper_media_evidence.cli", "derive-completion", str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr); self.assertEqual("full", result.stdout.strip())

    def test_absolute_path_migrate_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            result = subprocess.run([self.python, "-m", "tools.paper_media_evidence.cli", "migrate-legacy", str(LEGACY.resolve()), str(output), "--repo-root", str(ROOT)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            first = json.loads(sorted(output.glob("*.json"))[0].read_text(encoding="utf-8"))
            self.assertEqual("repo_relative", first["migration"]["source_location"]["kind"])


if __name__ == "__main__":
    unittest.main()
