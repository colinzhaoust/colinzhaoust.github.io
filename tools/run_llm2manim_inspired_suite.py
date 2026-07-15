#!/usr/bin/env python3
"""Render the LLM2Manim-inspired five-topic reproduction suite.

This is a method-level reproduction of the LLM2Manim paper pipeline, not an
official repository run. It renders five topic clips and marks the artifacts as
paper-method reconstructions.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENE_FILE = ROOT / "scenes" / "llm2manim_inspired_suite.py"
SPEC_DIR = ROOT / "experiments" / "reproductions" / "paper_specs"

TOPICS = [
    ("feynrl", "LLM2ManimFeynRL"),
    ("dpo", "LLM2ManimDPO"),
    ("attention", "LLM2ManimAttention"),
    ("transformers", "LLM2ManimTransformers"),
    ("rope", "LLM2ManimRoPE"),
]

PIPELINE_STEPS = [
    "concept brief",
    "segmentation",
    "symbol ledger",
    "constrained template",
    "HITL checkpoint",
    "partial regeneration note",
    "render",
]


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def load_specs() -> dict[str, dict[str, Any]]:
    specs = {}
    for path in SPEC_DIR.glob("*.json"):
        spec = json.loads(path.read_text(encoding="utf-8"))
        specs[spec["id"]] = spec
    return specs


def find_rendered_video(media_dir: Path, scene_name: str, output_name: str) -> Path:
    candidates = sorted((media_dir / "videos").glob(f"**/{output_name}.mp4"))
    if not candidates:
        candidates = sorted((media_dir / "videos").glob(f"**/{scene_name}.mp4"))
    if not candidates:
        raise FileNotFoundError(f"No rendered video found for {scene_name} under {media_dir}")
    return candidates[-1]


def update_manifest(manifest_path: Path, records: list[dict[str, Any]]) -> None:
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    by_topic = {record["paper_id"]: record for record in records}
    new_items = []
    replaced = set()
    for item in items:
        if item.get("adapter") == "llm2manim" and item.get("paper_id") in by_topic:
            new_items.append(by_topic[item["paper_id"]])
            replaced.add(item["paper_id"])
        else:
            new_items.append(item)
    for topic, record in by_topic.items():
        if topic not in replaced:
            new_items.append(record)
    manifest["items"] = new_items
    manifest["renderer_type"] = "mixed_preview_and_method_reproduction"
    manifest["note"] = (
        "Most coverage videos are deterministic framework-style previews. "
        "The LLM2Manim row is a method-level reproduction built from the paper pipeline, "
        "not an official LLM2Manim repository run."
    )
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_readme(out_dir: Path) -> None:
    text = """# LLM2Manim-Inspired Reproduction

This folder is a paper-method reproduction, not an official LLM2Manim repository run.

The upstream LLM2Manim paper emphasizes a human-in-the-loop pipeline with:

- segmentation;
- symbol ledgers;
- constrained prompt/templates;
- partial regeneration of failed segments;
- expert/HITL checkpoints;
- final rendering and learning-oriented evaluation.

The videos in this folder implement those ideas directly in Manim for the five local
baseline topics: FeynRL/P3O, DPO, scaled dot-product attention, Transformers, and RoPE.
They should be compared as "LLM2Manim-inspired" artifacts, not as results from a released
LLM2Manim codebase or checkpoint.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manim", default=str(ROOT / ".venv-arm64" / "bin" / "manim"))
    parser.add_argument("--media-dir", default="runs/llm2manim_inspired_media")
    parser.add_argument("--out-dir", default="runs/reproductions/llm2manim_inspired")
    parser.add_argument("--site-dir", default="progress_site/assets/baseline-coverage")
    parser.add_argument("--quality", default="-ql")
    parser.add_argument("--skip-site", action="store_true")
    args = parser.parse_args()

    media_dir = ROOT / args.media_dir
    out_dir = ROOT / args.out_dir
    site_dir = ROOT / args.site_dir
    specs = load_specs()
    started = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    out_dir.mkdir(parents=True, exist_ok=True)
    write_readme(out_dir)

    for topic, scene_name in TOPICS:
        output_name = f"llm2manim__{topic}"
        topic_dir = out_dir / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            args.manim,
            args.quality,
            "--media_dir",
            str(media_dir),
            str(SCENE_FILE),
            scene_name,
            "-o",
            output_name,
        ]
        run(cmd)
        rendered = find_rendered_video(media_dir, scene_name, output_name)
        target = topic_dir / f"{output_name}.mp4"
        shutil.copyfile(rendered, target)
        spec = specs.get(topic, {"title": topic, "short_title": topic})
        records.append(
            {
                "adapter": "llm2manim",
                "adapter_label": "LLM2Manim-inspired",
                "paper_id": topic,
                "paper_title": spec.get("title", topic),
                "provider": "local",
                "model": "deterministic Manim scene templates",
                "preview_elapsed_sec": None,
                "usage": None,
                "api_cost_usd": 0,
                "api_cost_note": "No API call. This is a paper-method reproduction implemented locally.",
                "source_preview": str(SCENE_FILE),
                "video": str(target),
                "video_size_bytes": target.stat().st_size,
                "renderer_type": "llm2manim_inspired_manim_renderer",
                "framework_status": "method-level reproduction; not an official LLM2Manim repo/checkpoint run",
                "pipeline_steps": PIPELINE_STEPS,
                "replication_note": "Generated by our LLM2Manim-inspired pipeline from paper specs.",
                "rendered_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    videos = [record["video"] for record in records]
    probe_dir = out_dir / "probe"
    run([str(ROOT / ".venv-arm64" / "bin" / "python"), str(ROOT / "tools" / "probe_rendered_videos.py"), "--videos", *videos, "--out-dir", str(probe_dir)])
    probe_records = json.loads((probe_dir / "probe_report.json").read_text(encoding="utf-8"))
    probe_by_stem = {Path(record["video"]).stem: record for record in probe_records}
    for record in records:
        stem = Path(record["video"]).stem
        probe = probe_by_stem[stem]
        record["duration_sec"] = round(float(probe["duration_sec"]), 3)
        record["width"] = probe["width"]
        record["height"] = probe["height"]
        record["fps"] = probe["fps"]
        record["contact_sheet"] = probe["contact_sheet"]

    summary = {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "renderer_type": "llm2manim_inspired_manim_renderer",
        "framework_status": "method-level reproduction; not an official LLM2Manim repo/checkpoint run",
        "items": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not args.skip_site:
        for record in records:
            stem = Path(record["video"]).stem
            topic = record["paper_id"]
            video_target = site_dir / "videos" / f"{stem}.mp4"
            sheet_target = site_dir / "contact-sheets" / f"{stem}.png"
            poster_target = site_dir / "posters" / f"{stem}.png"
            video_target.parent.mkdir(parents=True, exist_ok=True)
            sheet_target.parent.mkdir(parents=True, exist_ok=True)
            poster_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(record["video"], video_target)
            shutil.copyfile(record["contact_sheet"], sheet_target)
            frame = out_dir / "probe" / "frames" / stem / "01.png"
            shutil.copyfile(frame, poster_target)

            per_topic_manifest = ROOT / "runs" / "baseline_coverage" / "llm2manim" / topic / "run_manifest.json"
            per_topic_manifest.parent.mkdir(parents=True, exist_ok=True)
            per_topic_manifest.write_text(json.dumps(record, indent=2), encoding="utf-8")

        update_manifest(ROOT / "runs" / "baseline_coverage" / "manifest.json", records)
        update_manifest(site_dir / "manifests" / "manifest.json", records)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
