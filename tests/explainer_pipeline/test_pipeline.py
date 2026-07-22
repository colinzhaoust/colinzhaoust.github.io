from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.explainer_pipeline.common import DATA_ROOT, ROOT, resolve_repo_path, sha256_json
from tools.explainer_pipeline.pipeline import replay_provider, run_pipeline
from tools.explainer_pipeline.pricing import estimate_cost
from tools.explainer_pipeline.renderer import RenderError, render_comparison_site, render_site
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
            self.assertEqual(len(manifest["media"]), 24)
            self.assertTrue((root / "site" / "data" / "catalog.json").is_file())
            catalog = json.loads((root / "site" / "data" / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual("explainer-site-catalog/0.2.0", catalog["schema_version"])
            self.assertEqual("reviewed-reference", catalog["default_run"])
            self.assertEqual(1, len(catalog["runs"]))
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
                self.assertTrue(bundle["code_map"]["formula_code_edges"])
                self.assertTrue(bundle["code_map"]["dag_edges"])
                self.assertTrue(bundle["code_map"]["experiment_pipeline"])
                self.assertTrue(all(trace["usage"] is None for trace in bundle["generation"]["stage_traces"]))
                self.assertTrue(all(trace["cost"]["status"] == "not_recorded" for trace in bundle["generation"]["stage_traces"]))
            for paper_id in ("feynrl", "rope"):
                published_bundle = json.loads(
                    (root / "site" / "data" / "runs" / "reviewed-reference" / f"{paper_id}.json").read_text(
                        encoding="utf-8"
                    )
                )
                validate_bundle(published_bundle)

    def test_comparison_site_writes_independent_traceable_run_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = [
                run_pipeline(DATA_ROOT / "papers" / f"{paper_id}.json", root / "reference" / paper_id, replay_provider())
                for paper_id in ("feynrl", "rope")
            ]
            candidate = copy.deepcopy(reference)
            for bundle in candidate:
                for trace in bundle["generation"]["stage_traces"]:
                    trace["provider"] = "test_provider"
                    trace["model"] = "test-model-snapshot"
                    trace["generation_mode"] = "frozen_replay"
            manifest = render_comparison_site(
                [
                    {"run_id": "reviewed-reference", "label": "Reviewed reference", "bundles": reference},
                    {"run_id": "test-snapshot", "label": "Test snapshot", "bundles": candidate},
                ],
                root / "site",
            )
            self.assertEqual(["reviewed-reference", "test-snapshot"], manifest["runs"])
            self.assertEqual(48, len(manifest["media"]))
            catalog = json.loads((root / "site" / "data" / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(2, len(catalog["runs"]))
            self.assertEqual(["test-model-snapshot"], catalog["runs"][1]["models"])
            self.assertTrue((root / "site" / "data" / "runs" / "test-snapshot" / "feynrl.json").is_file())

    def test_comparison_fails_if_a_model_run_changes_the_frozen_source_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = run_pipeline(DATA_ROOT / "papers" / "feynrl.json", root / "reference", replay_provider())
            changed = copy.deepcopy(bundle)
            changed["generation"]["source_packet_sha256"] = "0" * 64
            with self.assertRaises(RenderError):
                render_comparison_site(
                    [
                        {"run_id": "reference-run", "bundles": [bundle]},
                        {"run_id": "changed-input", "bundles": [changed]},
                    ],
                    root / "site",
                )

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

    def test_live_usage_cost_is_estimated_only_with_a_matching_rate_card(self) -> None:
        usage = {"input_tokens": 10_000, "output_tokens": 2_000, "reasoning_tokens": 500, "total_tokens": 12_000}
        gpt = estimate_cost("bedrock_mantle", "openai.gpt-5.5", usage)
        self.assertEqual("estimated", gpt["status"])
        self.assertAlmostEqual(0.121, gpt["estimated_usd"])
        unknown = estimate_cost("amazon_bedrock", "qwen.qwen3-32b-v1:0", usage)
        self.assertEqual("rate_unavailable", unknown["status"])
        self.assertIsNone(unknown["estimated_usd"])

    def test_metric_bars_have_rendered_exact_value_evidence(self) -> None:
        manifest = json.loads((ROOT / "experiments/explainer_pipeline/micro_scene_manifest.json").read_text(encoding="utf-8"))
        scenes = {item["scene_id"]: item for item in manifest["scenes"]}
        for scene_id in ("FeynRLResultsMicro", "RoPEResultsMicro"):
            artifact = ROOT / scenes[scene_id]["artifact_ref"]
            self.assertTrue(artifact.is_file())
            import hashlib
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), scenes[scene_id]["sha256"])

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
