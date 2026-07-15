"""One-shot and self-refinement condition state machines."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .feedback import FeedbackBundle, FeedbackPolicy, ModelFeedback, RenderResult, build_feedback, write_feedback
from .reference import PreparedReference, ReferencePreparationError, validate_prepared_reference
from .registry import sha256_file


GENERIC_PROMPT = "Reconstruct the animation in the attached reference.mp4 as one self-contained Manim Community Python scene. Return Python source only."


class ConditionError(RuntimeError):
    """A condition is non-compliant or cannot be executed."""


@dataclass(frozen=True)
class AdapterCapabilities:
    video_input: bool
    image_only: bool = False
    network_disabled_sandbox: bool = True
    provider_name: str = "recording_mock"


@dataclass(frozen=True)
class ModelRequest:
    condition: str
    round_index: int
    reference_video: Path
    prompt: str
    current_code: str | None = None
    feedback: ModelFeedback | None = None


@dataclass(frozen=True)
class ModelResponse:
    raw_text: str
    usage: Mapping[str, Any] | None = None


class ModelAdapter(Protocol):
    capabilities: AdapterCapabilities

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...


class Renderer(Protocol):
    def render(self, code_path: Path, output_dir: Path, round_index: int) -> RenderResult:
        ...


@dataclass
class RecordingMockAdapter:
    """Offline adapter used to prove call count and exact request contracts."""

    scripted_responses: list[str]
    capabilities: AdapterCapabilities = field(default_factory=lambda: AdapterCapabilities(video_input=True))
    calls: list[ModelRequest] = field(default_factory=list)

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if not self.scripted_responses:
            raise ConditionError("Recording mock has no scripted response")
        return ModelResponse(raw_text=self.scripted_responses.pop(0), usage={"billable": False, "provider_calls": 0})


@dataclass
class FixtureRenderer:
    """Copies prebuilt synthetic fixture videos; never executes generated code."""

    videos_by_marker: Mapping[str, Path]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def render(self, code_path: Path, output_dir: Path, round_index: int) -> RenderResult:
        code = code_path.read_text(encoding="utf-8")
        marker_match = re.search(r"FIXTURE_VARIANT\s*=\s*['\"]([^'\"]+)['\"]", code)
        marker = marker_match.group(1) if marker_match else ""
        self.calls.append({"round_index": round_index, "code_hash": sha256_file(code_path), "marker": marker})
        if marker == "compile_error":
            return RenderResult(False, None, stderr=f"{code_path}: SyntaxError: synthetic fixture", failure_code="compile_error")
        if marker == "timeout":
            return RenderResult(False, None, stderr="Synthetic renderer timed out", failure_code="render_timeout")
        source_video = self.videos_by_marker.get(marker)
        if source_video is None or not source_video.is_file():
            return RenderResult(False, None, stderr=f"Unknown synthetic fixture marker: {marker}", failure_code="render_error")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_video = output_dir / "rendered.mp4"
        shutil.copyfile(source_video, output_video)
        return RenderResult(True, output_video, stdout="Synthetic fixture copied; no Python code executed.")


@dataclass(frozen=True)
class CandidateRound:
    round_index: int
    stage: str
    code_path: str | None
    code_hash: str | None
    parent_code_hash: str | None
    response_path: str | None
    render_path: str | None
    render_hash: str | None
    feedback_path: str | None
    feedback_hash: str | None
    technical_pass: bool
    visual_pass: bool
    early_stop: bool
    failure_code: str | None


@dataclass
class ConditionTrace:
    schema_version: str
    pairing_id: str
    case_id: str
    condition: str
    reference_hash: str
    feedback_policy_id: str
    rounds: list[CandidateRound]
    status: str
    failure_codes: list[str]
    provider_calls: int
    billable_provider_calls: int
    initial_one_shot_code_hash: str | None = None
    final_code_hash: str | None = None
    final_render_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notice"] = "Non-canonical harness trace. q-5 owns canonical run manifests and public projection."
        return data


def load_protocol(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "backtranslation-protocol/v1":
        raise ConditionError("Unsupported backtranslation protocol")
    policy = FeedbackPolicy.from_protocol(data)
    if policy.max_revision_rounds != 3:
        raise ConditionError("Protocol must cap self-refinement at three revisions")
    return data


def extract_python_source(raw_text: str) -> str:
    text = raw_text.strip()
    fence = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    if not text or not re.search(r"^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", text, re.MULTILINE):
        raise ConditionError("Model response did not contain a Manim scene class")
    return text


def _assert_adapter(adapter: ModelAdapter) -> None:
    capabilities = adapter.capabilities
    if not capabilities.video_input or capabilities.image_only:
        raise ConditionError("adapter_non_compliant: actual MP4/video input capability is required")
    if not capabilities.network_disabled_sandbox:
        raise ConditionError("adapter_non_compliant: network-disabled sandbox declaration is required")


def _assert_reference(prepared: PreparedReference, run_root: Path, redactions: Sequence[str]) -> None:
    try:
        validate_prepared_reference(
            prepared,
            run_root=run_root,
            forbidden_tokens=list(redactions),
        )
    except ReferencePreparationError as exc:
        raise ConditionError("reference_non_compliant: PreparedReference validation failed") from exc


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _relative(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    return path.resolve().relative_to(root.resolve()).as_posix()


def _round_from_artifacts(
    *,
    root: Path,
    round_index: int,
    stage: str,
    code_path: Path | None,
    parent_hash: str | None,
    response_path: Path | None,
    render: RenderResult,
    feedback_path: Path | None,
    feedback: FeedbackBundle,
) -> CandidateRound:
    render_hash = sha256_file(render.video_path) if render.video_path and render.video_path.is_file() else None
    return CandidateRound(
        round_index=round_index,
        stage=stage,
        code_path=_relative(code_path, root),
        code_hash=sha256_file(code_path) if code_path and code_path.is_file() else None,
        parent_code_hash=parent_hash,
        response_path=_relative(response_path, root),
        render_path=_relative(render.video_path, root),
        render_hash=render_hash,
        feedback_path=_relative(feedback_path, root),
        feedback_hash=sha256_file(feedback_path) if feedback_path and feedback_path.is_file() else None,
        technical_pass=feedback.technical_pass,
        visual_pass=feedback.visual_pass,
        early_stop=feedback.early_stop,
        failure_code=feedback.failure_code,
    )


def _failed_round(
    *,
    root: Path,
    round_index: int,
    stage: str,
    code_path: Path,
    parent_hash: str | None,
    response_path: Path | None,
    failure_code: str,
) -> CandidateRound:
    """Retain generated-code evidence even when later materialization fails."""

    return CandidateRound(
        round_index=round_index,
        stage=stage,
        code_path=_relative(code_path, root),
        code_hash=sha256_file(code_path),
        parent_code_hash=parent_hash,
        response_path=_relative(response_path, root),
        render_path=None,
        render_hash=None,
        feedback_path=None,
        feedback_hash=None,
        technical_pass=False,
        visual_pass=False,
        early_stop=False,
        failure_code=failure_code,
    )


def _failure_feedback(policy_id: str, failure_code: str, error_type: str) -> FeedbackBundle:
    return FeedbackBundle(
        policy_id=policy_id,
        technical_pass=False,
        visual_pass=False,
        early_stop=False,
        render_success=False,
        failure_code=failure_code,
        sanitized_render_errors=f"{failure_code}: {error_type}",
        technical_media_summary={"candidate_video_valid": False},
        numeric_similarity_summary={"sample_count": 0, "mean_similarity": None, "mean_absolute_error": None},
        frame_pairs=(),
    )


def _normalize_render_output(render: RenderResult, root: Path) -> RenderResult:
    if not render.success or render.video_path is None:
        return render
    try:
        resolved = render.video_path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        return RenderResult(
            False,
            None,
            stderr="Renderer output escaped the run root or is missing.",
            failure_code="render_error",
        )
    if not resolved.is_file():
        return RenderResult(False, None, stderr="Renderer output is not a regular file.", failure_code="render_error")
    return RenderResult(
        render.success,
        resolved,
        stderr=render.stderr,
        stdout=render.stdout,
        failure_code=render.failure_code,
    )


def _render_and_feedback(
    *,
    root: Path,
    reference_video: Path,
    code_path: Path,
    renderer: Renderer,
    policy: FeedbackPolicy,
    round_index: int,
    redactions: Sequence[str],
) -> tuple[RenderResult, FeedbackBundle, Path | None]:
    round_root = code_path.parent
    try:
        render = renderer.render(code_path, round_root / "render", round_index)
    except Exception as exc:
        render = RenderResult(False, None, stderr=str(exc), failure_code="render_error")
    render = _normalize_render_output(render, root)
    feedback_root = round_root / "feedback"
    try:
        feedback = build_feedback(reference_video, render, feedback_root, policy, redactions=redactions)
    except Exception as exc:
        feedback_root.mkdir(parents=True, exist_ok=True)
        feedback = _failure_feedback(policy.policy_id, "evaluation_error", type(exc).__name__)
    feedback_path = round_root / "feedback.json"
    try:
        write_feedback(feedback, feedback_path)
    except Exception:
        feedback = _failure_feedback(policy.policy_id, "evaluation_error", "feedback_persistence_error")
        feedback_path = None
    return render, feedback, feedback_path


def _write_trace(trace: ConditionTrace, run_root: Path) -> None:
    (run_root / "condition_trace.json").write_text(
        json.dumps(trace.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )


def run_one_shot(
    *,
    pairing_id: str,
    prepared_reference: PreparedReference,
    run_root: Path,
    adapter: ModelAdapter,
    renderer: Renderer,
    policy: FeedbackPolicy,
    redactions: Sequence[str] = (),
) -> ConditionTrace:
    _assert_adapter(adapter)
    _assert_reference(prepared_reference, run_root, redactions)
    run_root.mkdir(parents=True, exist_ok=True)
    case_id = prepared_reference.case_id
    reference_video = prepared_reference.video_path.resolve()
    reference_hash = sha256_file(reference_video)
    request = ModelRequest(
        condition="one_shot",
        round_index=0,
        reference_video=reference_video,
        prompt=GENERIC_PROMPT,
        current_code=None,
        feedback=None,
    )
    rounds: list[CandidateRound] = []
    failure_codes: list[str] = []
    provider_calls = 1
    try:
        response = adapter.generate(request)
    except Exception as exc:
        failure_codes.append("generation_error")
        _write_text(run_root / "round_0" / "failure.txt", f"generation_error: {type(exc).__name__}")
    else:
        response_path = run_root / "round_0" / "response.txt"
        _write_text(response_path, response.raw_text)
        try:
            code = extract_python_source(response.raw_text)
        except ConditionError:
            failure_codes.append("malformed_code")
            _write_text(run_root / "round_0" / "failure.txt", "malformed_code")
        else:
            code_path = run_root / "round_0" / "code.py"
            _write_text(code_path, code)
            try:
                render, feedback, feedback_path = _render_and_feedback(
                    root=run_root,
                    reference_video=reference_video,
                    code_path=code_path,
                    renderer=renderer,
                    policy=policy,
                    round_index=0,
                    redactions=redactions,
                )
                candidate = _round_from_artifacts(
                    root=run_root,
                    round_index=0,
                    stage="one_shot",
                    code_path=code_path,
                    parent_hash=None,
                    response_path=response_path,
                    render=render,
                    feedback_path=feedback_path,
                    feedback=feedback,
                )
            except Exception as exc:
                _write_text(run_root / "round_0" / "failure.txt", f"evaluation_error: {type(exc).__name__}")
                candidate = _failed_round(
                    root=run_root,
                    round_index=0,
                    stage="one_shot",
                    code_path=code_path,
                    parent_hash=None,
                    response_path=response_path,
                    failure_code="evaluation_error",
                )
            rounds.append(candidate)
            if candidate.failure_code:
                failure_codes.append(candidate.failure_code)

    final = rounds[-1] if rounds else None
    trace = ConditionTrace(
        schema_version="backtranslation-condition-trace/v1",
        pairing_id=pairing_id,
        case_id=case_id,
        condition="one_shot",
        reference_hash=reference_hash,
        feedback_policy_id=policy.policy_id,
        rounds=rounds,
        status="completed" if final and not final.failure_code else "failed",
        failure_codes=failure_codes,
        provider_calls=provider_calls,
        billable_provider_calls=0,
        final_code_hash=final.code_hash if final else None,
        final_render_hash=final.render_hash if final else None,
    )
    _write_trace(trace, run_root)
    return trace


def run_self_refined(
    *,
    pairing_id: str,
    prepared_reference: PreparedReference,
    one_shot_code_path: Path,
    expected_one_shot_hash: str,
    run_root: Path,
    adapter: ModelAdapter,
    renderer: Renderer,
    policy: FeedbackPolicy,
    redactions: Sequence[str] = (),
) -> ConditionTrace:
    _assert_adapter(adapter)
    _assert_reference(prepared_reference, run_root, redactions)
    case_id = prepared_reference.case_id
    reference_video = prepared_reference.video_path.resolve()
    actual_one_shot_hash = sha256_file(one_shot_code_path)
    if actual_one_shot_hash != expected_one_shot_hash:
        raise ConditionError("policy_violation: self-refinement parent is not the exact one-shot code")
    run_root.mkdir(parents=True, exist_ok=True)
    reference_hash = sha256_file(reference_video)
    rounds: list[CandidateRound] = []
    failure_codes: list[str] = []
    provider_calls = 0

    initial_code_path = run_root / "round_0" / "code.py"
    initial_code_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(one_shot_code_path, initial_code_path)
    if sha256_file(initial_code_path) != expected_one_shot_hash:
        raise ConditionError("policy_violation: copied round-zero code changed")
    try:
        render, feedback, feedback_path = _render_and_feedback(
            root=run_root,
            reference_video=reference_video,
            code_path=initial_code_path,
            renderer=renderer,
            policy=policy,
            round_index=0,
            redactions=redactions,
        )
        initial_round = _round_from_artifacts(
            root=run_root,
            round_index=0,
            stage="self_refined_initial_one_shot",
            code_path=initial_code_path,
            parent_hash=expected_one_shot_hash,
            response_path=None,
            render=render,
            feedback_path=feedback_path,
            feedback=feedback,
        )
    except Exception as exc:
        _write_text(run_root / "round_0" / "failure.txt", f"evaluation_error: {type(exc).__name__}")
        feedback = _failure_feedback(policy.policy_id, "evaluation_error", type(exc).__name__)
        (initial_code_path.parent / "feedback").mkdir(parents=True, exist_ok=True)
        initial_round = _failed_round(
            root=run_root,
            round_index=0,
            stage="self_refined_initial_one_shot",
            code_path=initial_code_path,
            parent_hash=expected_one_shot_hash,
            response_path=None,
            failure_code="evaluation_error",
        )
    rounds.append(initial_round)
    if initial_round.failure_code:
        failure_codes.append(initial_round.failure_code)

    current_code_path = initial_code_path
    current_code_hash = expected_one_shot_hash
    current_feedback = feedback
    current_feedback_root = initial_code_path.parent / "feedback"
    for round_index in range(1, policy.max_revision_rounds + 1):
        if current_feedback.early_stop:
            break
        request = ModelRequest(
            condition="self_refined",
            round_index=round_index,
            reference_video=reference_video,
            prompt=GENERIC_PROMPT,
            current_code=current_code_path.read_text(encoding="utf-8"),
            feedback=current_feedback.model_input(current_feedback_root),
        )
        round_root = run_root / f"round_{round_index}"
        provider_calls += 1
        try:
            response = adapter.generate(request)
        except Exception as exc:
            failure_codes.append("generation_error")
            _write_text(round_root / "failure.txt", f"generation_error: {type(exc).__name__}")
            break
        response_path = round_root / "response.txt"
        _write_text(response_path, response.raw_text)
        try:
            code = extract_python_source(response.raw_text)
        except ConditionError:
            failure_codes.append("malformed_code")
            _write_text(round_root / "failure.txt", "malformed_code")
            break
        code_path: Path | None = None
        try:
            code_path = round_root / "code.py"
            _write_text(code_path, code)
            render, next_feedback, feedback_path = _render_and_feedback(
                root=run_root,
                reference_video=reference_video,
                code_path=code_path,
                renderer=renderer,
                policy=policy,
                round_index=round_index,
                redactions=redactions,
            )
            candidate = _round_from_artifacts(
                root=run_root,
                round_index=round_index,
                stage="self_refined_revision",
                code_path=code_path,
                parent_hash=current_code_hash,
                response_path=response_path,
                render=render,
                feedback_path=feedback_path,
                feedback=next_feedback,
            )
            rounds.append(candidate)
            if candidate.failure_code:
                failure_codes.append(candidate.failure_code)
            current_code_path = code_path
            current_code_hash = candidate.code_hash or current_code_hash
            current_feedback = next_feedback
            current_feedback_root = code_path.parent / "feedback"
        except Exception as exc:
            failure_codes.append("evaluation_error")
            _write_text(round_root / "failure.txt", f"evaluation_error: {type(exc).__name__}")
            if code_path is not None and code_path.is_file():
                candidate = _failed_round(
                    root=run_root,
                    round_index=round_index,
                    stage="self_refined_revision",
                    code_path=code_path,
                    parent_hash=current_code_hash,
                    response_path=response_path,
                    failure_code="evaluation_error",
                )
                rounds.append(candidate)
                current_code_path = code_path
                current_code_hash = candidate.code_hash or current_code_hash
            break

    final = rounds[-1]
    exhausted = not final.early_stop and provider_calls >= policy.max_revision_rounds
    status = "completed" if final.early_stop else ("partial" if final.render_hash else "failed")
    if exhausted and "policy_threshold_not_met" not in failure_codes:
        failure_codes.append("policy_threshold_not_met")
    trace = ConditionTrace(
        schema_version="backtranslation-condition-trace/v1",
        pairing_id=pairing_id,
        case_id=case_id,
        condition="self_refined",
        reference_hash=reference_hash,
        feedback_policy_id=policy.policy_id,
        rounds=rounds,
        status=status,
        failure_codes=failure_codes,
        provider_calls=provider_calls,
        billable_provider_calls=0,
        initial_one_shot_code_hash=expected_one_shot_hash,
        final_code_hash=final.code_hash,
        final_render_hash=final.render_hash,
    )
    _write_trace(trace, run_root)
    return trace
