from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.conditions import (
    AdapterCapabilities,
    ConditionError,
    FixtureRenderer,
    RecordingMockAdapter,
    run_one_shot,
    run_self_refined,
)

from helpers import OfflineFixture, ROOT, fixture_code, load_json


class ConditionTests(unittest.TestCase):
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
                "refine_1": self.fixture.videos["refine_1"],
                "refine_2": self.fixture.prepared.video_path,
            }
        )

    def one_shot(self, marker: str = "one_shot", suffix: str = "one"):
        adapter = RecordingMockAdapter([fixture_code(marker)])
        root = self.fixture.root / suffix
        trace = run_one_shot(
            pairing_id="fixture-pair-r1",
            case_id="bt-999",
            reference_video=self.fixture.prepared.video_path,
            run_root=root,
            adapter=adapter,
            renderer=self.renderer(),
            policy=self.fixture.policy,
        )
        return trace, adapter, root

    def test_one_shot_is_exactly_one_mp4_only_call_without_feedback(self) -> None:
        trace, adapter, _ = self.one_shot(suffix="one_contract")
        self.assertEqual(1, len(adapter.calls))
        request = adapter.calls[0]
        self.assertEqual("reference.mp4", request.reference_video.name)
        self.assertIsNone(request.current_code)
        self.assertIsNone(request.feedback)
        self.assertEqual("one_shot", trace.condition)
        self.assertEqual(1, trace.provider_calls)
        self.assertEqual(0, trace.billable_provider_calls)

    def test_image_only_adapter_is_non_compliant(self) -> None:
        adapter = RecordingMockAdapter(
            [fixture_code("one_shot")],
            capabilities=AdapterCapabilities(video_input=False, image_only=True),
        )
        with self.assertRaisesRegex(ConditionError, "adapter_non_compliant"):
            run_one_shot(
                pairing_id="fixture-pair-r1",
                case_id="bt-999",
                reference_video=self.fixture.prepared.video_path,
                run_root=self.fixture.root / "non_compliant",
                adapter=adapter,
                renderer=self.renderer(),
                policy=self.fixture.policy,
            )

    def test_self_refinement_preserves_exact_parent_and_stops_on_both_gates(self) -> None:
        one, _, one_root = self.one_shot(suffix="paired_one")
        one_code = one_root / str(one.rounds[-1].code_path)
        adapter = RecordingMockAdapter([fixture_code("refine_1"), fixture_code("refine_2")])
        refined = run_self_refined(
            pairing_id=one.pairing_id,
            case_id=one.case_id,
            reference_video=self.fixture.prepared.video_path,
            one_shot_code_path=one_code,
            expected_one_shot_hash=one.final_code_hash or "",
            run_root=self.fixture.root / "paired_self",
            adapter=adapter,
            renderer=self.renderer(),
            policy=self.fixture.policy,
        )
        self.assertEqual(one.final_code_hash, refined.initial_one_shot_code_hash)
        self.assertEqual(one.final_code_hash, refined.rounds[0].code_hash)
        self.assertEqual(2, len(adapter.calls))
        self.assertEqual(3, len(refined.rounds))
        self.assertTrue(refined.rounds[-1].technical_pass)
        self.assertTrue(refined.rounds[-1].visual_pass)
        self.assertTrue(refined.rounds[-1].early_stop)
        self.assertEqual("completed", refined.status)
        self.assertIn("frame_pairs", adapter.calls[0].feedback or {})

    def test_self_refinement_rejects_changed_parent(self) -> None:
        one, _, one_root = self.one_shot(suffix="mismatch_one")
        one_code = one_root / str(one.rounds[-1].code_path)
        with self.assertRaisesRegex(ConditionError, "exact one-shot"):
            run_self_refined(
                pairing_id=one.pairing_id,
                case_id=one.case_id,
                reference_video=self.fixture.prepared.video_path,
                one_shot_code_path=one_code,
                expected_one_shot_hash="0" * 64,
                run_root=self.fixture.root / "mismatch_self",
                adapter=RecordingMockAdapter([fixture_code("refine_2")]),
                renderer=self.renderer(),
                policy=self.fixture.policy,
            )

    def test_self_refinement_never_exceeds_three_revision_calls(self) -> None:
        one, _, one_root = self.one_shot(suffix="budget_one")
        one_code = one_root / str(one.rounds[-1].code_path)
        adapter = RecordingMockAdapter([fixture_code("one_shot") for _ in range(3)])
        refined = run_self_refined(
            pairing_id=one.pairing_id,
            case_id=one.case_id,
            reference_video=self.fixture.prepared.video_path,
            one_shot_code_path=one_code,
            expected_one_shot_hash=one.final_code_hash or "",
            run_root=self.fixture.root / "budget_self",
            adapter=adapter,
            renderer=self.renderer(),
            policy=self.fixture.policy,
        )
        self.assertEqual(3, len(adapter.calls))
        self.assertEqual(4, len(refined.rounds))
        self.assertEqual("partial", refined.status)
        self.assertIn("policy_threshold_not_met", refined.failure_codes)

    def test_render_failure_is_retained_in_trace(self) -> None:
        trace, _, _ = self.one_shot(marker="compile_error", suffix="compile_failure")
        self.assertEqual("failed", trace.status)
        self.assertIn("compile_error", trace.failure_codes)
        self.assertEqual("compile_error", trace.rounds[0].failure_code)

    def test_malformed_generation_is_counted_and_not_rendered(self) -> None:
        adapter = RecordingMockAdapter(["not python source"])
        renderer = self.renderer()
        trace = run_one_shot(
            pairing_id="fixture-pair-r1",
            case_id="bt-999",
            reference_video=self.fixture.prepared.video_path,
            run_root=self.fixture.root / "malformed",
            adapter=adapter,
            renderer=renderer,
            policy=self.fixture.policy,
        )
        self.assertEqual("failed", trace.status)
        self.assertEqual(["malformed_code"], trace.failure_codes)
        self.assertEqual([], renderer.calls)


class CliDryRunTests(unittest.TestCase):
    def test_cli_dry_run_is_offline_and_canonical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="backtranslation_cli_") as raw:
            work = Path(raw) / "work"
            proc = subprocess.run(
                [sys.executable, "tools/run_backtranslation.py", "dry-run", "--work-dir", str(work)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, proc.returncode, proc.stderr)
            result = load_json(work / "dry_run_result.json")
            self.assertEqual("synthetic_fixture", result["implementation_origin"])
            self.assertEqual("placeholder", result["completion"])
            self.assertEqual(0, result["provider_calls"]["billable"])
            self.assertEqual({"human", "one_shot", "self_refined"}, set(result["canonical_manifests"]))
            self.assertEqual("completed", result["self_refined"]["status"])


if __name__ == "__main__":
    unittest.main()
