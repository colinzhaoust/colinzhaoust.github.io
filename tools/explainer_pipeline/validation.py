from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .common import SCHEMA_ROOT, load_json, resolve_repo_path, sha256_file


SOURCE_SCHEMA = SCHEMA_ROOT / "source-packet-0.1.0.schema.json"
BUNDLE_SCHEMA = SCHEMA_ROOT / "explainer-bundle-0.1.0.schema.json"


class ExplainerValidationError(ValueError):
    pass


def _schema_errors(document: dict[str, Any], schema_path: Path) -> list[str]:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(document)
    ]


def validate_source_packet(packet: dict[str, Any], check_local_assets: bool = True) -> None:
    errors = _schema_errors(packet, SOURCE_SCHEMA)
    source_ids = [item.get("source_id") for item in packet.get("sources", [])]
    if len(source_ids) != len(set(source_ids)):
        errors.append("source IDs must be unique")
    finding_ids = [item.get("finding_id") for item in packet.get("finding_coverage", [])]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("finding coverage IDs must be unique")
    for item in packet.get("equation_coverage", []):
        if item.get("coverage") == "fold" and not item.get("fold_reason"):
            errors.append(f"folded equations need a reason: {item.get('equation_ids')}")
    code_sources = packet.get("code_sources", [])
    source_by_code_id = {item.get("code_id"): item for item in code_sources}
    for code_source in code_sources:
        checkout_path = code_source.get("checkout_path")
        checkout_root = resolve_repo_path(checkout_path) if checkout_path else None
        for excerpt in code_source.get("excerpts", []):
            try:
                # Always reject paths that escape the repository. A published packet remains
                # portable when the optional upstream checkout is not present locally.
                resolve_repo_path(excerpt["path"])
                path = checkout_root / excerpt["path"] if checkout_root else None
            except (KeyError, ValueError) as exc:
                errors.append(str(exc))
                continue
            if check_local_assets and checkout_root and checkout_root.exists() and not path.is_file():
                errors.append(f"missing code excerpt path: {excerpt['path']}")
    code_ids = {item.get("code_id") for item in packet.get("code_sources", [])}

    def validate_upstream_location(item: dict[str, Any], label: str) -> None:
        code_id = item.get("code_id") or next(iter(code_ids), None)
        source = source_by_code_id.get(code_id)
        path_value = item.get("path")
        if not source or not path_value:
            errors.append(f"{label} needs a known code_id and repository-relative path")
            return
        try:
            resolve_repo_path(path_value)
            checkout = resolve_repo_path(source["checkout_path"]) if source.get("checkout_path") else None
            upstream_path = checkout / path_value if checkout else None
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
            return
        if check_local_assets and checkout and checkout.exists():
            if not upstream_path.is_file():
                errors.append(f"missing {label} upstream path: {path_value}")
                return
            line_start = item.get("line_start")
            line_end = item.get("line_end")
            if not isinstance(line_start, int) or not isinstance(line_end, int) or line_start < 1 or line_end < line_start:
                errors.append(f"invalid {label} line range: {path_value}:{line_start}-{line_end}")
                return
            line_count = sum(1 for _ in upstream_path.open(encoding="utf-8", errors="replace"))
            if line_end > line_count:
                errors.append(f"{label} line range exceeds {path_value}: {line_end} > {line_count}")

    formula_ids = set()
    for formula_ref in packet.get("formula_refs", []):
        try:
            formula_ids.add(load_json(resolve_repo_path(formula_ref))["formula_id"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid formula ref {formula_ref}: {exc}")
    understanding = packet.get("code_understanding", {})
    for link in understanding.get("formula_code_links", []):
        if link.get("formula_id") and link.get("formula_id") not in formula_ids:
            errors.append(f"unknown formula in code link: {link.get('formula_id')}")
        if not link.get("formula_id") and not link.get("equation_ids"):
            errors.append("code link needs formula_id or equation_ids")
        if link.get("code_id") not in code_ids:
            errors.append(f"unknown code source in code link: {link.get('code_id')}")
        else:
            validate_upstream_location(link, "formula-code mapping")
    for node in understanding.get("nodes", []):
        validate_upstream_location(node, "lifecycle node")
    dag_ids = {item.get("id") for item in understanding.get("nodes", [])}
    for edge in understanding.get("edges", []):
        if edge.get("source") not in dag_ids or edge.get("target") not in dag_ids:
            errors.append(f"dangling code DAG edge: {edge}")
    renderer = packet.get("scene_renderer", {})
    if renderer.get("coding_agent_required") is not False:
        errors.append("scene renderer must not require a coding agent")
    try:
        renderer_path = resolve_repo_path(renderer["entrypoint"])
    except (KeyError, ValueError) as exc:
        errors.append(str(exc))
    else:
        if check_local_assets and not renderer_path.is_file():
            errors.append(f"missing scene renderer entrypoint: {renderer.get('entrypoint')}")
    for media in packet.get("media", []):
        try:
            path = resolve_repo_path(media["path"])
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if check_local_assets:
            if not path.is_file():
                errors.append(f"missing media path: {media['path']}")
            elif sha256_file(path) != media["sha256"]:
                errors.append(f"media hash mismatch: {media['path']}")
    if errors:
        raise ExplainerValidationError("source packet invalid:\n" + "\n".join(f"- {item}" for item in errors))


def validate_stage_payload(stage: str, payload: dict[str, Any], packet: dict[str, Any]) -> None:
    errors: list[str] = []
    if stage == "concept_graph":
        required = {"thesis", "nodes", "edges", "unresolved"}
        if not required.issubset(payload):
            errors.append(f"concept graph missing {sorted(required - set(payload))}")
        node_ids = {item.get("id") for item in payload.get("nodes", []) if isinstance(item, dict)}
        for edge in payload.get("edges", []):
            if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
                errors.append(f"dangling concept edge: {edge}")
    elif stage == "lesson_plan":
        required_ids = packet.get("required_section_ids", [])
        sections = payload.get("sections", [])
        section_ids = [item.get("id") for item in sections if isinstance(item, dict)]
        if section_ids != required_ids:
            errors.append(f"lesson section order {section_ids} != required {required_ids}")
        for section in sections:
            for field in ("title", "intent", "question", "learning_goal", "misconception", "summary", "medium"):
                if not section.get(field):
                    errors.append(f"section {section.get('id')} missing {field}")
    elif stage == "section_content":
        allowed_blocks = {
            "prose", "comparison", "formula_steps", "code", "video", "micro_video",
            "line_chart", "bar_chart", "lineage", "numeric_fixture",
            "rotation", "limitation", "learner_check", "reported_trends",
            "paper_question", "related_reading",
            "equation_thread", "result_story",
        }
        media_ids = {item.get("media_id") for item in packet.get("media", [])}
        code_ids = {item.get("code_id") for item in packet.get("code_sources", [])}
        sections = payload.get("sections")
        if not isinstance(sections, dict):
            errors.append("section_content.sections must be an object")
        else:
            required_ids = packet.get("required_section_ids", [])
            if list(sections) != required_ids:
                errors.append("section content order must match required section IDs")
            for section_id, value in sections.items():
                blocks = value.get("blocks") if isinstance(value, dict) else None
                if not isinstance(blocks, list) or not blocks:
                    errors.append(f"section {section_id} must contain blocks")
                    continue
                for index, block in enumerate(blocks):
                    block_type = block.get("type") if isinstance(block, dict) else None
                    if block_type not in allowed_blocks:
                        errors.append(f"section {section_id} block {index} has unsupported type {block_type}")
                        continue
                    if block_type != "learner_check" and not block.get("source_refs"):
                        errors.append(f"section {section_id} block {index} needs source_refs")
                    if block_type in {"video", "micro_video"}:
                        for field in ("media_id", "poster_id", "captions_id"):
                            if block.get(field) not in media_ids:
                                errors.append(f"section {section_id} {block_type} has unknown {field} {block.get(field)}")
                    if block_type == "micro_video":
                        for field in ("intro", "observation", "consequence"):
                            if not block.get(field):
                                errors.append(f"section {section_id} micro_video needs {field}")
                    if block_type == "code" and block.get("code_source_id") not in code_ids:
                        errors.append(f"section {section_id} code block has unknown code_source_id")
                    if block_type in {"bar_chart", "line_chart", "reported_trends"} and not block.get("claim_label"):
                        errors.append(f"section {section_id} result block needs claim_label")
                    if block_type == "related_reading":
                        for item in block.get("items", []):
                            if not str(item.get("url", "")).startswith("https://"):
                                errors.append(f"section {section_id} related reading needs an https URL")
                    if block_type == "equation_thread":
                        if not block.get("stages") or not block.get("folded"):
                            errors.append(f"section {section_id} equation thread needs stages and folded decisions")
                    if block_type == "result_story":
                        for field in ("question", "setting", "metric", "evidence_kind", "takeaway"):
                            if not block.get(field):
                                errors.append(f"section {section_id} result story needs {field}")
        appendix_entries = payload.get("appendix_entries", [])
        appendix_ids = [item.get("id") for item in appendix_entries if isinstance(item, dict)]
        if len(appendix_ids) != len(set(appendix_ids)):
            errors.append("appendix entry IDs must be unique")
    else:
        errors.append(f"unsupported stage: {stage}")
    if errors:
        raise ExplainerValidationError(f"{stage} invalid:\n" + "\n".join(f"- {item}" for item in errors))


def validate_bundle(bundle: dict[str, Any], check_local_assets: bool = True) -> None:
    errors = _schema_errors(bundle, BUNDLE_SCHEMA)
    packet = bundle.get("source_packet", {})
    try:
        validate_source_packet(packet, check_local_assets=check_local_assets)
    except ExplainerValidationError as exc:
        errors.append(str(exc))
    section_ids = [item.get("id") for item in bundle.get("lesson_plan", {}).get("sections", [])]
    content_ids = list(bundle.get("section_content", {}).get("sections", {}))
    if section_ids != content_ids:
        errors.append("lesson plan and section content IDs/order must match")
    appendix_ids = {item.get("id") for item in bundle.get("section_content", {}).get("appendix_entries", [])}
    for section in bundle.get("lesson_plan", {}).get("sections", []):
        dangling = set(section.get("deep_links", [])) - appendix_ids
        if dangling:
            errors.append(f"section {section.get('id')} has dangling appendix refs {sorted(dangling)}")
    formula_map = bundle.get("formula_map", {})
    formula_node_ids = {item.get("node_id") for item in formula_map.get("formula_nodes", [])}
    manim_node_ids = {item.get("primitive_id") for item in formula_map.get("manim_nodes", [])}
    for edge in formula_map.get("edges", []):
        if edge.get("source") not in formula_node_ids or edge.get("target") not in manim_node_ids:
            errors.append(f"dangling formula-to-Manim edge: {edge.get('edge_id')}")
    if len(formula_map.get("formulas", [])) != len(packet.get("formula_refs", [])):
        errors.append("formula map inventory must match source packet formula refs")
    code_map = bundle.get("code_map", {})
    code_formula_ids = {item.get("formula_id") for item in code_map.get("formula_nodes", [])}
    for edge in code_map.get("formula_code_edges", []):
        if edge.get("source", "").removeprefix("formula:") not in code_formula_ids:
            errors.append(f"dangling code-map formula edge: {edge.get('edge_id')}")
    if errors:
        raise ExplainerValidationError("explainer bundle invalid:\n" + "\n".join(f"- {item}" for item in errors))


def validate_bundle_file(path: Path, check_local_assets: bool = True) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExplainerValidationError(f"cannot load bundle {path}: {exc}") from exc
    validate_bundle(document, check_local_assets=check_local_assets)
    return document
