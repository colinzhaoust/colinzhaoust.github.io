from __future__ import annotations

from typing import Any

from .common import ROOT, load_json, repo_path, resolve_repo_path


REGISTRY_PATH = ROOT / "data" / "formula_explainer" / "primitive_registry.json"


def build_formula_map(packet: dict[str, Any]) -> dict[str, Any]:
    """Compile formula IR and the Manim registry into a reader-facing bipartite graph."""

    registry = load_json(REGISTRY_PATH)
    primitives = {item["primitive_id"]: item for item in registry["primitives"]}
    formulas = [load_json(resolve_repo_path(path)) for path in packet.get("formula_refs", [])]
    formula_nodes: list[dict[str, Any]] = []
    manim_ids: set[str] = set()
    edges: list[dict[str, Any]] = []
    formula_summaries: list[dict[str, Any]] = []

    for formula in formulas:
        formula_id = formula["formula_id"]
        source_anchor = formula["source_anchor"]
        formula_summaries.append(
            {
                "formula_id": formula_id,
                "title": formula["title"],
                "latex": formula["display"]["latex"],
                "plain_text": formula["display"]["plain_text"],
                "source_anchor": source_anchor,
            }
        )
        display_node_id = f"node:{formula_id}:display"
        formula_nodes.append(
            {
                "node_id": display_node_id,
                "formula_id": formula_id,
                "level": "formula",
                "label": formula["title"],
                "expression": formula["display"]["plain_text"],
                "source_locator": source_anchor["locator"],
            }
        )
        for primitive_id, state, reason in (
            ("manim.math_tex", "implemented", "Typeset the paper equation as the stable visual anchor."),
            ("project.formula_operation_walk", "candidate", "Expose the equation's operation order before selecting specialized views."),
        ):
            manim_ids.add(primitive_id)
            edges.append(
                {
                    "edge_id": f"edge:{display_node_id}:{primitive_id}",
                    "source": display_node_id,
                    "target": primitive_id,
                    "state": state,
                    "operation_type": "formula_display",
                    "reason": reason,
                    "evidence_refs": [source_anchor["locator"]],
                }
            )
        if formula.get("code_mappings"):
            primitive_id = "project.formula_code_bridge"
            manim_ids.add(primitive_id)
            edges.append(
                {
                    "edge_id": f"edge:{display_node_id}:{primitive_id}",
                    "source": display_node_id,
                    "target": primitive_id,
                    "state": "implemented",
                    "operation_type": "formula_code_mapping",
                    "reason": primitives[primitive_id]["animation_contract"],
                    "evidence_refs": [item["path"] for item in formula["code_mappings"]],
                }
            )

        for operation in formula["operations"]:
            node_id = f"node:{operation['operation_id']}"
            formula_nodes.append(
                {
                    "node_id": node_id,
                    "formula_id": formula_id,
                    "level": "operation",
                    "label": operation["operation_type"].replace("_", " "),
                    "expression": operation["operation_id"].split(".")[-1].replace("_", " "),
                    "source_locator": source_anchor["locator"],
                }
            )
            primitive_id = operation["primitive_ref"]
            primitive = primitives[primitive_id]
            manim_ids.add(primitive_id)
            edge_state = "implemented" if primitive["status"] == "available" else operation["mapping_state"]
            edges.append(
                {
                    "edge_id": f"edge:{node_id}:{primitive_id}",
                    "source": node_id,
                    "target": primitive_id,
                    "state": edge_state,
                    "operation_type": operation["operation_type"],
                    "reason": primitive["animation_contract"],
                    "evidence_refs": operation["evidence_refs"],
                }
            )

            alternatives = [
                item for item in registry["primitives"]
                if item["primitive_id"] != primitive_id
                and operation["operation_type"] in item["operations"]
                and item["status"] == "available"
                and (item["origin"] == "built_in" or formula_id in item["used_by"])
            ]
            for alternative in alternatives[:1]:
                alternative_id = alternative["primitive_id"]
                manim_ids.add(alternative_id)
                edges.append(
                    {
                        "edge_id": f"edge:{node_id}:{alternative_id}:alternative",
                        "source": node_id,
                        "target": alternative_id,
                        "state": "candidate",
                        "operation_type": operation["operation_type"],
                        "reason": f"Compatible registry operation; not selected by this formula IR. {alternative['animation_contract']}",
                        "evidence_refs": operation["evidence_refs"],
                    }
                )

    # Coverage nodes make the source-grounding audit visible even when a full
    # operation-level Formula IR has not yet been authored for that equation.
    # They are deliberately less granular than Formula IR nodes, but they keep
    # every animate/explain decision connected to callable renderer functions.
    for index, coverage in enumerate(packet.get("equation_coverage", []), start=1):
        if coverage["coverage"] == "fold":
            continue
        coverage_id = f"coverage:{packet['paper_id']}:{index}"
        node_id = f"node:{coverage_id}"
        formula_nodes.append(
            {
                "node_id": node_id,
                "formula_id": coverage_id,
                "level": "equation coverage",
                "label": f"{' · '.join(coverage['equation_ids'])} — {coverage['thread_stage']}",
                "expression": coverage["intent"],
                "source_locator": " · ".join(coverage["source_refs"]),
            }
        )
        base_targets = [
            ("manim.math_tex", "implemented", "Keep the paper equation visible as the stable anchor."),
            ("project.formula_operation_walk", "candidate", "Expose operation order when a full Formula IR is available."),
        ]
        specialized = {
            "formula_transition": "manim.transform_matching_tex",
            "geometry": "project.rope_relative_rotation" if packet["paper_id"] == "rope" else "manim.axes_vector",
            "metric_animation": "project.ess_tradeoff_gauge" if "effective sample size" in coverage["thread_stage"] else "project.metric_bars",
            "none": "manim.math_tex",
        }[coverage["animation_recipe"]]
        if specialized != "manim.math_tex":
            base_targets.append((specialized, "implemented" if coverage["coverage"] == "animate" else "candidate", primitives[specialized]["animation_contract"]))
        for primitive_id, state, reason in base_targets:
            manim_ids.add(primitive_id)
            edges.append(
                {
                    "edge_id": f"edge:{node_id}:{primitive_id}",
                    "source": node_id,
                    "target": primitive_id,
                    "state": state,
                    "operation_type": coverage["animation_recipe"],
                    "reason": reason,
                    "evidence_refs": coverage["source_refs"],
                }
            )

    manim_nodes = []
    for primitive_id in sorted(manim_ids):
        primitive = primitives[primitive_id]
        manim_nodes.append(
            {
                "primitive_id": primitive_id,
                "label": primitive["source_symbol"] or primitive_id,
                "origin": primitive["origin"],
                "origin_label": primitive["origin_badge"]["label"],
                "status": primitive["status"],
                "operations": primitive["operations"],
                "animation_contract": primitive["animation_contract"],
                "limitations": primitive["limitations"],
            }
        )

    return {
        "schema_version": "formula-manim-map/0.1.0",
        "registry_ref": repo_path(REGISTRY_PATH),
        "manim_compatibility": registry["manim_compatibility"],
        "formulas": formula_summaries,
        "formula_nodes": formula_nodes,
        "manim_nodes": manim_nodes,
        "edges": edges,
    }
