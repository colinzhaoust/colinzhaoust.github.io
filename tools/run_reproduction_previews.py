#!/usr/bin/env python3
"""Generate repo-style reproduction previews for paper explainer systems.

This is a lightweight planning-level reproduction harness. It intentionally
does not import Paper2Manim, Code2Video, or TheoremExplainAgent, because their
full dependency stacks conflict. Instead it reproduces their public input/output
contracts closely enough to compare what each style would ask Manim to build.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "experiments" / "reproductions" / "paper_specs"
DEFAULT_OUT_DIR = ROOT / "runs" / "reproductions" / "previews"
WINE_BASE_URL = "https://ai-gateway.andrew.cmu.edu/v1"

ADAPTERS = ("paper2manim", "code2video", "theorem_explain_agent", "llm2manim", "manimtrainer")


def read_api_key_file(path: str | None, preferred_names: tuple[str, ...] = ()) -> str | None:
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.exists():
        return None
    pairs: dict[str, str] = {}
    bare_values: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
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


def load_paper_specs(selected: list[str] | None) -> list[dict[str, Any]]:
    specs = []
    wanted = set(selected or [])
    for path in sorted(SPEC_DIR.glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        if not wanted or spec["id"] in wanted:
            specs.append(spec)
    if not specs:
        raise SystemExit(f"No paper specs matched: {selected}")
    return specs


def compact_paper_context(spec: dict[str, Any]) -> str:
    units = []
    for unit in spec["teaching_units"]:
        units.append(
            {
                "id": unit["id"],
                "name": unit["name"],
                "goal": unit["goal"],
                "formulas": unit.get("formulas", []),
                "visual_example": unit.get("visual_example"),
                "code_refs": unit.get("code_refs", []),
            }
        )
    return json.dumps(
        {
            "title": spec["title"],
            "short_title": spec["short_title"],
            "audience": spec["audience"],
            "central_question": spec["central_question"],
            "teaching_units": units,
            "comparison_axes": spec.get("comparison_axes", []),
        },
        ensure_ascii=False,
        indent=2,
    )


def schema_for(adapter: str) -> dict[str, Any]:
    if adapter == "paper2manim":
        return {
            "title": "string",
            "scenes": [
                {
                    "name": "PascalCaseSceneName",
                    "description": "1-4 sentences describing exactly what Manim shows",
                    "duration_hint": 12.0,
                    "teaching_unit_ids": ["unit_id"],
                    "formula_refs": ["formula string"],
                    "code_refs": ["optional code paths"],
                }
            ],
            "expected_gap": "string",
        }
    if adapter == "code2video":
        return {
            "topic": "string",
            "target_audience": "string",
            "sections": [
                {
                    "id": "section_1",
                    "title": "Sec 1: section title",
                    "lecture_lines": ["<=10 words each"],
                    "animations": ["corresponding Manim animation descriptions"],
                    "key_section": True,
                }
            ],
            "expected_gap": "string",
        }
    if adapter == "theorem_explain_agent":
        return {
            "topic": "string",
            "scene_outline": {
                "SCENE_1": "scene outline text",
                "SCENE_2": "scene outline text",
            },
            "implementation_plans": [
                {
                    "scene": 1,
                    "vision_storyboard": "what the viewer sees",
                    "technical_implementation": "Manim objects and animations to use",
                    "animation_narration": "short narration beats",
                }
            ],
            "expected_gap": "string",
        }
    if adapter == "llm2manim":
        return {
            "topic": "string",
            "symbol_ledger": [
                {"symbol": "string", "meaning": "string", "first_scene": "string"}
            ],
            "pedagogy_steps": [
                {
                    "step": "string",
                    "template": "definition | worked_example | comparison | recap",
                    "visual_plan": "what Manim should show",
                    "formula_refs": ["formula string"],
                    "hitl_question": "short reviewer question before render",
                }
            ],
            "expected_gap": "string",
        }
    if adapter == "manimtrainer":
        return {
            "topic": "string",
            "retrieval_notes": ["paper or documentation facts to ground the scene"],
            "training_style_plan": [
                {
                    "scene": "string",
                    "manim_sketch": "objects and animations",
                    "reward_targets": ["renderability", "geometry", "teaching"],
                    "self_review": "likely failure and revision cue",
                }
            ],
            "expected_gap": "string",
        }
    raise ValueError(adapter)


def prompt_for(adapter: str, spec: dict[str, Any]) -> str:
    context = compact_paper_context(spec)
    schema = json.dumps(schema_for(adapter), indent=2)
    if adapter == "paper2manim":
        role = (
            "You are reproducing the planning style of Paper2Manim. "
            "Create a 2-5 scene Manim storyboard from a structured paper summary. "
            "Be concrete about equations, colors, and visual order. Use simple Manim objects only."
        )
    elif adapter == "code2video":
        role = (
            "You are reproducing the planning style of Code2Video. "
            "Create a progressive teaching outline plus storyboard sections from one knowledge topic. "
            "Each lecture line must be short and paired with a visual animation."
        )
    elif adapter == "theorem_explain_agent":
        role = (
            "You are reproducing the planning style of TheoremExplainAgent. "
            "Create a long-form concept explanation plan with XML-like scenes, vision storyboard, "
            "technical implementation, and narration beats."
        )
    elif adapter == "llm2manim":
        role = (
            "You are reproducing the planning style of LLM2Manim. "
            "Create a pedagogy-first Manim plan with prompt-template-like steps, a symbol ledger, "
            "and human-in-the-loop review checkpoints before rendering."
        )
    elif adapter == "manimtrainer":
        role = (
            "You are reproducing the planning style of ManimTrainer. "
            "Create a training-oriented Manim plan that states retrieval grounding, reward targets, "
            "and revision cues for renderability, geometry, and pedagogy."
        )
    else:
        raise ValueError(adapter)
    return f"""{role}

Paper/work context:
{context}

Return JSON only, no markdown fences. Match this schema:
{schema}

Important:
- This is a preview for comparing generation styles, not a final video.
- Prefer multiple teaching units when the paper has several important formulas.
- Mention code_refs only when the input provides them.
- State the expected gap honestly in `expected_gap`."""


def openai_compatible_call(
    prompt: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:1000]}") from exc
    text = raw["choices"][0]["message"].get("content", "")
    return text, raw


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
    return json.loads(cleaned)


def mock_preview(adapter: str, spec: dict[str, Any]) -> dict[str, Any]:
    units = spec["teaching_units"]
    if adapter == "paper2manim":
        scenes = []
        for unit in units[:5]:
            scenes.append(
                {
                    "name": "".join(part.title() for part in unit["id"].split("_")) + "Scene",
                    "description": (
                        f"Show '{unit['name']}' as one equation plus one diagram. "
                        f"Use the example: {unit['visual_example']} End with the goal: {unit['goal']}"
                    ),
                    "duration_hint": 16.0,
                    "teaching_unit_ids": [unit["id"]],
                    "formula_refs": unit.get("formulas", []),
                    "code_refs": unit.get("code_refs", []),
                }
            )
        return {"title": spec["short_title"], "scenes": scenes, "expected_gap": "Mock preview; no LLM refinement."}
    if adapter == "code2video":
        sections = []
        for idx, unit in enumerate(units, start=1):
            sections.append(
                {
                    "id": f"section_{idx}",
                    "title": f"Sec {idx}: {unit['name']}",
                    "lecture_lines": [
                        unit["name"][:36],
                        "Show the formula",
                        "Animate the example",
                    ],
                    "animations": [
                        f"Title and compact definition for {unit['name']}.",
                        f"Write formula(s): {'; '.join(unit.get('formulas', []))}.",
                        unit["visual_example"],
                    ],
                    "key_section": idx <= 3,
                }
            )
        return {
            "topic": spec["central_question"],
            "target_audience": spec["audience"],
            "sections": sections,
            "expected_gap": "Mock preview; Code2Video would need API/render feedback for layout polish.",
        }
    if adapter == "theorem_explain_agent":
        outline = {}
        plans = []
        for idx, unit in enumerate(units, start=1):
            outline[f"SCENE_{idx}"] = f"{unit['name']}: {unit['goal']}"
            plans.append(
                {
                    "scene": idx,
                    "vision_storyboard": unit["visual_example"],
                    "technical_implementation": f"Use Text, MathTex, arrows, table/bars as needed for {unit.get('formulas', [])}.",
                    "animation_narration": f"Explain {unit['name']} and why it matters for {spec['short_title']}.",
                }
            )
        return {
            "topic": spec["title"],
            "scene_outline": outline,
            "implementation_plans": plans,
            "expected_gap": "Mock preview; TEA would need full long-form codegen/render loop.",
        }
    if adapter == "llm2manim":
        ledger = []
        steps = []
        for idx, unit in enumerate(units, start=1):
            for formula in unit.get("formulas", [])[:2]:
                symbol = formula.split("=", 1)[0].strip()[:32] or unit["id"]
                ledger.append({"symbol": symbol, "meaning": unit["goal"], "first_scene": f"step_{idx}"})
            steps.append(
                {
                    "step": f"step_{idx}",
                    "template": "worked_example" if idx == 1 else "comparison",
                    "visual_plan": unit["visual_example"],
                    "formula_refs": unit.get("formulas", []),
                    "hitl_question": f"Are the symbols for {unit['name']} introduced before the formula?",
                }
            )
        return {
            "topic": spec["central_question"],
            "symbol_ledger": ledger[:8],
            "pedagogy_steps": steps,
            "expected_gap": "Mock preview; LLM2Manim would need template prompts and HITL review integration.",
        }
    if adapter == "manimtrainer":
        notes = [f"{unit['name']}: {unit['goal']}" for unit in units]
        plan = []
        for idx, unit in enumerate(units, start=1):
            plan.append(
                {
                    "scene": f"scene_{idx}",
                    "manim_sketch": f"{unit['visual_example']} Use formulas: {'; '.join(unit.get('formulas', []))}.",
                    "reward_targets": ["renderability", "geometry", "teaching"],
                    "self_review": f"Check whether {unit['name']} has enough motion and no crowded text.",
                }
            )
        return {
            "topic": spec["title"],
            "retrieval_notes": notes,
            "training_style_plan": plan,
            "expected_gap": "Mock preview; ManimTrainer would need trained policy/RITL loop for real generation.",
        }
    raise ValueError(adapter)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers", nargs="*", default=None, help="Paper spec ids. Defaults to all.")
    parser.add_argument("--adapters", nargs="*", choices=ADAPTERS, default=list(ADAPTERS))
    parser.add_argument("--provider", choices=["mock", "wine", "openai_compatible"], default="mock")
    parser.add_argument("--model", default="wine-claude-haiku-4-5")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-file", default=None)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    base_url = args.base_url
    api_key = args.api_key
    if args.provider == "wine":
        base_url = base_url or WINE_BASE_URL
        api_key = (
            api_key
            or os.environ.get("WINE_API_KEY")
            or os.environ.get("WINE_LAB_API_KEY")
            or read_api_key_file("~/.secrets/wine_litellm_api_key.txt", ("WINE_LAB_API_KEY", "WINE_API_KEY"))
        )
    elif args.provider == "openai_compatible":
        base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        api_key = api_key or os.environ.get("OPENAI_API_KEY") or read_api_key_file(args.api_key_file, ("OPENAI_API_KEY",))

    if args.provider != "mock" and (not base_url or not api_key):
        raise SystemExit("Non-mock provider requires base URL and API key.")

    out_dir = Path(args.out_dir)
    specs = load_paper_specs(args.papers)
    manifest = []
    for spec in specs:
        for adapter in args.adapters:
            prompt = prompt_for(adapter, spec)
            target_dir = out_dir / adapter / spec["id"]
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
            started = time.time()
            raw: dict[str, Any] = {}
            if args.provider == "mock":
                parsed = mock_preview(adapter, spec)
                text = json.dumps(parsed, ensure_ascii=False, indent=2)
            else:
                text, raw = openai_compatible_call(
                    prompt,
                    base_url=base_url or "",
                    api_key=api_key or "",
                    model=args.model,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
                try:
                    parsed = parse_jsonish(text)
                    parse_error = None
                except Exception as exc:  # keep going; malformed JSON is useful evidence.
                    parsed = {"parse_failed": True, "raw_text_preview": text[:2000]}
                    parse_error = f"{type(exc).__name__}: {exc}"
            record = {
                "adapter": adapter,
                "paper_id": spec["id"],
                "provider": args.provider,
                "model": args.model if args.provider != "mock" else "mock",
                "elapsed_sec": round(time.time() - started, 3),
                "preview": parsed,
                "raw_text": text,
                "raw_response": raw,
            }
            if args.provider != "mock" and parse_error:
                record["parse_error"] = parse_error
            (target_dir / "preview.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            manifest.append(
                {
                    "adapter": adapter,
                    "paper_id": spec["id"],
                    "provider": record["provider"],
                    "model": record["model"],
                    "path": str(target_dir / "preview.json"),
                    "elapsed_sec": record["elapsed_sec"],
                }
            )
            print(f"wrote {target_dir / 'preview.json'}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
