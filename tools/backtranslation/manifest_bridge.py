"""q-6 bridge into the q-5 canonical evidence and publication APIs.

The q-5 package remains the only schema owner.  This module builds q-6 records,
then delegates completion derivation, canonical validation, canonical hashing,
public projection, and public validation to q-5.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.paper_media_evidence import (
    derive_completion,
    project_public_manifest,
    validate_canonical,
    validate_public,
)

from .conditions import ConditionTrace, GENERIC_PROMPT, load_protocol
from .registry import load_registry, sha256_file


EMPTY_SHA256 = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MANIM_LICENSE_REF = "experiments/backtranslation/v1/licenses/manim-LICENSE.txt"
MANIM_COMMUNITY_LICENSE_REF = "experiments/backtranslation/v1/licenses/manim-LICENSE.community.txt"
ROOT = Path(__file__).resolve().parents[2]


class ManifestBridgeError(ValueError):
    """The q-6 trace cannot be represented without weakening q-5 evidence."""


@dataclass(frozen=True)
class HumanConditionInput:
    pairing_id: str
    case_id: str
    reference_video: Path
    implementation_origin: str = "synthetic_fixture"


@dataclass(frozen=True)
class CrossRunParent:
    run_id: str
    artifact_id: str
    relation: str
    content_hash: str
    canonical_manifest_hash: str
    evidence_ref: str

    def parent_ref(self) -> dict[str, Any]:
        return {
            "scope": "external",
            "run_id": self.run_id,
            "artifact_id": self.artifact_id,
            "relation": self.relation,
            "content_hash": self.content_hash,
            "canonical_manifest_hash": self.canonical_manifest_hash,
        }

    def evidence(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "canonical_manifest_hash": self.canonical_manifest_hash,
            "evidence_ref": self.evidence_ref,
            "source_visibility": "public",
        }


@dataclass(frozen=True)
class CanonicalManifestResult:
    run_id: str
    pairing_id: str
    condition: str
    manifest_path: Path
    public_manifest_path: Path
    public_manifest_ref: str
    canonical_manifest_hash: str
    artifact_ids: Mapping[str, str]
    canonical_manifest: Mapping[str, Any]
    public_manifest: Mapping[str, Any]


@dataclass(frozen=True)
class PairingManifestResult:
    pairing_id: str
    human: CanonicalManifestResult
    one_shot: CanonicalManifestResult
    self_refined: CanonicalManifestResult


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _prefixed_hash(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _lineage(
    *, origin: str, derivation: str, parents: Sequence[Mapping[str, Any]] = (), adapted: bool = False
) -> dict[str, Any]:
    return {
        "implementation_origin": origin,
        "input_contract_mode": "adapted" if adapted else "native",
        "adapter_ref": "tools/backtranslation/conditions.py" if adapted else None,
        "patch_level": "method_change" if derivation == "self_refined" else ("config_only" if adapted else "none"),
        "patchset_hash": EMPTY_SHA256,
        "derivation_stage": derivation,
        "parent_artifact_refs": [dict(item) for item in parents],
    }


class PaperMediaEvidenceBridge:
    """Concrete q-6 consumer of the accepted q-5 evidence contract."""

    def __init__(
        self,
        *,
        registry_path: Path,
        protocol_path: Path,
        pipeline_repository: str,
        pipeline_commit: str,
        generated_at: str = "2026-07-15T18:00:00Z",
    ) -> None:
        self.registry_path = registry_path
        self.protocol_path = protocol_path
        self.registry = load_registry(registry_path)
        self.protocol = load_protocol(protocol_path)
        self.pipeline_repository = pipeline_repository
        self.pipeline_commit = pipeline_commit
        self.generated_at = generated_at
        self.protocol_hash = _prefixed_hash(sha256_file(protocol_path))
        self.registry_hash = _prefixed_hash(sha256_file(registry_path))
        self.protocol_ref = self._repo_ref(protocol_path)
        self.registry_ref = self._repo_ref(registry_path)

    def emit_pairing(
        self,
        *,
        human: HumanConditionInput,
        one_shot_trace: ConditionTrace,
        one_shot_root: Path,
        self_refined_trace: ConditionTrace,
        self_refined_root: Path,
        artifact_root: Path,
        dry_run: bool,
    ) -> PairingManifestResult:
        self._assert_pairing(human, one_shot_trace, self_refined_trace, dry_run=dry_run)
        human_result = self.emit_human_run(human=human, artifact_root=artifact_root)
        human_parent = CrossRunParent(
            run_id=human_result.run_id,
            artifact_id=human_result.artifact_ids["reference_video"],
            relation="derived_from",
            content_hash=_prefixed_hash(sha256_file(human.reference_video)),
            canonical_manifest_hash=human_result.canonical_manifest_hash,
            evidence_ref=human_result.public_manifest_ref,
        )
        one_result = self.emit_backtranslation_run(
            trace=one_shot_trace,
            condition_root=one_shot_root,
            artifact_root=artifact_root,
            cross_run_parents=[human_parent],
            dry_run=dry_run,
        )
        one_code_id = one_result.artifact_ids.get("final_code")
        if not one_code_id or not one_shot_trace.final_code_hash:
            raise ManifestBridgeError("one-shot run has no exact generated-code parent for self-refinement")
        one_parent = CrossRunParent(
            run_id=one_result.run_id,
            artifact_id=one_code_id,
            relation="refined_from",
            content_hash=_prefixed_hash(one_shot_trace.final_code_hash),
            canonical_manifest_hash=one_result.canonical_manifest_hash,
            evidence_ref=one_result.public_manifest_ref,
        )
        self_result = self.emit_backtranslation_run(
            trace=self_refined_trace,
            condition_root=self_refined_root,
            artifact_root=artifact_root,
            cross_run_parents=[one_parent],
            dry_run=dry_run,
        )
        return PairingManifestResult(human.pairing_id, human_result, one_result, self_result)

    def _assert_pairing(
        self,
        human: HumanConditionInput,
        one: ConditionTrace,
        refined: ConditionTrace,
        *,
        dry_run: bool,
    ) -> None:
        if one.condition != "one_shot" or refined.condition != "self_refined":
            raise ManifestBridgeError("pairing requires one_shot and self_refined traces")
        if {human.pairing_id, one.pairing_id, refined.pairing_id} != {human.pairing_id}:
            raise ManifestBridgeError("pairing_id mismatch across Human/One-shot/Self-refined runs")
        if {human.case_id, one.case_id, refined.case_id} != {human.case_id}:
            raise ManifestBridgeError("case_id mismatch across paired runs")
        reference_hash = sha256_file(human.reference_video)
        if one.reference_hash != reference_hash or refined.reference_hash != reference_hash:
            raise ManifestBridgeError("paired traces do not use the exact Human reference video")
        if one.provider_calls != 1 or len(one.rounds) > 1:
            raise ManifestBridgeError("one-shot must contain exactly one generation call")
        if refined.provider_calls > 3 or len([item for item in refined.rounds if item.round_index > 0]) > 3:
            raise ManifestBridgeError("self-refinement exceeds the three-revision protocol maximum")
        if not refined.rounds or refined.rounds[0].round_index != 0:
            raise ManifestBridgeError("self-refinement is missing exact one-shot round zero")
        if (
            not one.final_code_hash
            or refined.initial_one_shot_code_hash != one.final_code_hash
            or refined.rounds[0].code_hash != one.final_code_hash
        ):
            raise ManifestBridgeError("self-refinement round zero is not the exact one-shot code hash")
        if dry_run and (one.billable_provider_calls != 0 or refined.billable_provider_calls != 0):
            raise ManifestBridgeError("offline dry-run recorded a billable provider call")

    def emit_human_run(self, *, human: HumanConditionInput, artifact_root: Path) -> CanonicalManifestResult:
        if not human.reference_video.is_file():
            raise ManifestBridgeError("Human reference video is missing")
        condition = "human"
        run_id = self._run_id(human.pairing_id, condition)
        artifact_id = f"artifact:{human.pairing_id}:{condition}:reference-video"
        content_hash = _prefixed_hash(sha256_file(human.reference_video))
        artifact = self._artifact(
            artifact_id=artifact_id,
            role="rendered_video",
            media_type="video/mp4",
            content_hash=content_hash,
            condition=condition,
            filename="reference.mp4",
            origin=human.implementation_origin,
            derivation="rendered",
            parents=(),
        )
        manifest = self._base_manifest(
            run_id=run_id,
            pairing_id=human.pairing_id,
            case_id=human.case_id,
            condition=condition,
            status="completed",
            origin=human.implementation_origin,
            derivation="rendered",
            run_parents=(),
            external_lineage=(),
            artifacts=[artifact],
            validations=[self._validation(artifact_id, condition)],
            claims=[
                self._claim(
                    "claim:human:attempt-denominator",
                    "Human reference denominator: 1 retained reference render, 0 failed attempts, 0 provider calls.",
                    [artifact_id],
                )
            ],
            repair_events=[],
        )
        return self._validate_project_write(
            manifest, artifact_root, condition, {"reference_video": artifact_id}
        )

    def emit_backtranslation_run(
        self,
        *,
        trace: ConditionTrace,
        condition_root: Path,
        artifact_root: Path,
        cross_run_parents: Sequence[CrossRunParent],
        dry_run: bool,
    ) -> CanonicalManifestResult:
        if trace.condition not in {"one_shot", "self_refined"}:
            raise ManifestBridgeError("unsupported generated condition")
        if len(cross_run_parents) != 1:
            raise ManifestBridgeError("generated conditions require exactly one cross-run parent")
        parent = cross_run_parents[0]
        expected_relation = "derived_from" if trace.condition == "one_shot" else "refined_from"
        if parent.relation != expected_relation:
            raise ManifestBridgeError(f"{trace.condition} requires {expected_relation} external lineage")
        expected_parent_hash = trace.reference_hash if trace.condition == "one_shot" else trace.initial_one_shot_code_hash
        if not expected_parent_hash or parent.content_hash != _prefixed_hash(expected_parent_hash):
            raise ManifestBridgeError("cross-run parent content hash does not match the exact condition input")
        if dry_run and trace.billable_provider_calls != 0:
            raise ManifestBridgeError("offline dry-run recorded a billable provider call")
        if trace.condition == "one_shot" and (trace.provider_calls != 1 or len(trace.rounds) > 1):
            raise ManifestBridgeError("one-shot call-count contract was violated")
        if trace.condition == "self_refined" and (
            trace.provider_calls > 3 or len([item for item in trace.rounds if item.round_index > 0]) > 3
        ):
            raise ManifestBridgeError("self-refinement exceeds the three-revision maximum")

        artifacts, validations, artifact_ids, repairs = self._trace_evidence(
            trace=trace,
            condition_root=condition_root,
            external_parent=parent,
            origin="synthetic_fixture" if dry_run else "project_native",
        )
        attempts, failures = self._attempt_denominator(trace)
        trace_artifact = artifact_ids["trace"]
        claims = [
            self._claim(
                f"claim:{trace.condition}:attempt-denominator",
                f"Attempt denominator: {attempts} retained candidate attempts; {failures} failed attempts.",
                [trace_artifact],
            ),
            self._claim(
                f"claim:{trace.condition}:provider-calls",
                f"Recorded adapter calls: {trace.provider_calls}; billable provider calls: {trace.billable_provider_calls}.",
                [trace_artifact],
            ),
        ]
        origin = "synthetic_fixture" if dry_run else "project_native"
        status = "stopped" if trace.status == "partial" else trace.status
        manifest = self._base_manifest(
            run_id=self._run_id(trace.pairing_id, trace.condition),
            pairing_id=trace.pairing_id,
            case_id=trace.case_id,
            condition=trace.condition,
            status=status,
            origin=origin,
            derivation=trace.condition,
            run_parents=[parent.parent_ref()],
            external_lineage=[parent.evidence()],
            artifacts=artifacts,
            validations=validations,
            claims=claims,
            repair_events=repairs,
        )
        return self._validate_project_write(manifest, artifact_root, trace.condition, artifact_ids)

    def _trace_evidence(
        self, *, trace: ConditionTrace, condition_root: Path, external_parent: CrossRunParent, origin: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
        trace_path = condition_root / "condition_trace.json"
        if not trace_path.is_file():
            raise ManifestBridgeError("condition_trace.json is missing")
        artifacts: list[dict[str, Any]] = []
        validations: list[dict[str, Any]] = []
        repairs: list[dict[str, Any]] = []
        ids: dict[str, str] = {}
        previous_code_id: str | None = None
        for item in trace.rounds:
            code_id: str | None = None
            if item.code_path:
                code_path = condition_root / item.code_path
                self._assert_file_hash(code_path, item.code_hash)
                code_id = f"artifact:{trace.pairing_id}:{trace.condition}:round:{item.round_index}:code"
                if item.round_index == 0:
                    code_parents = [external_parent.parent_ref()]
                elif previous_code_id:
                    previous = next(value for value in artifacts if value["artifact_id"] == previous_code_id)
                    code_parents = [self._local_parent(trace, previous, "refined_from")]
                else:
                    raise ManifestBridgeError("revision code has no retained parent code")
                artifacts.append(self._artifact(
                    artifact_id=code_id, role="generated_code", media_type="text/x-python",
                    content_hash=_prefixed_hash(item.code_hash or ""), condition=trace.condition,
                    filename=f"round-{item.round_index}-code.py", origin=origin,
                    derivation=trace.condition, parents=code_parents,
                ))
                validations.append(self._validation(code_id, trace.condition))
                if previous_code_id and item.round_index > 0:
                    repairs.append({
                        "event_id": f"repair:{trace.condition}:round:{item.round_index}",
                        "policy_id": trace.feedback_policy_id,
                        "parent_artifact_ref": previous_code_id,
                        "child_artifact_ref": code_id,
                        "iteration": item.round_index,
                        "created_at": self.generated_at,
                        "publishable": True,
                    })
                previous_code_id = code_id
                ids["final_code"] = code_id

            render_id: str | None = None
            if item.render_path:
                render_path = condition_root / item.render_path
                self._assert_file_hash(render_path, item.render_hash)
                render_id = f"artifact:{trace.pairing_id}:{trace.condition}:round:{item.round_index}:render"
                if not code_id:
                    raise ManifestBridgeError("render has no exact code parent")
                code_artifact = next(value for value in artifacts if value["artifact_id"] == code_id)
                role = "rendered_video" if item.render_hash == trace.final_render_hash else "candidate_video"
                artifacts.append(self._artifact(
                    artifact_id=render_id, role=role, media_type="video/mp4",
                    content_hash=_prefixed_hash(item.render_hash or ""), condition=trace.condition,
                    filename=f"round-{item.round_index}-render.mp4", origin=origin,
                    derivation="rendered", parents=[self._local_parent(trace, code_artifact, "rendered_from")],
                ))
                validations.append(self._validation(render_id, trace.condition))
                if role == "rendered_video":
                    ids["final_render"] = render_id

            if item.feedback_path:
                feedback_path = condition_root / item.feedback_path
                self._assert_file_hash(feedback_path, item.feedback_hash)
                feedback_id = f"artifact:{trace.pairing_id}:{trace.condition}:round:{item.round_index}:feedback"
                parent_id = render_id or code_id
                if not parent_id:
                    raise ManifestBridgeError("feedback has no retained render/code parent")
                parent_artifact = next(value for value in artifacts if value["artifact_id"] == parent_id)
                artifacts.append(self._artifact(
                    artifact_id=feedback_id, role="evaluation_feedback", media_type="application/json",
                    content_hash=_prefixed_hash(item.feedback_hash or ""), condition=trace.condition,
                    filename=f"round-{item.round_index}-feedback.json", origin=origin,
                    derivation=trace.condition, parents=[self._local_parent(trace, parent_artifact, "derived_from")],
                ))
                validations.append(self._validation(feedback_id, trace.condition))

        trace_id = f"artifact:{trace.pairing_id}:{trace.condition}:condition-trace"
        trace_parents: list[dict[str, Any]] = []
        if previous_code_id:
            previous = next(value for value in artifacts if value["artifact_id"] == previous_code_id)
            trace_parents = [self._local_parent(trace, previous, "derived_from")]
        artifacts.append(self._artifact(
            artifact_id=trace_id, role="attempt_ledger", media_type="application/json",
            content_hash=_prefixed_hash(sha256_file(trace_path)), condition=trace.condition,
            filename="condition-trace.json", origin=origin, derivation=trace.condition, parents=trace_parents,
        ))
        validations.append(self._validation(trace_id, trace.condition))
        ids["trace"] = trace_id
        return artifacts, validations, ids, repairs

    def _assert_file_hash(self, path: Path, expected: str | None) -> None:
        if not expected or not path.is_file() or sha256_file(path) != expected:
            raise ManifestBridgeError("retained artifact is missing or does not match its trace hash")

    def _local_parent(self, trace: ConditionTrace, artifact: Mapping[str, Any], relation: str) -> dict[str, Any]:
        return {
            "scope": "local", "run_id": self._run_id(trace.pairing_id, trace.condition),
            "artifact_id": artifact["artifact_id"], "relation": relation,
            "content_hash": artifact["content_hash"], "canonical_manifest_hash": None,
        }

    def _attempt_denominator(self, trace: ConditionTrace) -> tuple[int, int]:
        initial = 1 if trace.condition == "self_refined" else 0
        attempts = max(len(trace.rounds), trace.provider_calls + initial)
        round_failures = sum(item.failure_code is not None for item in trace.rounds)
        unmaterialized = max(0, attempts - len(trace.rounds))
        return attempts, round_failures + unmaterialized

    def _artifact(
        self, *, artifact_id: str, role: str, media_type: str, content_hash: str,
        condition: str, filename: str, origin: str, derivation: str,
        parents: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        validation_id = f"validation:{artifact_id.removeprefix('artifact:')}"
        completion = "placeholder" if origin == "synthetic_fixture" else "full"
        return {
            "artifact_id": artifact_id, "role": role, "private_path": None,
            "public_path": f"progress_site/assets/backtranslation/{artifact_id.replace(':', '/')}/{filename}",
            "content_hash": content_hash, "media_type": media_type, "completion": completion,
            "validation_refs": [validation_id],
            "lineage": _lineage(origin=origin, derivation=derivation, parents=parents, adapted=condition != "human"),
            "publishable": True,
        }

    def _validation(self, artifact_id: str, condition: str) -> dict[str, Any]:
        suffix = artifact_id.removeprefix("artifact:")
        return {
            "validation_id": f"validation:{suffix}", "validator_id": "q6-artifact-hash/1.0.0",
            "subject_ref": artifact_id, "result": "pass",
            "evidence_ref": f"evidence/backtranslation/{condition}/{suffix}.json",
            "validated_at": self.generated_at, "publishable": True,
        }

    def _claim(self, claim_id: str, statement: str, evidence_refs: Sequence[str]) -> dict[str, Any]:
        return {
            "claim_id": claim_id, "label": "MEASURED", "statement": statement,
            "evidence_refs": list(evidence_refs), "observed_at": self.generated_at, "publishable": True,
        }

    def _sources_and_licenses(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        upstream = self.registry["upstream"]
        repository_hash = _sha256_text(f"{upstream['repository']}\n{upstream['commit_sha']}\n")
        sources = [
            {
                "availability": "available", "source_id": "source:manim-repository", "source_type": "repository",
                "source_url": upstream["repository"], "revision": upstream["commit_sha"],
                "retrieved_at": upstream["retrieved_at"], "content_hash": repository_hash,
                "source_visibility": "public", "publication_decision": "allowed",
            },
            {
                "availability": "available", "source_id": "source:manim-example-gallery", "source_type": "example_gallery",
                "source_url": upstream["source_url"], "revision": upstream["source_blob_git_sha1"],
                "retrieved_at": upstream["retrieved_at"], "content_hash": _prefixed_hash(upstream["source_sha256"]),
                "source_visibility": "public", "publication_decision": "allowed",
            },
        ]
        primary_license = next(item for item in self.registry["license_snapshot"]["files"] if item["path"] == "LICENSE")
        constraints = ["Preserve the upstream LICENSE and LICENSE.community notices with redistributed source."]
        licenses = []
        for source in sources:
            licenses.append({
                "availability": "available", "item_id": f"license:{source['source_id'].removeprefix('source:')}",
                "source_ref": source["source_id"], "resource_type": source["source_type"],
                "source_url": source["source_url"], "source_revision": source["revision"],
                "retrieved_at": upstream["retrieved_at"], "content_hash": source["content_hash"],
                "declared_spdx": self.registry["license_snapshot"]["declared_spdx"],
                "license_text_ref": MANIM_LICENSE_REF, "license_text_hash": _prefixed_hash(primary_license["sha256"]),
                "constraints": constraints, "exceptions": [],
                "reviewer": {"type": "automatic", "id": "q6-pinned-license/1.0.0"},
                "redistribution_conclusion": self.registry["license_snapshot"]["redistribution_conclusion"],
                "evidence_refs": [MANIM_LICENSE_REF, MANIM_COMMUNITY_LICENSE_REF, self.registry_ref],
                "source_visibility": "public", "publication_decision": "allowed",
            })
        return sources, licenses

    def _base_manifest(
        self, *, run_id: str, pairing_id: str, case_id: str, condition: str, status: str,
        origin: str, derivation: str, run_parents: Sequence[Mapping[str, Any]],
        external_lineage: Sequence[Mapping[str, Any]], artifacts: list[dict[str, Any]],
        validations: list[dict[str, Any]], claims: list[dict[str, Any]],
        repair_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sources, licenses = self._sources_and_licenses()
        cell_id = f"backtranslation:{pairing_id}:{condition}"
        contract_id = "backtranslation-video/0.1.0"
        terminal = status in {"completed", "failed", "stopped"}
        artifact_refs = [item["artifact_id"] for item in artifacts]
        validation_refs = [item["validation_id"] for item in validations]
        execute_status = "failed" if status == "failed" else "succeeded"
        validate_status = "failed" if status in {"failed", "stopped"} else "succeeded"
        pipeline_repository = self.registry["upstream"]["repository"] if condition == "human" else self.pipeline_repository
        pipeline_commit = self.registry["upstream"]["commit_sha"] if condition == "human" else self.pipeline_commit
        adapted = condition != "human"
        manifest: dict[str, Any] = {
            "schema_version": "paper-media-manifest/0.1.0", "visibility": "private_canonical",
            "run_id": run_id, "pairing_id": pairing_id, "cell_id": cell_id,
            "experiment_config_id": self.protocol["experiment_id"], "thread": "backtranslation",
            "started_at": self.generated_at, "ended_at": self.generated_at if terminal else None, "status": status,
            "pipeline": {
                "id": "manim-gallery-reference" if condition == "human" else "q6-backtranslation-harness",
                "variant": condition, "repository": pipeline_repository, "repository_visibility": "public",
                "commit_sha": pipeline_commit, "completion_contract_id": contract_id,
            },
            "completion_contract": {
                "schema_version": "paper-media-completion-contract/0.1.0", "contract_id": contract_id,
                "rule_version": "paper-media-completion-rules/0.1.0",
                "required_stages": ["prepare", "execute", "validate"], "successful_stage_states": ["succeeded"],
                "smoke_stages": ["prepare"], "required_deliverable_roles": ["rendered_video"],
                "required_artifact_validation_results": ["pass"], "placeholder_origins": ["synthetic_fixture"],
                "terminal_run_statuses": {
                    "full_allowed": ["completed"],
                    "full_forbidden": ["running", "stopped", "failed", "migration_pending"],
                },
            },
            "lineage": _lineage(origin=origin, derivation=derivation, parents=run_parents, adapted=adapted),
            "external_lineage": [dict(item) for item in external_lineage],
            "input": {"canonical_topic_family": case_id, "granularity": "video", "source_snapshots": sources},
            "condition": {
                "condition_id": f"backtranslation:{condition}:r1",
                "model_policy": "not_applicable" if condition == "human" else "local", "replicate": 1,
            },
            "publication": {
                "source_visibility": "public", "decision": "allowed",
                "reason": "Pinned public Manim sources, complete MIT notice evidence, and synthetic dry-run outputs are approved.",
                "policy_id": "paper-media-public-projection/0.1.0",
            },
            "review_policy": {
                "policy_id": "q6-review-policy/1.0.0", "graph_confirmation_rubric_ids": ["graph-match/1.0.0"],
                "graph_reviewer_types": ["automatic"],
            },
            "license_ledger": licenses,
            "execution": {
                "availability": "available", "command": ["python", "tools/run_backtranslation.py", "dry-run"],
                "config_ref": self.protocol_ref, "config_hash": self.protocol_hash,
                "prompt_bundle_hash": _sha256_text(GENERIC_PROMPT if adapted else "human-reference-preparation"),
                "tool_policy_hash": self.protocol_hash, "random_seed": None, "seed_policy": "not_supported",
                "model_versions": [{
                    "role": "condition", "model_id": "q6/recording-mock" if adapted else "q6/reference-preparation",
                    "immutable_version": self.protocol_hash,
                }],
                "dependency_lock_ref": self.protocol_ref, "dependency_lock_hash": self.protocol_hash,
                "container_digest": _sha256_text("q6-offline-fixture:no-container"),
                "renderer_versions": {"manim_source": "0.20.1", "ffmpeg": "fixture-runtime"},
                "hardware": {"platform": "offline-fixture", "cpu": "not-recorded", "accelerator": "none"},
                "environment": {"evidence_ref": self.registry_ref, "evidence_hash": self.registry_hash,
                                "variables_hash": EMPTY_SHA256},
                "host_metadata": {},
            },
            "budget": {
                "experiment_id": self.protocol["experiment_id"], "cell_id": cell_id,
                "ledger_id": f"ledger:{pairing_id}:{condition}", "policy_id": "q6-zero-spend",
                "policy_version": "1.0.0", "currency": "USD", "experiment_limit_usd": 1,
                "cell_limit_usd": 1, "experiment_spend_before_usd": 0, "cell_spend_before_usd": 0,
                "shared_setup_allocation": "not_applicable",
                "rate_card": {"availability": "unavailable", "reason": "Offline fixture has no paid stages."},
                "reservations": [],
                "paid_stage_gate": {"next_stage_id": None, "reservation_id": None,
                                    "projected_next_stage_usd": None, "decision": "not_applicable"},
                "measured_usd": 0, "estimated_usd": 0, "coverage": ["local_compute"],
            },
            "stages": [
                {"id": "prepare", "status": "succeeded", "billing_class": "free", "started_at": self.generated_at,
                 "ended_at": self.generated_at, "evidence_refs": [], "stop_reason": None},
                {"id": "execute", "status": execute_status, "billing_class": "free", "started_at": self.generated_at,
                 "ended_at": self.generated_at, "evidence_refs": artifact_refs,
                 "stop_reason": "condition execution failed" if execute_status == "failed" else None},
                {"id": "validate", "status": validate_status, "billing_class": "free", "started_at": self.generated_at,
                 "ended_at": self.generated_at, "evidence_refs": validation_refs,
                 "stop_reason": "condition threshold was not satisfied" if validate_status == "failed" else None},
            ],
            "completion": {"contract_id": contract_id, "rule_version": "paper-media-completion-rules/0.1.0",
                           "derived_value": "failed", "derived_at": self.generated_at},
            "artifacts": artifacts, "validations": validations, "claims": claims, "reviews": [],
            "repair_events": repair_events, "graph": {"nodes": [], "edges": [], "migrations": []},
        }
        manifest["completion"]["derived_value"] = derive_completion(manifest)
        return manifest

    def _validate_project_write(
        self, manifest: dict[str, Any], artifact_root: Path, condition: str, artifact_ids: Mapping[str, str]
    ) -> CanonicalManifestResult:
        validate_canonical(manifest)
        public = project_public_manifest(manifest, generated_at=self.generated_at)
        validate_public(public)
        manifest_path = artifact_root / "manifests" / f"{condition}.canonical.json"
        public_path = artifact_root / "manifests" / f"{condition}.public.json"
        _atomic_json(manifest_path, manifest)
        _atomic_json(public_path, public)
        public_ref = f"progress_site/assets/backtranslation/manifests/{manifest['pairing_id']}/{condition}.public.json"
        return CanonicalManifestResult(
            run_id=manifest["run_id"], pairing_id=manifest["pairing_id"], condition=condition,
            manifest_path=manifest_path, public_manifest_path=public_path, public_manifest_ref=public_ref,
            canonical_manifest_hash=public["canonical_manifest_hash"], artifact_ids=dict(artifact_ids),
            canonical_manifest=manifest, public_manifest=public,
        )

    @staticmethod
    def _run_id(pairing_id: str, condition: str) -> str:
        return f"run:{pairing_id}:{condition}"

    @staticmethod
    def _repo_ref(path: Path) -> str:
        try:
            return path.resolve().relative_to(ROOT).as_posix()
        except ValueError as exc:
            raise ManifestBridgeError("registry and protocol evidence must be repository-relative") from exc


class ManifestBridgeUnavailable(RuntimeError):
    pass


def require_bridge(candidate: Any) -> PaperMediaEvidenceBridge:
    method = getattr(candidate, "emit_backtranslation_run", None)
    if not callable(method):
        raise ManifestBridgeUnavailable("q-5 bridge unavailable: expected emit_backtranslation_run")
    return candidate
