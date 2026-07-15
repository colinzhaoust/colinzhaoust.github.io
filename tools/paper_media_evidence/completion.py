"""Machine-derived pipeline completion."""

from __future__ import annotations

from typing import Any, Mapping


def _artifact_valid(artifact: Mapping[str, Any], validations: Mapping[str, Mapping[str, Any]]) -> bool:
    if artifact.get("completion") != "full" or not isinstance(artifact.get("content_hash"), str):
        return False
    refs = artifact.get("validation_refs", [])
    return bool(refs) and all(
        validations.get(ref, {}).get("result") == "pass"
        and validations.get(ref, {}).get("subject_ref") == artifact.get("artifact_id")
        for ref in refs
    )


def derive_completion(manifest: Mapping[str, Any]) -> str:
    """Derive completion from the versioned contract, stage state, and artifacts."""

    origin = manifest.get("lineage", {}).get("implementation_origin")
    contract = manifest.get("completion_contract", {})
    if origin in contract.get("placeholder_origins", []):
        return "placeholder"

    stages = {stage.get("id"): stage for stage in manifest.get("stages", [])}
    artifacts = manifest.get("artifacts", [])
    validations = {item.get("validation_id"): item for item in manifest.get("validations", [])}

    required_stages = contract.get("required_stages", [])
    required_roles = contract.get("required_deliverable_roles", [])
    successful_states = set(contract.get("successful_stage_states", ["succeeded"]))
    stages_full = bool(required_stages) and all(stages.get(stage_id, {}).get("status") in successful_states for stage_id in required_stages)
    artifacts_full = all(
        any(item.get("role") == role and _artifact_valid(item, validations) for item in artifacts)
        for role in required_roles
    )
    status = manifest.get("status")
    if status in contract.get("terminal_run_statuses", {}).get("full_allowed", []) and stages_full and artifacts_full:
        return "full"

    if status == "failed":
        return "failed"

    smoke_stages = contract.get("smoke_stages", [])
    if smoke_stages and all(stages.get(stage_id, {}).get("status") in successful_states for stage_id in smoke_stages):
        return "smoke"

    has_useful_output = any(
        isinstance(item.get("content_hash"), str) and item.get("completion") in {"full", "partial", "smoke"}
        for item in artifacts
    )
    has_progress = any(stage.get("status") in {"succeeded", "running"} for stage in stages.values())
    if has_useful_output:
        return "partial"

    if status == "running" or has_progress:
        return "partial"
    return "failed"
