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
from typing import Any, Mapping

from .reference import ReferencePreparationError, validate_model_visible_reference
from .registry import load_registry, sha256_file, verify_source_root


class ReferenceBatchError(RuntimeError):
    """A pinned source bundle or render inventory is inconsistent."""


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
        row = {
            "case_id": scene["case_id"],
            "scene_class": scene["scene_class"],
            "status": status.get("status"),
            "failure_code": status.get("failure_code"),
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
    return result


def main() -> int:
    args = parser().parse_args()
    registry = load_registry(args.registry)
    if args.command == "extract":
        manifest = extract_registered_scenes(registry, args.source_root, args.output_source)
        _write_json(args.output_manifest, manifest)
    else:
        protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        inventory = harvest_reference_inventory(registry, protocol, args.run_root)
        _write_json(args.output, inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
