import copy
import json
import subprocess
import unittest
from pathlib import Path

from tools.harvest_q8_babel_evidence import HarvestValidationError, normalize_capture
from tools.real_video_matrix import MatrixValidationError, materialize, validate_config


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "experiments" / "real_video_matrix" / "v1" / "config.json"
HARVEST = ROOT / "experiments" / "real_video_matrix" / "v1" / "babel" / "9313462-harvest-input.json"
RESULT = ROOT / "experiments" / "real_video_matrix" / "v1" / "babel" / "9313462-result.json"


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


class MatrixContractTests(unittest.TestCase):
    def test_matrix_has_exact_requested_axes_and_no_author_set_completion(self):
        config = load_config()
        validate_config(config)
        self.assertEqual(12, len(config["cells"]))
        self.assertTrue(all("completion" not in cell for cell in config["cells"]))
        self.assertNotIn("synthetic_fixture", {cell["implementation_origin"] for cell in config["cells"]})

    def test_missing_and_duplicate_cells_are_rejected(self):
        config = load_config()
        config["cells"].pop()
        with self.assertRaisesRegex(MatrixValidationError, "matrix-cardinality"):
            validate_config(config)
        config = load_config()
        config["cells"][-1] = copy.deepcopy(config["cells"][0])
        with self.assertRaisesRegex(MatrixValidationError, "matrix-coverage"):
            validate_config(config)

    def test_completion_is_derived_from_q5_contract(self):
        report = materialize(load_config(), ROOT)
        self.assertEqual({"full": 0, "partial": 10, "blocked": 2}, report["summary"])
        self.assertEqual(12, report["denominator"])
        self.assertEqual(12, sum(report["summary"].values()))

    def _full_candidate(self):
        config = load_config()
        cell = next(cell for cell in config["cells"] if cell["pipeline_id"] == "inhouse_v0")
        cell["status"] = "completed"
        next(stage for stage in cell["stages"] if stage["id"] == "provenance")["status"] = "succeeded"
        return config, cell["cell_id"]

    def test_full_gate_binds_revision_artifact_review_and_cost(self):
        config, full_id = self._full_candidate()
        report = materialize(config, ROOT)
        self.assertEqual("full", next(cell for cell in report["cells"] if cell["cell_id"] == full_id)["completion"])
        mutations = []
        broken, _ = self._full_candidate()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["repository_revision"]["commit"] = "a" * 40
        mutations.append((broken, "pinned-revision-not-approved", validate_config))
        broken, _ = self._full_candidate()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["cost"]["excluded_coverage"] = []
        mutations.append((broken, "cost-coverage-incomplete", validate_config))
        broken, _ = self._full_candidate()
        cell = next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)
        local = next(item for item in cell["artifacts"] if item["role"] == "rendered_video")
        local["local_path"] = "progress_site/assets/videos/DPOPreferenceExplainer.mp4"
        mutations.append((broken, "artifact-hash-mismatch", lambda value: materialize(value, ROOT)))
        broken, _ = self._full_candidate()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["reviews"][0]["result"] = "needs_revision"
        mutations.append((broken, "full-review-not-pass", lambda value: materialize(value, ROOT)))
        broken, _ = self._full_candidate()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["reviews"][0]["subject_ref"] = "artifact:wrong"
        mutations.append((broken, "full-review-subject-mismatch", lambda value: materialize(value, ROOT)))
        broken, _ = self._full_candidate()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["reviews"][0]["evidence_refs"][0]["content_hash"] = "sha256:" + "c" * 64
        mutations.append((broken, "full-review-evidence-hash-mismatch", lambda value: materialize(value, ROOT)))
        broken, _ = self._full_candidate()
        cell = next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)
        cell["artifacts"] = [{"artifact_id": "artifact:remote", "role": "rendered_video", "remote_path": "/remote/video.mp4", "content_hash": "sha256:" + "a" * 64}]
        mutations.append((broken, "full-local-deliverable-missing", lambda value: materialize(value, ROOT)))
        for value, error, validator in mutations:
            with self.subTest(error=error), self.assertRaisesRegex((MatrixValidationError, TypeError), error):
                validator(value)

    def test_observed_artifacts_are_clean_checkout_safe_and_git_tracked(self):
        config = load_config()
        for cell in (item for item in config["cells"] if item["artifacts"]):
            local = next(artifact["local_path"] for artifact in cell["artifacts"] if artifact["role"] == "rendered_video")
            self.assertTrue((ROOT / local).is_file())
            if (ROOT / ".git").exists():
                proc = subprocess.run(["git", "ls-files", "--error-unmatch", local], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, proc.returncode, local)

    def test_committed_report_is_byte_reproducible(self):
        expected = ROOT / "experiments" / "real_video_matrix" / "v1" / "report.json"
        rendered = json.dumps(materialize(load_config(), ROOT), indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(expected.read_text(encoding="utf-8"), rendered)

    def test_inhouse_is_source_embedded_not_paper_native(self):
        report = materialize(load_config(), ROOT)
        cells = [cell for cell in report["cells"] if cell["pipeline_id"] == "inhouse_v0"]
        self.assertTrue(all(cell["input_contract_mode"] == "source_embedded" for cell in cells))
        self.assertTrue(all(cell["execution_inputs"][0]["path"] == "scenes/inhouse_paper_explainer_suite.py" for cell in cells))
        self.assertTrue(all(cell["execution_inputs"][0]["consumed"] is True for cell in cells))
        self.assertTrue(all(all(ref.get("consumed") is False for ref in cell["reference_materials"]) for cell in cells))
        self.assertTrue(all("topic_reference_snapshot" in cell and "input_snapshot" not in cell for cell in cells))

    def test_harvest_reproduces_committed_babel_result(self):
        capture = json.loads(HARVEST.read_text(encoding="utf-8"))
        actual = normalize_capture(capture, Path("experiments/real_video_matrix/v1/babel/9313462-harvest-input.json"))
        expected = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)
        broken = copy.deepcopy(capture)
        broken["accounting"]["exit_code"] = "1:0"
        with self.assertRaisesRegex(HarvestValidationError, "job-nonzero-exit"):
            normalize_capture(broken, HARVEST)

    def test_roadmap_upstream_shortlist_is_not_silently_rewritten(self):
        note = load_config()["design_reconciliation"]
        self.assertEqual("inhouse_v0", note["q8_matrix_third_pipeline"])
        self.assertEqual("theorem_explain_agent", note["roadmap_upstream_third_pipeline"])
        self.assertEqual("separate_follow_up", note["resolution"])


if __name__ == "__main__":
    unittest.main()
