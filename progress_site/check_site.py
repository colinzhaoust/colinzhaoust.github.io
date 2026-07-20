#!/usr/bin/env python3
"""Fail-closed checks for the static progress-site publication bundle."""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".txt", ".vtt"}
PRIVATE_PATTERNS = {
    "absolute home path": re.compile(r"/(?:home|Users)/"),
    "local username": re.compile(r"(?:xinranz3|/Users/colin)", re.IGNORECASE),
    "private source locator": re.compile(r"source[-_]vault|/private/", re.IGNORECASE),
}
LOCAL_ATTRIBUTES = {
    "href",
    "src",
    "poster",
    "data-video",
    "data-poster",
    "data-video-src",
    "data-track-src",
    "data-reference-video",
    "data-reference-poster",
}


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[tuple[str, str, str]] = []
        self.direct_video_sources: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if not value:
                continue
            if name in LOCAL_ATTRIBUTES:
                self.assets.append((tag, name, value))
            if tag in {"video", "source"} and name == "src":
                self.direct_video_sources.append((tag, value))


def local_path(value: str) -> Path | None:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or value.startswith(("#", "mailto:", "data:")):
        return None
    return ROOT / unquote(parsed.path)


def main() -> int:
    failures: list[str] = []

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for label, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative}: contains {label}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as error:
                failures.append(f"{relative}: invalid JSON ({error})")

    parser = AssetParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    for tag, attribute, value in parser.assets:
        candidate = local_path(value)
        if candidate is not None and not candidate.exists():
            failures.append(f"index.html: missing {tag}[{attribute}] asset {value}")

    if parser.direct_video_sources:
        for tag, value in parser.direct_video_sources:
            failures.append(f"index.html: eager media source {tag}[src]={value}")

    evidence = json.loads((ROOT / "data" / "evidence.json").read_text(encoding="utf-8"))
    local = evidence["local_verification"]
    suite_passed = sum(item["passed"] for item in local["suites"])
    suite_total = sum(item["total"] for item in local["suites"])
    if (suite_passed, suite_total) != (local["passed"], local["total"]):
        failures.append("data/evidence.json: suite totals do not match aggregate")

    if failures:
        print("progress_site checks failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        f"progress_site checks passed: {len(parser.assets)} local references, "
        f"{local['passed']}/{local['total']} tests in {local['suite_count']} suites, "
        "no eager video sources or private locators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
