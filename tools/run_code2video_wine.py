#!/usr/bin/env python3
"""Run the upstream Code2Video pipeline through a WInE/OpenAI-compatible API.

This is a thin adapter around external/Code2Video-main/src/agent.py. It keeps
Code2Video's own outline -> storyboard -> Manim-code -> render -> concat flow,
while fixing local path assumptions and avoiding secrets in the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


WINE_BASE_URL = "https://ai-gateway.andrew.cmu.edu/v1"
DEFAULT_WINE_MODEL = "wine-claude-haiku-4-5"


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
    for name in ("WINE_LAB_API_KEY", "WINE_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY", "API_KEY"):
        if pairs.get(name):
            return pairs[name]
    for value in pairs.values():
        if value:
            return value
    return bare_values[0] if bare_values else None


def ensure_tree_link(link: Path, target: Path) -> None:
    if link.exists() or link.is_symlink():
        return
    if not target.exists():
        raise FileNotFoundError(f"Missing Code2Video asset tree: {target}")
    try:
        os.symlink(os.path.relpath(target, start=link.parent), link, target_is_directory=True)
    except OSError:
        shutil.copytree(target, link)


def ensure_code2video_layout(root: Path) -> Path:
    src = root / "src"
    if not src.exists():
        raise FileNotFoundError(f"Code2Video src directory does not exist: {src}")
    ensure_tree_link(src / "json_files", root / "json_files")
    ensure_tree_link(src / "assets", root / "assets")
    return src


def configure_wine(args: argparse.Namespace) -> None:
    api_key = (
        args.api_key
        or os.environ.get("CLAUDE_API_KEY")
        or os.environ.get("WINE_API_KEY")
        or os.environ.get("WINE_LAB_API_KEY")
        or read_api_key_file(args.api_key_file.expanduser())
    )
    if not api_key:
        raise SystemExit(f"No WInE API key found. Checked env vars and {args.api_key_file}.")

    os.environ["CLAUDE_BASE_URL"] = args.base_url
    os.environ["CLAUDE_MODEL"] = args.model
    os.environ["CLAUDE_API_KEY"] = api_key
    os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"


def import_code2video(root: Path, src: Path):
    sys.path.insert(0, str(src))
    sys.path.insert(0, str(root))
    from agent import RunConfig, TeachingVideoAgent, get_api_and_output  # type: ignore

    return RunConfig, TeachingVideoAgent, get_api_and_output


def trim_sections(agent: Any, max_sections: int) -> None:
    if max_sections <= 0 or len(agent.sections) <= max_sections:
        return
    keep_ids = {section.id for section in agent.sections[:max_sections]}
    agent.sections = agent.sections[:max_sections]
    if isinstance(agent.enhanced_storyboard, dict):
        trimmed = {
            **agent.enhanced_storyboard,
            "sections": [
                section
                for section in agent.enhanced_storyboard.get("sections", [])
                if section.get("id") in keep_ids
            ],
        }
        (agent.output_dir / "storyboard_trimmed_for_run.json").write_text(
            json.dumps(trimmed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def section_summary(agent: Any) -> list[dict[str, Any]]:
    rows = []
    for section in agent.sections:
        rows.append(
            {
                "id": section.id,
                "title": section.title,
                "rendered": section.id in agent.section_videos,
                "video_path": agent.section_videos.get(section.id),
                "code_path": str(agent.output_dir / f"{section.id}.py"),
                "lecture_lines": section.lecture_lines,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code2video-root", default="external/Code2Video-main", type=Path)
    parser.add_argument("--knowledge-point", required=True)
    parser.add_argument("--folder-prefix", default="REPRO")
    parser.add_argument("--base-url", default=WINE_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_WINE_MODEL)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-file", default=Path("~/.secrets/wine_litellm_api_key.txt"), type=Path)
    parser.add_argument("--max-sections", default=4, type=int)
    parser.add_argument("--max-code-token-length", default=8000, type=int)
    parser.add_argument("--max-fix-bug-tries", default=3, type=int)
    parser.add_argument("--max-regenerate-tries", default=2, type=int)
    parser.add_argument("--feedback", action="store_true", default=False)
    parser.add_argument("--assets", action="store_true", default=False)
    parser.add_argument("--out-summary", type=Path)
    args = parser.parse_args()

    repo_root = Path.cwd()
    root = args.code2video_root
    if not root.is_absolute():
        root = repo_root / root
    root = root.resolve()
    src = ensure_code2video_layout(root)
    configure_wine(args)

    RunConfig, TeachingVideoAgent, get_api_and_output = import_code2video(root, src)
    api, folder_name = get_api_and_output("claude")
    folder = src / "CASES" / f"{args.folder_prefix}_{folder_name}"
    cfg = RunConfig(
        api=api,
        use_feedback=args.feedback,
        use_assets=args.assets,
        max_code_token_length=args.max_code_token_length,
        max_fix_bug_tries=args.max_fix_bug_tries,
        max_regenerate_tries=args.max_regenerate_tries,
    )
    agent = TeachingVideoAgent(idx=0, knowledge_point=args.knowledge_point, folder=folder, cfg=cfg)

    agent.generate_outline()
    agent.generate_storyboard()
    trim_sections(agent, args.max_sections)

    for section in agent.sections:
        agent.generate_section_code(section, attempt=1)

    for section in agent.sections:
        agent.render_section(section)

    final_video = agent.merge_videos() if agent.section_videos else None
    summary = {
        "code2video_root": str(root),
        "output_dir": str(agent.output_dir),
        "knowledge_point": args.knowledge_point,
        "model": args.model,
        "use_feedback": args.feedback,
        "use_assets": args.assets,
        "max_sections": args.max_sections,
        "token_usage": agent.token_usage,
        "sections": section_summary(agent),
        "success_count": len(agent.section_videos),
        "section_count": len(agent.sections),
        "final_video": final_video,
    }
    summary_path = agent.output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.out_summary:
        args.out_summary.parent.mkdir(parents=True, exist_ok=True)
        args.out_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
