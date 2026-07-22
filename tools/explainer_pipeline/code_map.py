from __future__ import annotations

from typing import Any

from .common import load_json, resolve_repo_path


def build_code_map(packet: dict[str, Any]) -> dict[str, Any]:
    spec = packet["code_understanding"]
    sources = {source["code_id"]: source for source in packet["code_sources"]}

    def upstream_url(code_id: str, path: str, line_start: int, line_end: int) -> str | None:
        source = sources.get(code_id)
        if not source:
            return None
        return (
            f"{source['repository']}/blob/{source['revision']}/{path}"
            f"#L{line_start}-L{line_end}"
        )

    formulas = {}
    for ref in packet["formula_refs"]:
        formula = load_json(resolve_repo_path(ref))
        formulas[formula["formula_id"]] = formula
    formula_nodes = []
    code_nodes: dict[str, dict[str, Any]] = {}
    formula_code_edges = []
    for link in spec["formula_code_links"]:
        formula_id = link.get("formula_id")
        formula = formulas.get(formula_id) if formula_id else None
        if formula:
            formula_node_id = f"formula:{formula_id}"
            label = link.get("formula_label", formula["title"])
            expression = formula["display"]["plain_text"]
            formula_source_url = formula["source_anchor"]["source_url"]
        else:
            equation_key = ".".join(link.get("equation_ids", [link.get("formula_label", "equation")])).lower().replace(" ", "-")
            formula_id = f"coverage:{packet['paper_id']}:{equation_key}"
            formula_node_id = f"formula:{formula_id}"
            label = link["formula_label"]
            expression = link.get("expression", "See paper equation at the cited locator.")
            formula_source_url = packet["sources"][0].get("url")
        if not any(item["node_id"] == formula_node_id for item in formula_nodes):
            formula_nodes.append({
                "node_id": formula_node_id,
                "formula_id": formula_id,
                "label": label,
                "expression": expression,
                "source_url": formula_source_url,
            })
        code_node_id = f"code:{link['code_id']}:{link['symbol']}"
        code_nodes.setdefault(code_node_id, {
            "node_id": code_node_id,
            "code_id": link["code_id"],
            "symbol": link["symbol"],
            "path": link["path"],
            "line_start": link["line_start"],
            "line_end": link["line_end"],
            "role": link["role"],
            "source_url": upstream_url(link["code_id"], link["path"], link["line_start"], link["line_end"]),
        })
        formula_code_edges.append({
            "edge_id": f"{formula_node_id}->{code_node_id}",
            "source": formula_node_id,
            "target": code_node_id,
            "state": link.get("state", "confirmed"),
            "role": link["role"],
            "evidence_refs": link["evidence_refs"],
        })
    default_code_id = packet["code_sources"][0]["code_id"]
    lifecycle_nodes = []
    for node in spec["nodes"]:
        item = dict(node)
        item["source_url"] = upstream_url(
            item.get("code_id", default_code_id),
            item["path"],
            item["line_start"],
            item["line_end"],
        )
        lifecycle_nodes.append(item)

    return {
        "schema_version": "explainer-code-map/0.1.0",
        "formula_nodes": formula_nodes,
        "code_nodes": list(code_nodes.values()),
        "formula_code_edges": formula_code_edges,
        "example": spec["example"],
        "dag_nodes": lifecycle_nodes,
        "dag_edges": spec["edges"],
        "experiment_pipeline": spec["experiment_pipeline"],
        "repository_sources": packet["code_sources"],
    }
