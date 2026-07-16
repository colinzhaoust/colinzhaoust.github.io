#!/usr/bin/env python3
"""Validate and initialize the paper-to-slides baseline evidence matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SELECTED_PIPELINES = {
    "deeppresenter_current",
    "slidegen",
    "arcdeck",
}
PAPER_FAMILIES = {"transformers", "dpo", "feynrl", "rope"}
SHA256_HEX_LENGTH = 64
GIT_SHA_LENGTH = 40


class MatrixError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_matrix(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pipelines = matrix.get("pipelines", [])
    papers = matrix.get("papers", [])
    selected = {item.get("id") for item in pipelines if item.get("role") == "selected"}
    fallbacks = {item.get("id") for item in pipelines if item.get("role") == "fallback"}
    paper_ids = {item.get("id") for item in papers}

    if len({item.get("id") for item in pipelines}) != len(pipelines):
        errors.append("pipeline-ids-must-be-unique")
    if len(paper_ids) != len(papers):
        errors.append("paper-ids-must-be-unique")

    if selected != SELECTED_PIPELINES:
        errors.append("selected-pipelines-do-not-match-approved-shortlist")
    if fallbacks != {"paper2slides_fast_academic_short"}:
        errors.append("paper2slides-must-be-the-only-declared-fallback")
    if paper_ids != PAPER_FAMILIES or len(papers) != len(PAPER_FAMILIES):
        errors.append("paper-families-must-be-transformers-dpo-feynrl-rope")
    if len(selected) * len(paper_ids) != 12:
        errors.append("selected-matrix-must-have-twelve-cells")

    for pipeline in pipelines:
        sha = pipeline.get("commit_sha", "")
        license_hash = pipeline.get("license_sha256", "")
        if len(sha) != GIT_SHA_LENGTH or any(ch not in "0123456789abcdef" for ch in sha):
            errors.append(f"pipeline:{pipeline.get('id')}:invalid-commit-sha")
        if len(license_hash) != SHA256_HEX_LENGTH or any(ch not in "0123456789abcdef" for ch in license_hash):
            errors.append(f"pipeline:{pipeline.get('id')}:invalid-license-hash")
        if not pipeline.get("native_entrypoint"):
            errors.append(f"pipeline:{pipeline.get('id')}:missing-native-entrypoint")

    for paper in papers:
        content_hash = paper.get("content_sha256")
        if paper.get("snapshot_state") == "frozen":
            if not isinstance(content_hash, str) or len(content_hash) != SHA256_HEX_LENGTH:
                errors.append(f"paper:{paper.get('id')}:frozen-without-sha256")
            if not paper.get("retrieved_at"):
                errors.append(f"paper:{paper.get('id')}:frozen-without-retrieval-time")
        elif content_hash is not None:
            errors.append(f"paper:{paper.get('id')}:unstaged-must-not-claim-hash")

    budget = matrix.get("budget_policy", {})
    if budget.get("cell_limit_usd") != 15.0 or budget.get("experiment_limit_usd") != 200.0:
        errors.append("budget:approved-limits-mismatch")
    if budget.get("paid_stage_policy") != "fail_closed_when_rate_card_or_projection_unknown":
        errors.append("budget:must-fail-closed")
    return errors


def initial_ledger(matrix: dict[str, Any]) -> dict[str, Any]:
    cells = []
    selected = [item for item in matrix["pipelines"] if item["role"] == "selected"]
    for pipeline in selected:
        for paper in matrix["papers"]:
            blocker = None
            if paper["snapshot_state"] != "frozen":
                blocker = "input_snapshot_not_staged"
            cells.append(
                {
                    "cell_id": f"{pipeline['id']}:{paper['id']}",
                    "pipeline_id": pipeline["id"],
                    "paper_id": paper["id"],
                    "status": "blocked" if blocker else "not_started",
                    "completion": "blocked" if blocker else "planned",
                    "blocker": blocker,
                    "job_ids": [],
                    "artifacts": [],
                    "provider_calls": 0,
                    "provider_cost_measured_usd": 0.0,
                    "provider_cost_estimated_usd": None,
                    "compute": None,
                }
            )
    return {
        "schema_version": "paper-to-slides-results/1.0.0",
        "experiment_id": matrix["experiment_id"],
        "matrix_sha256": hashlib.sha256(
            json.dumps(matrix, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "cells": cells,
        "fallback_observations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--init-ledger", type=Path)
    args = parser.parse_args()
    matrix = load_json(args.matrix)
    errors = validate_matrix(matrix)
    if errors:
        raise MatrixError("; ".join(errors))
    if args.init_ledger:
        ledger = initial_ledger(matrix)
        args.init_ledger.parent.mkdir(parents=True, exist_ok=True)
        args.init_ledger.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print("valid: 3 selected pipelines x 4 paper families = 12 cells; 1 fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
