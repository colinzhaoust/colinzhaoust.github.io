from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator

from tools.slides_manim.validation import (
    DEMO_DIR,
    SAMPLE_SLIDE_PATH,
    SLIDE_SCHEMA_PATH,
    SLOT_SCHEMA_PATH,
    load_json,
    sha256,
    validate_demo_package,
    validate_slide_document,
)


EXPECTED_ANIMATION_SLOT_FIELDS = {
    "slot_id",
    "slot_version",
    "scene_ir_ref",
    "rendered_artifact_ref",
    "static_fallback_artifact_ref",
    "semantic_purpose",
    "slide_region",
    "expected_duration_seconds",
    "playback_mode",
    "poster_frame_ref",
    "caption",
    "alt_text",
    "aspect_ratio",
    "crop_policy",
    "artifact_hash",
    "composite_lineage",
    "requiredness",
}


class SlidesManimContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load_json(SAMPLE_SLIDE_PATH)

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(load_json(SLOT_SCHEMA_PATH))
        Draft202012Validator.check_schema(load_json(SLIDE_SCHEMA_PATH))

    def test_animation_slot_contract_requires_exact_fields(self) -> None:
        schema = load_json(SLOT_SCHEMA_PATH)
        self.assertEqual(EXPECTED_ANIMATION_SLOT_FIELDS, set(schema["required"]))
        self.assertEqual(EXPECTED_ANIMATION_SLOT_FIELDS, set(schema["properties"]))
        self.assertFalse(schema["additionalProperties"])

    def test_resolved_methodology_sample_passes(self) -> None:
        self.assertEqual([], validate_slide_document(self.document))
        self.assertEqual("smoke", self.document["completion"])
        self.assertEqual(1, len(self.document["animation_slots"]))
        self.assertEqual(
            "methodology_formula_explanation",
            self.document["animation_slots"][0]["semantic_purpose"],
        )

    def test_required_reference_cannot_be_omitted(self) -> None:
        document = copy.deepcopy(self.document)
        del document["animation_slots"][0]["static_fallback_artifact_ref"]
        errors = validate_slide_document(document)
        self.assertTrue(any(error.startswith("schema:animation_slots/0:required") for error in errors))

    def test_references_must_resolve_to_correct_roles(self) -> None:
        document = copy.deepcopy(self.document)
        slot = document["animation_slots"][0]
        slot["scene_ir_ref"] = slot["rendered_artifact_ref"]
        errors = validate_slide_document(document)
        self.assertIn(
            "slot:animation_slot:methodology.attention_softmax:scene_ir_ref:wrong-role",
            errors,
        )

    def test_hash_and_lineage_are_enforced(self) -> None:
        document = copy.deepcopy(self.document)
        slot = document["animation_slots"][0]
        slot["artifact_hash"] = "sha256:" + "0" * 64
        slot["composite_lineage"]["parent_artifact_refs"].remove(slot["poster_frame_ref"])
        errors = validate_slide_document(document)
        self.assertIn(
            "slot:animation_slot:methodology.attention_softmax:rendered-hash-mismatch",
            errors,
        )
        self.assertIn(
            "slot:animation_slot:methodology.attention_softmax:lineage-incomplete",
            errors,
        )

    def test_lineage_matches_parent_artifacts_and_resolved_run_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        slot = document["animation_slots"][0]
        slot["composite_lineage"]["source_run_ref"] = "babel:job:wrong"
        errors = validate_slide_document(document)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:run-evidence-source-mismatch", errors)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:parent-run-mismatch", errors)

        document = copy.deepcopy(self.document)
        document["animation_slots"][0]["composite_lineage"]["source_commit"] = "0" * 40
        errors = validate_slide_document(document)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:run-evidence-commit-mismatch", errors)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:parent-commit-mismatch", errors)

        document = copy.deepcopy(self.document)
        document["artifacts"][0]["lineage"]["source_commit"] = "0" * 40
        errors = validate_slide_document(document)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:parent-commit-mismatch", errors)

        document = copy.deepcopy(self.document)
        document["run_evidence"][0]["evidence_hash"] = "sha256:" + "0" * 64
        errors = validate_slide_document(document)
        self.assertIn("run-evidence:run_evidence:babel.9313551:hash-mismatch", errors)

        document = copy.deepcopy(self.document)
        video_id = document["animation_slots"][0]["rendered_artifact_ref"]
        video = next(item for item in document["artifacts"] if item["artifact_id"] == video_id)
        video["content_hash"] = "sha256:" + "0" * 64
        errors = validate_slide_document(document)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:run-video-hash-mismatch", errors)

    def test_missing_run_evidence_path_returns_schema_error_without_crashing(self) -> None:
        document = copy.deepcopy(self.document)
        del document["run_evidence"][0]["evidence_path"]
        errors = validate_slide_document(document)
        self.assertIn("schema:run_evidence/0:required", errors)

    def test_required_slot_needs_independent_static_fallback(self) -> None:
        document = copy.deepcopy(self.document)
        poster_id = document["animation_slots"][0]["static_fallback_artifact_ref"]
        next(item for item in document["artifacts"] if item["artifact_id"] == poster_id)[
            "understandable_without_playback"
        ] = False
        errors = validate_slide_document(document)
        self.assertIn(
            "slot:animation_slot:methodology.attention_softmax:fallback-not-independent",
            errors,
        )

    def test_static_fallback_must_be_a_non_video_understandable_image(self) -> None:
        document = copy.deepcopy(self.document)
        poster_id = document["animation_slots"][0]["static_fallback_artifact_ref"]
        poster = next(item for item in document["artifacts"] if item["artifact_id"] == poster_id)
        poster["media_type"] = "video/mp4"
        errors = validate_slide_document(document)
        self.assertIn(f"artifact:{poster_id}:static-fallback-media-type", errors)
        self.assertIn("schema:artifacts/2/media_type:pattern", errors)

    def test_geometry_duration_and_smoke_status_are_enforced(self) -> None:
        document = copy.deepcopy(self.document)
        slot = document["animation_slots"][0]
        slot["slide_region"].update({"x": 0.8, "width": 0.4})
        slot["expected_duration_seconds"] = 3
        document["completion"] = "full"
        errors = validate_slide_document(document)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:region-overflow", errors)
        self.assertIn("slot:animation_slot:methodology.attention_softmax:duration-mismatch", errors)
        self.assertIn("completion:smoke-cannot-be-full", errors)

    def test_architecture_and_performance_stay_explicitly_unresolved(self) -> None:
        planned = {item["semantic_purpose"]: item for item in self.document["planned_slots"]}
        self.assertEqual({"architecture_dataflow", "performance_comparison"}, set(planned))
        for item in planned.values():
            self.assertEqual("planned_missing", item["status"])
            self.assertEqual(
                {"scene_ir", "rendered_artifact", "static_fallback", "poster", "review"},
                set(item["missing_requirements"]),
            )

    def test_demo_package_and_real_artifact_hashes_pass(self) -> None:
        validate_demo_package()
        artifacts = {item["role"]: item for item in self.document["artifacts"]}
        for role in ("scene_ir", "rendered_video", "static_fallback"):
            artifact = artifacts[role]
            self.assertEqual(artifact["content_hash"], sha256(SAMPLE_SLIDE_PATH.parents[2] / artifact["path"]))
        html = (DEMO_DIR / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("autoplay", html)


if __name__ == "__main__":
    unittest.main()
