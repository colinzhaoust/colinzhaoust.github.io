"""Non-destructive migration for the legacy baseline coverage aggregate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .completion import derive_completion
from .constants import CANONICAL_SCHEMA_VERSION, COMPLETION_CONTRACT_VERSION

MIGRATOR_VERSION = "legacy-baseline-coverage/0.1.0"
EMPTY_HASH = "sha256:" + hashlib.sha256(b"").hexdigest()
TOPIC_FAMILY = {"attention": "transformer_attention", "transformers": "transformer_attention"}


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()


def _unavailable(reason: str) -> dict[str, str]:
    return {"availability": "unavailable", "reason": reason}


def _hash_file(path: Path | None) -> str | dict[str, str]:
    if path is None or not path.is_file():
        return _unavailable("legacy artifact content was not available to the migrator")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def migrate_legacy_baseline(
    legacy: Mapping[str, Any], *, source_path: str, source_hash: str, artifact_root: Path | None = None
) -> list[dict[str, Any]]:
    """Return deterministic private manifests; never modify the legacy input."""

    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for item in legacy.get("items", []):
        family = TOPIC_FAMILY.get(item["paper_id"], item["paper_id"])
        groups.setdefault((item["adapter"], family), []).append(item)

    migrated: list[dict[str, Any]] = []
    for adapter, family in sorted(groups):
        items = sorted(groups[(adapter, family)], key=lambda item: item["paper_id"])
        synthetic = all(item.get("provider") == "mock" for item in items)
        origin = "synthetic_fixture" if synthetic else "project_reimplementation"
        completion_value = "placeholder" if synthetic else "partial"
        variant = "legacy_synthetic_preview" if synthetic else "legacy_method_reproduction"
        contract_id = f"{variant}/0.1.0"
        started_at = legacy["started_at"]
        ended_at = max((item.get("rendered_at") or legacy.get("finished_at") for item in items))
        run_id = f"legacy.{_slug(adapter)}.{_slug(family)}"
        adapter_ref = MIGRATOR_VERSION
        lineage = {
            "implementation_origin": origin,
            "input_contract_mode": "adapted",
            "adapter_ref": adapter_ref,
            "patch_level": "none",
            "patchset_hash": EMPTY_HASH,
            "derivation_stage": "rendered",
            "parent_artifact_refs": [],
        }
        artifacts = []
        for item in items:
            artifact_id = f"artifact:{_slug(adapter)}:{_slug(item['paper_id'])}:video"
            legacy_path = Path(item["video"])
            resolved = artifact_root / legacy_path if artifact_root is not None else None
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "role": "rendered_video",
                    "private_path": item["video"],
                    "public_path": None,
                    "content_hash": _hash_file(resolved),
                    "media_type": "video/mp4",
                    "completion": completion_value,
                    "validation_refs": [],
                    "lineage": dict(lineage),
                    "publishable": False,
                }
            )
        contract = {
            "schema_version": COMPLETION_CONTRACT_VERSION,
            "contract_id": contract_id,
            "required_stages": ["legacy_render"],
            "smoke_stages": [],
            "required_deliverable_roles": ["rendered_video"],
            "placeholder_origins": ["synthetic_fixture"],
        }
        manifest: dict[str, Any] = {
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "visibility": "private_canonical",
            "run_id": run_id,
            "cell_id": f"legacy-baseline:{family}:{adapter}:{variant}:r1",
            "experiment_config_id": "legacy-baseline-coverage/2026-07-08",
            "thread": "real_video_pipelines",
            "started_at": started_at,
            "ended_at": ended_at,
            "status": "migration_pending",
            "pipeline": {
                "id": adapter,
                "variant": variant,
                "repository": _unavailable("legacy manifest did not pin a pipeline repository"),
                "commit_sha": _unavailable("legacy manifest did not pin a pipeline revision"),
                "completion_contract_id": contract_id,
            },
            "completion_contract": contract,
            "lineage": lineage,
            "input": {
                "canonical_topic_family": family,
                "granularity": "topic",
                "paper_snapshot": _unavailable("legacy manifest did not preserve a paper snapshot"),
                "code_snapshot": _unavailable("legacy manifest did not preserve a code snapshot"),
            },
            "license_snapshot": _unavailable("legacy manifest did not preserve license evidence"),
            "execution": _unavailable("legacy manifest did not preserve exact command and configuration evidence"),
            "budget": {
                "policy_id": "legacy-budget-unavailable/0.1.0",
                "shared_setup_allocation": "not_applicable",
                "rate_card": _unavailable("legacy manifest did not preserve a rate-card snapshot"),
                "reservations": [],
                "paid_stage_gate": {"next_stage_id": None, "projected_next_stage_usd": None, "decision": "not_applicable"},
                "measured_usd": None,
                "estimated_usd": None,
                "coverage": [],
            },
            "stages": [{"id": "legacy_render", "status": "succeeded", "started_at": started_at, "ended_at": ended_at, "evidence_refs": [item["artifact_id"] for item in artifacts]}],
            "completion": {"contract_id": contract_id, "derived_value": completion_value, "derived_at": ended_at},
            "artifacts": artifacts,
            "validations": [],
            "claims": [
                {"claim_id": f"claim:{_slug(adapter)}:{_slug(item['paper_id'])}:legacy-record", "label": "OBSERVED", "statement": "The legacy manifest recorded this artifact; immutable evidence remains unavailable.", "evidence_refs": [artifact["artifact_id"]], "observed_at": item.get("rendered_at") or ended_at}
                for item, artifact in zip(items, artifacts)
            ],
            "reviews": [],
            "repair_events": [],
            "graph": {"nodes": [], "edges": [], "migrations": []},
            "migration": {
                "source_path": source_path,
                "source_hash": source_hash,
                "migrator_version": MIGRATOR_VERSION,
                "warnings": [
                    "publication is blocked until source, license, execution, artifact path, and hash evidence is enriched",
                    "legacy null API cost was preserved as unknown, not zero",
                ],
            },
        }
        manifest["completion"]["derived_value"] = derive_completion(manifest)
        migrated.append(manifest)
    return migrated


def migrate_legacy_file(path: Path, *, artifact_root: Path | None = None) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    return migrate_legacy_baseline(
        json.loads(raw),
        source_path=path.as_posix(),
        source_hash="sha256:" + hashlib.sha256(raw).hexdigest(),
        artifact_root=artifact_root,
    )
