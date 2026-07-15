#!/usr/bin/env python3
"""Render baseline-style coverage videos from reproduction preview JSON.

The previews are planning contracts for different paper-to-video frameworks.
This renderer turns those contracts into short, comparable MP4 artifacts so the
progress report can show coverage across topics and framework styles. These are
not full upstream framework renders; each output manifest records the preview
provider and renderer type explicitly.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "experiments" / "reproductions" / "paper_specs"

ADAPTER_ORDER = ("paper2manim", "code2video", "theorem_explain_agent", "llm2manim", "manimtrainer")
PAPER_ORDER = ("feynrl", "dpo", "attention", "transformers", "rope")

ADAPTER_LABELS = {
    "paper2manim": "Paper2Manim",
    "code2video": "Code2Video",
    "theorem_explain_agent": "TEA",
    "llm2manim": "LLM2Manim",
    "manimtrainer": "ManimTrainer",
}

ADAPTER_PIPELINES = {
    "paper2manim": ["Paper", "Storyboard", "Scene code", "Render", "Memory"],
    "code2video": ["Topic", "Planner", "Coder", "Critic", "TeachQuiz"],
    "theorem_explain_agent": ["Theorem", "Long plan", "Implementation", "Render eval", "Revise"],
    "llm2manim": ["Prompt", "Symbol ledger", "Templates", "HITL", "Render"],
    "manimtrainer": ["Retrieval", "SFT policy", "RL feedback", "Render", "RITL-DOC"],
}

ACCENTS = {
    "paper2manim": (38, 113, 201),
    "code2video": (220, 102, 37),
    "theorem_explain_agent": (126, 87, 194),
    "llm2manim": (41, 150, 132),
    "manimtrainer": (183, 73, 105),
}

BG = (247, 249, 252)
INK = (28, 36, 50)
MUTED = (86, 100, 120)
SOFT = (224, 231, 241)
WHITE = (255, 255, 255)
GREEN = (34, 150, 98)
RED = (203, 73, 73)
YELLOW = (244, 190, 77)


def parse_size(raw: str) -> tuple[int, int]:
    try:
        w, h = raw.lower().split("x", 1)
        return int(w), int(h)
    except Exception as exc:
        raise argparse.ArgumentTypeError("size must look like 960x540") from exc


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "item"


@lru_cache(maxsize=None)
def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    candidates: list[str] = []
    if mono:
        candidates.extend(
            [
                "/System/Library/Fonts/Menlo.ttc",
                "/System/Library/Fonts/Supplemental/Courier New.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            ]
        )
    elif bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    text = " ".join(str(text).replace("\n", " ").split())
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if text_size(draw, candidate, fnt)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        while text_size(draw, current, fnt)[0] > max_width and len(current) > 8:
            split_at = max(6, int(len(current) * 0.72))
            lines.append(current[:split_at] + "-")
            current = current[split_at:]
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    max_width: int,
    *,
    size: int,
    fill: tuple[int, int, int] = INK,
    bold: bool = False,
    mono: bool = False,
    line_gap: int = 6,
    max_lines: int | None = None,
) -> int:
    fnt = font(size, bold=bold, mono=mono)
    lines = wrap_text(draw, text, fnt, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(".") + "..."
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + line_gap
    return y


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    radius: int = 8,
    fill: tuple[int, int, int] = WHITE,
    outline: tuple[int, int, int] = SOFT,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def load_specs() -> dict[str, dict[str, Any]]:
    specs = {}
    for path in SPEC_DIR.glob("*.json"):
        spec = json.loads(path.read_text(encoding="utf-8"))
        specs[spec["id"]] = spec
    return specs


def preview_paths(preview_root: Path, papers: set[str] | None, adapters: set[str] | None) -> list[Path]:
    paths = sorted(preview_root.glob("*/*/preview.json"))

    def key(path: Path) -> tuple[int, int, str]:
        adapter = path.parts[-3]
        paper = path.parts[-2]
        try:
            a_idx = ADAPTER_ORDER.index(adapter)
        except ValueError:
            a_idx = len(ADAPTER_ORDER)
        try:
            p_idx = PAPER_ORDER.index(paper)
        except ValueError:
            p_idx = len(PAPER_ORDER)
        return a_idx, p_idx, str(path)

    selected = []
    for path in sorted(paths, key=key):
        adapter = path.parts[-3]
        paper = path.parts[-2]
        if papers and paper not in papers:
            continue
        if adapters and adapter not in adapters:
            continue
        selected.append(path)
    return selected


def extract_items(adapter: str, preview: dict[str, Any]) -> list[dict[str, Any]]:
    if preview.get("parse_failed"):
        return [
            {
                "title": "Preview parse failed",
                "body": preview.get("raw_text_preview", "No preview content."),
                "details": [],
                "formulas": [],
                "meta": ["Manual repair needed before rendering."],
            }
        ]
    if adapter == "paper2manim":
        return [
            {
                "title": scene.get("name", f"Scene {idx}"),
                "body": scene.get("description", ""),
                "details": scene.get("teaching_unit_ids", []),
                "formulas": scene.get("formula_refs", []),
                "meta": scene.get("code_refs", []),
            }
            for idx, scene in enumerate(preview.get("scenes", []), start=1)
        ]
    if adapter == "code2video":
        return [
            {
                "title": section.get("title", f"Section {idx}"),
                "body": " | ".join(section.get("lecture_lines", [])),
                "details": section.get("animations", []),
                "formulas": [],
                "meta": ["key section" if section.get("key_section") else "supporting section"],
            }
            for idx, section in enumerate(preview.get("sections", []), start=1)
        ]
    if adapter == "theorem_explain_agent":
        return [
            {
                "title": f"Scene {plan.get('scene', idx)}",
                "body": plan.get("vision_storyboard", ""),
                "details": [plan.get("technical_implementation", ""), plan.get("animation_narration", "")],
                "formulas": [],
                "meta": [],
            }
            for idx, plan in enumerate(preview.get("implementation_plans", []), start=1)
        ]
    if adapter == "llm2manim":
        return [
            {
                "title": f"{step.get('step', f'step_{idx}')} / {step.get('template', 'template')}",
                "body": step.get("visual_plan", ""),
                "details": [step.get("hitl_question", "")],
                "formulas": step.get("formula_refs", []),
                "meta": [],
            }
            for idx, step in enumerate(preview.get("pedagogy_steps", []), start=1)
        ]
    if adapter == "manimtrainer":
        return [
            {
                "title": plan.get("scene", f"Scene {idx}"),
                "body": plan.get("manim_sketch", ""),
                "details": plan.get("reward_targets", []),
                "formulas": [],
                "meta": [plan.get("self_review", "")],
            }
            for idx, plan in enumerate(preview.get("training_style_plan", []), start=1)
        ]
    return []


def draw_pipeline(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    adapter: str,
    active: int,
    accent: tuple[int, int, int],
) -> None:
    rounded(draw, box, radius=8, fill=(252, 253, 255), outline=SOFT)
    x1, y1, x2, y2 = box
    steps = ADAPTER_PIPELINES.get(adapter, ["Input", "Plan", "Render", "Review"])
    draw.text((x1 + 18, y1 + 14), "Pipeline", font=font(18, bold=True), fill=INK)
    usable_x1 = x1 + 18
    usable_x2 = x2 - 18
    y = y1 + 58
    step_w = (usable_x2 - usable_x1) / len(steps)
    for idx, step in enumerate(steps):
        cx = int(usable_x1 + step_w * idx + step_w / 2)
        color = accent if idx == active else (185, 196, 212)
        draw.line((cx, y, cx, y + 18), fill=color, width=3)
        draw.ellipse((cx - 8, y - 8, cx + 8, y + 8), fill=color)
        max_w = max(70, int(step_w) - 12)
        label_y = y + 28
        fnt = font(13, bold=idx == active)
        lines = wrap_text(draw, step, fnt, max_w)[:2]
        for line in lines:
            tw, _ = text_size(draw, line, fnt)
            draw.text((cx - tw / 2, label_y), line, font=fnt, fill=INK if idx == active else MUTED)
            label_y += 15
        if idx < len(steps) - 1:
            next_cx = int(usable_x1 + step_w * (idx + 1) + step_w / 2)
            draw.line((cx + 12, y, next_cx - 12, y), fill=(205, 214, 226), width=2)
    draw.rectangle((x1, y2 - 5, int(x1 + (x2 - x1) * ((active + 1) / len(steps))), y2), fill=accent)


def draw_formula_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    formulas: list[str],
    details: list[str],
    meta: list[str],
) -> None:
    rounded(draw, box, radius=8, fill=WHITE, outline=SOFT)
    x1, y1, x2, y2 = box
    draw.text((x1 + 18, y1 + 16), "Grounding", font=font(18, bold=True), fill=INK)
    y = y1 + 50
    lines = [line for line in formulas if line] + [line for line in details if line] + [line for line in meta if line]
    if not lines:
        lines = ["No extra grounding emitted by this preview."]
    for idx, line in enumerate(lines[:7]):
        dot_color = GREEN if idx < len(formulas) else YELLOW if idx < len(formulas) + len(details) else RED
        draw.ellipse((x1 + 18, y + 5, x1 + 26, y + 13), fill=dot_color)
        y = draw_wrapped(
            draw,
            (x1 + 34, y),
            line,
            x2 - x1 - 52,
            size=14,
            fill=MUTED,
            mono=idx < len(formulas),
            max_lines=2,
        )
        y += 4
        if y > y2 - 22:
            break


def draw_scene_frame(
    record: dict[str, Any],
    spec: dict[str, Any],
    item: dict[str, Any],
    item_idx: int,
    item_count: int,
    local_t: float,
    size: tuple[int, int],
) -> Image.Image:
    adapter = record["adapter"]
    accent = ACCENTS.get(adapter, (60, 120, 190))
    w, h = size
    img = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, w, 9), fill=accent)
    draw.text((34, 27), ADAPTER_LABELS.get(adapter, adapter), font=font(25, bold=True), fill=accent)
    draw.text((34, 60), spec.get("short_title", record["paper_id"]), font=font(36, bold=True), fill=INK)
    provider = f"{record.get('provider', 'unknown')} / {record.get('model', 'unknown')}"
    draw.text((w - 34, 35), provider, font=font(14), fill=MUTED, anchor="ra")
    draw.text((w - 34, 58), "baseline-style coverage render", font=font(14, bold=True), fill=INK, anchor="ra")

    draw_pipeline(draw, (34, 108, w - 34, 210), adapter, item_idx % len(ADAPTER_PIPELINES.get(adapter, [1])), accent)

    left = (34, 235, int(w * 0.58), h - 54)
    right = (int(w * 0.60), 235, w - 34, h - 54)
    rounded(draw, left, radius=8, fill=WHITE, outline=SOFT)
    x1, y1, x2, y2 = left
    draw.rectangle((x1, y1, x1 + 8, y2), fill=accent)
    draw.text((x1 + 24, y1 + 20), f"{item_idx + 1}/{item_count}", font=font(15, bold=True), fill=accent)
    draw_wrapped(draw, (x1 + 24, y1 + 46), item.get("title", "Scene"), x2 - x1 - 48, size=25, bold=True, max_lines=2)
    progress = ease(local_t)
    draw.rectangle((x1 + 24, y1 + 118, x2 - 24, y1 + 124), fill=(232, 237, 246))
    draw.rectangle((x1 + 24, y1 + 118, int(x1 + 24 + (x2 - x1 - 48) * progress), y1 + 124), fill=accent)
    body_end = draw_wrapped(
        draw,
        (x1 + 24, y1 + 146),
        item.get("body", ""),
        x2 - x1 - 48,
        size=18,
        fill=INK,
        max_lines=4,
    )

    expected_gap = record.get("preview", {}).get("expected_gap", "")
    if expected_gap and body_end < y2 - 76:
        draw.text((x1 + 24, y2 - 62), "Expected gap", font=font(15, bold=True), fill=RED)
        draw_wrapped(draw, (x1 + 24, y2 - 40), expected_gap, x2 - x1 - 48, size=13, fill=MUTED, max_lines=2)

    draw_formula_panel(draw, right, item.get("formulas", []), item.get("details", []), item.get("meta", []))

    footer = f"{spec.get('central_question', '')}"
    draw_wrapped(draw, (34, h - 38), footer, w - 68, size=13, fill=MUTED, max_lines=1)
    return img


def render_video(
    record: dict[str, Any],
    spec: dict[str, Any],
    items: list[dict[str, Any]],
    out_video: Path,
    *,
    size: tuple[int, int],
    fps: int,
    seconds_per_item: float,
) -> dict[str, Any]:
    out_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{size[0]}x{size[1]}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_video),
    ]
    frames_per_item = max(1, int(round(fps * seconds_per_item)))
    started = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for item_idx, item in enumerate(items):
        for frame_idx in range(frames_per_item):
            local_t = frame_idx / max(frames_per_item - 1, 1)
            frame = draw_scene_frame(record, spec, item, item_idx, len(items), local_t, size)
            proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {out_video} with exit code {returncode}")
    elapsed = round(time.time() - started, 3)
    duration = round(len(items) * frames_per_item / fps, 3)
    return {"render_elapsed_sec": elapsed, "duration_sec": duration, "frames": len(items) * frames_per_item}


def usage_from(record: dict[str, Any]) -> dict[str, Any] | None:
    raw = record.get("raw_response") or {}
    usage = raw.get("usage")
    return usage if isinstance(usage, dict) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-root", default="runs/reproductions/previews")
    parser.add_argument("--out-dir", default="runs/baseline_coverage")
    parser.add_argument("--papers", nargs="*", default=None)
    parser.add_argument("--adapters", nargs="*", default=None)
    parser.add_argument("--size", default="960x540", type=parse_size)
    parser.add_argument("--fps", default=12, type=int)
    parser.add_argument("--seconds-per-item", default=2.5, type=float)
    parser.add_argument("--max-items", default=5, type=int)
    args = parser.parse_args()

    preview_root = ROOT / args.preview_root
    out_dir = ROOT / args.out_dir
    specs = load_specs()
    papers = set(args.papers) if args.papers else None
    adapters = set(args.adapters) if args.adapters else None
    paths = preview_paths(preview_root, papers, adapters)
    if not paths:
        raise SystemExit(f"No preview files found under {preview_root}")

    run_started = datetime.now(timezone.utc).isoformat()
    manifest = []
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        adapter = record["adapter"]
        paper_id = record["paper_id"]
        spec = specs.get(paper_id, {"short_title": paper_id, "central_question": ""})
        items = extract_items(adapter, record.get("preview", {}))[: args.max_items]
        if not items:
            items = [
                {
                    "title": "No scenes emitted",
                    "body": "The preview did not emit a renderable planning unit.",
                    "details": [],
                    "formulas": [],
                    "meta": [],
                }
            ]

        video_name = f"{slug(adapter)}__{slug(paper_id)}.mp4"
        target_dir = out_dir / adapter / paper_id
        out_video = target_dir / video_name
        render_meta = render_video(
            record,
            spec,
            items,
            out_video,
            size=args.size,
            fps=args.fps,
            seconds_per_item=args.seconds_per_item,
        )
        usage = usage_from(record)
        item = {
            "adapter": adapter,
            "adapter_label": ADAPTER_LABELS.get(adapter, adapter),
            "paper_id": paper_id,
            "paper_title": spec.get("title", paper_id),
            "provider": record.get("provider"),
            "model": record.get("model"),
            "preview_elapsed_sec": record.get("elapsed_sec"),
            "usage": usage,
            "api_cost_usd": None,
            "api_cost_note": "No provider rate card was applied; usage is recorded when present.",
            "source_preview": str(path),
            "video": str(out_video),
            "video_size_bytes": out_video.stat().st_size,
            "renderer_type": "deterministic_preview_renderer",
            "framework_status": "baseline-style render; not a full upstream framework run",
            "pipeline_steps": ADAPTER_PIPELINES.get(adapter, []),
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            **render_meta,
        }
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "run_manifest.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
        manifest.append(item)
        print(f"rendered {out_video}")

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "started_at": run_started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "preview_root": str(preview_root),
        "renderer_type": "deterministic_preview_renderer",
        "note": "Coverage videos are generated from framework-style previews, not full upstream framework render loops.",
        "items": manifest,
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
