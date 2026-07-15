"""Fail-closed allowlisted public projection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .constants import PROJECTION_POLICY_ID, PROJECTION_POLICY_PATH, PUBLIC_SCHEMA_VERSION
from .validation import ManifestValidationError, validate_canonical, validate_public


def _canonical_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(document: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(document)).hexdigest()


def _walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _safe_lineage(lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "implementation_origin": lineage["implementation_origin"],
        "input_contract_mode": lineage["input_contract_mode"],
        "patch_level": lineage["patch_level"],
        "patchset_hash": lineage["patchset_hash"],
        "derivation_stage": lineage["derivation_stage"],
        "parent_artifact_refs": lineage["parent_artifact_refs"],
    }


def _projection_errors(document: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if document["status"] == "migration_pending":
        errors.append("publication:migration-pending")
    for field in ("repository", "commit_sha"):
        if not isinstance(document["pipeline"][field], str):
            errors.append(f"publication:pipeline-{field}-unavailable")
    host = urlparse(document["pipeline"]["repository"]).hostname if isinstance(document["pipeline"]["repository"], str) else None
    if host not in policy["allowed_repository_hosts"]:
        errors.append("publication:repository-host-not-allowed")
    for name in ("paper_snapshot", "code_snapshot"):
        snapshot = document["input"][name]
        if snapshot.get("availability") != "available" or snapshot.get("source_visibility") != "public":
            errors.append(f"publication:{name}-not-public-snapshot")
    license_snapshot = document["license_snapshot"]
    if license_snapshot.get("availability") != "available":
        errors.append("publication:license-unavailable")
    elif license_snapshot.get("redistribution_conclusion") not in policy["allowed_redistribution_conclusions"]:
        errors.append("publication:license-disallows-projection")
    execution = document["execution"]
    if execution.get("availability") != "available":
        errors.append("publication:execution-unavailable")
    elif execution.get("host_metadata"):
        errors.append("publication:host-metadata-present")

    secret_patterns = [re.compile(pattern) for pattern in policy["secret_value_patterns"]]
    pii_patterns = [re.compile(pattern) for pattern in policy["pii_value_patterns"]]
    for key, value in _walk(document):
        if isinstance(value, str):
            if any(pattern.search(value) for pattern in secret_patterns):
                errors.append("publication:secret-pattern")
            if any(pattern.search(value) for pattern in pii_patterns):
                errors.append("publication:pii-pattern")
    if execution.get("availability") == "available":
        unsafe_command = re.compile(r"[;&|`$<>]|^/|^[A-Za-z]:[\\/]|^file:")
        if any(unsafe_command.search(token) for token in execution["command"]):
            errors.append("publication:unsafe-command")

    for artifact in document["artifacts"]:
        if not artifact["publishable"]:
            continue
        if not artifact["public_path"] or not isinstance(artifact["content_hash"], str):
            errors.append(f"publication:{artifact['artifact_id']}:missing-public-evidence")
    return errors


def project_public_manifest(document: Mapping[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    """Build a public document from an explicit allowlist; never mutate the input."""

    validate_canonical(document)
    policy = json.loads(PROJECTION_POLICY_PATH.read_text(encoding="utf-8"))
    errors = _projection_errors(document, policy)
    if errors:
        raise ManifestValidationError(errors)
    artifacts = [artifact for artifact in document["artifacts"] if artifact["publishable"]]
    license_snapshot = document["license_snapshot"]
    projected = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "canonical_manifest_hash": _hash(document),
        "projection_policy_id": PROJECTION_POLICY_ID,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "redaction_summary": {
            "omitted_fields": 9,
            "omitted_artifacts": len(document["artifacts"]) - len(artifacts),
        },
        "run_id": document["run_id"],
        "cell_id": document["cell_id"],
        "thread": document["thread"],
        "started_at": document["started_at"],
        "ended_at": document["ended_at"],
        "status": document["status"],
        "pipeline": {key: document["pipeline"][key] for key in ("id", "variant", "repository", "commit_sha")},
        "lineage": _safe_lineage(document["lineage"]),
        "completion": {
            "contract_id": document["completion"]["contract_id"],
            "derived_value": document["completion"]["derived_value"],
        },
        "artifacts": [
            {
                "artifact_id": item["artifact_id"], "role": item["role"], "public_path": item["public_path"],
                "content_hash": item["content_hash"], "media_type": item["media_type"],
                "completion": item["completion"], "lineage": _safe_lineage(item["lineage"]),
            }
            for item in artifacts
        ],
        "claims": document["claims"],
        "reviews": [
            {
                "review_id": item["review_id"], "subject_ref": item["subject_ref"], "rubric_id": item["rubric_id"],
                "evaluator_type": item["evaluator"]["type"], "result": item["result"],
                "evidence_refs": item["evidence_refs"], "reviewed_at": item["reviewed_at"],
            }
            for item in document["reviews"]
        ],
        "cost": {key: document["budget"][key] for key in ("measured_usd", "estimated_usd", "coverage")},
        "license": {
            "declared_spdx": license_snapshot["declared_spdx"],
            "redistribution_conclusion": license_snapshot["redistribution_conclusion"],
            "license_text_hash": license_snapshot["license_text_hash"],
        },
    }
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
