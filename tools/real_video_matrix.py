#!/usr/bin/env python3
"""Validate and materialize the q-8 real-video evidence matrix.

The matrix is an index over q-5-style evidence, not an alternate completion
authority.  Cell completion is derived from a versioned contract, stage state,
and validated artifacts.  Missing runs remain in the denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.paper_media_evidence.completion import derive_completion


EXPECTED_PIPELINES = {"code2video", "paper2manim", "inhouse_v0"}
EXPECTED_TOPICS = {"transformers", "dpo", "feynrl", "rope"}
FINAL_STATES = {"full", "partial", "blocked"}
STAGE_STATES = {"succeeded", "failed", "skipped", "not_started", "running", "blocked"}
COST_CATEGORIES = {"api", "local_compute", "labor", "storage", "assets"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


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
            "-show_entries", "stream=width,height,r_frame_rate", "-select_streams", "v:0",
            "-of", "json", str(path),
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


def _repo_path(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), f"path-empty:{label}")
    path = Path(value)
    _require(not path.is_absolute() and ".." not in path.parts, f"path-not-repo-relative:{label}")
    return value


def _validate_review(review: dict[str, Any], cell_id: str) -> None:
    required = {
        "event_id", "rubric_id", "rubric_version", "evaluator_type",
        "evaluator_id", "result", "evidence_refs", "reviewed_at",
    }
    _require(required <= set(review), f"review-unstructured:{cell_id}")
    _require(review["result"] in {"pass", "needs_revision", "informational"}, f"review-result:{cell_id}")
    _require(bool(review["evidence_refs"]), f"review-no-evidence:{cell_id}")
    for ref in review["evidence_refs"]:
        _repo_path(ref, f"review:{cell_id}")


def validate_config(config: dict[str, Any]) -> None:
    _require(config.get("schema_version") == "real-video-matrix/0.2.0", "schema-version")
    pipelines = config.get("pipelines", [])
    topics = config.get("topics", [])
    cells = config.get("cells", [])
    contract = config.get("completion_contract", {})
    contract_id = contract.get("contract_id")
    _require(bool(contract_id) and bool(contract.get("rule_version")), "completion-contract")
    _require(bool(contract.get("required_stages")), "completion-contract-stages")
    _require(bool(contract.get("required_deliverable_roles")), "completion-contract-deliverables")
    _require({item.get("id") for item in pipelines} == EXPECTED_PIPELINES, "pipeline-axis")
    _require({item.get("id") for item in topics} == EXPECTED_TOPICS, "topic-axis")
    _require(len(cells) == 12, "matrix-cardinality")
    expected = {(pipeline, topic) for pipeline in EXPECTED_PIPELINES for topic in EXPECTED_TOPICS}
    actual = {(cell.get("pipeline_id"), cell.get("topic_id")) for cell in cells}
    _require(actual == expected and len(actual) == len(cells), "matrix-coverage")

    for pipeline in pipelines:
        _require(bool(pipeline.get("variant")), f"pipeline-variant:{pipeline.get('id')}")
        _require(pipeline.get("comparison_group") == "q8_requested_matrix", "comparison-group")
        _require(pipeline.get("implementation_origin") in {"upstream_repository", "project_native"}, "implementation-origin")
    for topic in topics:
        _require(topic.get("id") != "p3o", "p3o-is-not-a-canonical-family")
        _repo_path(topic.get("reference_spec"), f"topic:{topic.get('id')}")

    for cell in cells:
        cell_id = cell.get("cell_id", "unknown")
        _require("completion" not in cell, f"completion-must-be-derived:{cell_id}")
        _require(cell.get("completion_contract_id") == contract_id, f"completion-contract-mismatch:{cell_id}")
        _require(cell.get("status") in {"completed", "stopped", "blocked"}, f"run-status:{cell_id}")
        _require(cell.get("implementation_origin") != "synthetic_fixture", f"synthetic-cell:{cell_id}")
        _require(cell.get("input_contract_mode") in {"native", "adapted", "source_embedded"}, f"input-mode:{cell_id}")

        stages = cell.get("stages", [])
        stage_ids = [stage.get("id") for stage in stages]
        _require(len(stage_ids) == len(set(stage_ids)), f"stage-duplicate:{cell_id}")
        _require(set(contract["required_stages"]) <= set(stage_ids), f"stage-missing:{cell_id}")
        _require(all(stage.get("status") in STAGE_STATES for stage in stages), f"stage-state:{cell_id}")

        revision = cell.get("repository_revision", {})
        if revision.get("availability") == "pinned":
            _require(bool(HEX40.fullmatch(revision.get("commit", ""))), f"pinned-revision-invalid:{cell_id}")
            source_hashes = revision.get("source_hashes", {})
            _require(bool(source_hashes), f"pinned-source-hashes-missing:{cell_id}")
            _require(all(SHA256.fullmatch(value or "") for value in source_hashes.values()), f"pinned-source-hash-invalid:{cell_id}")

        cost = cell.get("cost", {})
        coverage = set(cost.get("coverage", []))
        excluded = set(cost.get("excluded_coverage", []))
        _require(coverage.isdisjoint(excluded) and coverage | excluded == COST_CATEGORIES, f"cost-coverage-incomplete:{cell_id}")
        _require(cost.get("measured_usd") is None or isinstance(cost.get("measured_usd"), (int, float)), f"cost-measurement:{cell_id}")
        if "local_compute" in excluded:
            usage = cost.get("resource_usage", {})
            _require("wall_time_seconds" in usage, f"compute-disclosure-missing:{cell_id}")
            _require(
                usage.get("wall_time_seconds") is None or isinstance(usage.get("wall_time_seconds"), (int, float)),
                f"compute-disclosure-invalid:{cell_id}",
            )
            _require(usage.get("usd_conversion") is None, f"compute-exclusion-contradiction:{cell_id}")

        for artifact in cell.get("artifacts", []):
            if artifact.get("local_path"):
                _repo_path(artifact["local_path"], f"artifact:{cell_id}")
            else:
                _require(bool(artifact.get("remote_path")), f"artifact-unlocated:{cell_id}")
                _require(bool(SHA256.fullmatch(artifact.get("content_hash", ""))), f"remote-artifact-unhashed:{cell_id}")
        for execution_input in cell.get("execution_inputs", []):
            if execution_input.get("path"):
                _repo_path(execution_input["path"], f"execution-input:{cell_id}")
            _require(execution_input.get("consumed") is True, f"execution-input-not-consumed:{cell_id}")
        for review in cell.get("reviews", []):
            _validate_review(review, cell_id)


def _snapshot_path(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    result: dict[str, Any] = {"path": relative, "exists": path.is_file()}
    if path.is_file():
        result["content_hash"] = sha256_file(path)
    return result


def _derive_cell_completion(cell: dict[str, Any], contract: dict[str, Any]) -> str:
    artifacts: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    for index, artifact in enumerate(cell.get("artifacts", [])):
        observed = artifact.get("observed", {})
        content_hash = observed.get("content_hash") or artifact.get("content_hash")
        if not content_hash:
            continue
        artifact_id = f"artifact:{cell['cell_id']}:{index}"
        validation_id = f"validation:{cell['cell_id']}:{index}"
        artifacts.append({
            "artifact_id": artifact_id,
            "role": artifact.get("role"),
            "completion": "full",
            "content_hash": content_hash,
            "validation_refs": [validation_id],
        })
        validations.append({"validation_id": validation_id, "subject_ref": artifact_id, "result": "pass"})
    q5_manifest = {
        "status": {"completed": "completed", "stopped": "stopped", "blocked": "failed"}[cell["status"]],
        "lineage": {"implementation_origin": cell["implementation_origin"]},
        "completion_contract": contract,
        "stages": cell["stages"],
        "artifacts": artifacts,
        "validations": validations,
    }
    derived = derive_completion(q5_manifest)
    if cell["status"] == "blocked" and derived == "failed":
        return "blocked"
    _require(derived in FINAL_STATES, f"unsupported-derived-state:{cell['cell_id']}:{derived}")
    return derived


def materialize(config: dict[str, Any], root: Path) -> dict[str, Any]:
    validate_config(config)
    topics = {topic["id"]: topic for topic in config["topics"]}
    contract = config["completion_contract"]
    cells: list[dict[str, Any]] = []
    for source in config["cells"]:
        cell = json.loads(json.dumps(source))
        reference = topics[cell["topic_id"]]["reference_spec"]
        cell["topic_reference_snapshot"] = _snapshot_path(root, reference)
        for execution_input in cell.get("execution_inputs", []):
            if execution_input.get("path"):
                execution_input["observed"] = _snapshot_path(root, execution_input["path"])
        for artifact in cell.get("artifacts", []):
            local_path = artifact.get("local_path")
            if not local_path:
                continue
            observed = _snapshot_path(root, local_path)
            path = root / local_path
            if observed["exists"] and path.suffix.lower() == ".mp4":
                observed["media"] = media_probe(path)
            artifact["observed"] = observed

        cell["completion"] = _derive_cell_completion(cell, contract)
        if cell["completion"] == "full":
            local_deliverables = [
                artifact for artifact in cell.get("artifacts", [])
                if artifact.get("role") in contract["required_deliverable_roles"] and artifact.get("local_path")
            ]
            _require(local_deliverables, f"full-local-deliverable-missing:{cell['cell_id']}")
            _require(all(item.get("observed", {}).get("exists") for item in local_deliverables), f"full-artifact-missing:{cell['cell_id']}")
            _require(cell.get("reviews"), f"full-no-review:{cell['cell_id']}")
            _require(cell.get("repository_revision", {}).get("availability") == "pinned", f"full-unpinned-revision:{cell['cell_id']}")
            _require(cell.get("cost", {}).get("measured_usd") is not None, f"full-unmeasured-cost:{cell['cell_id']}")
            _require(cell.get("execution_inputs"), f"full-no-execution-input:{cell['cell_id']}")
            declared_hashes = cell["repository_revision"]["source_hashes"]
            for execution_input in cell["execution_inputs"]:
                path = execution_input.get("path")
                observed_hash = execution_input.get("observed", {}).get("content_hash")
                _require(declared_hashes.get(path) == observed_hash, f"full-input-hash-mismatch:{cell['cell_id']}:{path}")
            for review in cell["reviews"]:
                for evidence_ref in review["evidence_refs"]:
                    _require((root / evidence_ref).is_file(), f"full-review-evidence-missing:{cell['cell_id']}:{evidence_ref}")
        cells.append(cell)
    counts = Counter(cell["completion"] for cell in cells)
    return {
        "schema_version": "real-video-matrix-report/0.2.0",
        "experiment_id": config["experiment_id"],
        "completion_contract": contract,
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
