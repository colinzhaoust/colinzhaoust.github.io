from __future__ import annotations

import argparse
from pathlib import Path

from .validation import SAMPLE_SLIDE_PATH, validate_demo_package, validate_slide


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SlideIR and resolved AnimationSlots.")
    parser.add_argument("--slide", type=Path, default=SAMPLE_SLIDE_PATH)
    parser.add_argument("--skip-demo", action="store_true")
    args = parser.parse_args()
    validate_slide(args.slide)
    if not args.skip_demo:
        validate_demo_package()
    print("slides+manim validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
