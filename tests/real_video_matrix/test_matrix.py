import copy
import json
import unittest
from pathlib import Path

from tools.real_video_matrix import MatrixValidationError, materialize, validate_config


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "experiments" / "real_video_matrix" / "v1" / "config.json"


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


class MatrixContractTests(unittest.TestCase):
    def test_matrix_has_exact_requested_axes_and_no_dummy_cells(self):
        config = load_config()
        validate_config(config)
        self.assertEqual(12, len(config["cells"]))
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

    def test_full_requires_pinned_revision_measured_cost_and_review(self):
        config = load_config()
        cell = next(cell for cell in config["cells"] if cell["completion"] == "full")
        for field, error in (("repository_revision", "full-unpinned-revision"), ("cost", "full-unmeasured-cost"), ("quality_reviews", "full-no-review")):
            broken = load_config()
            target = next(item for item in broken["cells"] if item["cell_id"] == cell["cell_id"])
            if field == "repository_revision":
                target[field] = {"availability": "unknown"}
            elif field == "cost":
                target[field] = {"availability": "unavailable"}
            else:
                target[field] = []
            with self.subTest(field=field), self.assertRaisesRegex(MatrixValidationError, error):
                validate_config(broken)

    def test_report_keeps_all_failures_in_denominator_and_hashes_inputs(self):
        report = materialize(load_config(), ROOT)
        self.assertEqual(12, report["denominator"])
        self.assertEqual(12, sum(report["summary"].values()))
        self.assertTrue(all(cell["input_snapshot"]["content_hash"].startswith("sha256:") for cell in report["cells"]))

    def test_materialization_rejects_missing_full_artifact(self):
        config = load_config()
        cell = next(cell for cell in config["cells"] if cell["completion"] == "full")
        cell["artifacts"][0]["local_path"] = "runs/does-not-exist/q8.mp4"
        with self.assertRaisesRegex(MatrixValidationError, "full-artifact-missing"):
            materialize(config, ROOT)

    def test_roadmap_upstream_shortlist_is_not_silently_rewritten(self):
        config = load_config()
        note = config["design_reconciliation"]
        self.assertEqual("inhouse_v0", note["q8_matrix_third_pipeline"])
        self.assertEqual("theorem_explain_agent", note["roadmap_upstream_third_pipeline"])
        self.assertEqual("separate_follow_up", note["resolution"])


if __name__ == "__main__":
    unittest.main()
