from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.formula_explainer.compiler import build_all
from tools.formula_explainer.validation import (
    CANONICAL_SCHEMA,
    COMPOSITION_SCHEMA,
    FORMULA_SCHEMA,
    REGISTRY_PATH,
    REGISTRY_SCHEMA,
    ROOT,
    SCENE_SCHEMA,
    TOPICS_PATH,
    FormulaExplainerValidationError,
    load_json,
    validate_graph_fragment,
    validate_workspace,
)


class FormulaExplainerTests(unittest.TestCase):
    def test_focused_schemas_are_valid_draft_2020_12(self):
        for path in (FORMULA_SCHEMA, SCENE_SCHEMA, REGISTRY_SCHEMA, COMPOSITION_SCHEMA):
            Draft202012Validator.check_schema(load_json(path))

    def test_workspace_has_five_demo_topics_but_four_paper_families(self):
        validate_workspace()
        topics = load_json(TOPICS_PATH)
        self.assertEqual(5, len(topics))
        self.assertEqual(4, len({topic["paper_family_id"] for topic in topics.values()}))
        self.assertEqual(
            "paper_family:transformer_attention",
            topics["topic:transformers_core"]["paper_family_id"],
        )
        self.assertEqual(
            topics["topic:transformers_core"]["paper_family_id"],
            topics["topic:attention_softmax_lookup"]["paper_family_id"],
        )

    def test_primitive_origin_is_accessible_and_promotion_is_evidence_based(self):
        registry = load_json(REGISTRY_PATH)
        origins = {item["origin"] for item in registry["primitives"]}
        self.assertEqual({"built_in", "project_reusable", "generated_one_off", "missing_planned"}, origins)
        for item in registry["primitives"]:
            self.assertTrue(item["origin_badge"]["label"])
            self.assertTrue(item["origin_badge"]["icon"])
            if item["origin"] == "project_reusable":
                self.assertGreaterEqual(len(item["used_by"]), 2)

    def test_project_reusable_primitives_have_resolvable_verification_evidence(self):
        registry = load_json(REGISTRY_PATH)
        manifest = load_json(ROOT / "experiments/formula_explainer/babel_smoke_manifest.json")
        completed_jobs = {item["job_id"] for item in manifest["jobs"] if item["state"] == "completed"}
        for item in registry["primitives"]:
            if item["origin"] != "project_reusable":
                continue
            verification = item["verification"]
            self.assertTrue(verification["test_refs"])
            self.assertTrue(verification["golden_scene_refs"])
            for ref in verification["test_refs"]:
                self.assertTrue((ROOT / ref.split("::", 1)[0]).is_file())
            for ref in verification["golden_scene_refs"]:
                path_ref, job_ref = ref.split("#job:", 1)
                self.assertTrue((ROOT / path_ref).is_file())
                self.assertIn(job_ref, completed_jobs)

    def test_formula_operations_are_supported_by_bound_primitives(self):
        registry = load_json(REGISTRY_PATH)
        supported = {item["primitive_id"]: set(item["operations"]) for item in registry["primitives"]}
        for path in (ROOT / "data/formula_explainer/formulas").glob("**/*.json"):
            formula = load_json(path)
            for operation in formula["operations"]:
                self.assertIn(operation["operation_type"], supported[operation["primitive_ref"]])

    def test_manim_version_is_observed_render_provenance_not_an_unverified_pin(self):
        registry = load_json(REGISTRY_PATH)
        manifest = load_json(ROOT / "experiments/formula_explainer/babel_smoke_manifest.json")
        compatibility = registry["manim_compatibility"]
        self.assertEqual([manifest["render_environment"]["manim_version"]], compatibility["validated_render_versions"])
        self.assertIsNone(compatibility["minimum_supported_version"])
        self.assertNotIn("manim_version", registry)

    def test_primary_formula_anchors_and_feynrl_code_candidates_are_exact(self):
        expected = {
            "transformers_core/attention.json": ("arXiv:1706.03762v7", "Equation (1)"),
            "attention_softmax_lookup/softmax.json": ("arXiv:1706.03762v7", "Equation (1)"),
            "dpo/objective.json": ("arXiv:2305.18290v3", "Equation (7)"),
            "feynrl/ess.json": ("arXiv:2605.12380v1", "Equation (11)"),
            "feynrl/p3o_objective.json": ("arXiv:2605.12380v1", "Equation (12)"),
            "rope/relative.json": ("arXiv:2104.09864v5", "Equation (16)"),
        }
        base = ROOT / "data" / "formula_explainer" / "formulas"
        for relative, (revision, locator) in expected.items():
            formula = load_json(base / relative)
            self.assertEqual(revision, formula["source_anchor"]["revision"])
            self.assertIn(locator, formula["source_anchor"]["locator"])
            self.assertEqual("primary_source_visual", formula["source_anchor"]["verification"])
        for relative in ("feynrl/ess.json", "feynrl/p3o_objective.json"):
            formula = load_json(base / relative)
            self.assertTrue(formula["code_mappings"])
            self.assertTrue(all(mapping["repository_revision"] == "dfe85351e28a3744ab0eb02d2299fc1e6d3d5752" for mapping in formula["code_mappings"]))
            self.assertTrue(all(mapping["match_state"] == "candidate" for mapping in formula["code_mappings"]))

    def test_feynrl_does_not_alias_itself_to_p3o(self):
        topics = load_json(TOPICS_PATH)
        feynrl = topics["topic:feynrl"]
        self.assertEqual("FeynRL batch adaptation", feynrl["title"])
        self.assertIn("not a synonym", feynrl["claim_context"])

    def test_feynrl_eq12_kl_and_weight_are_separate_and_topologically_correct(self):
        formula = load_json(ROOT / "data/formula_explainer/formulas/feynrl/p3o_objective.json")
        atoms = {item["atom_id"] for item in formula["atoms"]}
        operations = {item["operation_id"]: item for item in formula["operations"]}
        self.assertIn("atom:feynrl.current_policy", atoms)
        self.assertIn("atom:feynrl.negative_one", atoms)
        self.assertEqual(
            ["atom:feynrl.negative_one", "value:feynrl.raw_score_term"],
            operations["op:feynrl.negate_score_term"]["input_refs"],
        )
        self.assertEqual("value:feynrl.score_term", operations["op:feynrl.negate_score_term"]["output_ref"])
        self.assertEqual(
            ["atom:feynrl.current_policy", "atom:feynrl.old_policy"],
            operations["op:feynrl.behavior_kl"]["input_refs"],
        )
        self.assertEqual("value:feynrl.raw_behavior_kl", operations["op:feynrl.behavior_kl"]["output_ref"])
        self.assertEqual(
            ["atom:feynrl.one", "atom:feynrl.eb"],
            operations["op:feynrl.off_policy_weight"]["input_refs"],
        )
        self.assertEqual(
            ["value:feynrl.off_policy_weight", "value:feynrl.raw_behavior_kl"],
            operations["op:feynrl.weighted_behavior_kl"]["input_refs"],
        )
        self.assertEqual(
            ["value:feynrl.score_term", "value:feynrl.weighted_behavior_kl"],
            operations["op:feynrl.objective_sum"]["input_refs"],
        )

    def test_build_emits_scene_plans_compositions_and_canonical_fragment(self):
        with tempfile.TemporaryDirectory(prefix=".formula-explainer-test-", dir=ROOT) as temp:
            output = Path(temp)
            summary = build_all(output)
            self.assertEqual(5, summary["demo_topic_count"])
            self.assertEqual(4, summary["benchmark_paper_family_count"])
            self.assertEqual(7, summary["formula_count"])
            validate_workspace(output)
            graph = load_json(output / "canonical_graph_fragment.json")
            self.assertEqual([], validate_graph_fragment(graph))
            self.assertTrue(all(edge["match_state"] not in {"confirmed", "rejected"} for edge in graph["edges"]))
            for path in (output / "scene_ir").glob("**/*.json"):
                states = {beat["state"] for beat in load_json(path)["beats"]}
                self.assertEqual({"initial", "intermediate", "terminal"}, states)

    def test_build_validation_rejects_missing_empty_incomplete_and_extra_inventories(self):
        with tempfile.TemporaryDirectory(prefix=".formula-explainer-inventory-", dir=ROOT) as temp:
            root = Path(temp)
            with self.assertRaises(FormulaExplainerValidationError):
                validate_workspace(root / "missing")
            empty = root / "empty"
            empty.mkdir()
            with self.assertRaises(FormulaExplainerValidationError):
                validate_workspace(empty)

            build = root / "build"
            build_all(build)
            (build / "build_summary.json").unlink()
            with self.assertRaises(FormulaExplainerValidationError):
                validate_workspace(build)

            build_all(build)
            (build / "unexpected.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(FormulaExplainerValidationError):
                validate_workspace(build)

    def test_build_validation_rejects_semantically_wrong_composition_and_graph(self):
        with tempfile.TemporaryDirectory(prefix=".formula-explainer-semantics-", dir=ROOT) as temp:
            build = Path(temp) / "build"
            build_all(build)
            composition_path = build / "topic_compositions/feynrl.json"
            composition = load_json(composition_path)
            composition["paper_family_id"] = "paper_family:wrong"
            composition_path.write_text(json.dumps(composition), encoding="utf-8")
            with self.assertRaisesRegex(FormulaExplainerValidationError, "paper_family_id"):
                validate_workspace(build)

            build_all(build)
            graph_path = build / "canonical_graph_fragment.json"
            graph = load_json(graph_path)
            graph["nodes"].pop()
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            with self.assertRaisesRegex(FormulaExplainerValidationError, "graph inventory: node mismatch"):
                validate_workspace(build)

            build_all(build)
            graph = load_json(graph_path)
            graph["edges"][0]["confidence"] = 0.25
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            with self.assertRaisesRegex(FormulaExplainerValidationError, "graph inventory: edge mismatch"):
                validate_workspace(build)

            build_all(build)
            graph = load_json(graph_path)
            graph["nodes"] = []
            graph["edges"] = []
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            with self.assertRaisesRegex(FormulaExplainerValidationError, "nodes and edges must both be nonempty"):
                validate_workspace(build)

if __name__ == "__main__":
    unittest.main()
