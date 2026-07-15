"""Deterministic render feedback with no learned or human evaluator."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageChops, ImageEnhance, ImageStat

from .reference import ReferencePreparationError, probe_media
from .registry import sha256_file


@dataclass(frozen=True)
class RenderResult:
    success: bool
    video_path: Path | None
    stderr: str = ""
    stdout: str = ""
    failure_code: str | None = None


@dataclass(frozen=True)
class FeedbackPolicy:
    policy_id: str
    sample_fractions: tuple[float, ...]
    max_duration_delta_ratio: float
    min_mean_similarity: float
    max_mean_absolute_error: float
    max_revision_rounds: int

    @classmethod
    def from_protocol(cls, protocol: Mapping[str, Any]) -> "FeedbackPolicy":
        policy = protocol["feedback_policy"]
        technical = policy["technical_thresholds"]
        visual = policy["similarity_thresholds"]
        sample_fractions = tuple(float(value) for value in policy["sample_fractions"])
        if not sample_fractions or any(value <= 0 or value >= 1 for value in sample_fractions):
            raise ValueError("sample_fractions must fall strictly between zero and one")
        rounds = int(policy["max_revision_rounds"])
        if rounds != 3:
            raise ValueError("feedback_policy/v1 requires exactly three maximum revision rounds")
        return cls(
            policy_id=str(policy["id"]),
            sample_fractions=sample_fractions,
            max_duration_delta_ratio=float(technical["max_duration_delta_ratio"]),
            min_mean_similarity=float(visual["min_mean_similarity"]),
            max_mean_absolute_error=float(visual["max_mean_absolute_error"]),
            max_revision_rounds=rounds,
        )


@dataclass(frozen=True)
class FrameComparison:
    index: int
    fraction: float
    reference_frame: str
    candidate_frame: str
    diff_overlay: str
    reference_hash: str
    candidate_hash: str
    diff_hash: str
    mean_absolute_error: float
    similarity: float


@dataclass(frozen=True)
class FeedbackBundle:
    policy_id: str
    technical_pass: bool
    visual_pass: bool
    early_stop: bool
    render_success: bool
    failure_code: str | None
    sanitized_render_errors: str
    technical_media_summary: Mapping[str, Any]
    numeric_similarity_summary: Mapping[str, Any]
    frame_pairs: tuple[FrameComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def model_view(self) -> dict[str, Any]:
        """Return the feedback_policy/v1 allowlist, excluding private paths/data."""

        return {
            "policy_id": self.policy_id,
            "technical_pass": self.technical_pass,
            "visual_pass": self.visual_pass,
            "sanitized_render_errors": self.sanitized_render_errors,
            "technical_media_summary": dict(self.technical_media_summary),
            "numeric_similarity_summary": dict(self.numeric_similarity_summary),
            "frame_pairs": [
                {
                    "index": item.index,
                    "fraction": item.fraction,
                    "reference_frame": item.reference_frame,
                    "candidate_frame": item.candidate_frame,
                    "diff_overlay": item.diff_overlay,
                    "mean_absolute_error": item.mean_absolute_error,
                    "similarity": item.similarity,
                }
                for item in self.frame_pairs
            ],
        }


def sanitize_render_errors(text: str, redactions: Sequence[str] = ()) -> str:
    lines = text.splitlines()[-40:]
    sanitized = "\n".join(lines)
    sanitized = re.sub(r"/Users/[^/\s]+", "/Users/<USER>", sanitized)
    sanitized = re.sub(r"/home/[^/\s]+", "/home/<USER>", sanitized)
    sanitized = re.sub(r"(?:[A-Za-z]:)?[/\\][^\s:'\"]+(?:[/\\][^\s:'\"]+)+", "<PATH>", sanitized)
    for value in sorted((value for value in redactions if value), key=len, reverse=True):
        sanitized = re.sub(re.escape(value), "<REDACTED>", sanitized, flags=re.IGNORECASE)
    return sanitized[-8000:]


def _extract_frame(video: Path, output: Path, timestamp: float, ffmpeg: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-ss",
            f"{timestamp:.6f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-fflags",
            "+bitexact",
            str(output),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0 or not output.is_file():
        raise RuntimeError(proc.stderr.strip()[-2000:] or "Frame extraction failed")


def _compare_frames(reference: Path, candidate: Path, overlay: Path) -> tuple[float, float]:
    with Image.open(reference) as reference_image, Image.open(candidate) as candidate_image:
        ref = reference_image.convert("RGB")
        cand = candidate_image.convert("RGB")
        if ref.size != cand.size:
            cand = cand.resize(ref.size, Image.Resampling.LANCZOS)
        diff = ImageChops.difference(ref, cand)
        channel_means = ImageStat.Stat(diff).mean
        mean_absolute_error = sum(channel_means) / (len(channel_means) * 255.0)
        similarity = max(0.0, 1.0 - mean_absolute_error)
        enhanced = ImageEnhance.Contrast(diff).enhance(4.0)
        panel = Image.new("RGB", (ref.width * 3, ref.height), "black")
        panel.paste(ref, (0, 0))
        panel.paste(cand, (ref.width, 0))
        panel.paste(enhanced, (ref.width * 2, 0))
        overlay.parent.mkdir(parents=True, exist_ok=True)
        panel.save(overlay, optimize=False, compress_level=9)
    return round(mean_absolute_error, 8), round(similarity, 8)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_feedback(
    reference_video: Path,
    render: RenderResult,
    output_dir: Path,
    policy: FeedbackPolicy,
    *,
    redactions: Sequence[str] = (),
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> FeedbackBundle:
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = sanitize_render_errors(render.stderr, redactions)
    if not render.success or render.video_path is None or not render.video_path.is_file():
        return FeedbackBundle(
            policy_id=policy.policy_id,
            technical_pass=False,
            visual_pass=False,
            early_stop=False,
            render_success=False,
            failure_code=render.failure_code or "render_error",
            sanitized_render_errors=errors,
            technical_media_summary={"candidate_video_valid": False},
            numeric_similarity_summary={"sample_count": 0, "mean_similarity": None, "mean_absolute_error": None},
            frame_pairs=(),
        )

    try:
        reference_media = probe_media(reference_video, ffprobe=ffprobe)
        candidate_media = probe_media(render.video_path, ffprobe=ffprobe)
    except ReferencePreparationError as exc:
        return FeedbackBundle(
            policy_id=policy.policy_id,
            technical_pass=False,
            visual_pass=False,
            early_stop=False,
            render_success=True,
            failure_code="invalid_media",
            sanitized_render_errors=sanitize_render_errors(f"{errors}\n{exc}", redactions),
            technical_media_summary={"candidate_video_valid": False},
            numeric_similarity_summary={"sample_count": 0, "mean_similarity": None, "mean_absolute_error": None},
            frame_pairs=(),
        )

    reference_duration = float(reference_media["duration_seconds"])
    candidate_duration = float(candidate_media["duration_seconds"])
    duration_delta_ratio = abs(candidate_duration - reference_duration) / max(reference_duration, 1e-9)
    technical_pass = bool(
        render.success
        and candidate_duration > 0
        and duration_delta_ratio <= policy.max_duration_delta_ratio
    )
    technical_summary = {
        "candidate_video_valid": True,
        "reference_duration_seconds": reference_duration,
        "candidate_duration_seconds": candidate_duration,
        "duration_delta_ratio": round(duration_delta_ratio, 8),
        "candidate_width": candidate_media["width"],
        "candidate_height": candidate_media["height"],
        "candidate_fps": candidate_media["fps"],
    }

    frame_pairs: list[FrameComparison] = []
    try:
        for index, fraction in enumerate(policy.sample_fractions, start=1):
            ref_frame = output_dir / "frames" / f"sample_{index:02d}_reference.png"
            cand_frame = output_dir / "frames" / f"sample_{index:02d}_candidate.png"
            overlay = output_dir / "diffs" / f"sample_{index:02d}_triptych.png"
            _extract_frame(reference_video, ref_frame, reference_duration * fraction, ffmpeg)
            _extract_frame(render.video_path, cand_frame, candidate_duration * fraction, ffmpeg)
            mae, similarity = _compare_frames(ref_frame, cand_frame, overlay)
            frame_pairs.append(
                FrameComparison(
                    index=index,
                    fraction=fraction,
                    reference_frame=_relative(ref_frame, output_dir),
                    candidate_frame=_relative(cand_frame, output_dir),
                    diff_overlay=_relative(overlay, output_dir),
                    reference_hash=sha256_file(ref_frame),
                    candidate_hash=sha256_file(cand_frame),
                    diff_hash=sha256_file(overlay),
                    mean_absolute_error=mae,
                    similarity=similarity,
                )
            )
    except Exception as exc:  # feedback failure remains an accounted experiment failure
        return FeedbackBundle(
            policy_id=policy.policy_id,
            technical_pass=technical_pass,
            visual_pass=False,
            early_stop=False,
            render_success=True,
            failure_code="evaluation_error",
            sanitized_render_errors=sanitize_render_errors(f"{errors}\n{exc}", redactions),
            technical_media_summary=technical_summary,
            numeric_similarity_summary={"sample_count": len(frame_pairs), "mean_similarity": None, "mean_absolute_error": None},
            frame_pairs=tuple(frame_pairs),
        )

    mean_similarity = sum(item.similarity for item in frame_pairs) / len(frame_pairs)
    mean_absolute_error = sum(item.mean_absolute_error for item in frame_pairs) / len(frame_pairs)
    visual_pass = bool(
        mean_similarity >= policy.min_mean_similarity
        and mean_absolute_error <= policy.max_mean_absolute_error
    )
    summary = {
        "sample_count": len(frame_pairs),
        "mean_similarity": round(mean_similarity, 8),
        "mean_absolute_error": round(mean_absolute_error, 8),
        "minimum_similarity": min(item.similarity for item in frame_pairs),
        "maximum_mean_absolute_error": max(item.mean_absolute_error for item in frame_pairs),
    }
    return FeedbackBundle(
        policy_id=policy.policy_id,
        technical_pass=technical_pass,
        visual_pass=visual_pass,
        early_stop=technical_pass and visual_pass,
        render_success=True,
        failure_code=None,
        sanitized_render_errors=errors,
        technical_media_summary=technical_summary,
        numeric_similarity_summary=summary,
        frame_pairs=tuple(frame_pairs),
    )


def write_feedback(bundle: FeedbackBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
