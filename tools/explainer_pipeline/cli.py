from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .common import DATA_ROOT, ROOT, load_json
from .ingestion import IngestionError, ingest_source_packet
from .pipeline import replay_provider, run_pipeline
from .providers import BedrockProvider, ProviderError
from .renderer import render_site
from .validation import ExplainerValidationError, validate_bundle_file


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an interactive paper + code explainer website.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the staged explainer pipeline")
    run.add_argument("paper_id", choices=("feynrl", "rope"))
    run.add_argument("--mode", choices=("replay", "bedrock"), default="replay")
    run.add_argument("--run-root", type=Path)
    run.add_argument("--env-file", type=Path)
    run.add_argument("--model-id", default="us.anthropic.claude-sonnet-5")

    build = sub.add_parser("build-site", help="render one site from validated bundles")
    build.add_argument("--bundle", type=Path, action="append")
    build.add_argument("--output", type=Path, default=ROOT / "explainer_site")

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
    package.add_argument("--env-file", type=Path)
    package.add_argument("--model-id", default="us.anthropic.claude-sonnet-5")

    args = parser.parse_args()
    try:
        if args.command == "run":
            source = DATA_ROOT / "papers" / f"{args.paper_id}.json"
            run_root = _resolve(args.run_root or Path("runs") / "explainer_pipeline" / args.paper_id)
            provider = (
                replay_provider()
                if args.mode == "replay"
                else BedrockProvider(model_id=args.model_id, env_file=_resolve(args.env_file) if args.env_file else None)
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
            print(json.dumps(render_site(bundles, _resolve(args.output)), indent=2))
        else:
            run_root = _resolve(args.run_root or Path("runs") / "explainer_pipeline" / "packages" / args.paper_id)
            output = _resolve(args.output or run_root / "site")
            provider = BedrockProvider(
                model_id=args.model_id,
                env_file=_resolve(args.env_file) if args.env_file else None,
            )
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
