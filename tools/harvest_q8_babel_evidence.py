#!/usr/bin/env python3
"""Validate a retained q8 Babel capture and emit the normalized job result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOPICS = {"transformers", "dpo", "feynrl", "rope"}
COST_CATEGORIES = {"api", "local_compute", "labor", "storage", "assets"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class HarvestValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HarvestValidationError(message)


def _hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_capture(capture: dict[str, Any], capture_path: Path) -> dict[str, Any]:
    _require(capture.get("schema_version") == "q8-babel-harvest-input/0.1.0", "schema-version")
    accounting = capture.get("accounting", {})
    _require(accounting.get("state") == "COMPLETED", "job-not-completed")
    _require(accounting.get("exit_code") == "0:0", "job-nonzero-exit")
    elapsed = int((_parse_time(accounting["ended_at"]) - _parse_time(accounting["started_at"])).total_seconds())
    _require(elapsed == accounting.get("wall_time_seconds"), "wall-time-mismatch")

    source = capture.get("source", {})
    _require(bool(HEX40.fullmatch(source.get("project_commit", ""))), "project-commit")
    _require(bool(HEX64.fullmatch(source.get("scene_sha256", ""))), "scene-hash")
    _require(bool(HEX64.fullmatch(source.get("reference_registry_sha256", ""))), "registry-hash")
    _require(source.get("reference_registry_consumed_at_runtime") is False, "registry-runtime-claim")

    cost = capture.get("cost", {})
    coverage = set(cost.get("coverage", []))
    excluded = set(cost.get("excluded_coverage", []))
    _require(coverage.isdisjoint(excluded) and coverage | excluded == COST_CATEGORIES, "cost-coverage")
    _require(cost.get("measured_api_cost_usd") == 0, "api-cost")

    artifacts = capture.get("artifacts", [])
    _require({item.get("topic") for item in artifacts} == TOPICS and len(artifacts) == 4, "artifact-topics")
    for artifact in artifacts:
        _require(bool(HEX64.fullmatch(artifact.get("sha256", ""))), f"artifact-hash:{artifact.get('topic')}")
        _require(artifact.get("duration_seconds", 0) > 0 and artifact.get("size_bytes", 0) > 0, f"artifact-media:{artifact.get('topic')}")
        _require(artifact.get("width", 0) > 0 and artifact.get("height", 0) > 0, f"artifact-dimensions:{artifact.get('topic')}")

    validation = capture.get("validation", {})
    _require(validation.get("result") == "pass", "probe-result")
    _require(validation.get("all_sampled_frames_non_background") is True, "probe-background")
    return {
        "schema_version": "q8-babel-result/0.2.0",
        "harvest": {
            "input_path": str(capture_path),
            "input_content_hash": _hash(capture_path),
            "capture_note": capture["capture_note"],
        },
        **accounting,
        "source": source,
        "cost": cost,
        "artifacts": artifacts,
        "validation": validation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/real_video_matrix/v1/babel/9313462-harvest-input.json")
    parser.add_argument("--out")
    args = parser.parse_args()
    capture_path = (ROOT / args.input).resolve()
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    normalized = normalize_capture(capture, Path(args.input))
    rendered = json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        out = (ROOT / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
