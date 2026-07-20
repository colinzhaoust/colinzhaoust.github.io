"""Package selected Babel reference outcomes into a clean-checkout-safe bundle.

The combined inventory remains the authority for attempt selection.  This tool
copies only the selected normalized reference and its private evidence, creates
a deterministic midpoint poster, and records hashes for every public artifact.
It never changes or relabels failed/static outcomes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reference import probe_media, validate_model_visible_reference
from .registry import sha256_file


class ReferenceEvidencePackagingError(RuntimeError):
    """The selected evidence is missing or inconsistent."""


FORBIDDEN_PUBLIC_TOKENS = (
    "/home/",
    "/Users/",
    "xinranz3",
    "source-vault",
    "source_vault",
    "private/",
)


def _write_json(destination: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "path": destination.name,
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
    }


def _sanitize_attempt(attempt: dict[str, Any], case_id: str) -> None:
    run_id = attempt["run_id"]
    raw_render = attempt.get("raw_render")
    if isinstance(raw_render, dict) and raw_render.get("path"):
        raw_render["path"] = f"babel:bt-reference-v1/{run_id}/{case_id}/raw-render"
    reference = attempt.get("reference")
    if isinstance(reference, dict) and reference.get("sha256"):
        reference["remote_relative_path"] = f"cases/{case_id}/reference.mp4"
    recovery = attempt.get("recovery")
    if isinstance(recovery, dict) and recovery.get("dependency_provenance"):
        recovery["dependency_provenance"] = "not_packaged"


def _assert_public_bundle(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_PUBLIC_TOKENS:
            if token in content:
                raise ReferenceEvidencePackagingError(
                    f"Public evidence contains forbidden internal token {token!r}: {path}"
                )


def _copy(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file():
        raise ReferenceEvidencePackagingError(f"Missing evidence file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {
        "path": destination.name,
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
    }


def _poster(reference: Path, destination: Path, *, ffmpeg: str, ffprobe: str) -> dict[str, Any]:
    media = probe_media(reference, ffprobe=ffprobe)
    midpoint = max(float(media["duration_seconds"]) / 2.0, 0.0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-nostdin",
        "-y",
        "-ss",
        f"{midpoint:.6f}",
        "-i",
        str(reference),
        "-frames:v",
        "1",
        "-map_metadata",
        "-1",
        "-threads",
        "1",
        "-fflags",
        "+bitexact",
        str(destination),
    ]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0 or not destination.is_file():
        detail = proc.stderr.decode("utf-8", errors="replace")[-2000:]
        raise ReferenceEvidencePackagingError(detail or "ffmpeg poster extraction failed")
    return {
        "path": destination.name,
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
        "sample_fraction": 0.5,
        "sample_time_seconds": round(midpoint, 6),
    }


def package_reference_evidence(
    inventory_path: Path,
    protocol: Mapping[str, Any],
    runs: Mapping[str, Path],
    output_root: Path,
    *,
    source_manifest_path: Path | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> dict[str, Any]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("schema_version") != "backtranslation-reference-combined-inventory/v1":
        raise ReferenceEvidencePackagingError("Expected a combined reference inventory")

    output_root.mkdir(parents=True, exist_ok=True)
    for case in inventory["cases"]:
        for attempt in case["attempts"]:
            _sanitize_attempt(attempt, case["case_id"])
    copied_inventory = output_root / "combined_reference_inventory.json"
    _write_json(copied_inventory, inventory)
    source_manifest: dict[str, Any] | None = None
    if source_manifest_path is not None:
        source_manifest = _copy(source_manifest_path, output_root / "source_manifest.json")

    cases: list[dict[str, Any]] = []
    completed = 0
    for case in inventory["cases"]:
        selected_index = case.get("selected_attempt_index")
        if selected_index is None:
            cases.append({
                "case_id": case["case_id"],
                "final_status": "missing",
                "artifacts": {},
            })
            continue
        selected = case["attempts"][selected_index]
        run_id = selected["run_id"]
        if run_id not in runs:
            raise ReferenceEvidencePackagingError(f"No local run root for {run_id}")
        source_case = runs[run_id] / "cases" / case["case_id"]
        destination_case = output_root / "cases" / case["case_id"]
        status = json.loads((source_case / "status.json").read_text(encoding="utf-8"))
        status_attempt = {"run_id": run_id, **status}
        _sanitize_attempt(status_attempt, case["case_id"])
        status_attempt.pop("run_id")
        artifacts: dict[str, Any] = {
            "status": _write_json(destination_case / "status.json", status_attempt)
        }
        if selected.get("status") == "completed":
            source_reference = source_case / "model_input" / case["case_id"] / "reference.mp4"
            expected_hash = (selected.get("reference") or {}).get("sha256")
            if sha256_file(source_reference) != expected_hash:
                raise ReferenceEvidencePackagingError(
                    f"Selected reference hash mismatch for {case['case_id']}"
                )
            validate_model_visible_reference(
                source_reference,
                case["case_id"],
                protocol["reference_preparation"],
                ffprobe=ffprobe,
            )
            artifacts["reference"] = _copy(
                source_reference, destination_case / "reference.mp4"
            )
            artifacts["poster"] = _poster(
                source_reference,
                destination_case / "poster.png",
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
            )
            artifacts["ffprobe"] = _copy(
                source_case / "private" / "reference-ffprobe.json",
                destination_case / "reference-ffprobe.json",
            )
            artifacts["preparation_manifest"] = _copy(
                source_case / "private" / "reference-preparation.json",
                destination_case / "reference-preparation.json",
            )
            completed += 1
        cases.append({
            "case_id": case["case_id"],
            "scene_class": case["scene_class"],
            "final_status": case["final_status"],
            "failure_detail": selected.get("failure_detail"),
            "selected_run_id": run_id,
            "selected_slurm": selected.get("slurm", {}),
            "artifacts": artifacts,
        })

    if completed != inventory.get("completed"):
        raise ReferenceEvidencePackagingError("Packaged completion count differs from inventory")
    manifest = {
        "schema_version": "backtranslation-reference-evidence-bundle/v1",
        "inventory": {
            "path": copied_inventory.name,
            "sha256": sha256_file(copied_inventory),
            "completed": completed,
            "denominator": inventory["denominator"],
        },
        "source_manifest": source_manifest,
        "license_notice_paths": [
            "../../licenses/manim-LICENSE.txt",
            "../../licenses/manim-LICENSE.community.txt",
        ],
        "conditions": inventory["conditions"],
        "cases": cases,
    }
    manifest_path = output_root / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _assert_public_bundle(output_root)
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--inventory", type=Path, required=True)
    result.add_argument("--protocol", type=Path, required=True)
    result.add_argument("--run", action="append", required=True, metavar="RUN_ID=PATH")
    result.add_argument("--source-manifest", type=Path)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--ffmpeg", default="ffmpeg")
    result.add_argument("--ffprobe", default="ffprobe")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    runs: dict[str, Path] = {}
    for raw in args.run:
        run_id, separator, path = raw.partition("=")
        if not separator or not run_id or not path or run_id in runs:
            raise ReferenceEvidencePackagingError(f"Invalid or duplicate --run: {raw!r}")
        runs[run_id] = Path(path)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    package_reference_evidence(
        args.inventory,
        protocol,
        runs,
        args.output_root,
        source_manifest_path=args.source_manifest,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
