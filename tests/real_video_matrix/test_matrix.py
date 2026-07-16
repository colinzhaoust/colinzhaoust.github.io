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
        self.assertEqual({"full": 4, "partial": 6, "blocked": 2}, report["summary"])
        self.assertEqual(12, report["denominator"])
        self.assertEqual(12, sum(report["summary"].values()))

    def test_full_gate_rejects_shallow_provenance_review_artifact_and_cost(self):
        config = load_config()
        full_id = next(cell["cell_id"] for cell in config["cells"] if cell["status"] == "completed")
        mutations = []
        broken = load_config()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["repository_revision"] = {"availability": "pinned"}
        mutations.append((broken, "pinned-revision-invalid", validate_config))
        broken = load_config()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["reviews"] = ["not-a-review-event"]
        mutations.append((broken, "review-unstructured", validate_config))
        broken = load_config()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["cost"]["excluded_coverage"] = []
        mutations.append((broken, "cost-coverage-incomplete", validate_config))
        broken = load_config()
        next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)["repository_revision"]["source_hashes"]["scenes/inhouse_paper_explainer_suite.py"] = "sha256:" + "b" * 64
        mutations.append((broken, "full-input-hash-mismatch", lambda value: materialize(value, ROOT)))
        broken = load_config()
        cell = next(cell for cell in broken["cells"] if cell["cell_id"] == full_id)
        cell["artifacts"] = [{"role": "rendered_video", "remote_path": "/remote/video.mp4", "content_hash": "sha256:" + "a" * 64}]
        mutations.append((broken, "full-local-deliverable-missing", lambda value: materialize(value, ROOT)))
        for value, error, validator in mutations:
            with self.subTest(error=error), self.assertRaisesRegex((MatrixValidationError, TypeError), error):
                validator(value)

    def test_full_artifacts_are_clean_checkout_safe_and_git_tracked(self):
        config = load_config()
        for cell in (item for item in config["cells"] if item["status"] == "completed"):
            local = next(artifact["local_path"] for artifact in cell["artifacts"] if artifact["role"] == "rendered_video")
            self.assertTrue((ROOT / local).is_file())
            if (ROOT / ".git").exists():
                proc = subprocess.run(["git", "ls-files", "--error-unmatch", local], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, proc.returncode, local)

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
