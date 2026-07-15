from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.registry import (
    EXPECTED_SCENES,
    RegistryError,
    load_registry,
    validate_registry,
    verify_source_root,
)

from helpers import REGISTRY_PATH


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry(REGISTRY_PATH)

    def test_exact_ten_scene_registry(self) -> None:
        self.assertEqual(10, len(self.registry["scenes"]))
        self.assertEqual(set(EXPECTED_SCENES), {scene["scene_class"] for scene in self.registry["scenes"]})
        self.assertEqual("1157b746c37130685e0a02d8aa0871d1f164d5f4", self.registry["upstream"]["commit_sha"])

    def test_registry_rejects_external_assets(self) -> None:
        changed = copy.deepcopy(self.registry)
        changed["scenes"][0]["external_assets"] = ["logo.svg"]
        with self.assertRaises(RegistryError):
            validate_registry(changed)

    def test_registry_requires_contamination_disclosure(self) -> None:
        changed = copy.deepcopy(self.registry)
        changed["contamination"]["risk"] = "none"
        with self.assertRaises(RegistryError):
            validate_registry(changed)

    def test_source_root_can_be_verified_offline_by_hash(self) -> None:
        changed = copy.deepcopy(self.registry)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / changed["upstream"]["source_path"]
            source.parent.mkdir(parents=True)
            lines = ["" for _ in range(max(scene["class_line"] for scene in changed["scenes"]))]
            for scene in changed["scenes"]:
                lines[scene["class_line"] - 1] = f"class {scene['scene_class']}(Scene):"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")
            changed["upstream"]["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            for item in changed["license_snapshot"]["files"]:
                license_path = root / item["path"]
                license_path.write_text(f"MIT fixture for {item['path']}\n", encoding="utf-8")
                item["sha256"] = hashlib.sha256(license_path.read_bytes()).hexdigest()
            result = verify_source_root(changed, root)
            self.assertEqual("verified_source_archive", result["source_root_mode"])
            self.assertEqual(10, result["scene_count"])

    def test_source_root_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / self.registry["upstream"]["source_path"]
            path.parent.mkdir(parents=True)
            path.write_text("not the pinned source", encoding="utf-8")
            with self.assertRaises(RegistryError):
                verify_source_root(self.registry, root)


if __name__ == "__main__":
    unittest.main()
