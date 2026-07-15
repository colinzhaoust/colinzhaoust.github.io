#!/usr/bin/env python3
"""Run the in-house paper explainer Manim suite end to end."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "data" / "inhouse_paper_video_specs.json"


def find_manim() -> str:
    candidates = [
        ROOT / ".venv-arm64" / "bin" / "manim",
        ROOT / ".venv" / "bin" / "manim",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("manim")
    if found:
        return found
    raise SystemExit("Could not find manim. Set --manim-bin or install/use the local venv.")


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def load_specs(selected: set[str] | None) -> list[dict]:
    specs = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if selected:
        specs = [spec for spec in specs if spec["id"] in selected or spec["scene_class"] in selected]
    if not specs:
        raise SystemExit("No matching specs selected.")
    return specs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="Spec ids or scene class names to run. Defaults to all.")
    parser.add_argument("--quality", default="-ql")
    parser.add_argument("--media-dir", default="runs/inhouse_manim_media")
    parser.add_argument("--eval-dir", default="runs/inhouse_eval")
    parser.add_argument("--manim-bin")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--skip-probe", action="store_true")
    parser.add_argument("--review-provider", choices=["none", "mock", "wine", "openai_compatible", "bedrock"], default="none")
    parser.add_argument("--review-model", default="wine-gemini-2.5-flash")
    parser.add_argument("--review-max-tokens", type=int, default=4096)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-file")
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--aws-key-file")
    args = parser.parse_args()

    specs = load_specs(set(args.ids) if args.ids else None)
    media_dir = ROOT / args.media_dir
    eval_dir = ROOT / args.eval_dir
    manim_bin = args.manim_bin or find_manim()

    if not args.skip_render:
        source_files = sorted({str(ROOT / spec["source_file"]) for spec in specs})
        if len(source_files) != 1:
            raise SystemExit("Current suite expects selected scenes to share one source file.")
        run([manim_bin, args.quality, "--media_dir", str(media_dir), source_files[0], *[spec["scene_class"] for spec in specs]])

    videos = [str(ROOT / spec["rendered_video"]) for spec in specs]
    if not args.skip_probe:
        run([sys.executable, str(ROOT / "tools" / "probe_rendered_videos.py"), "--videos", *videos, "--out-dir", str(eval_dir)])

    if args.review_provider != "none":
        for spec in specs:
            out = eval_dir / "vlm_reviews" / f"{spec['scene_class']}.{args.review_provider}.json"
            cmd = [
                sys.executable,
                str(ROOT / "tools" / "vlm_render_review.py"),
                "--provider",
                args.review_provider,
                "--model",
                args.review_model,
                "--max-tokens",
                str(args.review_max_tokens),
                "--image",
                str(ROOT / spec["contact_sheet"]),
                "--paper",
                spec["paper_or_topic"],
                "--goal",
                spec["teaching_goal"],
                "--out",
                str(out),
            ]
            if args.base_url:
                cmd += ["--base-url", args.base_url]
            if args.api_key_file:
                cmd += ["--api-key-file", args.api_key_file]
            if args.aws_key_file:
                cmd += ["--aws-key-file", args.aws_key_file]
            if args.aws_region:
                cmd += ["--aws-region", args.aws_region]
            run(cmd)

    print(f"Completed {len(specs)} scene(s). Probe report: {eval_dir / 'probe_report.md'}")


if __name__ == "__main__":
    main()
