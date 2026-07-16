from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validation import FormulaExplainerValidationError, ROOT, REGISTRY_PATH, TOPICS_PATH, load_json, validate_workspace


def _write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compile_scene(formula_ref: str, formula: dict[str, Any], output_dir: Path) -> tuple[str, dict[str, Any]]:
    operations = formula["operations"]
    relative = Path("scene_ir") / formula["topic_id"].split(":", 1)[1] / f"{formula['formula_id'].split(':', 1)[1].replace('.', '_')}.json"
    scene = {
        "schema_version": "scene-ir/0.1.0",
        "scene_id": f"scene:{formula['formula_id'].split(':', 1)[1]}",
        "canonical_node_id": f"scene:{formula['formula_id'].split(':', 1)[1]}",
        "formula_ir_ref": formula_ref,
        "title": formula["title"],
        "aspect_ratio": "16:9",
        "render_targets": ["mp4", "poster_png"],
        "beats": [
            {"beat_id": f"beat:{formula['formula_id'].split(':', 1)[1]}.initial", "operation_ref": operations[0]["operation_id"], "primitive_ref": "project.formula_operation_walk", "state": "initial", "caption": "Start from the sourced formula and its typed atoms.", "duration_seconds": 1.0, "narration_hook": "What values enter this formula?"},
            *[
                {"beat_id": f"beat:{operation['operation_id'].split(':', 1)[1]}", "operation_ref": operation["operation_id"], "primitive_ref": operation["primitive_ref"], "state": "intermediate", "caption": f"Apply semantic operation: {operation['operation_type']}.", "duration_seconds": 1.0, "narration_hook": f"Track {operation['output_ref']} as it is produced."}
                for operation in operations
            ],
            {"beat_id": f"beat:{formula['formula_id'].split(':', 1)[1]}.terminal", "operation_ref": operations[-1]["operation_id"], "primitive_ref": "project.formula_operation_walk", "state": "terminal", "caption": f"End at {formula['output_ref']} and retain source/code evidence state.", "duration_seconds": 1.0, "narration_hook": "What did the operation chain establish?"}
        ],
        "static_fallback_plan": "Use the terminal frame with the formula, operation sequence, primitive-origin badges, and source locator visible."
    }
    _write(output_dir / relative, scene)
    return relative.as_posix(), scene


def _canonical_node(node_id: str, node_type: str, coverage: str = "observed") -> dict[str, Any]:
    return {"node_id": node_id, "node_type": node_type, "coverage_state": coverage, "aliases": [], "publishable": True}


def build_all(output_dir: Path) -> dict[str, Any]:
    try:
        output_relative = output_dir.relative_to(ROOT)
    except ValueError as exc:
        raise FormulaExplainerValidationError(
            f"build output must be inside repository root {ROOT}: {output_dir}"
        ) from exc
    validate_workspace()
    topics = load_json(TOPICS_PATH)
    registry = load_json(REGISTRY_PATH)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    compositions: list[str] = []
    for primitive in registry["primitives"]:
        coverage = "planned_missing" if primitive["status"] == "missing" else "observed"
        nodes[primitive["canonical_node_id"]] = _canonical_node(primitive["canonical_node_id"], "primitive", coverage)
    for topic_id, topic in topics.items():
        nodes[topic_id] = _canonical_node(topic_id, "topic")
        formula_ir_refs: list[str] = []
        scene_ir_refs: list[str] = []
        sequence: list[dict[str, Any]] = []
        for order, formula_ref in enumerate(topic["formula_refs"], start=1):
            formula = load_json(ROOT / formula_ref)
            scene_ref, scene = compile_scene(formula_ref, formula, output_dir)
            formula_ir_refs.append(formula_ref)
            scene_path_ref = (output_relative / scene_ref).as_posix()
            scene_ir_refs.append(scene_path_ref)
            sequence.append({"order": order, "scene_ir_ref": scene_path_ref, "transition": "claim_context" if order == 1 else ("code_grounding" if formula["code_mappings"] else "formula_dependency")})
            nodes[formula["canonical_node_id"]] = _canonical_node(formula["canonical_node_id"], "formula")
            nodes[scene["canonical_node_id"]] = _canonical_node(scene["canonical_node_id"], "scene")
            edges.append({"edge_id": f"edge:{topic_id.split(':',1)[1]}.contains.{formula['formula_id'].split(':',1)[1]}", "edge_type": "contains", "source_ref": topic_id, "target_ref": formula["canonical_node_id"], "match_state": "candidate", "evidence_refs": [], "confidence": 1.0, "review_ref": None, "publishable": True})
            edges.append({"edge_id": f"edge:{formula['formula_id'].split(':',1)[1]}.visualized_by.scene", "edge_type": "visualized_by", "source_ref": formula["canonical_node_id"], "target_ref": scene["canonical_node_id"], "match_state": "candidate", "evidence_refs": [f"artifact:formula_ir.{formula['formula_id'].split(':',1)[1]}"], "confidence": 1.0, "review_ref": None, "publishable": True})
            for operation in formula["operations"]:
                nodes[operation["canonical_node_id"]] = _canonical_node(operation["canonical_node_id"], "operation", "inferred")
                edges.append({"edge_id": f"edge:{formula['formula_id'].split(':',1)[1]}.contains.{operation['operation_id'].split(':',1)[1]}", "edge_type": "contains", "source_ref": formula["canonical_node_id"], "target_ref": operation["canonical_node_id"], "match_state": "candidate", "evidence_refs": [], "confidence": 1.0, "review_ref": None, "publishable": True})
                edges.append({"edge_id": f"edge:{operation['operation_id'].split(':',1)[1]}.visualized_by.{operation['primitive_ref'].replace(':','_')}", "edge_type": "visualized_by", "source_ref": operation["canonical_node_id"], "target_ref": next(item["canonical_node_id"] for item in registry["primitives"] if item["primitive_id"] == operation["primitive_ref"]), "match_state": operation["mapping_state"], "evidence_refs": [f"artifact:formula_ir.{formula['formula_id'].split(':',1)[1]}"], "confidence": None if operation["mapping_state"] == "unresolved" else 0.8, "review_ref": None, "publishable": True})
            for mapping in formula["code_mappings"]:
                nodes[mapping["code_node_id"]] = _canonical_node(mapping["code_node_id"], "code")
                edges.append({"edge_id": f"edge:{mapping['code_node_id'].split(':',1)[1]}.implements.{formula['formula_id'].split(':',1)[1]}", "edge_type": "implements", "source_ref": mapping["code_node_id"], "target_ref": formula["canonical_node_id"], "match_state": mapping["match_state"], "evidence_refs": [f"artifact:formula_ir.{formula['formula_id'].split(':',1)[1]}"], "confidence": 0.9 if mapping["match_state"] == "candidate" else None, "review_ref": None, "publishable": True})
        composition = {"schema_version": "topic-composition/0.1.0", "topic_id": topic_id, "paper_family_id": topic["paper_family_id"], "title": topic["title"], "canonical_node_id": topic_id, "formula_ir_refs": formula_ir_refs, "scene_ir_refs": scene_ir_refs, "composition": sequence, "claim_context": topic["claim_context"], "code_transition_policy": topic["code_transition_policy"]}
        composition_ref = Path("topic_compositions") / f"{topic_id.split(':', 1)[1]}.json"
        _write(output_dir / composition_ref, composition)
        compositions.append(composition_ref.as_posix())
    graph = {"nodes": sorted(nodes.values(), key=lambda item: item["node_id"]), "edges": sorted(edges, key=lambda item: item["edge_id"]), "migrations": []}
    _write(output_dir / "canonical_graph_fragment.json", graph)
    summary = {"schema_version": "formula-explainer-build/0.1.0", "demo_topic_count": len(topics), "benchmark_paper_family_count": len({item["paper_family_id"] for item in topics.values()}), "formula_count": sum(len(item["formula_refs"]) for item in topics.values()), "primitive_count": len(registry["primitives"]), "topic_composition_refs": compositions, "canonical_graph_fragment_ref": (output_relative / "canonical_graph_fragment.json").as_posix()}
    _write(output_dir / "build_summary.json", summary)
    validate_workspace(output_dir)
    return summary
