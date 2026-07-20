from __future__ import annotations

import json
import unittest
from pathlib import Path

from PIL import Image

from tools.backtranslation.reference import validate_model_visible_reference
from tools.backtranslation.registry import sha256_file


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "experiments" / "backtranslation" / "v1" / "evidence" / "babel_20260716"
PROTOCOL = json.loads(
    (ROOT / "experiments" / "backtranslation" / "v1" / "protocol.json").read_text(
        encoding="utf-8"
    )
)


class ReferenceEvidenceBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (EVIDENCE / "artifact_manifest.json").read_text(encoding="utf-8")
        )

    def test_inventory_and_completion_counts_are_consistent(self) -> None:
        inventory_path = EVIDENCE / self.manifest["inventory"]["path"]
        self.assertEqual(
            self.manifest["inventory"]["sha256"], sha256_file(inventory_path)
        )
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(10, inventory["denominator"])
        self.assertEqual(8, inventory["completed"])
        self.assertEqual(30, inventory["attempt_count"])
        self.assertEqual(8, self.manifest["inventory"]["completed"])

    def test_every_declared_artifact_hashes_and_completed_media_validate(self) -> None:
        completed = 0
        for case in self.manifest["cases"]:
            case_root = EVIDENCE / "cases" / case["case_id"]
            for artifact in case["artifacts"].values():
                path = case_root / artifact["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(artifact["sha256"], sha256_file(path))
                self.assertEqual(artifact["size_bytes"], path.stat().st_size)
            if case["final_status"] != "completed":
                self.assertEqual(["status"], sorted(case["artifacts"]))
                self.assertEqual("upstream_save_last_frame_no_mp4", case["failure_detail"])
                continue
            completed += 1
            reference = case_root / case["artifacts"]["reference"]["path"]
            media = validate_model_visible_reference(
                reference, case["case_id"], PROTOCOL["reference_preparation"]
            )
            self.assertEqual(854, media["width"])
            self.assertEqual(480, media["height"])
            with Image.open(case_root / case["artifacts"]["poster"]["path"]) as poster:
                self.assertEqual((854, 480), poster.size)
        self.assertEqual(8, completed)

    def test_source_manifest_and_license_notices_are_present(self) -> None:
        source = self.manifest["source_manifest"]
        source_path = EVIDENCE / source["path"]
        self.assertEqual(source["sha256"], sha256_file(source_path))
        for relative in self.manifest["license_notice_paths"]:
            self.assertTrue((EVIDENCE / relative).resolve().is_file(), relative)

    def test_public_bundle_contains_no_internal_absolute_or_private_paths(self) -> None:
        forbidden = ("/home/", "/Users/", "xinranz3", "source-vault", "source_vault", "private/")
        for path in EVIDENCE.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in forbidden:
                self.assertNotIn(token, content, f"{token!r} leaked in {path}")


if __name__ == "__main__":
    unittest.main()
