from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .common import DATA_ROOT, load_json, sha256_json
from .formula_map import build_formula_map
from .code_map import build_code_map
from .pricing import estimate_cost
from .prompts import build_prompt, build_repair_prompt, build_section_content_prompt
from .providers import ProviderError, ReplayProvider, StageProvider, StageResult
from .validation import ExplainerValidationError, validate_bundle, validate_source_packet, validate_stage_payload


STAGES = ("concept_graph", "lesson_plan", "section_content")


class PipelineError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _attempt_generation(
    *,
    provider: StageProvider,
    stage: str,
    paper_id: str,
    original_prompt: str,
    validator: Callable[[dict[str, Any]], None],
    max_attempts: int,
) -> tuple[StageResult | None, list[dict[str, Any]], str, str]:
    prompt = original_prompt
    attempts: list[dict[str, Any]] = []
    last_error = "unknown generation failure"
    for attempt_index in range(max_attempts):
        try:
            candidate = provider.generate(stage, paper_id, prompt)
        except ProviderError as exc:
            last_error = str(exc)
            attempts.append({
                "attempt": attempt_index + 1,
                "status": "provider_error",
                "prompt_sha256": sha256_json({"prompt": prompt}),
                "error": last_error[:1000],
            })
            prompt = (
                original_prompt
                if "HTTP 5" in last_error or "timed out" in last_error.lower()
                else build_repair_prompt(stage, original_prompt, None, last_error)
            )
            continue
        try:
            validator(candidate.payload)
        except ExplainerValidationError as exc:
            last_error = str(exc)
            attempts.append({
                "attempt": attempt_index + 1,
                "status": "invalid",
                "prompt_sha256": sha256_json({"prompt": prompt}),
                "response_sha256": candidate.response_sha256,
                "usage": candidate.usage,
                "duration_ms": candidate.duration_ms,
                "error": last_error[:1000],
                "payload_excerpt": json.dumps(candidate.payload, ensure_ascii=False)[:2000],
            })
            prompt = build_repair_prompt(stage, original_prompt, candidate.payload, last_error)
            continue
        attempts.append({
            "attempt": attempt_index + 1,
            "status": "valid",
            "prompt_sha256": sha256_json({"prompt": prompt}),
            "response_sha256": candidate.response_sha256,
            "usage": candidate.usage,
            "duration_ms": candidate.duration_ms,
        })
        return candidate, attempts, prompt, last_error
    return None, attempts, prompt, last_error


def _summed_usage(attempts: list[dict[str, Any]]) -> dict[str, int] | None:
    usage_records = [item["usage"] for item in attempts if item.get("usage")]
    if not usage_records:
        return None
    return {
        key: sum(item.get(key, 0) for item in usage_records)
        for key in ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens")
    }


def _materialize_animation_blocks(payload: dict[str, Any], packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Compile semantic animation decisions into standard registered media blocks."""
    sections = payload.get("sections", {})
    media_ids = {item.get("media_id") for item in packet.get("media", [])}
    operations: list[dict[str, Any]] = []
    if isinstance(sections, dict):
        for section_id, section in sections.items():
            blocks = section.get("blocks", []) if isinstance(section, dict) else []
            authored_media = [block for block in blocks if block.get("type") in {"video", "micro_video"}]
            if authored_media:
                section["blocks"] = [block for block in blocks if block.get("type") not in {"video", "micro_video"}]
                operations.append({
                    "section_id": section_id,
                    "operation": "discard_model_media_glue_before_materialization",
                    "count": len(authored_media),
                })
    for decision in payload.get("animation_plan", []):
        section_id = decision.get("section_id")
        media_id = decision.get("media_id")
        blocks = sections.get(section_id, {}).get("blocks", []) if isinstance(sections, dict) else []
        matches = [
            index
            for index, block in enumerate(blocks)
            if block.get("type") in {"video", "micro_video"} and block.get("media_id") == media_id
        ]
        poster_id = f"{media_id}-poster"
        captions_id = f"{media_id}-captions"
        if not matches and {media_id, poster_id, captions_id} <= media_ids and blocks:
            anchor = decision.get("adjacent_block_index")
            anchor = anchor if isinstance(anchor, int) and 0 <= anchor < len(blocks) else 0
            source_refs = list(blocks[anchor].get("source_refs", []))
            insertion_index = anchor + 1
            blocks.insert(insertion_index, {
                "type": "micro_video",
                "media_id": media_id,
                "poster_id": poster_id,
                "captions_id": captions_id,
                "title": decision.get("purpose", "Observe the state change"),
                "intro": decision.get("purpose", "Observe the state change."),
                "observation": f"{decision.get('before_state', 'before')} → {decision.get('after_state', 'after')}",
                "consequence": decision.get("after_state", "Observe the resulting state."),
                "beats": [decision.get("before_state", "before"), decision.get("after_state", "after")],
                "source_refs": source_refs,
            })
            matches = [insertion_index]
            operations.append({
                "section_id": section_id,
                "operation": "materialize_micro_video_from_animation_plan",
                "media_id": media_id,
            })
    # Later insertions can shift earlier block positions, so resolve every
    # mechanical index only after the complete section has been materialized.
    for decision in payload.get("animation_plan", []):
        section_id = decision.get("section_id")
        media_id = decision.get("media_id")
        blocks = sections.get(section_id, {}).get("blocks", []) if isinstance(sections, dict) else []
        matches = [
            index
            for index, block in enumerate(blocks)
            if block.get("type") in {"video", "micro_video"} and block.get("media_id") == media_id
        ]
        if len(matches) == 1 and decision.get("adjacent_block_index") != matches[0]:
            decision["adjacent_block_index"] = matches[0]
            operations.append({
                "section_id": section_id,
                "operation": "animation_index_from_media_id",
                "media_id": media_id,
            })
    return operations


def run_pipeline(
    source_path: Path,
    run_root: Path,
    provider: StageProvider,
    *,
    max_attempts: int = 1,
) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    packet = load_json(source_path)
    validate_source_packet(packet)
    paper_id = packet["paper_id"]
    outputs: dict[str, Any] = {}
    traces: list[dict[str, Any]] = []
    for stage in STAGES:
        if stage == "section_content" and getattr(provider, "supports_fragmented_sections", False):
            section_results: list[StageResult] = []
            section_prompts: list[str] = []
            final_prompts: list[str] = []
            attempts: list[dict[str, Any]] = []
            structural_normalizations: list[dict[str, Any]] = []
            merged = {"sections": {}, "animation_plan": [], "appendix_entries": []}
            appendix_by_id: dict[str, dict[str, Any]] = {}
            for section in outputs["lesson_plan"]["sections"]:
                section_id = section["id"]
                original_prompt = build_section_content_prompt(packet, outputs, section)
                section_prompts.append(original_prompt)
                fragment_outputs = {
                    "concept_graph": outputs["concept_graph"],
                    "lesson_plan": {**outputs["lesson_plan"], "sections": [section]},
                }
                def validate_fragment(payload: dict[str, Any], prior: dict[str, Any] = fragment_outputs) -> None:
                    structural_normalizations.extend(_materialize_animation_blocks(payload, packet))
                    validate_stage_payload(stage, payload, packet, prior)

                result, section_attempts, final_prompt, last_error = _attempt_generation(
                    provider=provider,
                    stage=stage,
                    paper_id=paper_id,
                    original_prompt=original_prompt,
                    validator=validate_fragment,
                    max_attempts=max_attempts,
                )
                for attempt in section_attempts:
                    attempt["section_id"] = section_id
                attempts.extend(section_attempts)
                final_prompts.append(final_prompt)
                if result is None:
                    failure = {
                        "paper_id": paper_id,
                        "stage": stage,
                        "section_id": section_id,
                        "attempts": attempts,
                        "error": last_error,
                    }
                    _write_json(run_root / "stages" / "section_content.failure.json", failure)
                    raise PipelineError(
                        f"{paper_id}/{stage}/{section_id} failed after {max_attempts} attempts: {last_error}"
                    )
                section_results.append(result)
                fragment = result.payload
                merged["sections"][section_id] = fragment["sections"][section_id]
                merged["animation_plan"].extend(fragment.get("animation_plan", []))
                for entry in fragment.get("appendix_entries", []):
                    entry_id = entry.get("id")
                    if entry_id in appendix_by_id and appendix_by_id[entry_id] != entry:
                        structural_normalizations.append({
                            "section_id": section_id,
                            "operation": "keep_first_shared_appendix_entry",
                            "appendix_id": entry_id,
                        })
                        continue
                    appendix_by_id[entry_id] = entry
                merged["appendix_entries"] = list(appendix_by_id.values())
                _write_json(
                    run_root / "stages" / f"section_content.{section_id}.json",
                    {"attempts": section_attempts, "payload": fragment},
                )
            validate_stage_payload(stage, merged, packet, outputs)
            outputs[stage] = merged
            usage = _summed_usage(attempts)
            result = section_results[-1]
            trace = {
                "stage": stage,
                "paper_id": paper_id,
                "provider": result.provider,
                "model": result.model,
                "generation_mode": result.generation_mode,
                "prompt_sha256": sha256_json({"prompts": section_prompts}),
                "final_prompt_sha256": sha256_json({"prompts": final_prompts}),
                "response_sha256": sha256_json(merged),
                "source_record": None,
                "usage": usage,
                "duration_ms": sum(item.get("duration_ms", 0) for item in attempts),
                "attempt_count": len(attempts),
                "section_call_count": len(section_results),
                "structural_normalizations": structural_normalizations,
                "attempts": attempts,
                "cost": estimate_cost(result.provider, result.model, usage),
            }
            traces.append(trace)
            _write_json(run_root / "stages" / f"{stage}.json", {"trace": trace, "payload": merged})
            continue

        original_prompt = build_prompt(stage, packet, outputs)
        result, attempts, prompt, last_error = _attempt_generation(
            provider=provider,
            stage=stage,
            paper_id=paper_id,
            original_prompt=original_prompt,
            validator=lambda payload: validate_stage_payload(stage, payload, packet, outputs),
            max_attempts=max_attempts,
        )
        if result is None:
            _write_json(
                run_root / "stages" / f"{stage}.failure.json",
                {"paper_id": paper_id, "stage": stage, "attempts": attempts, "error": last_error},
            )
            raise PipelineError(f"{paper_id}/{stage} failed after {max_attempts} attempts: {last_error}")
        outputs[stage] = result.payload
        usage = _summed_usage(attempts)
        trace = {
            "stage": stage,
            "paper_id": paper_id,
            "provider": result.provider,
            "model": result.model,
            "generation_mode": result.generation_mode,
            "prompt_sha256": sha256_json({"prompt": original_prompt}),
            "final_prompt_sha256": sha256_json({"prompt": prompt}),
            "response_sha256": result.response_sha256,
            "source_record": result.source_record,
            "usage": usage,
            "duration_ms": sum(item.get("duration_ms", 0) for item in attempts),
            "attempt_count": len(attempts),
            "attempts": attempts,
            "cost": estimate_cost(result.provider, result.model, usage),
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
