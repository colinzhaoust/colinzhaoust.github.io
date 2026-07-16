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

    def test_build_emits_scene_plans_compositions_and_canonical_fragment(self):
        runs_dir = ROOT / "runs"
        with tempfile.TemporaryDirectory(prefix="formula-explainer-test-", dir=runs_dir) as temp:
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


if __name__ == "__main__":
    unittest.main()
