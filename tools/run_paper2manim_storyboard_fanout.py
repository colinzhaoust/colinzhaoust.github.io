#!/usr/bin/env python3
"""Render every scene from a Paper2Manim MVP1 storyboard.

Paper2Manim's MVP1 graph can produce a multi-scene storyboard but renders only
the current scene index, which defaults to 0. This driver keeps the upstream
storyboarder/coder/render pieces intact and fans out a saved storyboard across
all scene indices, then concatenates the successful renders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from paper2manim.agents.coder import coder_node
from paper2manim.artifacts import append_trace, run_dir, save_attempt_result, save_json
from paper2manim.sandbox.concat import concat_videos
from paper2manim.sandbox.render import render


def load_storyboard(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "scenes" not in data or not isinstance(data["scenes"], list):
        raise ValueError(f"{path} does not look like a Paper2Manim storyboard")
    return data


def render_scene(
    *,
    run_id: str,
    storyboard: dict[str, Any],
    scene_idx: int,
    quality: str,
    max_retries: int,
) -> dict[str, Any]:
    scene = storyboard["scenes"][scene_idx]
    scene_name = scene["name"]
    error_feedback: dict[str, Any] | None = None
    attempts: list[dict[str, Any]] = []

    for attempt_idx in range(max_retries + 1):
        state: dict[str, Any] = {
            "run_id": run_id,
            "storyboard": storyboard,
            "current_scene_idx": scene_idx,
            "iter_count": attempt_idx,
            "quality": quality,
            "skip_render": False,
            "retrieved_success": [],
            "retrieved_failure": [],
            "error_feedback": error_feedback,
        }
        code_result = coder_node(state)  # Saves attempts/<iter>_<scene>.py.
        code = code_result.get("current_code")
        if not code:
            raise RuntimeError(f"coder produced no code for scene {scene_name}")

        workdir = run_dir(run_id) / "attempts" / f"work_{scene_name}_{attempt_idx:02d}_fanout"
        rr = render(code, scene_name, quality=quality, workdir=workdir)
        save_attempt_result(run_id, scene_name, attempt_idx, rr)
        append_trace(
            run_id,
            "fanout_render",
            {
                "scene": scene_name,
                "scene_idx": scene_idx,
                "iter": attempt_idx,
                "status": rr.get("status"),
                "category": rr.get("category"),
            },
        )
        attempts.append({"iter": attempt_idx, "code": code, "render_result": rr})

        if rr.get("status") == "success" and rr.get("video_path"):
            return {
                "scene": scene_name,
                "scene_idx": scene_idx,
                "status": "success",
                "video_path": rr["video_path"],
                "attempts": attempts,
            }

        error_feedback = {
            "render_result": rr,
            "hint": "Fix the Manim code. Prefer Text over MathTex and avoid external assets.",
        }

    return {
        "scene": scene_name,
        "scene_idx": scene_idx,
        "status": "failed",
        "video_path": None,
        "attempts": attempts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--quality", default="l", choices=["l", "m", "h"])
    parser.add_argument("--max-retries", default=1, type=int)
    parser.add_argument("--output-name", default="output_fanout.mp4")
    parser.add_argument(
        "--scene-indices",
        default=None,
        help="Optional comma-separated zero-based scene indices to render.",
    )
    parser.add_argument(
        "--merge-results",
        default=None,
        type=Path,
        help="Optional prior fanout_results.json to merge updated scene results into.",
    )
    parser.add_argument("--results-name", default="fanout_results")
    args = parser.parse_args()

    storyboard = load_storyboard(args.storyboard)
    if args.scene_indices:
        scene_indices = [int(part.strip()) for part in args.scene_indices.split(",") if part.strip()]
    else:
        scene_indices = list(range(len(storyboard["scenes"])))

    results = []
    for idx in scene_indices:
        result = render_scene(
            run_id=args.run_id,
            storyboard=storyboard,
            scene_idx=idx,
            quality=args.quality,
            max_retries=args.max_retries,
        )
        results.append(result)

    if args.merge_results:
        merged_by_idx = {
            int(result["scene_idx"]): result
            for result in json.loads(args.merge_results.read_text(encoding="utf-8"))
        }
        for result in results:
            merged_by_idx[int(result["scene_idx"])] = result
        final_results = [merged_by_idx[idx] for idx in sorted(merged_by_idx)]
    else:
        final_results = results

    video_paths = [
        result["video_path"]
        for result in final_results
        if result["status"] == "success" and result.get("video_path")
    ]

    save_json(args.run_id, args.results_name, final_results)
    if not video_paths:
        raise SystemExit("No scenes rendered successfully; not concatenating.")

    final_path = run_dir(args.run_id) / "final" / args.output_name
    concat_videos(video_paths, final_path)
    print(json.dumps({"final_video_path": str(final_path), "scenes_rendered": len(video_paths)}, indent=2))


if __name__ == "__main__":
    main()
