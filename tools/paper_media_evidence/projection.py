"""Fail-closed, dependency-closed, allowlisted public projection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .constants import PROJECTION_POLICY_ID, PROJECTION_POLICY_PATH, PUBLIC_SCHEMA_VERSION
from .sources import typed_source_snapshots
from .validation import ManifestValidationError, validate_canonical, validate_public


def _canonical_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(document: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(document)).hexdigest()


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (str(key),)
            yield child_path, child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, path + (str(index),))


def _leaf_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(child) for child in value)
    return 1


def _safe_parent(parent: Mapping[str, Any]) -> dict[str, Any]:
    return {key: parent[key] for key in ("scope", "run_id", "artifact_id", "relation", "content_hash", "canonical_manifest_hash")}


def _safe_lineage(lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "implementation_origin": lineage["implementation_origin"],
        "input_contract_mode": lineage["input_contract_mode"],
        "patch_level": lineage["patch_level"],
        "patchset_hash": lineage["patchset_hash"],
        "derivation_stage": lineage["derivation_stage"],
        "parent_artifact_refs": [_safe_parent(item) for item in lineage["parent_artifact_refs"]],
    }


def _selected(items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [item for item in items if item.get("publishable") is True]


def _projection_gate_errors(document: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if document["status"] in {"running", "migration_pending"}:
        errors.append("publication:nonterminal-or-migration-pending")
    publication = document["publication"]
    if publication["decision"] != "allowed" or publication["source_visibility"] != "public":
        errors.append("publication:run-not-approved-public")
    pipeline = document["pipeline"]
    if pipeline["repository_visibility"] != "public":
        errors.append("publication:repository-not-public")
    for field in ("repository", "commit_sha"):
        if not isinstance(pipeline[field], str):
            errors.append(f"publication:pipeline-{field}-unavailable")
    host = urlparse(pipeline["repository"]).hostname if isinstance(pipeline["repository"], str) else None
    if host not in policy["allowed_repository_hosts"]:
        errors.append("publication:repository-host-not-allowed")
    for snapshot in typed_source_snapshots(document):
        if snapshot.get("availability") != "available" or snapshot.get("source_visibility") != "public" or snapshot.get("publication_decision") != "allowed":
            errors.append("publication:source-snapshot-not-approved-public")
    for item in document["license_ledger"]:
        if item.get("availability") != "available":
            errors.append("publication:license-ledger-incomplete")
            continue
        if item["source_visibility"] != "public" or item["publication_decision"] != "allowed":
            errors.append("publication:license-source-not-approved-public")
        if item["redistribution_conclusion"] not in policy["allowed_redistribution_conclusions"]:
            errors.append("publication:license-disallows-projection")
    execution = document["execution"]
    if execution.get("availability") != "available":
        errors.append("publication:execution-unavailable")
    elif execution["host_metadata"]:
        errors.append("publication:host-metadata-present")
    if any(item["status"] not in {"reconciled", "released", "expired"} for item in document["budget"]["reservations"]):
        errors.append("publication:cost-ledger-not-reconciled")

    secret_patterns = [re.compile(pattern) for pattern in policy["secret_value_patterns"]]
    pii_patterns = [re.compile(pattern) for pattern in policy["pii_value_patterns"]]
    for _, value in _walk(document):
        if isinstance(value, str):
            if any(pattern.search(value) for pattern in secret_patterns):
                errors.append("publication:secret-pattern")
            if any(pattern.search(value) for pattern in pii_patterns):
                errors.append("publication:pii-pattern")
    if execution.get("availability") == "available":
        unsafe_patterns = [re.compile(pattern) for pattern in policy["unsafe_path_patterns"]]
        if any(pattern.search(token) for token in execution["command"] for pattern in unsafe_patterns):
            errors.append("publication:unsafe-command")
    return errors


def _dependency_errors(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    artifacts = {item["artifact_id"]: item for item in _selected(document["artifacts"])}
    validations = {item["validation_id"]: item for item in _selected(document["validations"])}
    claims = {item["claim_id"]: item for item in _selected(document["claims"])}
    reviews = {item["review_id"]: item for item in _selected(document["reviews"])}
    repairs = _selected(document["repair_events"])
    nodes = {item["node_id"]: item for item in _selected(document["graph"]["nodes"])}
    edges = {item["edge_id"]: item for item in _selected(document["graph"]["edges"])}
    evidence = set(artifacts) | set(validations) | set(claims)
    subjects = set(artifacts) | set(nodes) | set(edges)

    for parent in document["lineage"]["parent_artifact_refs"]:
        if parent["scope"] == "local" and parent["artifact_id"] not in artifacts:
            errors.append("publication:run-local-lineage-closure")
        if parent["scope"] == "external" and not any(
            item["run_id"] == parent["run_id"] and item["artifact_id"] == parent["artifact_id"]
            and item["content_hash"] == parent["content_hash"] and item["canonical_manifest_hash"] == parent["canonical_manifest_hash"]
            and item["source_visibility"] == "public" for item in document["external_lineage"]
        ):
            errors.append("publication:run-external-lineage-closure")

    for artifact in artifacts.values():
        if not artifact["public_path"] or not isinstance(artifact["content_hash"], str):
            errors.append(f"publication:{artifact['artifact_id']}:missing-public-evidence")
        if any(ref not in validations or validations[ref]["subject_ref"] != artifact["artifact_id"] for ref in artifact["validation_refs"]):
            errors.append(f"publication:{artifact['artifact_id']}:validation-closure")
        for parent in artifact["lineage"]["parent_artifact_refs"]:
            if parent["scope"] == "local" and parent["artifact_id"] not in artifacts:
                errors.append(f"publication:{artifact['artifact_id']}:local-lineage-closure")
            if parent["scope"] == "external" and not any(
                item["run_id"] == parent["run_id"] and item["artifact_id"] == parent["artifact_id"]
                and item["content_hash"] == parent["content_hash"] and item["canonical_manifest_hash"] == parent["canonical_manifest_hash"]
                and item["source_visibility"] == "public" for item in document["external_lineage"]
            ):
                errors.append(f"publication:{artifact['artifact_id']}:external-lineage-closure")
    for validation in validations.values():
        if validation["subject_ref"] not in artifacts or validation["validation_id"] not in artifacts[validation["subject_ref"]]["validation_refs"]:
            errors.append(f"publication:{validation['validation_id']}:subject-closure")
    for claim in claims.values():
        if any(ref not in evidence | set(reviews) for ref in claim["evidence_refs"]):
            errors.append(f"publication:{claim['claim_id']}:evidence-closure")
    for review in reviews.values():
        if review["subject_ref"] not in subjects or any(ref not in evidence for ref in review["evidence_refs"]):
            errors.append(f"publication:{review['review_id']}:dependency-closure")
    for edge in edges.values():
        if edge["source_ref"] not in nodes or edge["target_ref"] not in nodes:
            errors.append(f"publication:{edge['edge_id']}:node-closure")
        if any(ref not in evidence for ref in edge["evidence_refs"]):
            errors.append(f"publication:{edge['edge_id']}:evidence-closure")
        if edge["review_ref"] is not None and (edge["review_ref"] not in reviews or reviews[edge["review_ref"]]["subject_ref"] != edge["edge_id"]):
            errors.append(f"publication:{edge['edge_id']}:review-closure")
    for repair in repairs:
        if repair["parent_artifact_ref"] not in artifacts or repair["child_artifact_ref"] not in artifacts:
            errors.append(f"publication:{repair['event_id']}:artifact-closure")
    return errors


def _scan_projected(document: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    forbidden_keys = tuple(fragment.lower() for fragment in policy["forbidden_key_fragments"])
    patterns = [
        ("secret-pattern", re.compile(pattern)) for pattern in policy["secret_value_patterns"]
    ] + [("pii-pattern", re.compile(pattern)) for pattern in policy["pii_value_patterns"]] + [
        ("unsafe-path", re.compile(pattern)) for pattern in policy["unsafe_path_patterns"]
    ]
    for path, value in _walk(document):
        key = path[-1].lower()
        if any(fragment in key for fragment in forbidden_keys):
            errors.append("publication:forbidden-projected-key")
        if isinstance(value, str):
            for label, pattern in patterns:
                if pattern.search(value):
                    errors.append(f"publication:projected-{label}")
    return errors


def _redaction_summary(document: Mapping[str, Any]) -> dict[str, int]:
    unpublishable_artifacts = [item for item in document["artifacts"] if not item["publishable"]]
    collections = ("validations", "claims", "reviews", "repair_events")
    omitted_records = sum(sum(not item["publishable"] for item in document[name]) for name in collections)
    omitted_records += sum(not item["publishable"] for item in document["graph"]["nodes"])
    omitted_records += sum(not item["publishable"] for item in document["graph"]["edges"])
    always_private = [
        document["visibility"], document["experiment_config_id"], document["completion_contract"],
        document["execution"], document["review_policy"], document["migration"] if "migration" in document else {},
        document["publication"]["reason"], document["publication"]["policy_id"],
        document["pipeline"]["completion_contract_id"], document["completion"]["derived_at"],
    ]
    omitted_fields = sum(_leaf_count(value) for value in always_private)
    if "source_snapshots" in document["input"]:
        omitted_fields += _leaf_count(document["input"].get("paper_snapshot", {}))
        omitted_fields += _leaf_count(document["input"].get("code_snapshot", {}))
    omitted_fields += sum(4 if item["availability"] == "available" else _leaf_count(item) - 2 for item in typed_source_snapshots(document))
    omitted_fields += _leaf_count(document["external_lineage"])
    omitted_fields += sum(_leaf_count(item) for item in unpublishable_artifacts)
    omitted_fields += sum(_leaf_count(item) for name in collections for item in document[name] if not item["publishable"])
    omitted_fields += sum(_leaf_count(item) for item in document["graph"]["nodes"] if not item["publishable"])
    omitted_fields += sum(_leaf_count(item) for item in document["graph"]["edges"] if not item["publishable"])
    omitted_fields += sum(3 for item in document["artifacts"] if item["publishable"])  # private_path + lineage.adapter_ref + publishable
    omitted_fields += sum(1 for name in ("validations", "claims") for item in document[name] if item["publishable"])
    omitted_fields += sum(3 for item in document["reviews"] if item["publishable"])  # evaluator id + notes + publishable
    omitted_fields += sum(1 for item in document["graph"]["nodes"] if item["publishable"])
    omitted_fields += sum(1 for item in document["graph"]["edges"] if item["publishable"])
    omitted_fields += sum(_leaf_count(item) for item in document["repair_events"] if item["publishable"])
    omitted_fields += sum(7 for item in document["license_ledger"] if item["availability"] == "available")
    omitted_fields += 1  # run lineage.adapter_ref
    public_budget_leaves = 3 + len(document["budget"]["coverage"])
    omitted_fields += _leaf_count(document["budget"]) - public_budget_leaves
    return {"omitted_fields": omitted_fields, "omitted_artifacts": len(unpublishable_artifacts), "omitted_records": omitted_records}


def _public_reservation_state(reservations: Iterable[Mapping[str, Any]]) -> str:
    statuses = {item["status"] for item in reservations}
    if not statuses:
        return "none"
    if len(statuses) == 1:
        return next(iter(statuses))
    return "mixed_finalized"


def project_public_manifest(document: Mapping[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    """Build a public document from explicit allowlists; never mutate the input."""

    validate_canonical(document)
    policy = json.loads(PROJECTION_POLICY_PATH.read_text(encoding="utf-8"))
    errors = _projection_gate_errors(document, policy) + _dependency_errors(document)
    if errors:
        raise ManifestValidationError(errors)
    artifacts = _selected(document["artifacts"])
    validations = _selected(document["validations"])
    claims = _selected(document["claims"])
    reviews = _selected(document["reviews"])
    repairs = _selected(document["repair_events"])
    nodes = _selected(document["graph"]["nodes"])
    edges = _selected(document["graph"]["edges"])
    public_node_ids = {item["node_id"] for item in nodes}
    projected = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "canonical_manifest_hash": _hash(document),
        "projection_policy_id": PROJECTION_POLICY_ID,
        "publication_validator_version": policy["publication_validator_version"],
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "redaction_summary": _redaction_summary(document),
        "run_id": document["run_id"], "cell_id": document["cell_id"], "thread": document["thread"],
        "started_at": document["started_at"], "ended_at": document["ended_at"], "status": document["status"],
        "pipeline": {key: document["pipeline"][key] for key in ("id", "variant", "repository", "repository_visibility", "commit_sha")},
        "input": {
            "canonical_topic_family": document["input"]["canonical_topic_family"],
            "granularity": document["input"]["granularity"],
            "source_snapshots": [
                {key: item[key] for key in ("source_id", "source_type", "source_url", "revision", "content_hash")}
                for item in typed_source_snapshots(document)
            ],
        },
        "condition": {key: document["condition"][key] for key in ("condition_id", "model_policy", "replicate")},
        "publication": {"source_visibility": document["publication"]["source_visibility"], "decision": document["publication"]["decision"]},
        "lineage": _safe_lineage(document["lineage"]),
        "completion": {key: document["completion"][key] for key in ("contract_id", "rule_version", "derived_value")},
        "artifacts": [
            {"artifact_id": item["artifact_id"], "role": item["role"], "public_path": item["public_path"], "content_hash": item["content_hash"], "media_type": item["media_type"], "completion": item["completion"], "validation_refs": list(item["validation_refs"]), "lineage": _safe_lineage(item["lineage"])}
            for item in artifacts
        ],
        "validations": [
            {key: item[key] for key in ("validation_id", "validator_id", "subject_ref", "result", "evidence_ref", "validated_at")}
            for item in validations
        ],
        "claims": [
            {key: item[key] for key in ("claim_id", "label", "statement", "evidence_refs", "observed_at")}
            for item in claims
        ],
        "reviews": [
            {"review_id": item["review_id"], "subject_ref": item["subject_ref"], "rubric_id": item["rubric_id"], "evaluator_type": item["evaluator"]["type"], "result": item["result"], "evidence_refs": list(item["evidence_refs"]), "reviewed_at": item["reviewed_at"]}
            for item in reviews
        ],
        "graph": {
            "nodes": [{key: item[key] for key in ("node_id", "node_type", "coverage_state", "aliases")} for item in nodes],
            "edges": [{key: item[key] for key in ("edge_id", "edge_type", "source_ref", "target_ref", "match_state", "evidence_refs", "confidence", "review_ref")} for item in edges],
            "migrations": [dict(item) for item in document["graph"]["migrations"] if item["new_id"] in public_node_ids and any(item["old_id"] in node["aliases"] for node in nodes)],
        },
        "repair_summary": {"event_count": len(repairs), "max_iteration": max((item["iteration"] for item in repairs), default=0), "policy_ids": sorted({item["policy_id"] for item in repairs})},
        "cost": {"currency": document["budget"]["currency"], "measured_usd": document["budget"]["measured_usd"], "estimated_usd": document["budget"]["estimated_usd"], "coverage": list(document["budget"]["coverage"]), "reservation_state": _public_reservation_state(document["budget"]["reservations"])},
        "license_ledger": [
            {key: item[key] for key in ("item_id", "source_ref", "resource_type", "source_url", "source_revision", "declared_spdx", "constraints", "exceptions", "redistribution_conclusion", "evidence_refs", "source_visibility", "publication_decision")}
            for item in document["license_ledger"]
        ],
    }
    if "pairing_id" in document:
        projected["pairing_id"] = document["pairing_id"]
    errors = _scan_projected(projected, policy)
    if errors:
        raise ManifestValidationError(errors)
    validate_public(projected)
    return projected


def write_public_manifest_atomic(document: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    """Validate before writing, then atomically replace the destination."""

    projected = project_public_manifest(document)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, prefix=".public-manifest-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(projected, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return projected
