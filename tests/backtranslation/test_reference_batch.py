from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.reference import prepare_reference
from tools.backtranslation.reference_batch import (
    extract_registered_scenes,
    harvest_reference_inventory,
)
from tools.backtranslation.registry import load_registry, sha256_file

from helpers import OfflineFixture, PROTOCOL_PATH, REGISTRY_PATH


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


if __name__ == "__main__":
    unittest.main()
