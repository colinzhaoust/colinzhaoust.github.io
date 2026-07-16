#!/usr/bin/env python3
"""Validate and materialize the q-8 real-video evidence matrix.

The matrix is deliberately stricter than a gallery: every requested cell must
be present, missing runs remain in the denominator, and an MP4 alone cannot be
promoted to ``full`` without pinned execution and cost provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PIPELINES = {"code2video", "paper2manim", "inhouse_v0"}
EXPECTED_TOPICS = {"transformers", "dpo", "feynrl", "rope"}
FINAL_STATES = {"full", "partial", "blocked"}


class MatrixValidationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def media_probe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration,size",
            "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", str(path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    data = json.loads(proc.stdout)
    stream = data["streams"][0]
    return {
        "duration_seconds": round(float(data["format"]["duration"]), 6),
        "size_bytes": int(data["format"]["size"]),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frame_rate": stream["r_frame_rate"],
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixValidationError(message)


def validate_config(config: dict[str, Any]) -> None:
    _require(config.get("schema_version") == "real-video-matrix/0.1.0", "schema-version")
    pipelines = config.get("pipelines", [])
    topics = config.get("topics", [])
    cells = config.get("cells", [])
    _require({item.get("id") for item in pipelines} == EXPECTED_PIPELINES, "pipeline-axis")
    _require({item.get("id") for item in topics} == EXPECTED_TOPICS, "topic-axis")
    _require(len(cells) == 12, "matrix-cardinality")
    expected = {(pipeline, topic) for pipeline in EXPECTED_PIPELINES for topic in EXPECTED_TOPICS}
    actual = {(cell.get("pipeline_id"), cell.get("topic_id")) for cell in cells}
    _require(actual == expected and len(actual) == len(cells), "matrix-coverage")

    for pipeline in pipelines:
        _require(bool(pipeline.get("variant")), f"pipeline-variant:{pipeline.get('id')}")
        _require(pipeline.get("comparison_group") in {"q8_requested_matrix", "upstream_shortlist"}, "comparison-group")
        _require(pipeline.get("implementation_origin") in {"upstream_repository", "project_native"}, "implementation-origin")
    for topic in topics:
        _require(topic.get("id") != "p3o", "p3o-is-not-a-canonical-family")
        _require(bool(topic.get("input_spec")), f"input-spec:{topic.get('id')}")

    for cell in cells:
        cell_id = cell.get("cell_id", "unknown")
        state = cell.get("completion")
        _require(state in FINAL_STATES, f"non-final-state:{cell_id}")
        _require(cell.get("implementation_origin") != "synthetic_fixture", f"synthetic-cell:{cell_id}")
        _require(cell.get("input_contract_mode") in {"native", "adapted"}, f"input-mode:{cell_id}")
        revision = cell.get("repository_revision", {})
        cost = cell.get("cost", {})
        if state == "full":
            _require(revision.get("availability") == "pinned", f"full-unpinned-revision:{cell_id}")
            _require(cost.get("availability") == "measured", f"full-unmeasured-cost:{cell_id}")
            _require(bool(cell.get("artifacts")), f"full-no-artifact:{cell_id}")
            _require(bool(cell.get("quality_reviews")), f"full-no-review:{cell_id}")
        elif state == "partial":
            _require(bool(cell.get("artifacts") or cell.get("attempts")), f"partial-no-evidence:{cell_id}")
            _require(bool(cell.get("missing_requirements")), f"partial-without-gap:{cell_id}")
        else:
            _require(bool(cell.get("attempts")), f"blocked-no-attempt:{cell_id}")
            _require(bool(cell.get("blocker")), f"blocked-no-reason:{cell_id}")


def materialize(config: dict[str, Any], root: Path) -> dict[str, Any]:
    validate_config(config)
    topics = {topic["id"]: topic for topic in config["topics"]}
    cells: list[dict[str, Any]] = []
    for source in config["cells"]:
        cell = json.loads(json.dumps(source))
        spec_path = root / topics[cell["topic_id"]]["input_spec"]
        cell["input_snapshot"] = {
            "path": str(spec_path.relative_to(root)),
            "exists": spec_path.is_file(),
            "content_hash": sha256_file(spec_path) if spec_path.is_file() else None,
        }
        for artifact in cell.get("artifacts", []):
            local_path = artifact.get("local_path")
            if not local_path:
                continue
            path = root / local_path
            artifact["observed"] = {"exists": path.is_file()}
            if path.is_file():
                artifact["observed"]["content_hash"] = sha256_file(path)
                if path.suffix.lower() == ".mp4":
                    artifact["observed"]["media"] = media_probe(path)
        if cell["completion"] == "full":
            missing = [
                artifact.get("local_path", artifact.get("remote_path", "unlocated"))
                for artifact in cell.get("artifacts", [])
                if artifact.get("local_path") and not artifact.get("observed", {}).get("exists")
            ]
            _require(not missing, f"full-artifact-missing:{cell['cell_id']}:{','.join(missing)}")
        cells.append(cell)
    counts = Counter(cell["completion"] for cell in cells)
    return {
        "schema_version": "real-video-matrix-report/0.1.0",
        "experiment_id": config["experiment_id"],
        "axis": {"pipelines": sorted(EXPECTED_PIPELINES), "topics": sorted(EXPECTED_TOPICS)},
        "summary": {state: counts.get(state, 0) for state in ("full", "partial", "blocked")},
        "denominator": len(cells),
        "cells": cells,
        "design_reconciliation": config["design_reconciliation"],
        "babel_jobs": config.get("babel_jobs", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/real_video_matrix/v1/config.json")
    parser.add_argument("--out")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    report = materialize(config, ROOT)
    if args.out:
        out = (ROOT / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.check or not args.out:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
