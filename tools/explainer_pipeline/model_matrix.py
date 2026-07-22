from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .common import DATA_ROOT, ROOT, load_json, sha256_json
from .pipeline import replay_provider, run_pipeline
from .providers import BedrockProvider, OpenAICompatibleProvider, StageProvider, VertexProvider
from .renderer import render_comparison_site
from .validation import validate_bundle


class MatrixError(RuntimeError):
    pass


def normalize_repeated_animation_media(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Give each registered animation first-use ownership within one paper."""
    seen: set[str] = set()
    operations: list[dict[str, Any]] = []
    content = bundle["section_content"]
    decisions_by_section: dict[str, list[dict[str, Any]]] = {}
    for decision in content.get("animation_plan", []):
        decisions_by_section.setdefault(decision["section_id"], []).append(decision)
    kept_decisions: list[dict[str, Any]] = []
    for section in bundle["lesson_plan"]["sections"]:
        section_id = section["id"]
        blocks = content["sections"][section_id]["blocks"]
        duplicate_media: set[str] = set()
        for decision in decisions_by_section.get(section_id, []):
            media_id = decision["media_id"]
            if media_id in seen:
                duplicate_media.add(media_id)
                operations.append({
                    "section_id": section_id,
                    "operation": "drop_repeated_animation_after_first_use",
                    "media_id": media_id,
                })
            else:
                seen.add(media_id)
                kept_decisions.append(decision)
        if duplicate_media:
            content["sections"][section_id]["blocks"] = [
                block
                for block in blocks
                if not (
                    block.get("type") in {"video", "micro_video"}
                    and block.get("media_id") in duplicate_media
                )
            ]
    content["animation_plan"] = kept_decisions
    if operations:
        trace = next(
            item for item in bundle["generation"]["stage_traces"] if item["stage"] == "section_content"
        )
        trace.setdefault("structural_normalizations", []).extend(operations)
        trace["response_sha256"] = sha256_json(content)
    return operations


def _path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def provider_from_spec(spec: dict[str, Any]) -> StageProvider:
    mode = spec.get("mode")
    common = {
        "model_id": spec["model_id"],
        "max_tokens": int(spec.get("max_tokens", 8000)),
    }
    if mode == "bedrock":
        return BedrockProvider(
            **common,
            region=str(spec.get("region", "us-east-1")),
            env_file=_path(spec["env_file"]) if spec.get("env_file") else None,
        )
    if mode == "vertex":
        return VertexProvider(
            **common,
            credential_file=_path(spec["credential_file"]),
            project_id=str(spec["project_id"]),
            location=str(spec.get("location", "global")),
            timeout=int(spec.get("timeout", 600)),
        )
    if mode == "openai-compatible":
        return OpenAICompatibleProvider(
            **common,
            base_url=str(spec["base_url"]),
            api_key_env=str(spec.get("api_key_env", "OPENAI_API_KEY")),
            env_file=_path(spec["env_file"]) if spec.get("env_file") else None,
            api_path=str(spec.get("api_path", "chat/completions")),
            provider_name=str(spec.get("provider_name", "openai_compatible")),
            timeout=int(spec.get("timeout", 600)),
        )
    raise MatrixError(f"unsupported provider mode: {mode}")


def _load_or_run(
    *,
    run_spec: dict[str, Any],
    paper_spec: dict[str, Any],
    run_root: Path,
    resume: bool,
) -> dict[str, Any]:
    paper_id = str(paper_spec["paper_id"])
    source_path = _path(paper_spec.get("source_packet", DATA_ROOT / "papers" / f"{paper_id}.json"))
    destination = run_root / str(run_spec["run_id"]) / paper_id
    bundle_path = destination / "explainer_bundle.json"
    if resume and bundle_path.is_file():
        bundle = load_json(bundle_path)
        operations = normalize_repeated_animation_media(bundle)
        validate_bundle(bundle)
        if operations:
            bundle_path.write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            section_stage_path = destination / "stages" / "section_content.json"
            if section_stage_path.is_file():
                section_stage = load_json(section_stage_path)
                section_stage["payload"] = bundle["section_content"]
                section_stage["trace"] = next(
                    item
                    for item in bundle["generation"]["stage_traces"]
                    if item["stage"] == "section_content"
                )
                section_stage_path.write_text(
                    json.dumps(section_stage, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            manifest_path = destination / "run_manifest.json"
            if manifest_path.is_file():
                manifest = load_json(manifest_path)
                manifest["bundle_sha256"] = sha256_json(bundle)
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        expected_hash = sha256_json(load_json(source_path))
        if bundle["generation"]["source_packet_sha256"] == expected_hash:
            print(f"[{run_spec['run_id']}/{paper_id}] reuse validated bundle", flush=True)
            return bundle
    print(f"[{run_spec['run_id']}/{paper_id}] generate", flush=True)
    bundle = run_pipeline(
        source_path,
        destination,
        provider_from_spec(run_spec["provider"]),
        max_attempts=int(run_spec.get("max_attempts", 3)),
    )
    print(f"[{run_spec['run_id']}/{paper_id}] complete", flush=True)
    return bundle


def _run_model_row(
    *,
    run_spec: dict[str, Any],
    paper_specs: list[dict[str, Any]],
    run_root: Path,
    resume: bool,
) -> dict[str, dict[str, Any]]:
    """Run one model across papers sequentially while models run in parallel."""
    return {
        str(paper_spec["paper_id"]): _load_or_run(
            run_spec=run_spec,
            paper_spec=paper_spec,
            run_root=run_root,
            resume=resume,
        )
        for paper_spec in paper_specs
    }


def run_model_matrix(
    specification_path: Path,
    *,
    run_root: Path,
    output_dir: Path,
    workers: int = 3,
    resume: bool = True,
) -> dict[str, Any]:
    specification = load_json(specification_path)
    if specification.get("schema_version") != "explainer-model-matrix/0.1.0":
        raise MatrixError("matrix specification must use explainer-model-matrix/0.1.0")
    paper_specs = specification.get("papers", [])
    run_specs = specification.get("runs", [])
    if not paper_specs or not run_specs:
        raise MatrixError("matrix needs at least one paper and one model run")

    reference_bundles = [
        run_pipeline(
            _path(paper.get("source_packet", DATA_ROOT / "papers" / f"{paper['paper_id']}.json")),
            run_root / "reviewed-reference" / str(paper["paper_id"]),
            replay_provider(),
        )
        for paper in paper_specs
    ]
    completed: dict[tuple[str, str], dict[str, Any]] = {}
    failed_rows: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                _run_model_row,
                run_spec=run_spec,
                paper_specs=paper_specs,
                run_root=run_root,
                resume=resume,
            ): str(run_spec["run_id"])
            for run_spec in run_specs
        }
        for future in as_completed(futures):
            run_id = futures[future]
            try:
                for paper_id, bundle in future.result().items():
                    completed[(run_id, paper_id)] = bundle
            except Exception as exc:  # noqa: BLE001 - identify the failed matrix cell
                failed_rows[run_id] = str(exc)
                print(f"[{run_id}] failed: {exc}", flush=True)

    rendered_runs = [{
        "run_id": "reviewed-reference",
        "label": "Reviewed reference",
        "description": "Human-reviewed frozen API outputs used as the teaching target.",
        "status": "reviewed",
        "model_summary": "Human/Codex-reviewed reference, not a live-model output.",
        "endpoint": "No live endpoint; frozen replay",
        "bundles": reference_bundles,
    }]
    for run_spec in run_specs:
        run_id = str(run_spec["run_id"])
        if run_id in failed_rows:
            continue
        rendered_runs.append({
            "run_id": run_id,
            "label": str(run_spec.get("label", run_id)),
            "description": str(run_spec.get("description", "Live model output under the fixed teaching harness.")),
            "status": "generated",
            "model_summary": str(run_spec.get("model_summary", run_spec["provider"]["model_id"])),
            "endpoint": str(run_spec.get("endpoint", run_spec["provider"]["mode"])),
            "bundles": [completed[(run_id, str(paper["paper_id"]))] for paper in paper_specs],
        })
    failed_candidates = [
        {
            "candidate_id": str(run_spec["run_id"]),
            "label": str(run_spec.get("label", run_spec["run_id"])),
            "status": "generation_failed",
            "model_summary": str(run_spec.get("model_summary", run_spec["provider"]["model_id"])),
            "provider": str(run_spec["provider"]["mode"]),
            "model_id": str(run_spec["provider"]["model_id"]),
            "endpoint": str(run_spec.get("endpoint", run_spec["provider"]["mode"])),
            "note": failed_rows[str(run_spec["run_id"])][:500],
            "documentation_url": str(run_spec.get("documentation_url", "#")),
        }
        for run_spec in run_specs
        if str(run_spec["run_id"]) in failed_rows
    ]
    site_manifest = render_comparison_site(rendered_runs, output_dir, candidate_runs=failed_candidates)
    sanitized = {
        "schema_version": "explainer-model-matrix-run/0.1.0",
        "specification_sha256": sha256_json(specification),
        "runs": [
            {
                "run_id": run["run_id"],
                "label": run["label"],
                "models": sorted({
                    trace["model"]
                    for bundle in run["bundles"]
                    for trace in bundle["generation"]["stage_traces"]
                }),
                "bundles": [
                    {
                        "paper_id": bundle["paper_id"],
                        "bundle_sha256": sha256_json(bundle),
                    }
                    for bundle in run["bundles"]
                ],
            }
            for run in rendered_runs
        ],
        "failed_rows": failed_rows,
        "site_manifest": site_manifest,
    }
    manifest_path = run_root / "matrix_run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sanitized
