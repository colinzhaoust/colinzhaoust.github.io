from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "formula-explainer"
FORMULA_SCHEMA = SCHEMA_DIR / "formula-ir-0.1.0.schema.json"
SCENE_SCHEMA = SCHEMA_DIR / "scene-ir-0.1.0.schema.json"
REGISTRY_SCHEMA = SCHEMA_DIR / "primitive-registry-0.1.0.schema.json"
COMPOSITION_SCHEMA = SCHEMA_DIR / "topic-composition-0.1.0.schema.json"
CANONICAL_SCHEMA = ROOT / "schemas" / "paper-media" / "canonical-manifest-0.1.0.schema.json"
REGISTRY_PATH = ROOT / "data" / "formula_explainer" / "primitive_registry.json"
TOPICS_PATH = ROOT / "data" / "formula_explainer" / "topics.json"

# Mirrors the focused subset consumed by canonical-manifest-0.1.0. The build
# deliberately exports only these combinations, so it can be embedded without
# inventing a second graph model.
ALLOWED_CANONICAL_GRAPH_EDGES = {
    "contains": {("topic", "claim"), ("topic", "formula"), ("formula", "operation"), ("scene", "primitive")},
    "supports": {("evidence", "claim"), ("claim", "claim"), ("formula", "claim")},
    "depends_on": {(kind, kind) for kind in ("claim", "formula", "operation", "code", "scene")},
    "implements": {("code", "formula"), ("code", "operation"), ("dataflow", "formula"), ("dataflow", "operation")},
    "consumes": {(source, target) for source in ("code", "operation", "primitive", "scene") for target in ("data", "value", "artifact")},
    "visualized_by": {(source, target) for source in ("claim", "formula", "operation", "code", "dataflow") for target in ("primitive", "scene")},
    "composes": {(kind, kind) for kind in ("formula", "scene", "slide", "topic")},
    "embedded_in": {("scene", "animation_slot"), ("scene", "slide"), ("artifact", "animation_slot"), ("artifact", "slide")},
    "renders_to": {(source, "artifact") for source in ("scene", "slide", "source")},
}


class FormulaExplainerValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(document: dict[str, Any], schema_path: Path) -> list[str]:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return [f"{'.'.join(str(x) for x in error.path) or '<root>'}: {error.message}" for error in Draft202012Validator(schema).iter_errors(document)]


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def validate_formula(formula: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors = _schema_errors(formula, FORMULA_SCHEMA)
    atoms = {item["atom_id"] for item in formula.get("atoms", [])}
    operations = formula.get("operations", [])
    operation_ids = [item["operation_id"] for item in operations]
    outputs = {item["output_ref"] for item in operations}
    if duplicate := _duplicates(operation_ids):
        errors.append(f"duplicate operation IDs: {sorted(duplicate)}")
    known = set(atoms)
    for operation in operations:
        missing = set(operation["input_refs"]) - known
        if missing:
            errors.append(f"{operation['operation_id']}: inputs are not topologically available: {sorted(missing)}")
        known.add(operation["output_ref"])
    if formula.get("output_ref") not in outputs:
        errors.append("formula output_ref is not produced by an operation")
    registry_ids = {item["primitive_id"] for item in registry.get("primitives", [])}
    for operation in operations:
        if operation["primitive_ref"] not in registry_ids:
            errors.append(f"{operation['operation_id']}: unknown primitive {operation['primitive_ref']}")
    for mapping in formula.get("code_mappings", []):
        if mapping["line_end"] < mapping["line_start"]:
            errors.append(f"{mapping['code_node_id']}: reversed line range")
        if mapping["match_state"] == "confirmed":
            errors.append(f"{mapping['code_node_id']}: confirmed requires a canonical review event; focused FormulaIR must stay candidate")
    return errors


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors = _schema_errors(registry, REGISTRY_SCHEMA)
    primitives = registry.get("primitives", [])
    ids = [item["primitive_id"] for item in primitives]
    if duplicate := _duplicates(ids):
        errors.append(f"duplicate primitive IDs: {sorted(duplicate)}")
    for item in primitives:
        if item["origin"] == "project_reusable" and len(item["used_by"]) < 2:
            errors.append(f"{item['primitive_id']}: project_reusable requires at least two formula uses")
        if item["origin"] == "missing_planned" and item["status"] != "missing":
            errors.append(f"{item['primitive_id']}: missing_planned must have missing status")
        if item["origin"] == "built_in" and not (item["source_symbol"] or "").startswith("manim."):
            errors.append(f"{item['primitive_id']}: built-in primitive must cite a manim symbol")
    return errors


def validate_scene(scene: dict[str, Any], formula: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors = _schema_errors(scene, SCENE_SCHEMA)
    operation_ids = {item["operation_id"] for item in formula["operations"]}
    primitive_ids = {item["primitive_id"] for item in registry["primitives"]}
    for beat in scene.get("beats", []):
        if beat["operation_ref"] not in operation_ids:
            errors.append(f"{beat['beat_id']}: unknown operation_ref")
        if beat["primitive_ref"] not in primitive_ids:
            errors.append(f"{beat['beat_id']}: unknown primitive_ref")
    states = {beat["state"] for beat in scene.get("beats", [])}
    if states != {"initial", "intermediate", "terminal"}:
        errors.append(f"scene must expose initial/intermediate/terminal states, got {sorted(states)}")
    return errors


def validate_composition(composition: dict[str, Any]) -> list[str]:
    errors = _schema_errors(composition, COMPOSITION_SCHEMA)
    orders = [item["order"] for item in composition.get("composition", [])]
    if orders != list(range(1, len(orders) + 1)):
        errors.append("composition order must be contiguous and sorted from one")
    return errors


def validate_graph_fragment(fragment: dict[str, Any]) -> list[str]:
    canonical = load_json(CANONICAL_SCHEMA)
    graph_schema = {"$schema": canonical["$schema"], "$defs": canonical["$defs"], **canonical["$defs"]["graph"]}
    errors = [f"canonical graph fragment: {message}" for message in _schema_errors_with_schema(fragment, graph_schema)]
    nodes = {item["node_id"]: item for item in fragment.get("nodes", [])}
    for edge in fragment.get("edges", []):
        source = nodes.get(edge["source_ref"])
        target = nodes.get(edge["target_ref"])
        if not source or not target:
            errors.append(f"canonical graph fragment: {edge['edge_id']}: dangling node")
        elif (source["node_type"], target["node_type"]) not in ALLOWED_CANONICAL_GRAPH_EDGES[edge["edge_type"]]:
            errors.append(f"canonical graph fragment: {edge['edge_id']}: disallowed typed edge")
        if edge["edge_type"] not in {"contains", "depends_on"} and not edge["evidence_refs"]:
            errors.append(f"canonical graph fragment: {edge['edge_id']}: missing artifact evidence ref")
        if edge["match_state"] in {"confirmed", "rejected"}:
            errors.append(f"canonical graph fragment: {edge['edge_id']}: focused build cannot confirm without manifest review event")
    return errors


def _schema_errors_with_schema(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return [f"{'.'.join(str(x) for x in error.path) or '<root>'}: {error.message}" for error in Draft202012Validator(schema).iter_errors(document)]


def validate_workspace(build_dir: Path | None = None) -> None:
    registry = load_json(REGISTRY_PATH)
    errors = validate_registry(registry)
    topics = load_json(TOPICS_PATH)
    formula_paths = sorted((ROOT / "data" / "formula_explainer" / "formulas").glob("**/*.json"))
    formulas = {path.relative_to(ROOT).as_posix(): load_json(path) for path in formula_paths}
    for path, formula in formulas.items():
        errors.extend(f"{path}: {error}" for error in validate_formula(formula, registry))
    declared = {ref for topic in topics.values() for ref in topic["formula_refs"]}
    if declared != set(formulas):
        errors.append(f"topic/formula inventory mismatch: missing={sorted(set(formulas)-declared)} extra={sorted(declared-set(formulas))}")
    if len(topics) != 5:
        errors.append(f"expected five demo topics, got {len(topics)}")
    families = {topic["paper_family_id"] for topic in topics.values()}
    if len(families) != 4:
        errors.append(f"expected four benchmark paper families, got {len(families)}")
    if build_dir and build_dir.exists():
        for path in sorted((build_dir / "scene_ir").glob("**/*.json")):
            scene = load_json(path)
            formula_ref = scene["formula_ir_ref"]
            errors.extend(f"{path.relative_to(ROOT)}: {error}" for error in validate_scene(scene, formulas[formula_ref], registry))
        for path in sorted((build_dir / "topic_compositions").glob("*.json")):
            errors.extend(f"{path.relative_to(ROOT)}: {error}" for error in validate_composition(load_json(path)))
        graph_path = build_dir / "canonical_graph_fragment.json"
        if graph_path.exists():
            errors.extend(validate_graph_fragment(load_json(graph_path)))
    if errors:
        raise FormulaExplainerValidationError("\n".join(errors))
