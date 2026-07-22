from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from .common import TEMPLATE_ROOT, resolve_repo_path, sha256_file, sha256_json
from .pipeline import build_catalog
from .validation import validate_bundle


class RenderError(RuntimeError):
    pass


def _copy(path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)


def _validated_run_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", value):
        raise RenderError(f"invalid run_id {value!r}; use lowercase letters, digits, and hyphens")
    return value


def _trace_summary(traces: list[dict[str, Any]]) -> dict[str, Any]:
    usage_records = [item["usage"] for item in traces if item.get("usage")]
    costs = [item.get("cost", {}).get("estimated_usd") for item in traces]
    estimated_costs = [value for value in costs if isinstance(value, (int, float))]
    return {
        "stage_count": len(traces),
        "api_call_count": sum(item.get("attempt_count", 1) for item in traces),
        "repair_count": sum(
            max(0, item.get("attempt_count", 1) - item.get("section_call_count", 1))
            for item in traces
        ),
        "structural_compilation_count": sum(
            len(item.get("structural_normalizations", [])) for item in traces
        ),
        "corrective_normalization_count": sum(
            operation.get("operation") in {
                "discard_model_media_glue_before_materialization",
                "keep_first_shared_appendix_entry",
                "drop_repeated_animation_after_first_use",
            }
            for item in traces
            for operation in item.get("structural_normalizations", [])
        ),
        "input_tokens": sum(item.get("input_tokens", 0) for item in usage_records) if usage_records else None,
        "output_tokens": sum(item.get("output_tokens", 0) for item in usage_records) if usage_records else None,
        "reasoning_tokens": sum(item.get("reasoning_tokens", 0) for item in usage_records) if usage_records else None,
        "total_tokens": sum(item.get("total_tokens", 0) for item in usage_records) if usage_records else None,
        "duration_ms": sum(item.get("duration_ms", 0) for item in traces),
        "estimated_cost_usd": round(sum(estimated_costs), 6) if len(estimated_costs) == len(traces) else None,
        "measurement": "recorded" if usage_records else "not_recorded",
    }


def render_comparison_site(
    runs: Iterable[dict[str, Any]],
    output_dir: Path,
    *,
    candidate_runs: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Render complete frozen runs into one comparison-ready static site.

    ``runs`` is deliberately a renderer input, not browser configuration.  A
    model only appears in the selector after every bundle has passed validation
    and has been written with immutable trace hashes.
    """
    run_documents = []
    seen_run_ids: set[str] = set()
    source_hashes: dict[str, str] = {}
    paper_order: list[str] = []
    paper_metadata: dict[str, dict[str, Any]] = {}
    for raw_run in runs:
        run_id = _validated_run_id(str(raw_run.get("run_id", "")))
        if run_id in seen_run_ids:
            raise RenderError(f"duplicate run_id: {run_id}")
        seen_run_ids.add(run_id)
        documents = list(raw_run.get("bundles", []))
        if not documents:
            raise RenderError(f"run {run_id} has no bundles")
        for document in documents:
            validate_bundle(document)
            paper_id = document["paper_id"]
            packet_hash = document["generation"]["source_packet_sha256"]
            if paper_id in source_hashes and source_hashes[paper_id] != packet_hash:
                raise RenderError(
                    f"run {run_id}/{paper_id} changes the source packet; "
                    "planner comparison requires identical frozen inputs"
                )
            source_hashes[paper_id] = packet_hash
            if paper_id not in paper_order:
                paper_order.append(paper_id)
                packet = document["source_packet"]
                paper_metadata[paper_id] = {
                    "paper_id": paper_id,
                    "short_title": packet["short_title"],
                    "title": packet["title"],
                    "central_question": packet["central_question"],
                    "completion": document["generation"]["completion"],
                }
        run_documents.append(
            {
                "run_id": run_id,
                "label": str(raw_run.get("label") or run_id),
                "description": str(raw_run.get("description") or "Frozen validated model run."),
                "status": str(raw_run.get("status") or "generated"),
                "model_summary": str(raw_run.get("model_summary") or "Model identity is recorded by immutable provider and model IDs."),
                "endpoint": str(raw_run.get("endpoint") or "frozen replay"),
                "bundles": documents,
            }
        )
    if not run_documents:
        raise RenderError("at least one complete explainer run is required")
    expected_papers = set(paper_order)
    for run in run_documents:
        actual = {bundle["paper_id"] for bundle in run["bundles"]}
        if actual != expected_papers:
            raise RenderError(
                f"run {run['run_id']} covers {sorted(actual)}; expected {sorted(expected_papers)}"
            )
    if output_dir.resolve() == Path("/") or output_dir.resolve() == Path.home().resolve():
        raise RenderError("refusing to render into a broad filesystem target")
    output_dir.mkdir(parents=True, exist_ok=True)
    for generated in (output_dir / "assets", output_dir / "data"):
        if generated.is_dir():
            shutil.rmtree(generated)
    for filename in ("index.html", "styles.css", "app.js"):
        _copy(TEMPLATE_ROOT / filename, output_dir / filename)
    data_root = output_dir / "data"
    media_index: list[dict[str, Any]] = []
    catalog_runs = []
    for run in run_documents:
        run_id = run["run_id"]
        traces = [trace for bundle in run["bundles"] for trace in bundle["generation"]["stage_traces"]]
        catalog_papers = []
        for bundle in run["bundles"]:
            paper_id = bundle["paper_id"]
            rendered = json.loads(json.dumps(bundle))
            for media in rendered["source_packet"].get("media", []):
                source = resolve_repo_path(media["path"])
                suffix = source.suffix.lower()
                destination = output_dir / "assets" / run_id / paper_id / f"{media['media_id']}{suffix}"
                _copy(source, destination)
                media["published_path"] = destination.relative_to(output_dir).as_posix()
                media_index.append(
                    {
                        "run_id": run_id,
                        "paper_id": paper_id,
                        "media_id": media["media_id"],
                        "path": media["published_path"],
                        "sha256": sha256_file(destination),
                        "size_bytes": destination.stat().st_size,
                    }
                )
            bundle_path = data_root / "runs" / run_id / f"{paper_id}.json"
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            bundle_path.write_text(
                json.dumps(rendered, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            catalog_papers.append(
                {
                    "paper_id": paper_id,
                    "bundle": bundle_path.relative_to(output_dir).as_posix(),
                    "bundle_sha256": sha256_json(rendered),
                    "source_packet_sha256": bundle["generation"]["source_packet_sha256"],
                    "section_count": len(bundle["lesson_plan"]["sections"]),
                    "block_count": sum(
                        len(section["blocks"])
                        for section in bundle["section_content"]["sections"].values()
                    ),
                    "animation_count": len(bundle["section_content"].get("animation_plan", [])),
                    "trace_summary": _trace_summary(bundle["generation"]["stage_traces"]),
                }
            )
        catalog_runs.append(
            {
                "run_id": run_id,
                "label": run["label"],
                "description": run["description"],
                "status": run["status"],
                "model_summary": run["model_summary"],
                "endpoint": run["endpoint"],
                "providers": sorted({trace["provider"] for trace in traces}),
                "models": sorted({trace["model"] for trace in traces}),
                "generation_modes": sorted({trace["generation_mode"] for trace in traces}),
                "trace_summary": _trace_summary(traces),
                "papers": catalog_papers,
            }
        )
    seed = run_documents[0]
    catalog = build_catalog(
        seed["bundles"],
        run_id=seed["run_id"],
        run_label=seed["label"],
        run_description=seed["description"],
        run_status=seed["status"],
    )
    catalog["papers"] = [paper_metadata[paper_id] for paper_id in paper_order]
    catalog["runs"] = catalog_runs
    catalog["candidate_runs"] = list(candidate_runs)
    (data_root / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "explainer-site-manifest/0.2.0",
        "run_count": len(run_documents),
        "runs": [run["run_id"] for run in run_documents],
        "paper_count": len(paper_order),
        "papers": paper_order,
        "media": media_index,
    }
    (data_root / "site_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def render_site(
    bundles: Iterable[dict[str, Any]],
    output_dir: Path,
    *,
    candidate_runs: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Render the reviewed-reference run (backward-compatible convenience API)."""
    return render_comparison_site(
        [
            {
                "run_id": "reviewed-reference",
                "label": "Reviewed reference",
                "description": "Human-reviewed frozen API outputs used as the reference run.",
                "status": "reviewed",
                "model_summary": "Human-reviewed API-shaped JSON fixture. It is a reference condition, not a frontier-model benchmark result.",
                "endpoint": "No live endpoint · frozen replay",
                "bundles": list(bundles),
            }
        ],
        output_dir,
        candidate_runs=candidate_runs,
    )
