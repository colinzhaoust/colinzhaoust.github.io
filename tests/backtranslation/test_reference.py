from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.backtranslation.reference import (
    ReferencePreparationError,
    assert_workspace_isolation,
    prepare_reference,
)

from helpers import OfflineFixture


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = OfflineFixture()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def test_reference_is_normalized_and_metadata_stripped(self) -> None:
        prepared = self.fixture.prepared
        self.assertEqual("reference.mp4", prepared.video_path.name)
        self.assertEqual(854, prepared.media["width"])
        self.assertEqual(480, prepared.media["height"])
        self.assertEqual(15.0, prepared.media["fps"])
        self.assertEqual(0, prepared.media["audio_stream_count"])
        self.assertNotIn("title", prepared.media["tags"])
        self.assertNotIn("comment", prepared.media["tags"])

    def test_preparation_is_byte_deterministic_in_same_environment(self) -> None:
        first = prepare_reference(
            self.fixture.videos["reference"],
            self.fixture.root / "repeat_a",
            "bt-998",
            self.fixture.protocol["reference_preparation"],
        )
        second = prepare_reference(
            self.fixture.videos["reference"],
            self.fixture.root / "repeat_b",
            "bt-998",
            self.fixture.protocol["reference_preparation"],
        )
        self.assertEqual(first.content_hash, second.content_hash)

    def test_private_manifest_cannot_enter_model_workspace(self) -> None:
        output_root = self.fixture.root / "bad_private"
        with self.assertRaises(ReferencePreparationError):
            prepare_reference(
                self.fixture.videos["reference"],
                output_root,
                "bt-997",
                self.fixture.protocol["reference_preparation"],
                private_manifest_path=output_root / "prep.json",
            )

    def test_workspace_isolation_rejects_extra_files(self) -> None:
        model_root = self.fixture.root / "model_inputs"
        assert_workspace_isolation(
            model_root,
            reference_path=self.fixture.prepared.video_path,
            source_root=None,
            forbidden_tokens=["OpeningManim", "docs/source/examples.rst"],
        )
        leaked = model_root / "bt-999" / "metadata.json"
        leaked.write_text('{"scene": "OpeningManim"}', encoding="utf-8")
        with self.assertRaises(ReferencePreparationError):
            assert_workspace_isolation(
                model_root,
                reference_path=self.fixture.prepared.video_path,
                source_root=None,
                forbidden_tokens=["OpeningManim", "docs/source/examples.rst"],
            )
        leaked.unlink()

    def test_source_and_generation_roots_must_be_disjoint(self) -> None:
        model_root = self.fixture.root / "model_inputs"
        with self.assertRaises(ReferencePreparationError):
            assert_workspace_isolation(
                model_root,
                reference_path=self.fixture.prepared.video_path,
                source_root=model_root / "source",
                forbidden_tokens=[],
            )


if __name__ == "__main__":
    unittest.main()
