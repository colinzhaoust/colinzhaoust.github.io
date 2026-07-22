from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.explainer_pipeline.common import DATA_ROOT, ROOT, resolve_repo_path, sha256_json
from tools.explainer_pipeline.pipeline import replay_provider, run_pipeline
from tools.explainer_pipeline.renderer import render_site
from tools.explainer_pipeline.validation import ExplainerValidationError, validate_bundle


class ExplainerPipelineTests(unittest.TestCase):
    def test_both_reviewed_runs_use_same_pipeline_and_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundles = [
                run_pipeline(DATA_ROOT / "papers" / f"{paper_id}.json", root / paper_id, replay_provider())
                for paper_id in ("feynrl", "rope")
            ]
            manifest = render_site(bundles, root / "site")
            self.assertEqual(manifest["papers"], ["feynrl", "rope"])
            self.assertEqual(len(manifest["media"]), 15)
            self.assertTrue((root / "site" / "data" / "catalog.json").is_file())
            for bundle in bundles:
                self.assertEqual(
                    bundle["source_packet"]["required_section_ids"],
                    list(bundle["section_content"]["sections"]),
                )
                self.assertEqual(
                    {trace["generation_mode"] for trace in bundle["generation"]["stage_traces"]},
                    {"frozen_replay"},
                )
                self.assertTrue(all(not Path(trace["source_record"]).is_absolute() for trace in bundle["generation"]["stage_traces"]))
                self.assertEqual(len(bundle["formula_map"]["formulas"]), len(bundle["source_packet"]["formula_refs"]))
                self.assertTrue(bundle["formula_map"]["edges"])
                self.assertTrue(all(edge["source"].startswith("node:") for edge in bundle["formula_map"]["edges"]))

    def test_formula_map_exposes_real_and_candidate_n_to_n_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = run_pipeline(DATA_ROOT / "papers" / "feynrl.json", Path(temporary), replay_provider())
            mapping = bundle["formula_map"]
            self.assertEqual("formula-manim-map/0.1.0", mapping["schema_version"])
            self.assertTrue(any(node["label"].endswith("EssTradeoffGauge") for node in mapping["manim_nodes"]))
            self.assertIn("implemented", {edge["state"] for edge in mapping["edges"]})
            self.assertIn("candidate", {edge["state"] for edge in mapping["edges"]})
            targets_per_formula = {}
            node_formula = {node["node_id"]: node["formula_id"] for node in mapping["formula_nodes"]}
            for edge in mapping["edges"]:
                targets_per_formula.setdefault(node_formula[edge["source"]], set()).add(edge["target"])
            self.assertTrue(all(len(targets) > 1 for targets in targets_per_formula.values()))

    def test_manifest_hash_matches_exact_written_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_pipeline(DATA_ROOT / "papers" / "feynrl.json", root, replay_provider())
            bundle = json.loads((root / "explainer_bundle.json").read_text(encoding="utf-8"))
            manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["bundle_sha256"], sha256_json(bundle))

    def test_dangling_appendix_link_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = run_pipeline(DATA_ROOT / "papers" / "rope.json", Path(temporary), replay_provider())
            invalid = copy.deepcopy(bundle)
            invalid["lesson_plan"]["sections"][0]["deep_links"] = ["missing-entry"]
            with self.assertRaises(ExplainerValidationError):
                validate_bundle(invalid)

    def test_unknown_media_reference_fails_stage_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = run_pipeline(DATA_ROOT / "papers" / "rope.json", Path(temporary), replay_provider())
            invalid = copy.deepcopy(bundle)
            video = next(
                block
                for block in invalid["section_content"]["sections"]["rope"]["blocks"]
                if block["type"] == "micro_video"
            )
            video["media_id"] = "missing-video"
            from tools.explainer_pipeline.validation import validate_stage_payload
            with self.assertRaises(ExplainerValidationError):
                validate_stage_payload("section_content", invalid["section_content"], invalid["source_packet"])

    def test_repository_path_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            resolve_repo_path("../outside.json")
        with self.assertRaises(ValueError):
            resolve_repo_path("/tmp/outside.json")

    def test_runtime_contract_requires_no_coding_agent_or_legacy_media(self) -> None:
        for paper_id in ("feynrl", "rope"):
            packet = json.loads((DATA_ROOT / "papers" / f"{paper_id}.json").read_text(encoding="utf-8"))
            self.assertFalse(packet["scene_renderer"]["coding_agent_required"])
            self.assertTrue(all("self-refine" not in item["path"] for item in packet["media"]))
            for stage in ("concept_graph", "lesson_plan", "section_content"):
                replay = json.loads((DATA_ROOT / "replays" / paper_id / f"{stage}.json").read_text(encoding="utf-8"))
                self.assertNotEqual(replay["provider"], "codex")


if __name__ == "__main__":
    unittest.main()
