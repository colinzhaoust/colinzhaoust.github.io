"""Pinned-source extraction and evidence harvesting for reference renders.

This module never fetches source.  Callers must provide a local checkout or
archive which :func:`verify_source_root` validates against the registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reference import ReferencePreparationError, validate_model_visible_reference
from .registry import load_registry, sha256_file, verify_source_root


class ReferenceBatchError(RuntimeError):
    """A pinned source bundle or render inventory is inconsistent."""


UPSTREAM_SAVE_LAST_FRAME_SCENES = {"GraphAreaPlot", "ThreeDSurfacePlot"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _directive_body(lines: list[str], scene_class: str) -> tuple[list[str], int, int]:
    marker = f".. manim:: {scene_class}"
    try:
        directive_index = next(index for index, line in enumerate(lines) if line.strip() == marker)
    except StopIteration as exc:
        raise ReferenceBatchError(f"Missing pinned RST directive for {scene_class}") from exc

    end = directive_index + 1
    while end < len(lines):
        line = lines[end]
        if line and not line[0].isspace():
            break
        end += 1

    block = lines[directive_index + 1 : end]
    class_marker = f"class {scene_class}("
    try:
        class_offset = next(index for index, line in enumerate(block) if class_marker in line)
    except StopIteration as exc:
        raise ReferenceBatchError(f"Missing class body for {scene_class}") from exc

    code = textwrap.dedent("\n".join(block[class_offset:])).rstrip().splitlines()
    if not code or not code[0].startswith(class_marker):
        raise ReferenceBatchError(f"Could not dedent exact class body for {scene_class}")
    return code, directive_index + 1, directive_index + 2 + class_offset


def extract_registered_scenes(
    registry: Mapping[str, Any], source_root: Path, output_path: Path
) -> dict[str, Any]:
    """Verify the checkout and extract exactly the ten registered RST snippets."""

    source_verification = verify_source_root(registry, source_root)
    source_path = source_root / registry["upstream"]["source_path"]
    lines = source_path.read_text(encoding="utf-8").splitlines()
    chunks = [
        "# Generated from the pinned Manim Community gallery source.",
        "# Do not hand edit. See the adjacent source_manifest.json.",
        "from manim import *",
        "import numpy as np",
        "",
    ]
    extracted: list[dict[str, Any]] = []
    for scene in registry["scenes"]:
        code, directive_line, class_line = _directive_body(lines, scene["scene_class"])
        if directive_line != scene["directive_line"] or class_line != scene["class_line"]:
            raise ReferenceBatchError(
                f"Pinned line mismatch for {scene['scene_class']}: "
                f"directive={directive_line}, class={class_line}"
            )
        chunks.extend(code)
        chunks.extend(["", ""])
        extracted.append(
            {
                "case_id": scene["case_id"],
                "scene_class": scene["scene_class"],
                "directive_line": directive_line,
                "class_line": class_line,
                "code_sha256": hashlib.sha256(
                    ("\n".join(code) + "\n").encode("utf-8")
                ).hexdigest(),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "backtranslation-reference-source-bundle/v1",
        "generated_at": _utc_now(),
        "registry_id": registry["registry_id"],
        "upstream": registry["upstream"],
        "source_verification": source_verification,
        "generated_source": {
            "path": output_path.name,
            "sha256": sha256_file(output_path),
        },
        "license_notice_paths": [item["path"] for item in registry["license_snapshot"]["files"]],
        "scenes": extracted,
    }
    return manifest


def harvest_reference_inventory(
    registry: Mapping[str, Any], protocol: Mapping[str, Any], run_root: Path
) -> dict[str, Any]:
    """Build a ten-row inventory while retaining every failure in the denominator."""

    rows: list[dict[str, Any]] = []
    completed = 0
    config = protocol["reference_preparation"]
    for scene in registry["scenes"]:
        case_root = run_root / "cases" / scene["case_id"]
        status_path = case_root / "status.json"
        if not status_path.is_file():
            rows.append(
                {
                    "case_id": scene["case_id"],
                    "scene_class": scene["scene_class"],
                    "status": "missing",
                    "failure_code": "missing_job_evidence",
                }
            )
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        failure_detail = status.get("failure_code")
        tex_logs = list((case_root / "raw_media").glob("Tex/*.log"))
        if any("standalone.cls" in path.read_text(encoding="utf-8", errors="replace") for path in tex_logs):
            failure_detail = "missing_runtime_dependency_standalone_cls"
        elif (
            status.get("status") != "completed"
            and scene["scene_class"] in UPSTREAM_SAVE_LAST_FRAME_SCENES
            and (status.get("exit_codes") or {}).get("render") == 0
            and not (status.get("raw_render") or {}).get("path")
        ):
            failure_detail = "upstream_save_last_frame_no_mp4"
        row = {
            "case_id": scene["case_id"],
            "scene_class": scene["scene_class"],
            "status": status.get("status"),
            "failure_code": status.get("failure_code"),
            "failure_detail": failure_detail,
            "started_at": status.get("started_at"),
            "finished_at": status.get("finished_at"),
            "pipeline_commit": status.get("pipeline_commit"),
            "upstream_commit": status.get("upstream_commit"),
            "exit_codes": status.get("exit_codes", {}),
            "recovery": status.get("recovery"),
            "slurm": status.get("slurm", {}),
            "raw_render": status.get("raw_render"),
            "reference": status.get("reference"),
        }
        if status.get("status") == "completed":
            reference = case_root / "model_input" / scene["case_id"] / "reference.mp4"
            try:
                media = validate_model_visible_reference(reference, scene["case_id"], config)
            except (ReferencePreparationError, FileNotFoundError) as exc:
                row["status"] = "failed"
                row["failure_code"] = "invalid_reference_media"
                row["validation_error"] = type(exc).__name__
            else:
                expected_hash = (status.get("reference") or {}).get("sha256")
                actual_hash = sha256_file(reference)
                if expected_hash != actual_hash:
                    row["status"] = "failed"
                    row["failure_code"] = "reference_hash_mismatch"
                else:
                    row["reference"] = {
                        **(status.get("reference") or {}),
                        "sha256": actual_hash,
                        "media": media,
                    }
                    completed += 1
        rows.append(row)

    return {
        "schema_version": "backtranslation-reference-inventory/v1",
        "generated_at": _utc_now(),
        "registry_id": registry["registry_id"],
        "claim_scope": registry["benchmark_claim"],
        "contamination": registry["contamination"],
        "upstream": registry["upstream"],
        "license_snapshot": registry["license_snapshot"],
        "denominator": len(registry["scenes"]),
        "completed": completed,
        "failed_or_missing": len(registry["scenes"]) - completed,
        "conditions": {
            "human_reference": "measured_from_pinned_source",
            "one_shot": "blocked_no_true_video_input_provider_and_external_sandbox",
            "self_refined": "blocked_no_true_video_input_provider_and_external_sandbox",
        },
        "cases": rows,
    }


def combine_reference_runs(
    registry: Mapping[str, Any],
    protocol: Mapping[str, Any],
    runs: Sequence[tuple[str, Path]],
    *,
    retrieval_root: str | None = None,
) -> dict[str, Any]:
    """Combine initial and recovery runs without erasing failed attempts.

    A recovery array normally schedules only a subset of the ten cases. Missing
    rows from such a run are therefore not counted as attempts; only persisted
    ``status.json`` rows enter the ledger. The selected outcome is the latest
    successful attempt, or the latest persisted failure when no attempt
    completed. The result contains no wall-clock generation timestamp, so the
    same immutable run directories produce byte-identical JSON.
    """

    if not runs:
        raise ReferenceBatchError("At least one reference run is required")
    run_ids = [run_id for run_id, _ in runs]
    if len(run_ids) != len(set(run_ids)):
        raise ReferenceBatchError("Reference run IDs must be unique")

    attempts_by_case: dict[str, list[dict[str, Any]]] = {
        scene["case_id"]: [] for scene in registry["scenes"]
    }
    run_ledger: list[dict[str, Any]] = []
    observed_times: list[str] = []
    total_attempts = 0

    for run_id, run_root in runs:
        inventory = harvest_reference_inventory(registry, protocol, run_root)
        persisted = [
            row for row in inventory["cases"]
            if row.get("failure_code") != "missing_job_evidence"
        ]
        commits = sorted({
            row["pipeline_commit"] for row in persisted if row.get("pipeline_commit")
        })
        upstream_commits = sorted({
            row["upstream_commit"] for row in persisted if row.get("upstream_commit")
        })
        scheduled = [row["case_id"] for row in persisted]
        run_record: dict[str, Any] = {
            "run_id": run_id,
            "scheduled_case_ids": scheduled,
            "attempt_count": len(persisted),
            "pipeline_commits": commits,
            "upstream_commits": upstream_commits,
        }
        if retrieval_root:
            run_record["retrieval_root"] = f"{retrieval_root.rstrip('/')}/runs/{run_id}"
        run_ledger.append(run_record)
        for row in persisted:
            attempt = {"run_id": run_id, **row}
            attempts_by_case[row["case_id"]].append(attempt)
            total_attempts += 1
            if row.get("finished_at"):
                observed_times.append(row["finished_at"])

    cases: list[dict[str, Any]] = []
    completed = 0
    for scene in registry["scenes"]:
        attempts = attempts_by_case[scene["case_id"]]
        successful_indices = [
            index for index, attempt in enumerate(attempts)
            if attempt.get("status") == "completed"
        ]
        selected_index = successful_indices[-1] if successful_indices else (
            len(attempts) - 1 if attempts else None
        )
        final_status = (
            attempts[selected_index].get("status") if selected_index is not None else "missing"
        )
        if final_status == "completed":
            completed += 1
        cases.append({
            "case_id": scene["case_id"],
            "scene_class": scene["scene_class"],
            "attempt_count": len(attempts),
            "selected_attempt_index": selected_index,
            "final_status": final_status,
            "attempts": attempts,
        })

    return {
        "schema_version": "backtranslation-reference-combined-inventory/v1",
        "observed_at": max(observed_times) if observed_times else None,
        "registry_id": registry["registry_id"],
        "claim_scope": registry["benchmark_claim"],
        "contamination": registry["contamination"],
        "upstream": registry["upstream"],
        "license_snapshot": registry["license_snapshot"],
        "denominator": len(registry["scenes"]),
        "completed": completed,
        "failed_or_missing": len(registry["scenes"]) - completed,
        "attempt_count": total_attempts,
        "runs": run_ledger,
        "conditions": {
            "human_reference": "measured_from_pinned_source",
            "one_shot": "blocked_no_true_video_input_provider_and_external_sandbox",
            "self_refined": "blocked_no_true_video_input_provider_and_external_sandbox",
        },
        "cases": cases,
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract")
    extract.add_argument("--registry", type=Path, required=True)
    extract.add_argument("--source-root", type=Path, required=True)
    extract.add_argument("--output-source", type=Path, required=True)
    extract.add_argument("--output-manifest", type=Path, required=True)
    harvest = subparsers.add_parser("harvest")
    harvest.add_argument("--registry", type=Path, required=True)
    harvest.add_argument("--protocol", type=Path, required=True)
    harvest.add_argument("--run-root", type=Path, required=True)
    harvest.add_argument("--output", type=Path, required=True)
    combine = subparsers.add_parser("combine")
    combine.add_argument("--registry", type=Path, required=True)
    combine.add_argument("--protocol", type=Path, required=True)
    combine.add_argument(
        "--run", action="append", required=True, metavar="RUN_ID=PATH",
        help="Immutable initial or recovery run directory; repeat in chronological order.",
    )
    combine.add_argument("--retrieval-root")
    combine.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    registry = load_registry(args.registry)
    if args.command == "extract":
        manifest = extract_registered_scenes(registry, args.source_root, args.output_source)
        _write_json(args.output_manifest, manifest)
    elif args.command == "harvest":
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        inventory = harvest_reference_inventory(registry, protocol, args.run_root)
        _write_json(args.output, inventory)
    else:
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        runs: list[tuple[str, Path]] = []
        for value in args.run:
            run_id, separator, raw_path = value.partition("=")
            if not separator or not run_id or not raw_path:
                raise ReferenceBatchError(f"Invalid --run value: {value!r}")
            runs.append((run_id, Path(raw_path)))
        inventory = combine_reference_runs(
            registry, protocol, runs, retrieval_root=args.retrieval_root
        )
        _write_json(args.output, inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
