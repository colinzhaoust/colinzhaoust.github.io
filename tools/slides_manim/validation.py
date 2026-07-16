from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "slides-manim"
SLOT_SCHEMA_PATH = SCHEMA_DIR / "animation-slot-0.1.0.schema.json"
SLIDE_SCHEMA_PATH = SCHEMA_DIR / "slide-ir-0.1.0.schema.json"
SAMPLE_SLIDE_PATH = ROOT / "experiments" / "slides_manim" / "methodology_attention_softmax.slide-ir.json"
DEMO_DIR = ROOT / "experiments" / "slides_manim" / "demo"


class SlidesManimValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _validator() -> Draft202012Validator:
    slot_schema = load_json(SLOT_SCHEMA_PATH)
    slide_schema = load_json(SLIDE_SCHEMA_PATH)
    Draft202012Validator.check_schema(slot_schema)
    Draft202012Validator.check_schema(slide_schema)
    resolver = RefResolver.from_schema(slide_schema, store={slot_schema["$id"]: slot_schema})
    return Draft202012Validator(slide_schema, resolver=resolver, format_checker=FormatChecker())


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate",
            "-of", "json", str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def _artifact_probe(path: Path) -> dict[str, Any]:
    data = _probe(path)
    stream = data["streams"][0]
    result = {"width": int(stream["width"]), "height": int(stream["height"])}
    if "format" in data and data["format"].get("duration"):
        result["duration"] = float(data["format"]["duration"])
    if stream.get("codec_name"):
        result["codec_name"] = stream["codec_name"]
    return result


def validate_slide_document(document: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors = [
        f"schema:{'/'.join(str(item) for item in error.absolute_path) or '<root>'}:{error.validator}"
        for error in _validator().iter_errors(document)
    ]
    artifacts = {item.get("artifact_id"): item for item in document.get("artifacts", []) if item.get("artifact_id")}
    if len(artifacts) != len(document.get("artifacts", [])):
        errors.append("artifacts:duplicate-id")

    probed: dict[str, dict[str, Any]] = {}
    for artifact_id, artifact in artifacts.items():
        path = root / artifact["path"]
        if not path.is_file():
            errors.append(f"artifact:{artifact_id}:missing-file")
            continue
        if sha256(path) != artifact["content_hash"]:
            errors.append(f"artifact:{artifact_id}:hash-mismatch")
        if artifact["validation_status"] != "pass":
            errors.append(f"artifact:{artifact_id}:not-validated")
        if artifact["role"] in {"rendered_video", "static_fallback"}:
            try:
                probed[artifact_id] = _artifact_probe(path)
            except (subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError):
                errors.append(f"artifact:{artifact_id}:media-probe-failed")
        if artifact["role"] == "scene_ir":
            try:
                scene = load_json(path)
            except (OSError, json.JSONDecodeError):
                errors.append(f"artifact:{artifact_id}:scene-ir-invalid-json")
            else:
                if scene.get("schema_version") != "scene-ir/0.1.0":
                    errors.append(f"artifact:{artifact_id}:scene-ir-version")

    expected_roles = {
        "scene_ir_ref": "scene_ir",
        "rendered_artifact_ref": "rendered_video",
        "static_fallback_artifact_ref": "static_fallback",
        "poster_frame_ref": "static_fallback",
    }
    for slot in document.get("animation_slots", []):
        referenced: set[str] = set()
        for field, role in expected_roles.items():
            artifact_ref = slot.get(field)
            artifact = artifacts.get(artifact_ref)
            if not artifact:
                errors.append(f"slot:{slot.get('slot_id', 'unknown')}:{field}:unresolved")
                continue
            referenced.add(artifact_ref)
            if artifact["role"] != role:
                errors.append(f"slot:{slot['slot_id']}:{field}:wrong-role")
        video = artifacts.get(slot.get("rendered_artifact_ref"))
        fallback = artifacts.get(slot.get("static_fallback_artifact_ref"))
        if video and slot.get("artifact_hash") != video["content_hash"]:
            errors.append(f"slot:{slot['slot_id']}:rendered-hash-mismatch")
        if slot.get("requiredness") == "required_for_comprehension" and fallback and not fallback["understandable_without_playback"]:
            errors.append(f"slot:{slot['slot_id']}:fallback-not-independent")
        parents = set(slot.get("composite_lineage", {}).get("parent_artifact_refs", []))
        if not referenced.issubset(parents):
            errors.append(f"slot:{slot.get('slot_id', 'unknown')}:lineage-incomplete")
        region = slot.get("slide_region", {})
        if region.get("x", 0) + region.get("width", 0) > 1 or region.get("y", 0) + region.get("height", 0) > 1:
            errors.append(f"slot:{slot.get('slot_id', 'unknown')}:region-overflow")
        video_probe = probed.get(slot.get("rendered_artifact_ref"))
        poster_probe = probed.get(slot.get("poster_frame_ref"))
        if video_probe:
            if abs(video_probe.get("duration", 0) - slot.get("expected_duration_seconds", 0)) > 0.05:
                errors.append(f"slot:{slot['slot_id']}:duration-mismatch")
            ratio = video_probe["width"] / video_probe["height"]
            expected_ratio = {"16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1, "9:16": 9 / 16}.get(slot.get("aspect_ratio"))
            if expected_ratio and abs(ratio - expected_ratio) > 0.02:
                errors.append(f"slot:{slot['slot_id']}:aspect-ratio-mismatch")
        if video_probe and poster_probe and (video_probe["width"], video_probe["height"]) != (poster_probe["width"], poster_probe["height"]):
            errors.append(f"slot:{slot['slot_id']}:poster-dimensions-mismatch")

    planned = document.get("planned_slots", [])
    planned_purposes = {item.get("semantic_purpose") for item in planned}
    if not {"architecture_dataflow", "performance_comparison"}.issubset(planned_purposes):
        errors.append("planned-slots:architecture-and-performance-required")
    if document.get("completion") == "full":
        errors.append("completion:smoke-cannot-be-full")
    return sorted(set(errors))


def validate_slide(path: Path = SAMPLE_SLIDE_PATH) -> None:
    errors = validate_slide_document(load_json(path))
    if errors:
        raise SlidesManimValidationError("slides+manim validation failed: " + "; ".join(errors))


def validate_demo_package(demo_dir: Path = DEMO_DIR) -> None:
    html_path = demo_dir / "index.html"
    css_path = demo_dir / "styles.css"
    caption_path = demo_dir / "assets" / "attention_softmax_9313551.vtt"
    errors: list[str] = []
    for path in (html_path, css_path, caption_path):
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"demo:{path.name}:missing")
    if html_path.is_file():
        html = html_path.read_text(encoding="utf-8")
        required = (
            'controls', 'preload="metadata"', 'poster="assets/attention_softmax_9313551_poster.png"',
            'src="assets/attention_softmax_9313551.mp4"', 'kind="captions"', 'SMOKE · Babel 9313551',
            'Planned / missing',
        )
        for token in required:
            if token not in html:
                errors.append(f"demo:index:{token}:missing")
        if "autoplay" in html:
            errors.append("demo:index:autoplay-forbidden")
    if errors:
        raise SlidesManimValidationError("slides+manim demo validation failed: " + "; ".join(errors))
