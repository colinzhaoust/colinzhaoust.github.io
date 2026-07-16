from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.slides_baselines import initial_ledger, validate_matrix


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "experiments" / "slides_baselines" / "v1" / "matrix.json"
RESULTS = ROOT / "experiments" / "slides_baselines" / "v1" / "results.json"

APPROVED_PIPELINE_PINS = {
    "deeppresenter_current": {
        "commit_sha": "2419d30b134a71486523e95ded60b32489fd3c61",
        "license_sha256": "e1faa9265adfb5feb24c4be691b5c39b559dec4f0414d9ec3a1157cf94faaf8b",
    },
    "slidegen": {
        "commit_sha": "f9416e4c99e83dfe368d26bb8c74e02889da8b3a",
        "license_sha256": "fd88b41d9a41ecbb0e813a76564ec8c281b65e187e4ca464ea0f787b141f2525",
    },
    "arcdeck": {
        "commit_sha": "47c54ae7f5deeb1640ed89367c388ada22484fef",
        "license_sha256": "3e42a4c95a1977f17fc45337960a15ea6828a13d6d087ceff1e6f99b22679486",
    },
    "paper2slides_fast_academic_short": {
        "commit_sha": "0785051d1f52814097e94c44751e3f12b83f7c8a",
        "license_sha256": "804ee173a7f604efd7d4932d94f1c7fdbac7f2f2770aa3007ecc7670ea76fd35",
    },
}

APPROVED_PAPER_SNAPSHOTS = {
    "transformers": {
        "source_url": "https://arxiv.org/pdf/1706.03762v7",
        "source_revision": "arxiv:1706.03762v7",
        "content_sha256": "bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697",
    },
    "dpo": {
        "source_url": "https://arxiv.org/pdf/2305.18290v3",
        "source_revision": "arxiv:2305.18290v3",
        "content_sha256": "92cb3a2b71362acda98a789b03d88688fd33cf5fcf13f81d2b1de30ee7d3b67a",
    },
    "feynrl": {
        "source_url": "https://arxiv.org/pdf/2605.12380v1",
        "source_revision": "arxiv:2605.12380v1",
        "content_sha256": "19b66e9758e35de7988ef96a6ef7ed84dda1572bddb07efee23fa1992bf7b15e",
    },
    "rope": {
        "source_url": "https://arxiv.org/pdf/2104.09864v5",
        "source_revision": "arxiv:2104.09864v5",
        "content_sha256": "e9a481fbe1c8a20b7b1fa566b13102a1896c7829fa9a8b4c80528452a5ddaf79",
    },
}

APPROVED_ARTIFACT_SHA256 = {
    "transformers": "0d7abafee4eedba1ce15fe0aeffc0f4099cdedc0c7959131d5c6560deef91f41",
    "dpo": "03e6c21931ba89dd4cb9762390bf2308510fa01ace79ecaf36bbb01ec43bab74",
    "feynrl": "042ded56f89954b087f34303ecdeecb07b1a24c0a1b049a653240d88f7672f75",
    "rope": "6e859c9c7f77ec7937677ef3332aad71e9d3afa39c604a300c33468ba27b3189",
}


def load_matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


class SlideBaselineMatrixTests(unittest.TestCase):
    def test_approved_matrix_is_valid_and_has_twelve_selected_cells(self):
        matrix = load_matrix()
        self.assertEqual([], validate_matrix(matrix))
        self.assertEqual(
            APPROVED_PIPELINE_PINS,
            {
                pipeline["id"]: {
                    "commit_sha": pipeline["commit_sha"],
                    "license_sha256": pipeline["license_sha256"],
                }
                for pipeline in matrix["pipelines"]
            },
        )
        self.assertEqual(
            APPROVED_PAPER_SNAPSHOTS,
            {
                paper["id"]: {
                    "source_url": paper["source_url"],
                    "source_revision": paper["source_revision"],
                    "content_sha256": paper["content_sha256"],
                }
                for paper in matrix["papers"]
            },
        )
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
        self.assertEqual(
            APPROVED_ARTIFACT_SHA256,
            {
                cell["paper_id"]: cell["artifact"]["sha256"]
                for cell in slidegen["cells"]
            },
        )
        for cell in slidegen["cells"]:
            self.assertEqual("COMPLETED", cell["state"])
            self.assertEqual("0:0", cell["exit_code"])
            self.assertEqual(by_paper[cell["paper_id"]]["content_sha256"], cell["input_sha256"])
            self.assertEqual(
                APPROVED_ARTIFACT_SHA256[cell["paper_id"]],
                cell["artifact"]["sha256"],
            )
        self.assertFalse(results["fallback_result"]["selected_matrix_cell"])
        self.assertIsNone(results["fallback_result"]["provider_cost_measured_usd"])


if __name__ == "__main__":
    unittest.main()
