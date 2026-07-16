from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import build_all
from .validation import FormulaExplainerValidationError, ROOT, validate_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate bottom-up FormulaIR/SceneIR artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--output", type=Path, default=ROOT / "runs" / "formula_explainer" / "build")
    validate = sub.add_parser("validate")
    validate.add_argument("--build-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            output = args.output if args.output.is_absolute() else ROOT / args.output
            print(json.dumps(build_all(output), indent=2, sort_keys=True))
        else:
            build_dir = args.build_dir
            if build_dir and not build_dir.is_absolute():
                build_dir = ROOT / build_dir
            validate_workspace(build_dir)
            print("formula explainer validation: PASS")
    except (FormulaExplainerValidationError, json.JSONDecodeError, OSError) as exc:
        print(f"formula explainer validation: FAIL\n{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
