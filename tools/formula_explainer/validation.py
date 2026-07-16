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
    # Semantic checks assume the required FormulaIR fields exist. Malformed
    # documents should be reported as invalid, not crash the validator.
    if errors:
        return errors
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
    registry_by_id = {item["primitive_id"]: item for item in registry.get("primitives", [])}
    for operation in operations:
        primitive = registry_by_id.get(operation["primitive_ref"])
        if not primitive:
            errors.append(f"{operation['operation_id']}: unknown primitive {operation['primitive_ref']}")
        elif operation["operation_type"] not in primitive["operations"]:
            errors.append(
                f"{operation['operation_id']}: operation {operation['operation_type']} "
                f"is not supported by {operation['primitive_ref']}"
            )
    for mapping in formula.get("code_mappings", []):
        if mapping["line_end"] < mapping["line_start"]:
            errors.append(f"{mapping['code_node_id']}: reversed line range")
        if mapping["match_state"] == "confirmed":
            errors.append(f"{mapping['code_node_id']}: confirmed requires a canonical review event; focused FormulaIR must stay candidate")
    return errors


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors = _schema_errors(registry, REGISTRY_SCHEMA)
    if errors:
        return errors
    primitives = registry.get("primitives", [])
    ids = [item["primitive_id"] for item in primitives]
    if duplicate := _duplicates(ids):
        errors.append(f"duplicate primitive IDs: {sorted(duplicate)}")
    compatibility = registry.get("manim_compatibility", {})
    if compatibility.get("minimum_supported_version") is not None:
        errors.append("manim compatibility: minimum_supported_version must stay null until a lower-bound render is tested")
    for ref in compatibility.get("render_evidence_refs", []):
        if not _ref_target(ref).is_file():
            errors.append(f"manim compatibility: unresolved render evidence {ref}")
    for item in primitives:
        if item["origin"] == "project_reusable" and len(item["used_by"]) < 2:
            errors.append(f"{item['primitive_id']}: project_reusable requires at least two formula uses")
        if item["origin"] == "project_reusable":
            verification = item.get("verification", {})
            for field in ("test_refs", "golden_scene_refs"):
                refs = verification.get(field, [])
                if not refs:
                    errors.append(f"{item['primitive_id']}: project_reusable requires {field}")
                for ref in refs:
                    if not _ref_target(ref).is_file():
                        errors.append(f"{item['primitive_id']}: unresolved {field} target {ref}")
        if item["origin"] == "missing_planned" and item["status"] != "missing":
            errors.append(f"{item['primitive_id']}: missing_planned must have missing status")
        if item["origin"] == "built_in" and not (item["source_symbol"] or "").startswith("manim."):
            errors.append(f"{item['primitive_id']}: built-in primitive must cite a manim symbol")
    return errors


def _ref_target(ref: str) -> Path:
    relative = ref.split("::", 1)[0].split("#", 1)[0]
    return ROOT / relative


def validate_scene(scene: dict[str, Any], formula: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors = _schema_errors(scene, SCENE_SCHEMA)
    if errors:
        return errors
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


def validate_composition(
    composition: dict[str, Any],
    *,
    expected_topic_id: str | None = None,
    expected_topic: dict[str, Any] | None = None,
    expected_scene_refs: list[str] | None = None,
    formulas: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    errors = _schema_errors(composition, COMPOSITION_SCHEMA)
    if errors:
        return errors
    orders = [item["order"] for item in composition.get("composition", [])]
    if orders != list(range(1, len(orders) + 1)):
        errors.append("composition order must be contiguous and sorted from one")
    if expected_topic_id is not None and expected_topic is not None and expected_scene_refs is not None:
        if composition.get("topic_id") != expected_topic_id:
            errors.append(f"composition topic_id expected {expected_topic_id}")
        if composition.get("canonical_node_id") != expected_topic_id:
            errors.append(f"composition canonical_node_id expected {expected_topic_id}")
        if composition.get("paper_family_id") != expected_topic["paper_family_id"]:
            errors.append("composition paper_family_id does not match topic registry")
        if composition.get("title") != expected_topic["title"]:
            errors.append("composition title does not match topic registry")
        expected_formula_refs = expected_topic["formula_refs"]
        if composition.get("formula_ir_refs") != expected_formula_refs:
            errors.append("composition formula_ir_refs do not match topic registry order")
        if composition.get("scene_ir_refs") != expected_scene_refs:
            errors.append("composition scene_ir_refs do not match expected compiled scenes")
        expected_sequence = []
        for order, (formula_ref, scene_ref) in enumerate(zip(expected_formula_refs, expected_scene_refs), start=1):
            formula = (formulas or {}).get(formula_ref, {})
            expected_sequence.append({
                "order": order,
                "scene_ir_ref": scene_ref,
                "transition": "claim_context" if order == 1 else ("code_grounding" if formula.get("code_mappings") else "formula_dependency"),
            })
        if composition.get("composition") != expected_sequence:
            errors.append("composition sequence does not match formula/scene semantics")
    return errors


def validate_graph_inventory(
    fragment: dict[str, Any],
    topics: dict[str, Any],
    formulas: dict[str, dict[str, Any]],
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    expected_nodes: dict[str, dict[str, Any]] = {}
    expected_edges: dict[str, dict[str, Any]] = {}

    def node(node_id: str, node_type: str, coverage_state: str) -> dict[str, Any]:
        return {
            "node_id": node_id,
            "node_type": node_type,
            "coverage_state": coverage_state,
            "aliases": [],
            "publishable": True,
        }

    def edge(
        edge_id: str,
        edge_type: str,
        source_ref: str,
        target_ref: str,
        match_state: str,
        evidence_refs: list[str],
        confidence: float | None,
    ) -> dict[str, Any]:
        return {
            "edge_id": edge_id,
            "edge_type": edge_type,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "match_state": match_state,
            "evidence_refs": evidence_refs,
            "confidence": confidence,
            "review_ref": None,
            "publishable": True,
        }

    primitive_nodes = {item["primitive_id"]: item for item in registry["primitives"]}
    for primitive in registry["primitives"]:
        coverage = "planned_missing" if primitive["status"] == "missing" else "observed"
        expected_nodes[primitive["canonical_node_id"]] = node(primitive["canonical_node_id"], "primitive", coverage)
    for topic_id, topic in topics.items():
        expected_nodes[topic_id] = node(topic_id, "topic", "observed")
        for formula_ref in topic["formula_refs"]:
            formula = formulas[formula_ref]
            formula_suffix = formula["formula_id"].split(":", 1)[1]
            scene_id = f"scene:{formula_suffix}"
            expected_nodes[formula["canonical_node_id"]] = node(formula["canonical_node_id"], "formula", "observed")
            expected_nodes[scene_id] = node(scene_id, "scene", "observed")
            contains_formula_id = f"edge:{topic_id.split(':', 1)[1]}.contains.{formula_suffix}"
            expected_edges[contains_formula_id] = edge(
                contains_formula_id, "contains", topic_id, formula["canonical_node_id"], "candidate", [], 1.0,
            )
            formula_scene_id = f"edge:{formula_suffix}.visualized_by.scene"
            expected_edges[formula_scene_id] = edge(
                formula_scene_id, "visualized_by", formula["canonical_node_id"], scene_id, "candidate",
                [f"artifact:formula_ir.{formula_suffix}"], 1.0,
            )
            for operation in formula["operations"]:
                operation_suffix = operation["operation_id"].split(":", 1)[1]
                expected_nodes[operation["canonical_node_id"]] = node(operation["canonical_node_id"], "operation", "inferred")
                contains_operation_id = f"edge:{formula_suffix}.contains.{operation_suffix}"
                expected_edges[contains_operation_id] = edge(
                    contains_operation_id, "contains", formula["canonical_node_id"], operation["canonical_node_id"],
                    "candidate", [], 1.0,
                )
                primitive = primitive_nodes[operation["primitive_ref"]]
                operation_primitive_id = f"edge:{operation_suffix}.visualized_by.{operation['primitive_ref'].replace(':', '_')}"
                expected_edges[operation_primitive_id] = edge(
                    operation_primitive_id, "visualized_by", operation["canonical_node_id"], primitive["canonical_node_id"],
                    operation["mapping_state"], [f"artifact:formula_ir.{formula_suffix}"],
                    None if operation["mapping_state"] == "unresolved" else 0.8,
                )
            for mapping in formula["code_mappings"]:
                code_suffix = mapping["code_node_id"].split(":", 1)[1]
                expected_nodes[mapping["code_node_id"]] = node(mapping["code_node_id"], "code", "observed")
                code_formula_id = f"edge:{code_suffix}.implements.{formula_suffix}"
                expected_edges[code_formula_id] = edge(
                    code_formula_id, "implements", mapping["code_node_id"], formula["canonical_node_id"],
                    mapping["match_state"], [f"artifact:formula_ir.{formula_suffix}"],
                    0.9 if mapping["match_state"] == "candidate" else None,
                )

    actual_node_list = fragment.get("nodes", [])
    actual_edge_list = fragment.get("edges", [])
    if not actual_node_list or not actual_edge_list:
        errors.append("graph inventory: nodes and edges must both be nonempty")
    actual_nodes = {
        item.get("node_id"): item
        for item in actual_node_list
        if item.get("node_id")
    }
    actual_edges = {
        item.get("edge_id"): item
        for item in actual_edge_list
        if item.get("edge_id")
    }
    if len(actual_nodes) != len(actual_node_list):
        errors.append("graph inventory: duplicate or missing node IDs")
    if len(actual_edges) != len(actual_edge_list):
        errors.append("graph inventory: duplicate or missing edge IDs")
    if actual_nodes != expected_nodes:
        changed = sorted(key for key in set(expected_nodes) & set(actual_nodes) if expected_nodes[key] != actual_nodes[key])
        errors.append(
            f"graph inventory: node mismatch missing={sorted(set(expected_nodes) - set(actual_nodes))} "
            f"extra={sorted(set(actual_nodes) - set(expected_nodes))} changed={changed}"
        )
    if actual_edges != expected_edges:
        changed = sorted(key for key in set(expected_edges) & set(actual_edges) if expected_edges[key] != actual_edges[key])
        errors.append(
            f"graph inventory: edge mismatch missing={sorted(set(expected_edges) - set(actual_edges))} "
            f"extra={sorted(set(actual_edges) - set(expected_edges))} changed={changed}"
        )
    return errors


def validate_graph_fragment(fragment: dict[str, Any]) -> list[str]:
    canonical = load_json(CANONICAL_SCHEMA)
    graph_schema = {"$schema": canonical["$schema"], "$defs": canonical["$defs"], **canonical["$defs"]["graph"]}
    errors = [f"canonical graph fragment: {message}" for message in _schema_errors_with_schema(fragment, graph_schema)]
    if errors:
        return errors
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
    if build_dir is not None:
        expected_scenes = {
            Path("scene_ir")
            / formula["topic_id"].split(":", 1)[1]
            / f"{formula['formula_id'].split(':', 1)[1].replace('.', '_')}.json": formula_ref
            for formula_ref, formula in formulas.items()
        }
        expected_compositions = {
            Path("topic_compositions") / f"{topic_id.split(':', 1)[1]}.json"
            for topic_id in topics
        }
        expected_files = set(expected_scenes) | expected_compositions | {
            Path("canonical_graph_fragment.json"),
            Path("build_summary.json"),
        }
        if not build_dir.is_dir():
            errors.append(f"build inventory: directory missing: {build_dir}")
        else:
            actual_files = {
                path.relative_to(build_dir)
                for path in build_dir.rglob("*")
                if path.is_file()
            }
            missing = expected_files - actual_files
            extra = actual_files - expected_files
            if missing:
                errors.append(f"build inventory: missing={sorted(path.as_posix() for path in missing)}")
            if extra:
                errors.append(f"build inventory: extra={sorted(path.as_posix() for path in extra)}")

            for relative, formula_ref in sorted(expected_scenes.items()):
                path = build_dir / relative
                if not path.is_file():
                    continue
                scene = load_json(path)
                if scene.get("formula_ir_ref") != formula_ref:
                    errors.append(f"{relative}: expected formula_ir_ref {formula_ref}")
                    continue
                errors.extend(f"{relative}: {error}" for error in validate_scene(scene, formulas[formula_ref], registry))
            for relative in sorted(expected_compositions):
                path = build_dir / relative
                if path.is_file():
                    topic_id = f"topic:{relative.stem}"
                    expected_scene_refs = []
                    for formula_ref in topics[topic_id]["formula_refs"]:
                        scene_relative = next(key for key, value in expected_scenes.items() if value == formula_ref)
                        expected_scene_refs.append((build_dir.relative_to(ROOT) / scene_relative).as_posix())
                    errors.extend(
                        f"{relative}: {error}"
                        for error in validate_composition(
                            load_json(path),
                            expected_topic_id=topic_id,
                            expected_topic=topics[topic_id],
                            expected_scene_refs=expected_scene_refs,
                            formulas=formulas,
                        )
                    )
            graph_path = build_dir / "canonical_graph_fragment.json"
            if graph_path.is_file():
                graph = load_json(graph_path)
                errors.extend(validate_graph_fragment(graph))
                errors.extend(validate_graph_inventory(graph, topics, formulas, registry))
            summary_path = build_dir / "build_summary.json"
            if summary_path.is_file():
                summary = load_json(summary_path)
                expected_counts = {
                    "demo_topic_count": len(topics),
                    "benchmark_paper_family_count": len(families),
                    "formula_count": len(formulas),
                    "primitive_count": len(registry["primitives"]),
                }
                for field, expected in expected_counts.items():
                    if summary.get(field) != expected:
                        errors.append(f"build summary: {field} expected {expected}, got {summary.get(field)}")
                expected_refs = sorted(path.as_posix() for path in expected_compositions)
                if sorted(summary.get("topic_composition_refs", [])) != expected_refs:
                    errors.append("build summary: topic_composition_refs do not match the five expected compositions")
    if errors:
        raise FormulaExplainerValidationError("\n".join(errors))
