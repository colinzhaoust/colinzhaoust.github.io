from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.backtranslation.conditions import FeedbackPolicy, load_protocol
from tools.backtranslation.reference import prepare_reference
from tools.backtranslation.synthetic import create_fixture_videos


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "experiments" / "backtranslation" / "v1" / "scene_registry.json"
PROTOCOL_PATH = ROOT / "experiments" / "backtranslation" / "v1" / "protocol.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "backtranslation" / "synthetic_fixture.json"


class OfflineFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="backtranslation_test_")
        self.root = Path(self.temp.name)
        self.protocol = load_protocol(PROTOCOL_PATH)
        self.policy = FeedbackPolicy.from_protocol(self.protocol)
        self.videos = create_fixture_videos(FIXTURE_PATH, self.root / "raw")
        self.prepared = prepare_reference(
            self.videos["reference"],
            self.root / "model_inputs",
            "bt-999",
            self.protocol["reference_preparation"],
            private_manifest_path=self.root / "private" / "prep.json",
        )

    def close(self) -> None:
        self.temp.cleanup()


def fixture_code(marker: str) -> str:
    return f"from manim import Scene\n\nclass OfflineFixtureScene(Scene):\n    FIXTURE_VARIANT = {marker!r}\n"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
