from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.probe_rendered_videos import output_keys


class ProbeOutputKeyTests(unittest.TestCase):
    def test_unique_stems_preserve_historical_output_names(self) -> None:
        videos = [Path("renders/attention.mp4"), Path("renders/rope.mp4")]
        self.assertEqual(["attention", "rope"], output_keys(videos))

    def test_duplicate_stems_use_readable_parent_identity(self) -> None:
        videos = [
            Path("cases/bt-001/reference.mp4"),
            Path("cases/bt-002/reference.mp4"),
        ]
        self.assertEqual(
            ["bt-001__reference", "bt-002__reference"], output_keys(videos)
        )

    def test_repeated_parent_names_gain_stable_path_digest(self) -> None:
        videos = [
            Path("first/case/reference.mp4"),
            Path("second/case/reference.mp4"),
        ]
        first = output_keys(videos)
        second = output_keys(videos)
        self.assertEqual(first, second)
        self.assertEqual(2, len(set(first)))
        self.assertTrue(all(key.startswith("case__reference__") for key in first))

    def test_same_resolved_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            video = Path(raw) / "reference.mp4"
            video.touch()
            with self.assertRaisesRegex(ValueError, "same file"):
                output_keys([video, video.parent / "." / video.name])


if __name__ == "__main__":
    unittest.main()
