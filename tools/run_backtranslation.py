#!/usr/bin/env python3
"""Offline CLI for the q-6 Manim backtranslation harness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.backtranslation.conditions import (
    FeedbackPolicy,
    FixtureRenderer,
    RecordingMockAdapter,
    load_protocol,
    run_one_shot,
    run_self_refined,
)
from tools.backtranslation.evaluation import CodeSafetyHook, PairedDeltaHook, run_hooks
from tools.backtranslation.manifest_bridge import HumanConditionInput, PaperMediaEvidenceBridge
from tools.backtranslation.reference import (
    assert_workspace_isolation,
    prepare_reference,
)
from tools.backtranslation.registry import load_registry, sha256_file, verify_source_root
from tools.backtranslation.synthetic import create_fixture_videos


DEFAULT_REGISTRY = ROOT / "experiments" / "backtranslation" / "v1" / "scene_registry.json"
DEFAULT_PROTOCOL = ROOT / "experiments" / "backtranslation" / "v1" / "protocol.json"
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "backtranslation" / "synthetic_fixture.json"
DEFAULT_PIPELINE_REPOSITORY = "https://github.com/colinzhaoust/4blue2brown-progress"


def _load_reference_config(protocol: dict) -> dict:
    return dict(protocol["reference_preparation"])


def command_validate_registry(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    result = {
        "registry_id": registry["registry_id"],
        "scene_count": len(registry["scenes"]),
        "commit_sha": registry["upstream"]["commit_sha"],
        "source_root_verification": None,
    }
    if args.source_root:
        result["source_root_verification"] = verify_source_root(registry, args.source_root)
    print(json.dumps(result, indent=2))
    return 0


def command_prepare_reference(args: argparse.Namespace) -> int:
    protocol = load_protocol(args.protocol)
    prepared = prepare_reference(
        args.input_video,
        args.output_root,
        args.case_id,
        _load_reference_config(protocol),
        private_manifest_path=args.private_manifest,
    )
    print(
        json.dumps(
            {
                "case_id": prepared.case_id,
                "video_path": str(prepared.video_path),
                "content_hash": prepared.content_hash,
                "media": prepared.media,
            },
            indent=2,
        )
    )
    return 0


def _fixture_code(marker: str) -> str:
    return f"from manim import Scene\n\nclass OfflineFixtureScene(Scene):\n    FIXTURE_VARIANT = {marker!r}\n"


def _git_head() -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if process.returncode != 0 or len(process.stdout.strip()) != 40:
        raise RuntimeError("A pinned pipeline commit is required for canonical evidence")
    return process.stdout.strip()


def command_dry_run(args: argparse.Namespace) -> int:
    protocol = load_protocol(args.protocol)
    policy = FeedbackPolicy.from_protocol(protocol)
    registry = load_registry(args.registry)
    work_root = args.work_dir.resolve()
    fixture_videos = create_fixture_videos(args.fixture, work_root / "synthetic_raw")

    prepared = prepare_reference(
        fixture_videos["reference"],
        work_root / "model_inputs",
        "bt-999",
        _load_reference_config(protocol),
        private_manifest_path=work_root / "private" / "reference_preparation.json",
    )
    forbidden_tokens = [scene["scene_class"] for scene in registry["scenes"]]
    forbidden_tokens.extend([registry["upstream"]["source_path"], registry["upstream"]["repository"]])
    assert_workspace_isolation(
        work_root / "model_inputs",
        reference_path=prepared.video_path,
        source_root=None,
        forbidden_tokens=forbidden_tokens,
    )

    renderer = FixtureRenderer(
        {
            "one_shot": fixture_videos["one_shot"],
            "refine_1": fixture_videos["refine_1"],
            "refine_2": prepared.video_path,
        }
    )
    one_adapter = RecordingMockAdapter([_fixture_code("one_shot")])
    one_root = work_root / "runs" / "one_shot"
    one_trace = run_one_shot(
        pairing_id="fixture-bt-999-r1",
        prepared_reference=prepared,
        run_root=one_root,
        adapter=one_adapter,
        renderer=renderer,
        policy=policy,
        redactions=forbidden_tokens,
    )
    if not one_trace.rounds or not one_trace.final_code_hash:
        raise RuntimeError("Synthetic one-shot did not produce the required code artifact")
    one_code = one_root / str(one_trace.rounds[-1].code_path)

    refine_adapter = RecordingMockAdapter([_fixture_code("compile_error"), _fixture_code("refine_2")])
    self_root = work_root / "runs" / "self_refined"
    self_trace = run_self_refined(
        pairing_id=one_trace.pairing_id,
        prepared_reference=prepared,
        one_shot_code_path=one_code,
        expected_one_shot_hash=one_trace.final_code_hash,
        run_root=self_root,
        adapter=refine_adapter,
        renderer=renderer,
        policy=policy,
        redactions=forbidden_tokens,
    )
    evaluations = run_hooks(
        [
            CodeSafetyHook(one_code, forbidden_source_tokens=forbidden_tokens),
            PairedDeltaHook(one_trace, self_trace),
        ]
    )
    bridge = PaperMediaEvidenceBridge(
        registry_path=args.registry,
        protocol_path=args.protocol,
        pipeline_repository=args.pipeline_repository,
        pipeline_commit=args.pipeline_commit or _git_head(),
    )
    manifests = bridge.emit_pairing(
        human=HumanConditionInput(
            pairing_id=one_trace.pairing_id,
            prepared_reference=prepared,
            implementation_origin="synthetic_fixture",
        ),
        one_shot_trace=one_trace,
        one_shot_root=one_root,
        self_refined_trace=self_trace,
        self_refined_root=self_root,
        artifact_root=work_root / "evidence",
        dry_run=True,
    )
    result = {
        "schema_version": "backtranslation-dry-run-result/v1",
        "implementation_origin": "synthetic_fixture",
        "completion": "placeholder",
        "provider_calls": {
            "one_shot_recorded": len(one_adapter.calls),
            "self_refined_recorded": len(refine_adapter.calls),
            "billable": 0,
        },
        "one_shot": one_trace.to_dict(),
        "self_refined": self_trace.to_dict(),
        "evaluations": evaluations,
        "protocol_hash": sha256_file(args.protocol),
        "canonical_manifests": {
            item.condition: {
                "canonical": str(item.manifest_path),
                "public": str(item.public_manifest_path),
                "canonical_manifest_hash": item.canonical_manifest_hash,
                "completion": item.public_manifest["completion"]["derived_value"],
            }
            for item in (manifests.human, manifests.one_shot, manifests.self_refined)
        },
    }
    result_path = work_root / "dry_run_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"result": str(result_path), "self_refined_status": self_trace.status, "evaluations": evaluations}, indent=2))
    return 0 if self_trace.status == "completed" and all(item["result"] == "pass" for item in evaluations) else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-registry")
    validate.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    validate.add_argument("--source-root", type=Path)
    validate.set_defaults(func=command_validate_registry)

    prepare = subparsers.add_parser("prepare-reference")
    prepare.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    prepare.add_argument("--input-video", type=Path, required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--case-id", required=True)
    prepare.add_argument("--private-manifest", type=Path)
    prepare.set_defaults(func=command_prepare_reference)

    dry_run = subparsers.add_parser("dry-run")
    dry_run.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    dry_run.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    dry_run.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    dry_run.add_argument("--work-dir", type=Path, required=True)
    dry_run.add_argument("--pipeline-repository", default=DEFAULT_PIPELINE_REPOSITORY)
    dry_run.add_argument("--pipeline-commit")
    dry_run.set_defaults(func=command_dry_run)
    return root


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
