"""Structural and cross-record evidence manifest validation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .completion import derive_completion
from .constants import (
    CANONICAL_SCHEMA_PATH,
    COMPLETION_SCHEMA_PATH,
    PUBLIC_SCHEMA_PATH,
)


class ManifestValidationError(ValueError):
    """A safe aggregate validation error that never echoes field values."""

    def __init__(self, errors: Iterable[str]):
        self.errors = sorted(set(errors))
        super().__init__("manifest validation failed: " + "; ".join(self.errors))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = _load(schema_path)
    completion = _load(COMPLETION_SCHEMA_PATH)
    registry = Registry().with_resources(
        [
            (schema["$id"], Resource.from_contents(schema)),
            (completion["$id"], Resource.from_contents(completion)),
        ]
    )
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def _pointer(path: Iterable[Any]) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(parts) if parts else "/"


def _structural_errors(document: Mapping[str, Any], schema_path: Path) -> list[str]:
    return [f"schema:{_pointer(error.absolute_path)}:{error.validator}" for error in _validator(schema_path).iter_errors(document)]


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


ALLOWED_GRAPH_EDGES = {
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


def _semantic_errors(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    pipeline = document["pipeline"]
    contract = document["completion_contract"]
    if pipeline["completion_contract_id"] != contract["contract_id"]:
        errors.append("completion:contract-id-mismatch")
    if document["completion"]["contract_id"] != contract["contract_id"]:
        errors.append("completion:result-contract-id-mismatch")
    if document["completion"]["derived_value"] != derive_completion(document):
        errors.append("completion:not-machine-derived")

    if _parse_time(document["started_at"]) > _parse_time(document["ended_at"]):
        errors.append("time:run-start-after-end")

    lineage_records = [("run", document["lineage"])] + [
        (artifact["artifact_id"], artifact["lineage"]) for artifact in document["artifacts"]
    ]
    for subject, lineage in lineage_records:
        if lineage["input_contract_mode"] == "adapted" and not lineage["adapter_ref"]:
            errors.append(f"lineage:{subject}:adapted-without-adapter")
        if lineage["input_contract_mode"] == "native" and lineage["adapter_ref"] is not None:
            errors.append(f"lineage:{subject}:native-with-adapter")

    groups = {
        "stage": [item["id"] for item in document["stages"]],
        "artifact": [item["artifact_id"] for item in document["artifacts"]],
        "validation": [item["validation_id"] for item in document["validations"]],
        "claim": [item["claim_id"] for item in document["claims"]],
        "review": [item["review_id"] for item in document["reviews"]],
        "repair": [item["event_id"] for item in document["repair_events"]],
        "node": [item["node_id"] for item in document["graph"]["nodes"]],
        "edge": [item["edge_id"] for item in document["graph"]["edges"]],
    }
    for group, values in groups.items():
        if _duplicates(values):
            errors.append(f"ids:{group}:duplicate")

    artifact_ids = set(groups["artifact"])
    validation_ids = set(groups["validation"])
    review_ids = set(groups["review"])
    evidence_ids = artifact_ids | validation_ids | review_ids
    for artifact in document["artifacts"]:
        if any(ref not in validation_ids for ref in artifact["validation_refs"]):
            errors.append(f"refs:{artifact['artifact_id']}:validation")
        if any(parent["artifact_id"] not in artifact_ids for parent in artifact["lineage"]["parent_artifact_refs"]):
            errors.append(f"refs:{artifact['artifact_id']}:parent")
    for validation in document["validations"]:
        if validation["subject_ref"] not in artifact_ids:
            errors.append(f"refs:{validation['validation_id']}:subject")
    for claim in document["claims"]:
        if any(ref not in evidence_ids for ref in claim["evidence_refs"]):
            errors.append(f"refs:{claim['claim_id']}:evidence")
    for review in document["reviews"]:
        if review["subject_ref"] not in artifact_ids | set(groups["node"]) | set(groups["edge"]):
            errors.append(f"refs:{review['review_id']}:subject")
        if any(ref not in artifact_ids | validation_ids for ref in review["evidence_refs"]):
            errors.append(f"refs:{review['review_id']}:evidence")
    for repair in document["repair_events"]:
        if repair["parent_artifact_ref"] not in artifact_ids or repair["child_artifact_ref"] not in artifact_ids:
            errors.append(f"refs:{repair['event_id']}:artifact")

    reservations = document["budget"]["reservations"]
    if _duplicates(item["reservation_id"] for item in reservations):
        errors.append("cost:duplicate-reservation")
    for item in reservations:
        if item["status"] == "reconciled" and item["reconciled_usd"] is None:
            errors.append(f"cost:{item['reservation_id']}:missing-reconciliation")
        if item["status"] != "reconciled" and item["reconciled_usd"] is not None:
            errors.append(f"cost:{item['reservation_id']}:unexpected-reconciliation")
    gate = document["budget"]["paid_stage_gate"]
    if gate["decision"] == "allowed":
        if gate["projected_next_stage_usd"] is None or document["budget"]["rate_card"].get("availability") != "available":
            errors.append("cost:allowed-with-unknown-projection")
        if not any(item["stage_id"] == gate["next_stage_id"] and item["status"] in {"active", "reconciled"} for item in reservations):
            errors.append("cost:allowed-without-reservation")
    if gate["projected_next_stage_usd"] is None and gate["decision"] not in {"blocked", "not_applicable"}:
        errors.append("cost:unknown-paid-stage-must-fail-closed")

    nodes = {item["node_id"]: item for item in document["graph"]["nodes"]}
    aliases: set[str] = set()
    for node in nodes.values():
        for alias in node["aliases"]:
            if alias in aliases or alias in nodes:
                errors.append("graph:duplicate-or-live-alias")
            aliases.add(alias)
    for edge in document["graph"]["edges"]:
        source = nodes.get(edge["source_ref"])
        target = nodes.get(edge["target_ref"])
        if not source or not target:
            errors.append(f"graph:{edge['edge_id']}:dangling-node")
            continue
        pair = (source["node_type"], target["node_type"])
        if pair not in ALLOWED_GRAPH_EDGES[edge["edge_type"]]:
            errors.append(f"graph:{edge['edge_id']}:disallowed-types")
        if edge["edge_type"] not in {"contains", "depends_on"} and not edge["evidence_refs"]:
            errors.append(f"graph:{edge['edge_id']}:missing-evidence")
        if edge["match_state"] in {"confirmed", "rejected"} and edge["review_ref"] not in review_ids:
            errors.append(f"graph:{edge['edge_id']}:missing-review")
    for migration in document["graph"]["migrations"]:
        if migration["old_id"] not in aliases or migration["new_id"] not in nodes:
            errors.append("graph:dangling-migration")

    if document["status"] == "migration_pending":
        if document["completion"]["derived_value"] not in {"partial", "placeholder", "failed"}:
            errors.append("migration:unsafe-completion")
    return errors


def validate_canonical(document: Mapping[str, Any]) -> None:
    errors = _structural_errors(document, CANONICAL_SCHEMA_PATH)
    if not errors:
        errors.extend(_semantic_errors(document))
    if errors:
        raise ManifestValidationError(errors)


def validate_public(document: Mapping[str, Any]) -> None:
    errors = _structural_errors(document, PUBLIC_SCHEMA_PATH)
    if errors:
        raise ManifestValidationError(errors)
