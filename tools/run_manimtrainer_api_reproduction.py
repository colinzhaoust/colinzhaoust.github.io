#!/usr/bin/env python3
"""Run a ManimTrainer/ManimAgent-style API reproduction.

The upstream ManimTrainer CLI is built around local HuggingFace/Unsloth model
loading. This runner keeps the repo's prompt templates and RITL/RITL-DOC idea,
but uses an OpenAI-compatible API so we can exercise the generation -> render
-> feedback loop without training or loading an 8B checkpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


WINE_BASE_URL = "https://ai-gateway.andrew.cmu.edu/v1"
DEFAULT_MODEL = "wine-claude-haiku-4-5"


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


def load_manimtrainer_modules(root: Path):
    sys.path.insert(0, str(root))
    from src.rag.api_inspector import ApiInspector  # type: ignore
    from src.rag.call_extractor import CallExtractor  # type: ignore
    from src.rag.rag_engine import RAGEngine  # type: ignore
    from src.utils.prompt_template import PromptTemplate  # type: ignore
    import manim  # type: ignore

    return PromptTemplate, RAGEngine(ApiInspector(manim), CallExtractor())


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    data = json.loads(body)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected API response: {body[:1000]}") from exc


def extract_code(text: str) -> str:
    code_match = re.search(r"<CODE>\s*(.*?)\s*</CODE>", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = code_match.group(1) if code_match else text
    fence_match = re.search(r"```(?:python)?\s*(.*?)```", candidate, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1)
    return candidate.strip()


def scene_name_from_code(code: str) -> str | None:
    match = re.search(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((?:[^)]*Scene[^)]*)\):", code, flags=re.MULTILINE)
    return match.group(1) if match else None


def render_code(code: str, output_dir: Path, manim_exec: str, timeout: int, quality: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = scene_name_from_code(code)
    timestamp = int(time.time())
    with tempfile.TemporaryDirectory(prefix="manimtrainer_media_") as media_dir:
        code_path = output_dir / f"generated_{timestamp}.py"
        code_path.write_text(code, encoding="utf-8")
        output_stem = output_dir / f"render_{timestamp}"
        cmd = [manim_exec, str(code_path)]
        if scene_name:
            cmd.append(scene_name)
        cmd.extend([quality, "--media_dir", media_dir, "-o", str(output_stem)])
        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "code_path": str(code_path),
                "video_path": None,
                "stdout": exc.stdout or "",
                "stderr": f"Rendering timed out after {timeout} seconds.",
                "command": cmd,
            }
        video_path = output_stem.with_suffix(".mp4")
        return {
            "success": result.returncode == 0 and video_path.exists(),
            "code_path": str(code_path),
            "video_path": str(video_path) if video_path.exists() else None,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }


def make_messages(template: Any, **kwargs: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": template.system_prompt_template},
        {"role": "user", "content": template.user_prompt_template.format(**kwargs)},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manimtrainer-root", default="external/manim-trainer", type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=WINE_BASE_URL)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-file", default=Path("~/.secrets/wine_litellm_api_key.txt"), type=Path)
    parser.add_argument("--max-tokens", default=4096, type=int)
    parser.add_argument("--temperature", default=0.2, type=float)
    parser.add_argument("--api-timeout", default=300, type=int)
    parser.add_argument("--render-timeout", default=300, type=int)
    parser.add_argument("--feedback-rounds", default=1, type=int)
    parser.add_argument("--ritl-doc", action="store_true")
    parser.add_argument("--manim-exec", default="manimce")
    parser.add_argument("--quality", default="-ql")
    args = parser.parse_args()

    root = args.manimtrainer_root
    if not root.is_absolute():
        root = Path.cwd() / root
    root = root.resolve()
    if not (root / "src" / "utils" / "prompt_template.py").exists():
        raise SystemExit(f"Not a ManimTrainer repo: {root}")

    api_key = (
        args.api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("WINE_API_KEY")
        or os.environ.get("WINE_LAB_API_KEY")
        or read_api_key_file(args.api_key_file.expanduser())
    )
    if not api_key:
        raise SystemExit(f"No WInE API key found. Checked env vars and {args.api_key_file}.")

    PromptTemplate, rag_engine = load_manimtrainer_modules(root)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    template = PromptTemplate.MANIM_VIDEO_GEN_CHAT_TEMPLATE
    messages = make_messages(template, reviewed_description=args.prompt)
    response = chat_completion(
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.api_timeout,
    )
    code = extract_code(response)
    (output_dir / "attempt_0_response.txt").write_text(response, encoding="utf-8")
    (output_dir / "attempt_0_code.py").write_text(code, encoding="utf-8")
    render = render_code(code, output_dir, args.manim_exec, args.render_timeout, args.quality)
    attempts.append({"round": 0, "mode": "initial", "render": render})

    for round_idx in range(1, args.feedback_rounds + 1):
        if render["success"]:
            break
        render_errors = "\n".join((render.get("stderr") or "").splitlines()[-30:])
        if args.ritl_doc:
            api_info = rag_engine.get_formatted_api_info(code)[:12000]
            template = PromptTemplate.MANIM_VIDEO_GEN_CHAT_RAG_FB_TEMPLATE
            messages = make_messages(
                template,
                reviewed_description=args.prompt,
                initial_code=code,
                api_info=api_info,
                render_errors=render_errors,
            )
            mode = "ritl-doc"
        else:
            template = PromptTemplate.MANIM_VIDEO_GEN_CHAT_FB_ONLY_TEMPLATE
            messages = make_messages(
                template,
                reviewed_description=args.prompt,
                initial_code=code,
                render_errors=render_errors,
            )
            mode = "ritl"

        response = chat_completion(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            messages=messages,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.api_timeout,
        )
        code = extract_code(response)
        (output_dir / f"attempt_{round_idx}_response.txt").write_text(response, encoding="utf-8")
        (output_dir / f"attempt_{round_idx}_code.py").write_text(code, encoding="utf-8")
        render = render_code(code, output_dir, args.manim_exec, args.render_timeout, args.quality)
        attempts.append({"round": round_idx, "mode": mode, "render": render})

    summary = {
        "system": "ManimTrainer/ManimAgent API-mode reproduction",
        "manimtrainer_root": str(root),
        "model": args.model,
        "prompt": args.prompt,
        "ritl_doc": args.ritl_doc,
        "feedback_rounds_requested": args.feedback_rounds,
        "success": bool(attempts[-1]["render"]["success"]) if attempts else False,
        "final_video": attempts[-1]["render"].get("video_path") if attempts else None,
        "attempts": attempts,
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
