#!/usr/bin/env python3
"""Run TheoremExplainAgent in WInE-backed planning mode.

This keeps TEA's upstream planner and implementation-plan generation intact,
while supplying an OpenAI-compatible WInE endpoint and avoiding repository
secrets.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


WINE_BASE_URL = "https://ai-gateway.andrew.cmu.edu/v1"
DEFAULT_MODEL = "openai/wine-claude-haiku-4-5"


def read_api_key_file(path: Path) -> str | None:
    if not path.exists():
        return None
    pairs: dict[str, str] = {}
    bare_values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, value = line.split("=", 1)
            pairs[name.strip()] = value.strip().strip("'\"")
        else:
            bare_values.append(line.strip().strip("'\""))
    for name in ("WINE_LAB_API_KEY", "WINE_API_KEY", "OPENAI_API_KEY", "API_KEY"):
        if pairs.get(name):
            return pairs[name]
    for value in pairs.values():
        if value:
            return value
    return bare_values[0] if bare_values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tea-root", default="external/TheoremExplainAgent-main", type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--helper-model", default=None)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-file", default=Path("~/.secrets/wine_litellm_api_key.txt"), type=Path)
    parser.add_argument("--base-url", default=WINE_BASE_URL)
    parser.add_argument("--max-scene-concurrency", default=1, type=int)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    repo_root = Path.cwd()
    tea_root = args.tea_root if args.tea_root.is_absolute() else repo_root / args.tea_root
    tea_root = tea_root.resolve()
    if not (tea_root / "generate_video.py").exists():
        raise SystemExit(f"TEA root does not contain generate_video.py: {tea_root}")

    api_key = (
        args.api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("WINE_API_KEY")
        or os.environ.get("WINE_LAB_API_KEY")
        or read_api_key_file(args.api_key_file.expanduser())
    )
    if not api_key:
        raise SystemExit(f"No WInE API key found. Checked env vars and {args.api_key_file}.")

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_API_BASE"] = args.base_url
    env["OPENAI_BASE_URL"] = args.base_url
    env["PYTHONPATH"] = f"{tea_root}{os.pathsep}{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable,
        "generate_video.py",
        "--model",
        args.model,
        "--topic",
        args.topic,
        "--context",
        args.context,
        "--output_dir",
        str(args.output_dir),
        "--only_plan",
        "--max_scene_concurrency",
        str(args.max_scene_concurrency),
    ]
    if args.helper_model:
        cmd.extend(["--helper_model", args.helper_model])
    if args.verbose:
        cmd.append("--verbose")

    subprocess.run(cmd, cwd=tea_root, env=env, check=True)


if __name__ == "__main__":
    main()
