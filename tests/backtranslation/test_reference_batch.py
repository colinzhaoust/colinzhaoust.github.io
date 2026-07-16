from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.reference import prepare_reference
from tools.backtranslation.reference_batch import (
    ReferenceBatchError,
    UPSTREAM_SAVE_LAST_FRAME_SCENES,
    combine_reference_runs,
    extract_registered_scenes,
    harvest_reference_inventory,
)
from tools.backtranslation.registry import load_registry, sha256_file

from helpers import OfflineFixture, PROTOCOL_PATH, REGISTRY_PATH


STATIC_REPLACEMENTS_PATH = (
    REGISTRY_PATH.parent / "static_scene_replacements.json"
)


def source_fixture(registry: dict, root: Path) -> None:
    source = root / registry["upstream"]["source_path"]
    source.parent.mkdir(parents=True)
    lines = ["" for _ in range(max(scene["class_line"] for scene in registry["scenes"]) + 2)]
    for scene in registry["scenes"]:
        lines[scene["directive_line"] - 1] = f".. manim:: {scene['scene_class']}"
        lines[scene["class_line"] - 1] = f"    class {scene['scene_class']}(Scene):"
        lines[scene["class_line"]] = "        pass"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    registry["upstream"]["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    for item in registry["license_snapshot"]["files"]:
        path = root / item["path"]
        path.write_text(f"MIT test fixture: {item['path']}\n", encoding="utf-8")
        item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = OfflineFixture()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def test_extract_verifies_and_bundles_exact_ten_scenes(self) -> None:
        registry = copy.deepcopy(load_registry(REGISTRY_PATH))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_fixture(registry, root)
            output = root / "generated" / "scenes.py"
            manifest = extract_registered_scenes(registry, root, output)
            self.assertEqual(10, len(manifest["scenes"]))
            self.assertEqual(sha256_file(output), manifest["generated_source"]["sha256"])
            generated = output.read_text(encoding="utf-8")
            self.assertEqual(10, generated.count("class "))
            self.assertIn("from manim import *", generated)

    def test_harvest_keeps_missing_cases_in_denominator(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            run_root = Path(raw)
            case = registry["scenes"][0]
            case_root = run_root / "cases" / case["case_id"]
            prepared = prepare_reference(
                self.fixture.videos["reference"],
                case_root / "model_input",
                case["case_id"],
                protocol["reference_preparation"],
            )
            status = {
                "status": "completed",
                "failure_code": None,
                "reference": {"sha256": prepared.content_hash},
                "raw_render": {"path": "fixture.mp4", "sha256": "0" * 64},
                "slurm": {"job_id": "fixture"},
            }
            case_root.mkdir(parents=True, exist_ok=True)
            (case_root / "status.json").write_text(json.dumps(status), encoding="utf-8")
            inventory = harvest_reference_inventory(registry, protocol, run_root)
            self.assertEqual(10, inventory["denominator"])
            self.assertEqual(1, inventory["completed"])
            self.assertEqual(9, inventory["failed_or_missing"])
            self.assertEqual("missing_job_evidence", inventory["cases"][1]["failure_code"])
            self.assertTrue(inventory["conditions"]["one_shot"].startswith("blocked_"))

    def test_harvest_rejects_claimed_hash_mismatch(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            run_root = Path(raw)
            case = registry["scenes"][0]
            case_root = run_root / "cases" / case["case_id"]
            prepare_reference(
                self.fixture.videos["reference"],
                case_root / "model_input",
                case["case_id"],
                protocol["reference_preparation"],
            )
            case_root.mkdir(parents=True, exist_ok=True)
            (case_root / "status.json").write_text(
                json.dumps({"status": "completed", "reference": {"sha256": "f" * 64}}),
                encoding="utf-8",
            )
            inventory = harvest_reference_inventory(registry, protocol, run_root)
            self.assertEqual(0, inventory["completed"])
            self.assertEqual("reference_hash_mismatch", inventory["cases"][0]["failure_code"])

    def test_harvest_identifies_upstream_static_no_video_outcome(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            run_root = Path(raw)
            case = next(scene for scene in registry["scenes"] if scene["scene_class"] == "ThreeDSurfacePlot")
            case_root = run_root / "cases" / case["case_id"]
            case_root.mkdir(parents=True)
            (case_root / "status.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "failure_code": "render_error",
                        "exit_codes": {"render": 0},
                        "raw_render": {"path": None, "sha256": None},
                    }
                ),
                encoding="utf-8",
            )
            inventory = harvest_reference_inventory(registry, protocol, run_root)
            row = next(item for item in inventory["cases"] if item["case_id"] == case["case_id"])
            self.assertEqual("upstream_save_last_frame_no_mp4", row["failure_detail"])

    def test_harvest_classifies_exact_tex_toolchain_failure(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        case = registry["scenes"][0]
        fixtures = (
            (
                "preview",
                "(job-local/standalone.cls)\n! LaTeX Error: File `preview.sty' not found.\n",
                "",
                "missing_runtime_dependency_preview_sty",
            ),
            (
                "dvisvgm",
                "(job-local/standalone.cls) (job-local/preview.sty)\n",
                "FileNotFoundError: [Errno 2] No such file or directory: 'dvisvgm'\n",
                "missing_runtime_dependency_dvisvgm",
            ),
        )
        for name, tex_log, render_stderr, expected in fixtures:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                run_root = Path(raw)
                case_root = run_root / "cases" / case["case_id"]
                tex_root = case_root / "raw_media" / "Tex"
                private_root = case_root / "private"
                tex_root.mkdir(parents=True)
                private_root.mkdir(parents=True)
                (case_root / "status.json").write_text(
                    json.dumps({"status": "failed", "failure_code": "render_error"}),
                    encoding="utf-8",
                )
                (tex_root / "fixture.log").write_text(tex_log, encoding="utf-8")
                (private_root / "render.stderr").write_text(
                    render_stderr, encoding="utf-8"
                )
                inventory = harvest_reference_inventory(registry, protocol, run_root)
                self.assertEqual(expected, inventory["cases"][0]["failure_detail"])

    def test_combine_preserves_failures_and_selects_latest_success(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            initial = root / "initial"
            recovery = root / "recovery"
            first_case, second_case = registry["scenes"][:2]

            failed_root = initial / "cases" / first_case["case_id"]
            failed_root.mkdir(parents=True)
            (failed_root / "status.json").write_text(
                json.dumps({
                    "status": "failed",
                    "failure_code": "render_error",
                    "started_at": "2026-07-16T01:00:00Z",
                    "finished_at": "2026-07-16T01:01:00Z",
                    "pipeline_commit": "a" * 40,
                    "upstream_commit": registry["upstream"]["commit_sha"],
                    "slurm": {"array_job_id": "initial"},
                }),
                encoding="utf-8",
            )

            for run_root, case, timestamp, commit in (
                (initial, second_case, "2026-07-16T01:02:00Z", "a" * 40),
                (recovery, first_case, "2026-07-16T02:00:00Z", "b" * 40),
            ):
                case_root = run_root / "cases" / case["case_id"]
                prepared = prepare_reference(
                    self.fixture.videos["reference"],
                    case_root / "model_input",
                    case["case_id"],
                    protocol["reference_preparation"],
                )
                case_root.mkdir(parents=True, exist_ok=True)
                (case_root / "status.json").write_text(
                    json.dumps({
                        "status": "completed",
                        "failure_code": None,
                        "finished_at": timestamp,
                        "pipeline_commit": commit,
                        "upstream_commit": registry["upstream"]["commit_sha"],
                        "reference": {"sha256": prepared.content_hash},
                        "raw_render": {"path": "fixture.mp4", "sha256": "0" * 64},
                        "slurm": {"array_job_id": run_root.name},
                    }),
                    encoding="utf-8",
                )

            runs = [("initial", initial), ("recovery", recovery)]
            inventory = combine_reference_runs(
                registry, protocol, runs, retrieval_root="babel:/evidence"
            )
            repeated = combine_reference_runs(
                registry, protocol, runs, retrieval_root="babel:/evidence"
            )
            self.assertEqual(inventory, repeated)
            self.assertEqual(3, inventory["attempt_count"])
            self.assertEqual(2, inventory["completed"])
            self.assertEqual("2026-07-16T02:00:00Z", inventory["observed_at"])
            first = inventory["cases"][0]
            self.assertEqual(2, first["attempt_count"])
            self.assertEqual(1, first["selected_attempt_index"])
            self.assertEqual("render_error", first["attempts"][0]["failure_code"])
            self.assertEqual("completed", first["final_status"])
            self.assertEqual(
                "babel:/evidence/runs/recovery", inventory["runs"][1]["retrieval_root"]
            )

    def test_combine_rejects_duplicate_run_ids(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaisesRegex(ReferenceBatchError, "unique"):
                combine_reference_runs(
                    registry, protocol, [("same", root), ("same", root)]
                )

    def test_static_replacements_are_source_exact_and_disclose_tradeoffs(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        replacements = json.loads(STATIC_REPLACEMENTS_PATH.read_text(encoding="utf-8"))
        rows = replacements["recommendations"]
        self.assertEqual(UPSTREAM_SAVE_LAST_FRAME_SCENES, {
            row["original_scene_class"] for row in rows
        })
        self.assertEqual(2, len({row["replacement_scene_class"] for row in rows}))
        self.assertTrue(all(row["source_exact"] is True for row in rows))
        self.assertTrue(all(len(row["code_sha256"]) == 64 for row in rows))
        self.assertTrue(all(row["animation_evidence"] for row in rows))
        self.assertTrue(all(row["coverage_tradeoff"] for row in rows))
        registry_scenes = {scene["scene_class"] for scene in registry["scenes"]}
        self.assertTrue(all(
            row["replacement_scene_class"] not in registry_scenes for row in rows
        ))


if __name__ == "__main__":
    unittest.main()
