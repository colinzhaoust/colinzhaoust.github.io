#!/usr/bin/env python3
"""Ask a multimodal model to review rendered explainer contact sheets.

The tool is deliberately small and dependency-light. It supports:

- WInE / OpenAI-compatible chat completions with image_url payloads.
- AWS Bedrock Converse with image bytes.
- A mock mode for local pipeline tests without spending API calls.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


WINE_BASE_URL = "https://ai-gateway.andrew.cmu.edu/v1"


def read_text_file(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip()


def read_api_key_file(path: str | None, preferred_names: tuple[str, ...] = ()) -> str | None:
    text = read_text_file(path)
    if not text:
        return None
    pairs: dict[str, str] = {}
    bare_values: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, value = line.split("=", 1)
            pairs[name.strip()] = value.strip().strip("'\"")
        else:
            bare_values.append(line.strip().strip("'\""))
    for name in preferred_names:
        if pairs.get(name):
            return pairs[name]
    for value in pairs.values():
        if value:
            return value
    return bare_values[0] if bare_values else None


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def review_prompt(paper: str, goal: str) -> str:
    return f"""You are reviewing a contact sheet from a Manim educational video.

Paper/topic: {paper}
Teaching goal: {goal}

Return minified JSON only. Do not use markdown fences. Keep each list to at most 2 short strings.
Use exactly these fields:
- overall_score: integer 1-5
- verdict: one sentence
- visible_content: short list of what appears in the frames
- teaching_gaps: short list of what a learner still would not understand
- visual_gaps: short list of layout/pacing/readability issues
- suggested_scene_edits: short list of concrete edits to the Manim scene
- should_rerender: boolean

Judge the actual visible frames, not just the topic name."""


def parse_jsonish(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def post_json(url: str, payload: dict[str, Any], api_key: str, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except ValueError as exc:
        raise RuntimeError("Invalid request header; check that the API key file resolves to one key string.") from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:1200]}") from exc


def openai_compatible_review(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    base_url = (args.base_url or os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    api_key = args.api_key or read_api_key_file(args.api_key_file, ("OPENAI_API_KEY", "API_KEY")) or os.environ.get("OPENAI_API_KEY")
    if args.provider == "wine":
        base_url = base_url or WINE_BASE_URL
        api_key = (
            api_key
            or os.environ.get("WINE_API_KEY")
            or os.environ.get("WINE_LAB_API_KEY")
            or read_api_key_file("~/.secrets/wine_litellm_api_key.txt", ("WINE_LAB_API_KEY", "WINE_API_KEY", "OPENAI_API_KEY"))
        )
    if not base_url or not api_key:
        raise SystemExit("OpenAI-compatible review requires --base-url and API key, or provider=wine on Babel.")

    payload = {
        "model": args.model,
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(Path(args.image))}},
                ],
            }
        ],
    }
    raw = post_json(f"{base_url}/chat/completions", payload, api_key, args.timeout)
    text = raw["choices"][0]["message"].get("content", "")
    return {"provider": args.provider, "model": args.model, "text": text, "json": parse_jsonish(text), "raw": raw}


def load_aws_csv(path: str | None) -> None:
    if not path:
        return
    p = Path(path).expanduser()
    if not p.exists():
        raise SystemExit(f"AWS key file does not exist: {p}")
    with p.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    mapping = {
        "AWS_ACCESS_KEY_ID": ("Access key ID", "aws_access_key_id", "AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": ("Secret access key", "aws_secret_access_key", "AWS_SECRET_ACCESS_KEY"),
        "AWS_SESSION_TOKEN": ("Session token", "aws_session_token", "AWS_SESSION_TOKEN"),
    }
    for env_key, names in mapping.items():
        for name in names:
            value = row.get(name)
            if value:
                os.environ[env_key] = value
                break


def bedrock_review(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    load_aws_csv(args.aws_key_file)
    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("Bedrock review requires boto3 in the active Python environment.") from exc

    image = Path(args.image)
    fmt = image.suffix.lower().lstrip(".") or "png"
    if fmt == "jpg":
        fmt = "jpeg"
    client = boto3.client("bedrock-runtime", region_name=args.aws_region)
    raw = client.converse(
        modelId=args.model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": prompt},
                    {"image": {"format": fmt, "source": {"bytes": image.read_bytes()}}},
                ],
            }
        ],
        inferenceConfig={"maxTokens": args.max_tokens, "temperature": 0},
    )
    parts = raw.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in parts)
    return {"provider": "bedrock", "model": args.model, "text": text, "json": parse_jsonish(text), "raw": raw}


def mock_review(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "provider": "mock",
        "model": "heuristic",
        "json": {
            "overall_score": 3,
            "verdict": "Renderable storyboard, but not yet a complete lesson.",
            "visible_content": ["title cards", "formula or data panel", "final takeaway panel"],
            "teaching_gaps": ["needs narration timing", "needs a learner-facing example", "needs a final check question"],
            "visual_gaps": ["contact sheet cannot verify animation semantics", "small text may be hard on mobile"],
            "suggested_scene_edits": ["split dense formula panels", "add a worked numeric step", "hold final takeaways longer"],
            "should_rerender": True,
        },
        "text": "",
        "raw": {},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "wine", "openai_compatible", "bedrock"], default="mock")
    parser.add_argument("--model", default="wine-gemini-2.5-flash")
    parser.add_argument("--image", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--goal", default="Help a learner understand the key mechanism.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-file")
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--aws-key-file")
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    prompt = review_prompt(args.paper, args.goal)
    if args.provider == "mock":
        result = mock_review(args)
    elif args.provider in {"wine", "openai_compatible"}:
        result = openai_compatible_review(args, prompt)
    else:
        result = bedrock_review(args, prompt)
    result["image"] = str(Path(args.image).resolve())
    result["paper"] = args.paper
    result["goal"] = args.goal

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    json.dump(result.get("json") or {"text": result.get("text", "")}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
