from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .common import DATA_ROOT, ROOT, load_json
from .ingestion import IngestionError, ingest_source_packet
from .pipeline import replay_provider, run_pipeline
from .providers import BedrockProvider, OpenAICompatibleProvider, ProviderError
from .renderer import render_comparison_site, render_site
from .validation import ExplainerValidationError, validate_bundle_file


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _live_provider(args: argparse.Namespace):
    env_file = _resolve(args.env_file) if args.env_file else None
    if args.mode == "bedrock":
        return BedrockProvider(model_id=args.model_id, env_file=env_file)
    if not args.base_url:
        raise ValueError("--base-url is required for openai-compatible mode")
    return OpenAICompatibleProvider(
        model_id=args.model_id,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        env_file=env_file,
        api_path=args.api_path,
        provider_name=args.provider_name,
    )


def _add_live_provider_arguments(parser: argparse.ArgumentParser, *, include_replay: bool) -> None:
    modes = ("replay", "bedrock", "openai-compatible") if include_replay else ("bedrock", "openai-compatible")
    parser.add_argument("--mode", choices=modes, default="replay" if include_replay else "bedrock")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model-id", default="qwen.qwen3-32b-v1:0")
    parser.add_argument("--base-url")
    parser.add_argument("--api-path", default="chat/completions")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--provider-name", default="openai_compatible")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an interactive paper + code explainer website.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the staged explainer pipeline")
    run.add_argument("paper_id", choices=("feynrl", "rope"))
    run.add_argument("--run-root", type=Path)
    _add_live_provider_arguments(run, include_replay=True)

    build = sub.add_parser("build-site", help="render one site from validated bundles")
    build.add_argument("--bundle", type=Path, action="append")
    build.add_argument("--output", type=Path, default=ROOT / "explainer_site")

    compare = sub.add_parser("build-comparison", help="render multiple complete frozen runs from a manifest")
    compare.add_argument("manifest", type=Path)
    compare.add_argument("--output", type=Path, default=ROOT / "explainer_site")

    validate = sub.add_parser("validate", help="validate one explainer bundle")
    validate.add_argument("bundle", type=Path)

    demo = sub.add_parser("demo", help="run both frozen demos and render the subsite")
    demo.add_argument("--run-root", type=Path, default=ROOT / "runs" / "explainer_pipeline" / "demo")
    demo.add_argument("--output", type=Path, default=ROOT / "explainer_site")

    package = sub.add_parser("package", help="generate a website from an input PDF and git repository using JSON API stages")
    package.add_argument("--paper", type=Path, required=True)
    package.add_argument("--repo", type=Path, required=True)
    package.add_argument("--paper-id", required=True)
    package.add_argument("--title")
    package.add_argument("--paper-url")
    package.add_argument("--audience", default="Technical readers learning the paper, its related work, implementation, and findings.")
    package.add_argument("--run-root", type=Path)
    package.add_argument("--output", type=Path)
    _add_live_provider_arguments(package, include_replay=False)

    args = parser.parse_args()
    try:
        if args.command == "run":
            source = DATA_ROOT / "papers" / f"{args.paper_id}.json"
            run_root = _resolve(args.run_root or Path("runs") / "explainer_pipeline" / args.paper_id)
            provider = (
                replay_provider()
                if args.mode == "replay"
                else _live_provider(args)
            )
            bundle = run_pipeline(source, run_root, provider)
            print(json.dumps(bundle["generation"], indent=2))
        elif args.command == "build-site":
            bundle_paths = args.bundle or [
                ROOT / "runs" / "explainer_pipeline" / "demo" / paper / "explainer_bundle.json"
                for paper in ("feynrl", "rope")
            ]
            bundles = [validate_bundle_file(_resolve(path)) for path in bundle_paths]
            print(json.dumps(render_site(bundles, _resolve(args.output)), indent=2))
        elif args.command == "validate":
            validate_bundle_file(_resolve(args.bundle))
            print("explainer bundle validation: PASS")
        elif args.command == "demo":
            run_root = _resolve(args.run_root)
            bundles = []
            provider = replay_provider()
            for paper_id in ("feynrl", "rope"):
                bundles.append(
                    run_pipeline(
                        DATA_ROOT / "papers" / f"{paper_id}.json",
                        run_root / paper_id,
                        provider,
                    )
                )
            candidate_spec = load_json(DATA_ROOT / "comparison_candidates.json")
            print(
                json.dumps(
                    render_site(
                        bundles,
                        _resolve(args.output),
                        candidate_runs=candidate_spec.get("candidates", []),
                    ),
                    indent=2,
                )
            )
        elif args.command == "build-comparison":
            manifest_path = _resolve(args.manifest)
            specification = load_json(manifest_path)
            if specification.get("schema_version") != "explainer-comparison/0.1.0":
                raise ValueError("comparison manifest must use explainer-comparison/0.1.0")
            runs = []
            for run_spec in specification.get("runs", []):
                bundle_paths = [
                    path if path.is_absolute() else manifest_path.parent / path
                    for path in (Path(value) for value in run_spec.get("bundles", []))
                ]
                runs.append(
                    {
                        "run_id": run_spec["run_id"],
                        "label": run_spec.get("label", run_spec["run_id"]),
                        "description": run_spec.get("description", "Frozen validated model run."),
                        "status": run_spec.get("status", "generated"),
                        "bundles": [validate_bundle_file(path) for path in bundle_paths],
                    }
                )
            print(
                json.dumps(
                    render_comparison_site(
                        runs,
                        _resolve(args.output),
                        candidate_runs=specification.get("candidate_runs", []),
                    ),
                    indent=2,
                )
            )
        else:
            run_root = _resolve(args.run_root or Path("runs") / "explainer_pipeline" / "packages" / args.paper_id)
            output = _resolve(args.output or run_root / "site")
            provider = _live_provider(args)
            packet = ingest_source_packet(
                paper_id=args.paper_id,
                paper=_resolve(args.paper),
                repository=_resolve(args.repo),
                run_root=run_root,
                provider=provider,
                title=args.title,
                paper_url=args.paper_url,
                audience=args.audience,
            )
            source_path = run_root / "source_packet.json"
            bundle = run_pipeline(source_path, run_root / "pipeline", provider)
            manifest = render_site([bundle], output)
            print(json.dumps({"source_packet": source_path.as_posix(), "site": output.as_posix(), "manifest": manifest}, indent=2))
    except (ExplainerValidationError, IngestionError, ProviderError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"explainer pipeline: FAIL\n{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
