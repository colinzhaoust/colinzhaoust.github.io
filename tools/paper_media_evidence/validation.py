"""Structural, semantic, and dependency-closure manifest validation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .completion import derive_completion
from .constants import CANONICAL_SCHEMA_PATH, COMPLETION_SCHEMA_PATH, PUBLIC_SCHEMA_PATH


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
        [(schema["$id"], Resource.from_contents(schema)), (completion["$id"], Resource.from_contents(completion))]
    )
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def _pointer(path: Iterable[Any]) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(parts) if parts else "/"


def _structural_errors(document: Mapping[str, Any], schema_path: Path) -> list[str]:
    return [f"schema:{_pointer(error.absolute_path)}:{error.validator}" for error in _validator(schema_path).iter_errors(document)]


def validate_canonical_structure(document: Mapping[str, Any]) -> None:
    """Validate only the immutable document shape, for derivation tooling."""

    errors = _structural_errors(document, CANONICAL_SCHEMA_PATH)
    if errors:
        raise ManifestValidationError(errors)


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


def _lineage_errors(document: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    external = {
        (item["run_id"], item["artifact_id"], item["content_hash"], item["canonical_manifest_hash"])
        for item in document["external_lineage"]
    }
    records = [("run", document["lineage"])] + [(item["artifact_id"], item["lineage"]) for item in artifacts.values()]
    for subject, lineage in records:
        if lineage["input_contract_mode"] == "adapted" and not lineage["adapter_ref"]:
            errors.append(f"lineage:{subject}:adapted-without-adapter")
        if lineage["input_contract_mode"] == "native" and lineage["adapter_ref"] is not None:
            errors.append(f"lineage:{subject}:native-with-adapter")
        for parent in lineage["parent_artifact_refs"]:
            identity = (parent["run_id"], parent["artifact_id"], parent["content_hash"], parent["canonical_manifest_hash"])
            if parent["scope"] == "local":
                local = artifacts.get(parent["artifact_id"])
                if parent["run_id"] != document["run_id"] or parent["canonical_manifest_hash"] is not None:
                    errors.append(f"lineage:{subject}:invalid-local-identity")
                if not local or local["content_hash"] != parent["content_hash"]:
                    errors.append(f"lineage:{subject}:unresolved-local-parent")
            else:
                if parent["run_id"] == document["run_id"] or parent["canonical_manifest_hash"] is None or identity not in external:
                    errors.append(f"lineage:{subject}:unresolved-external-parent")
    return errors


def _cost_errors(document: Mapping[str, Any], stages: Mapping[str, Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    budget = document["budget"]
    if budget["experiment_id"] != document["experiment_config_id"] or budget["cell_id"] != document["cell_id"]:
        errors.append("cost:ledger-identity-mismatch")
    reservations = budget["reservations"]
    for key in ("reservation_id", "atomic_operation_id"):
        if _duplicates(item[key] for item in reservations):
            errors.append(f"cost:duplicate-{key}")
    reconciled_total = 0.0
    active_total = 0.0
    by_id = {item["reservation_id"]: item for item in reservations}
    paid_stage_reservations: dict[str, list[Mapping[str, Any]]] = {}
    for item in reservations:
        if item["experiment_id"] != budget["experiment_id"] or item["cell_id"] != budget["cell_id"] or item["ledger_id"] != budget["ledger_id"]:
            errors.append(f"cost:{item['reservation_id']}:identity-mismatch")
        if item["stage_id"] not in stages:
            errors.append(f"cost:{item['reservation_id']}:unknown-stage")
        if budget["cell_spend_before_usd"] + item["projected_usd"] > budget["cell_limit_usd"] + 1e-9:
            errors.append(f"cost:{item['reservation_id']}:cell-reservation-over-limit")
        if budget["experiment_spend_before_usd"] + item["projected_usd"] > budget["experiment_limit_usd"] + 1e-9:
            errors.append(f"cost:{item['reservation_id']}:experiment-reservation-over-limit")
        paid_stage_reservations.setdefault(item["stage_id"], []).append(item)
        if item["status"] == "reconciled":
            if item["reconciled_at"] is None or item["reconciled_usd"] is None or item["usage_evidence_ref"] is None:
                errors.append(f"cost:{item['reservation_id']}:incomplete-reconciliation")
            else:
                reconciled_total += item["reconciled_usd"]
        elif any(item[field] is not None for field in ("reconciled_at", "reconciled_usd", "usage_evidence_ref")):
            errors.append(f"cost:{item['reservation_id']}:unexpected-reconciliation")
        if item["status"] == "active":
            active_total += item["projected_usd"]

    measured = budget["measured_usd"]
    if measured is None and reconciled_total:
        errors.append("cost:missing-measured-total")
    if measured is not None and abs(measured - reconciled_total) > 1e-9:
        errors.append("cost:measured-total-contradiction")

    for stage_id, stage in stages.items():
        if stage["billing_class"] != "paid":
            continue
        stage_reservations = paid_stage_reservations.get(stage_id, [])
        if budget["rate_card"].get("availability") != "available":
            errors.append(f"cost:{stage_id}:paid-without-rate-card")
        if stage["status"] in {"running", "succeeded", "failed"} and not stage_reservations:
            errors.append(f"cost:{stage_id}:paid-without-reservation")
        if stage["status"] in {"succeeded", "failed"} and not any(item["status"] == "reconciled" for item in stage_reservations):
            errors.append(f"cost:{stage_id}:terminal-paid-stage-unreconciled")
        if stage["status"] == "running" and not any(item["status"] == "active" for item in stage_reservations):
            errors.append(f"cost:{stage_id}:running-paid-stage-unreserved")

    gate = budget["paid_stage_gate"]
    if gate["decision"] == "allowed":
        reservation = by_id.get(gate["reservation_id"])
        if gate["projected_next_stage_usd"] is None or budget["rate_card"].get("availability") != "available":
            errors.append("cost:allowed-with-unknown-projection")
        if gate["next_stage_id"] not in stages or stages.get(gate["next_stage_id"], {}).get("billing_class") != "paid":
            errors.append("cost:allowed-stage-is-not-paid")
        if not reservation or reservation["stage_id"] != gate["next_stage_id"] or reservation["status"] not in {"active", "reconciled"}:
            errors.append("cost:allowed-without-atomic-reservation")
        elif abs(reservation["projected_usd"] - gate["projected_next_stage_usd"]) > 1e-9:
            errors.append("cost:gate-reservation-projection-mismatch")
    elif gate["reservation_id"] is not None:
        errors.append("cost:blocked-gate-has-reservation")
    if gate["projected_next_stage_usd"] is None and gate["decision"] not in {"blocked", "not_applicable"}:
        errors.append("cost:unknown-paid-stage-must-fail-closed")

    run_measured = measured or 0.0
    if budget["cell_spend_before_usd"] + run_measured + active_total > budget["cell_limit_usd"] + 1e-9:
        errors.append("cost:cell-limit-exceeded")
    if budget["experiment_spend_before_usd"] + run_measured + active_total > budget["experiment_limit_usd"] + 1e-9:
        errors.append("cost:experiment-limit-exceeded")
    return errors


def _semantic_errors(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = document["completion_contract"]
    if document["pipeline"]["completion_contract_id"] != contract["contract_id"] or document["completion"]["contract_id"] != contract["contract_id"]:
        errors.append("completion:contract-id-mismatch")
    if document["completion"]["rule_version"] != contract["rule_version"]:
        errors.append("completion:rule-version-mismatch")
    if document["completion"]["derived_value"] != derive_completion(document):
        errors.append("completion:not-machine-derived")
    if document["status"] in contract["terminal_run_statuses"]["full_forbidden"] and document["completion"]["derived_value"] == "full":
        errors.append("completion:nonterminal-or-failed-full")

    if document["ended_at"] is not None and _parse_time(document["started_at"]) > _parse_time(document["ended_at"]):
        errors.append("time:run-start-after-end")
    if document["execution"].get("availability") == "available":
        execution = document["execution"]
        if (execution["seed_policy"] == "explicit") != (execution["random_seed"] is not None):
            errors.append("execution:seed-policy-contradiction")

    available_license_types = {item["resource_type"] for item in document["license_ledger"] if item["availability"] == "available"}
    required_license_types = {"paper", "repository"}
    if document["execution"].get("availability") == "available" and document["execution"]["model_versions"]:
        required_license_types.add("model")
    if document["status"] != "migration_pending" and not required_license_types.issubset(available_license_types):
        errors.append("license:required-resource-coverage")

    groups = {
        "stage": [item["id"] for item in document["stages"]],
        "artifact": [item["artifact_id"] for item in document["artifacts"]],
        "validation": [item["validation_id"] for item in document["validations"]],
        "claim": [item["claim_id"] for item in document["claims"]],
        "review": [item["review_id"] for item in document["reviews"]],
        "repair": [item["event_id"] for item in document["repair_events"]],
        "node": [item["node_id"] for item in document["graph"]["nodes"]],
        "edge": [item["edge_id"] for item in document["graph"]["edges"]],
        "license": [item["item_id"] for item in document["license_ledger"]],
    }
    for group, values in groups.items():
        if _duplicates(values):
            errors.append(f"ids:{group}:duplicate")

    artifacts = {item["artifact_id"]: item for item in document["artifacts"]}
    validations = {item["validation_id"]: item for item in document["validations"]}
    claims = {item["claim_id"]: item for item in document["claims"]}
    reviews = {item["review_id"]: item for item in document["reviews"]}
    stages = {item["id"]: item for item in document["stages"]}
    nodes = {item["node_id"]: item for item in document["graph"]["nodes"]}
    edges = {item["edge_id"]: item for item in document["graph"]["edges"]}
    errors.extend(_lineage_errors(document, artifacts))
    if any(stage_id not in stages for stage_id in contract["required_stages"] + contract["smoke_stages"]):
        errors.append("completion:contract-stage-not-declared")
    for stage in stages.values():
        if stage["status"] in {"succeeded", "failed"} and (stage["started_at"] is None or stage["ended_at"] is None):
            errors.append(f"stage:{stage['id']}:terminal-timestamps")
        if stage["status"] == "running" and (stage["started_at"] is None or stage["ended_at"] is not None):
            errors.append(f"stage:{stage['id']}:running-timestamps")
        if stage["status"] == "not_started" and (stage["started_at"] is not None or stage["ended_at"] is not None):
            errors.append(f"stage:{stage['id']}:not-started-timestamps")
    if document["status"] != "running" and any(stage["status"] == "running" for stage in stages.values()):
        errors.append("stage:running-under-terminal-run")

    for artifact in artifacts.values():
        bound = [validations.get(ref) for ref in artifact["validation_refs"]]
        if any(item is None or item["subject_ref"] != artifact["artifact_id"] for item in bound):
            errors.append(f"refs:{artifact['artifact_id']}:validation-subject")
        evidence_valid = isinstance(artifact["content_hash"], str) and bool(bound) and all(item and item["result"] == "pass" for item in bound)
        if artifact["completion"] == "full" and not evidence_valid:
            errors.append(f"completion:{artifact['artifact_id']}:full-without-evidence")
        if artifact["completion"] == "placeholder" and artifact["lineage"]["implementation_origin"] not in contract["placeholder_origins"]:
            errors.append(f"completion:{artifact['artifact_id']}:placeholder-origin")
        if artifact["completion"] == "failed" and evidence_valid:
            errors.append(f"completion:{artifact['artifact_id']}:failed-with-passing-evidence")
        if document["status"] != "migration_pending" and artifact["completion"] in {"partial", "smoke"} and not isinstance(artifact["content_hash"], str):
            errors.append(f"completion:{artifact['artifact_id']}:useful-without-content")
    for validation in validations.values():
        subject = artifacts.get(validation["subject_ref"])
        if not subject or validation["validation_id"] not in subject["validation_refs"]:
            errors.append(f"refs:{validation['validation_id']}:not-bound-by-subject")

    evidence_ids = set(artifacts) | set(validations) | set(claims) | set(reviews)
    subject_ids = set(artifacts) | set(nodes) | set(edges)
    for stage in stages.values():
        if any(ref not in evidence_ids for ref in stage["evidence_refs"]):
            errors.append(f"refs:{stage['id']}:evidence")
    for claim in claims.values():
        if any(ref not in evidence_ids - {claim["claim_id"]} for ref in claim["evidence_refs"]):
            errors.append(f"refs:{claim['claim_id']}:evidence")
    for review in reviews.values():
        if review["subject_ref"] not in subject_ids:
            errors.append(f"refs:{review['review_id']}:subject")
        if any(ref not in set(artifacts) | set(validations) | set(claims) for ref in review["evidence_refs"]):
            errors.append(f"refs:{review['review_id']}:evidence")
        if review["subject_ref"] in edges and edges[review["subject_ref"]]["review_ref"] != review["review_id"]:
            errors.append(f"graph:{review['subject_ref']}:review-not-referenced")
    for repair in document["repair_events"]:
        if repair["parent_artifact_ref"] not in artifacts or repair["child_artifact_ref"] not in artifacts:
            errors.append(f"refs:{repair['event_id']}:artifact")
        elif not any(parent["artifact_id"] == repair["parent_artifact_ref"] for parent in artifacts[repair["child_artifact_ref"]]["lineage"]["parent_artifact_refs"]):
            errors.append(f"refs:{repair['event_id']}:lineage-chain")

    aliases: set[str] = set()
    for node in nodes.values():
        for alias in node["aliases"]:
            if alias in aliases or alias in nodes:
                errors.append("graph:duplicate-or-live-alias")
            aliases.add(alias)
    allowed_rubrics = set(document["review_policy"]["graph_confirmation_rubric_ids"])
    allowed_reviewers = set(document["review_policy"]["graph_reviewer_types"])
    for edge in edges.values():
        source, target = nodes.get(edge["source_ref"]), nodes.get(edge["target_ref"])
        if not source or not target:
            errors.append(f"graph:{edge['edge_id']}:dangling-node")
            continue
        if (source["node_type"], target["node_type"]) not in ALLOWED_GRAPH_EDGES[edge["edge_type"]]:
            errors.append(f"graph:{edge['edge_id']}:disallowed-types")
        if any(ref not in set(artifacts) | set(validations) | set(claims) for ref in edge["evidence_refs"]):
            errors.append(f"graph:{edge['edge_id']}:unresolved-evidence")
        if edge["edge_type"] not in {"contains", "depends_on"} and not edge["evidence_refs"]:
            errors.append(f"graph:{edge['edge_id']}:missing-evidence")
        if edge["match_state"] in {"confirmed", "rejected"}:
            review = reviews.get(edge["review_ref"])
            expected_result = "pass" if edge["match_state"] == "confirmed" else "fail"
            if not review or review["subject_ref"] != edge["edge_id"]:
                errors.append(f"graph:{edge['edge_id']}:review-not-bound")
            elif review["rubric_id"] not in allowed_rubrics or review["evaluator"]["type"] not in allowed_reviewers:
                errors.append(f"graph:{edge['edge_id']}:review-policy")
            elif review["result"] != expected_result or not set(edge["evidence_refs"]).issubset(review["evidence_refs"]):
                errors.append(f"graph:{edge['edge_id']}:review-evidence-or-result")
        elif edge["review_ref"] is not None:
            errors.append(f"graph:{edge['edge_id']}:premature-review")
    for migration in document["graph"]["migrations"]:
        if migration["old_id"] not in aliases or migration["new_id"] not in nodes:
            errors.append("graph:dangling-migration")

    errors.extend(_cost_errors(document, stages))
    if document["status"] == "migration_pending" and document["completion"]["derived_value"] not in {"partial", "placeholder", "failed"}:
        errors.append("migration:unsafe-completion")
    return errors


def _public_semantic_errors(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    artifacts = {item["artifact_id"]: item for item in document["artifacts"]}
    validations = {item["validation_id"]: item for item in document["validations"]}
    claims = {item["claim_id"]: item for item in document["claims"]}
    reviews = {item["review_id"]: item for item in document["reviews"]}
    nodes = {item["node_id"]: item for item in document["graph"]["nodes"]}
    edges = {item["edge_id"]: item for item in document["graph"]["edges"]}
    evidence = set(artifacts) | set(validations) | set(claims)
    for artifact in artifacts.values():
        if any(ref not in validations or validations[ref]["subject_ref"] != artifact["artifact_id"] for ref in artifact["validation_refs"]):
            errors.append(f"public:{artifact['artifact_id']}:validation-closure")
    for validation in validations.values():
        if validation["subject_ref"] not in artifacts or validation["validation_id"] not in artifacts[validation["subject_ref"]]["validation_refs"]:
            errors.append(f"public:{validation['validation_id']}:subject-closure")
    for claim in claims.values():
        if any(ref not in evidence | set(reviews) for ref in claim["evidence_refs"]):
            errors.append(f"public:{claim['claim_id']}:evidence-closure")
    for review in reviews.values():
        if review["subject_ref"] not in set(artifacts) | set(nodes) | set(edges) or any(ref not in evidence for ref in review["evidence_refs"]):
            errors.append(f"public:{review['review_id']}:dependency-closure")
    for edge in edges.values():
        if edge["source_ref"] not in nodes or edge["target_ref"] not in nodes:
            errors.append(f"public:{edge['edge_id']}:node-closure")
        if any(ref not in evidence for ref in edge["evidence_refs"]):
            errors.append(f"public:{edge['edge_id']}:evidence-closure")
        if edge["review_ref"] is not None and (edge["review_ref"] not in reviews or reviews[edge["review_ref"]]["subject_ref"] != edge["edge_id"]):
            errors.append(f"public:{edge['edge_id']}:review-closure")
    aliases = {alias for node in nodes.values() for alias in node["aliases"]}
    for migration in document["graph"]["migrations"]:
        if migration["old_id"] not in aliases or migration["new_id"] not in nodes:
            errors.append("public:graph-migration-closure")
    return errors


def validate_canonical(document: Mapping[str, Any]) -> None:
    errors = _structural_errors(document, CANONICAL_SCHEMA_PATH)
    if not errors:
        errors.extend(_semantic_errors(document))
    if errors:
        raise ManifestValidationError(errors)


def validate_public(document: Mapping[str, Any]) -> None:
    errors = _structural_errors(document, PUBLIC_SCHEMA_PATH)
    if not errors:
        errors.extend(_public_semantic_errors(document))
    if errors:
        raise ManifestValidationError(errors)
