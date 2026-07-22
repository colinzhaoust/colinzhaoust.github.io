from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .common import DATA_ROOT, load_json, sha256_json
from .formula_map import build_formula_map
from .code_map import build_code_map
from .pricing import estimate_cost
from .prompts import build_prompt
from .providers import ReplayProvider, StageProvider
from .validation import validate_bundle, validate_source_packet, validate_stage_payload


STAGES = ("concept_graph", "lesson_plan", "section_content")


class PipelineError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_pipeline(
    source_path: Path,
    run_root: Path,
    provider: StageProvider,
) -> dict[str, Any]:
    packet = load_json(source_path)
    validate_source_packet(packet)
    paper_id = packet["paper_id"]
    outputs: dict[str, Any] = {}
    traces: list[dict[str, Any]] = []
    for stage in STAGES:
        prompt = build_prompt(stage, packet, outputs)
        result = provider.generate(stage, paper_id, prompt)
        validate_stage_payload(stage, result.payload, packet)
        outputs[stage] = result.payload
        trace = {
            "stage": stage,
            "paper_id": paper_id,
            "provider": result.provider,
            "model": result.model,
            "generation_mode": result.generation_mode,
            "prompt_sha256": sha256_json({"prompt": prompt}),
            "response_sha256": result.response_sha256,
            "source_record": result.source_record,
            "usage": result.usage,
            "duration_ms": result.duration_ms,
            "cost": estimate_cost(result.provider, result.model, result.usage),
        }
        traces.append(trace)
        _write_json(run_root / "stages" / f"{stage}.json", {"trace": trace, "payload": result.payload})
    bundle = {
        "schema_version": "explainer-bundle/0.1.0",
        "paper_id": paper_id,
        "source_packet": packet,
        "concept_graph": outputs["concept_graph"],
        "lesson_plan": outputs["lesson_plan"],
        "section_content": outputs["section_content"],
        "formula_map": build_formula_map(packet),
        "code_map": build_code_map(packet),
        "generation": {
            "pipeline_version": "explainer-pipeline/0.1.0",
            "source_packet_sha256": sha256_json(packet),
            "stage_traces": traces,
            "completion": "full",
        },
    }
    validate_bundle(bundle)
    _write_json(run_root / "explainer_bundle.json", bundle)
    bundle_hash = sha256_json(bundle)
    _write_json(
        run_root / "run_manifest.json",
        {
            "schema_version": "explainer-run/0.1.0",
            "paper_id": paper_id,
            "bundle_ref": "explainer_bundle.json",
            "bundle_sha256": bundle_hash,
            "stage_count": len(traces),
            "generation_modes": sorted({item["generation_mode"] for item in traces}),
        },
    )
    return bundle


def replay_provider() -> ReplayProvider:
    return ReplayProvider(DATA_ROOT / "replays")


def build_catalog(
    bundles: Iterable[dict[str, Any]],
    *,
    run_id: str = "reviewed-reference",
    run_label: str = "Reviewed reference",
    run_description: str = "Human-reviewed frozen API outputs used as the reference run.",
    run_status: str = "reviewed",
) -> dict[str, Any]:
    """Build a single-run catalog.

    The renderer uses the same shape for one or many frozen runs.  Keeping this
    helper single-run preserves the small public API while making model identity
    explicit instead of attaching a mutable label in the browser.
    """
    papers = []
    documents = list(bundles)
    for bundle in documents:
        packet = bundle["source_packet"]
        papers.append(
            {
                "paper_id": bundle["paper_id"],
                "short_title": packet["short_title"],
                "title": packet["title"],
                "central_question": packet["central_question"],
                "completion": bundle["generation"]["completion"],
            }
        )
    traces = [trace for bundle in documents for trace in bundle["generation"]["stage_traces"]]
    run = {
        "run_id": run_id,
        "label": run_label,
        "description": run_description,
        "status": run_status,
        "providers": sorted({trace["provider"] for trace in traces}),
        "models": sorted({trace["model"] for trace in traces}),
        "generation_modes": sorted({trace["generation_mode"] for trace in traces}),
        "papers": [
            {
                "paper_id": bundle["paper_id"],
                "bundle": f"data/runs/{run_id}/{bundle['paper_id']}.json",
            }
            for bundle in documents
        ],
    }
    return {
        "schema_version": "explainer-site-catalog/0.2.0",
        "title": "Paper + Code Explainer Pipeline",
        "papers": papers,
        "runs": [run],
        "default_run": run_id,
        "default_paper": papers[0]["paper_id"] if papers else None,
        "comparison_protocol": {
            "scope": "planner_stages",
            "fixed": [
                "source packet and source locators",
                "stage prompts and JSON schemas",
                "validation policy",
                "formula compiler and Manim registry",
                "HTML/Manim renderer and published media",
            ],
            "varied": ["concept graph", "lesson plan", "typed section content"],
            "rule": "Only complete, validated, frozen bundles appear in the model-run selector.",
        },
    }
