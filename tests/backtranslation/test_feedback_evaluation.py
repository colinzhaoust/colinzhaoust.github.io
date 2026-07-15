from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.conditions import FixtureRenderer, RecordingMockAdapter, run_one_shot, run_self_refined
from tools.backtranslation.evaluation import CodeSafetyHook, PairedDeltaHook
from tools.backtranslation.feedback import RenderResult, build_feedback, sanitize_render_errors
from tools.backtranslation.manifest_bridge import ManifestBridgeUnavailable, require_bridge

from helpers import OfflineFixture, fixture_code


class FeedbackEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = OfflineFixture()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def renderer(self) -> FixtureRenderer:
        return FixtureRenderer(
            {
                "one_shot": self.fixture.videos["one_shot"],
                "refine_2": self.fixture.prepared.video_path,
            }
        )

    def test_feedback_is_deterministic_for_identical_inputs(self) -> None:
        render = RenderResult(True, self.fixture.prepared.video_path)
        first = build_feedback(
            self.fixture.prepared.video_path,
            render,
            self.fixture.root / "feedback_a",
            self.fixture.policy,
        )
        second = build_feedback(
            self.fixture.prepared.video_path,
            render,
            self.fixture.root / "feedback_b",
            self.fixture.policy,
        )
        self.assertEqual(first.numeric_similarity_summary, second.numeric_similarity_summary)
        self.assertEqual(
            [item.diff_hash for item in first.frame_pairs],
            [item.diff_hash for item in second.frame_pairs],
        )
        self.assertTrue(first.technical_pass)
        self.assertTrue(first.visual_pass)
        self.assertTrue(first.early_stop)

    def test_render_errors_are_sanitized(self) -> None:
        errors = "/Users/colin/private/source.py failed in OpeningManim"
        cleaned = sanitize_render_errors(errors, ["OpeningManim"])
        self.assertNotIn("colin", cleaned)
        self.assertNotIn("OpeningManim", cleaned)
        self.assertIn("<REDACTED>", cleaned)

    def test_code_safety_hook_detects_blocked_import_and_source_token(self) -> None:
        path = self.fixture.root / "unsafe.py"
        path.write_text("import os\n# OpeningManim\nclass Unsafe: pass\n", encoding="utf-8")
        result = CodeSafetyHook(path, ["OpeningManim"]).evaluate()
        self.assertEqual("fail", result.result)
        self.assertEqual(1, result.metrics["blocked_import_count"])
        self.assertEqual(1, result.metrics["source_token_match_count"])

    def test_paired_hook_verifies_exact_cross_condition_lineage(self) -> None:
        one_root = self.fixture.root / "eval_one"
        one = run_one_shot(
            pairing_id="fixture-eval-r1",
            case_id="bt-999",
            reference_video=self.fixture.prepared.video_path,
            run_root=one_root,
            adapter=RecordingMockAdapter([fixture_code("one_shot")]),
            renderer=self.renderer(),
            policy=self.fixture.policy,
        )
        code_path = one_root / str(one.rounds[-1].code_path)
        refined = run_self_refined(
            pairing_id=one.pairing_id,
            case_id=one.case_id,
            reference_video=self.fixture.prepared.video_path,
            one_shot_code_path=code_path,
            expected_one_shot_hash=one.final_code_hash or "",
            run_root=self.fixture.root / "eval_self",
            adapter=RecordingMockAdapter([fixture_code("refine_2")]),
            renderer=self.renderer(),
            policy=self.fixture.policy,
        )
        result = PairedDeltaHook(one, refined).evaluate()
        self.assertEqual("pass", result.result)
        self.assertTrue(result.metrics["lineage_exact"])

    def test_manifest_bridge_fails_explicitly_when_q5_is_unavailable(self) -> None:
        with self.assertRaisesRegex(ManifestBridgeUnavailable, "emit_backtranslation_run"):
            require_bridge(object())

    def test_manifest_bridge_accepts_only_the_typed_method(self) -> None:
        class Bridge:
            def emit_backtranslation_run(self, **kwargs):
                return kwargs

        self.assertIsInstance(require_bridge(Bridge()), Bridge)


if __name__ == "__main__":
    unittest.main()
