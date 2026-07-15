"""Deterministic, metadata-stripping preparation of model-visible MP4s."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from .registry import CASE_ID_RE, sha256_file


BLOCKED_METADATA_KEYS = {
    "artist",
    "comment",
    "copyright",
    "creation_time",
    "date",
    "description",
    "location",
    "title",
}
GENERIC_TECHNICAL_METADATA = {"handler_name": {"VideoHandler"}}


class ReferencePreparationError(RuntimeError):
    """Reference preparation or validation failed closed."""


@dataclass(frozen=True)
class PreparedReference:
    case_id: str
    video_path: Path
    content_hash: str
    media: Mapping[str, Any]
    private_evidence: Mapping[str, Any]


def _run_json(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise ReferencePreparationError(proc.stderr.strip() or f"Command failed: {command[0]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReferencePreparationError(f"Invalid JSON from {command[0]}") from exc


def probe_media(path: Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    data = _run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name:format_tags:stream=index,codec_type,codec_name,width,height,pix_fmt,r_frame_rate:stream_tags",
            "-of",
            "json",
            str(path),
        ]
    )
    streams = data.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1:
        raise ReferencePreparationError(f"Expected exactly one video stream, found {len(video_streams)}")
    video = video_streams[0]
    format_data = data.get("format", {})
    tags: dict[str, str] = {}
    for source in (format_data.get("tags", {}), video.get("tags", {})):
        for key, value in source.items():
            tags[str(key).lower()] = str(value)
    fps = Fraction(str(video.get("r_frame_rate", "0/1")))
    return {
        "format_name": format_data.get("format_name"),
        "duration_seconds": round(float(format_data.get("duration", 0.0)), 6),
        "size_bytes": int(format_data.get("size", path.stat().st_size)),
        "codec": video.get("codec_name"),
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "pixel_format": video.get("pix_fmt"),
        "fps": float(fps),
        "audio_stream_count": len(audio_streams),
        "tags": tags,
    }


def validate_model_visible_reference(
    path: Path,
    case_id: str,
    config: Mapping[str, Any],
    *,
    ffprobe: str = "ffprobe",
) -> dict[str, Any]:
    if not CASE_ID_RE.fullmatch(case_id):
        raise ReferencePreparationError("case_id must be an opaque bt-NNN identifier")
    if path.name != config.get("model_visible_filename", "reference.mp4"):
        raise ReferencePreparationError("Model-visible video must be named reference.mp4")
    if path.parent.name != case_id:
        raise ReferencePreparationError("Model-visible reference must live under its opaque case ID")
    media = probe_media(path, ffprobe=ffprobe)
    expected = {
        "width": int(config["width"]),
        "height": int(config["height"]),
        "pixel_format": config["pixel_format"],
        "audio_stream_count": 0,
    }
    for key, value in expected.items():
        if media[key] != value:
            raise ReferencePreparationError(f"Reference {key}={media[key]!r}; expected {value!r}")
    if abs(media["fps"] - float(config["fps"])) > 1e-6:
        raise ReferencePreparationError("Reference frame rate does not match protocol")
    blocked = sorted(key for key in media["tags"] if key in BLOCKED_METADATA_KEYS)
    if blocked:
        raise ReferencePreparationError(f"Reference contains blocked metadata keys: {', '.join(blocked)}")
    for key, allowed_values in GENERIC_TECHNICAL_METADATA.items():
        if key in media["tags"] and media["tags"][key] not in allowed_values:
            raise ReferencePreparationError(f"Reference contains non-generic {key} metadata")
    return media


def _safe_private_manifest_path(path: Path, output_root: Path) -> None:
    try:
        path.resolve().relative_to(output_root.resolve())
    except ValueError:
        return
    raise ReferencePreparationError("Private evidence manifest must not be inside the model-visible reference root")


def prepare_reference(
    input_video: Path,
    output_root: Path,
    case_id: str,
    config: Mapping[str, Any],
    *,
    private_manifest_path: Path | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> PreparedReference:
    """Transcode an existing local video; never fetches or discovers input assets."""

    if not input_video.is_file():
        raise ReferencePreparationError("Input video does not exist")
    if not CASE_ID_RE.fullmatch(case_id):
        raise ReferencePreparationError("case_id must be an opaque bt-NNN identifier")
    if private_manifest_path is not None:
        _safe_private_manifest_path(private_manifest_path, output_root)

    case_root = output_root / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    output_path = case_root / str(config.get("model_visible_filename", "reference.mp4"))
    width = int(config["width"])
    height = int(config["height"])
    fps = int(config["fps"])
    filter_graph = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},format={config['pixel_format']}"
    )
    command = [
        ffmpeg,
        "-nostdin",
        "-y",
        "-i",
        str(input_video),
        "-map",
        "0:v:0",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-an",
        "-vf",
        filter_graph,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-threads",
        str(config.get("threads", 1)),
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-metadata",
        "title=",
        "-metadata",
        "comment=",
        "-metadata",
        "description=",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0 or not output_path.is_file():
        raise ReferencePreparationError(proc.stderr.strip()[-4000:] or "ffmpeg failed")

    media = validate_model_visible_reference(output_path, case_id, config, ffprobe=ffprobe)
    private_evidence = {
        "schema_version": "backtranslation-reference-preparation/v1",
        "case_id": case_id,
        "input_content_hash": sha256_file(input_video),
        "output_content_hash": sha256_file(output_path),
        "output_media": media,
        "preparation_command": [
            "ffmpeg",
            "<INPUT_VIDEO>",
            "--normalized-reference-policy-v1",
            f"{width}x{height}@{fps}",
            "<OUTPUT_REFERENCE>",
        ],
    }
    if private_manifest_path is not None:
        private_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        private_manifest_path.write_text(json.dumps(private_evidence, indent=2), encoding="utf-8")
    return PreparedReference(
        case_id=case_id,
        video_path=output_path,
        content_hash=private_evidence["output_content_hash"],
        media=media,
        private_evidence=private_evidence,
    )


def assert_workspace_isolation(
    generation_root: Path,
    *,
    reference_path: Path,
    source_root: Path | None,
    forbidden_tokens: list[str],
) -> None:
    """Fail closed when model-visible workspace names/text expose source metadata."""

    generation_root = generation_root.resolve()
    reference_path = reference_path.resolve()
    if reference_path.parent.parent != generation_root:
        raise ReferencePreparationError("Generation root may contain only opaque case directories")
    if source_root is not None:
        source_root = source_root.resolve()
        if source_root == generation_root or source_root in generation_root.parents or generation_root in source_root.parents:
            raise ReferencePreparationError("Source root and generation workspace must be disjoint")
    allowed = {reference_path}
    text_suffixes = {".json", ".txt", ".md", ".yaml", ".yml"}
    normalized_tokens = [token.lower() for token in forbidden_tokens if token]
    for path in generation_root.rglob("*"):
        if path.is_dir():
            continue
        if path not in allowed:
            raise ReferencePreparationError(f"Unexpected model-visible file: {path.relative_to(generation_root)}")
        relative_name = str(path.relative_to(generation_root)).lower()
        if any(token in relative_name for token in normalized_tokens):
            raise ReferencePreparationError("Model-visible filename leaks source metadata")
        if path.suffix.lower() in text_suffixes:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
            if any(re.search(re.escape(token), content) for token in normalized_tokens):
                raise ReferencePreparationError("Model-visible text leaks source metadata")
