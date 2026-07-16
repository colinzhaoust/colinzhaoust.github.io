from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.slides_baselines import initial_ledger, validate_matrix


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "experiments" / "slides_baselines" / "v1" / "matrix.json"
RESULTS = ROOT / "experiments" / "slides_baselines" / "v1" / "results.json"


def load_matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


class SlideBaselineMatrixTests(unittest.TestCase):
    def test_approved_matrix_is_valid_and_has_twelve_selected_cells(self):
        matrix = load_matrix()
        self.assertEqual([], validate_matrix(matrix))
        ledger = initial_ledger(matrix)
        self.assertEqual(12, len(ledger["cells"]))
        self.assertNotIn(
            "paper2slides_fast_academic_short",
            {cell["pipeline_id"] for cell in ledger["cells"]},
        )

    def test_pipeline_revision_and_license_hashes_are_required(self):
        for field in ("commit_sha", "license_sha256"):
            matrix = load_matrix()
            matrix["pipelines"][0][field] = "unknown"
            self.assertTrue(validate_matrix(matrix), field)

    def test_unfrozen_paper_is_fail_closed(self):
        matrix = load_matrix()
        transformer = next(item for item in matrix["papers"] if item["id"] == "transformers")
        transformer["snapshot_state"] = "not_staged"
        transformer["content_sha256"] = None
        ledger = initial_ledger(matrix)
        transformer_cells = [cell for cell in ledger["cells"] if cell["paper_id"] == "transformers"]
        self.assertTrue(all(cell["status"] == "blocked" for cell in transformer_cells))
        feynrl_cells = [cell for cell in ledger["cells"] if cell["paper_id"] == "feynrl"]
        self.assertTrue(all(cell["status"] == "not_started" for cell in feynrl_cells))

    def test_shortlist_substitution_is_rejected(self):
        matrix = copy.deepcopy(load_matrix())
        matrix["pipelines"][2]["id"] = "paper2slides"
        self.assertIn(
            "selected-pipelines-do-not-match-approved-shortlist",
            validate_matrix(matrix),
        )

    def test_duplicate_pipeline_or_missing_snapshot_time_is_rejected(self):
        matrix = load_matrix()
        matrix["pipelines"].append(copy.deepcopy(matrix["pipelines"][0]))
        self.assertIn("pipeline-ids-must-be-unique", validate_matrix(matrix))

        matrix = load_matrix()
        del matrix["papers"][0]["retrieved_at"]
        self.assertIn(
            "paper:transformers:frozen-without-retrieval-time",
            validate_matrix(matrix),
        )

    def test_preserved_results_match_inputs_and_do_not_claim_full_decks(self):
        matrix = load_matrix()
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        self.assertEqual(
            {"full": 0, "partial": 0, "smoke": 4, "blocked": 8},
            {key: results["matrix_summary"][key] for key in ("full", "partial", "smoke", "blocked")},
        )
        by_paper = {item["id"]: item for item in matrix["papers"]}
        by_pipeline = {item["pipeline_id"]: item for item in results["pipeline_results"]}
        self.assertEqual(
            {"deeppresenter_current", "slidegen", "arcdeck"},
            set(by_pipeline),
        )
        slidegen = by_pipeline["slidegen"]
        self.assertEqual("smoke", slidegen["completion"])
        self.assertEqual(0, slidegen["provider_calls"])
        self.assertEqual(0.0, slidegen["provider_cost_measured_usd"])
        self.assertEqual(4, len(slidegen["cells"]))
        for cell in slidegen["cells"]:
            self.assertEqual("COMPLETED", cell["state"])
            self.assertEqual("0:0", cell["exit_code"])
            self.assertEqual(by_paper[cell["paper_id"]]["content_sha256"], cell["input_sha256"])
            self.assertEqual(64, len(cell["artifact"]["sha256"]))
        self.assertFalse(results["fallback_result"]["selected_matrix_cell"])
        self.assertIsNone(results["fallback_result"]["provider_cost_measured_usd"])


if __name__ == "__main__":
    unittest.main()
