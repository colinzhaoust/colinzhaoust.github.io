#!/usr/bin/env python3
"""Render a deterministic repair scene and merge it into fanout results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from paper2manim.artifacts import run_dir, save_attempt_code, save_attempt_result, save_json
from paper2manim.sandbox.concat import concat_videos
from paper2manim.sandbox.render import render


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scene-name", required=True)
    parser.add_argument("--scene-idx", required=True, type=int)
    parser.add_argument("--code-path", required=True, type=Path)
    parser.add_argument("--iter-idx", default=99, type=int)
    parser.add_argument("--quality", default="l", choices=["l", "m", "h"])
    parser.add_argument("--merge-results", required=True, type=Path)
    parser.add_argument("--results-name", default="fanout_results_repaired")
    parser.add_argument("--output-name", default="output_fanout_repaired.mp4")
    args = parser.parse_args()

    code = args.code_path.read_text(encoding="utf-8")
    save_attempt_code(args.run_id, args.scene_name, args.iter_idx, code)
    workdir = run_dir(args.run_id) / "attempts" / f"work_{args.scene_name}_{args.iter_idx:02d}_manual"
    rr = render(code, args.scene_name, quality=args.quality, workdir=workdir)
    save_attempt_result(args.run_id, args.scene_name, args.iter_idx, rr)

    repaired = {
        "scene": args.scene_name,
        "scene_idx": args.scene_idx,
        "status": "success" if rr.get("status") == "success" and rr.get("video_path") else "failed",
        "video_path": rr.get("video_path"),
        "attempts": [{"iter": args.iter_idx, "code": code, "render_result": rr}],
        "repair": "manual_no_latex_scene",
    }

    merged_by_idx: dict[int, dict[str, Any]] = {
        int(result["scene_idx"]): result
        for result in json.loads(args.merge_results.read_text(encoding="utf-8"))
    }
    merged_by_idx[args.scene_idx] = repaired
    final_results = [merged_by_idx[idx] for idx in sorted(merged_by_idx)]
    save_json(args.run_id, args.results_name, final_results)

    video_paths = [
        result["video_path"]
        for result in final_results
        if result["status"] == "success" and result.get("video_path")
    ]
    if not video_paths:
        raise SystemExit("No successful videos after repair.")

    final_path = run_dir(args.run_id) / "final" / args.output_name
    concat_videos(video_paths, final_path)
    print(json.dumps({"final_video_path": str(final_path), "scenes_rendered": len(video_paths)}, indent=2))


if __name__ == "__main__":
    main()
