#!/usr/bin/env python3
"""Fail-closed checks for the static progress-site publication bundle."""

from __future__ import annotations

import hashlib
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
BACKTRANSLATION_ROOT = ROOT / "assets" / "backtranslation"
DUMMY_REFERENCE_PATTERNS = {
    "baseline-coverage asset": re.compile(
        r"(?:assets/)?baseline-coverage/|runs/baseline_coverage/",
        re.IGNORECASE,
    ),
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_backtranslation_manifest(failures: list[str]) -> int:
    """Validate closure and integrity of every artifact declared for publication."""
    manifest_path = BACKTRANSLATION_ROOT / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(
            f"assets/backtranslation/artifact_manifest.json: cannot validate ({error})"
        )
        return 0

    cases = manifest.get("cases") if isinstance(manifest, dict) else None
    if not isinstance(cases, list):
        failures.append(
            "assets/backtranslation/artifact_manifest.json: cases must be a list"
        )
        return 0

    checked = 0

    for case in cases:
        if not isinstance(case, dict):
            failures.append(
                "assets/backtranslation/artifact_manifest.json: case must be an object"
            )
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not re.fullmatch(r"bt-\d{3}", case_id):
            failures.append(
                "assets/backtranslation/artifact_manifest.json: invalid case_id "
                f"{case_id!r}"
            )
            continue

        case_root = BACKTRANSLATION_ROOT / "cases" / case_id
        artifacts = case.get("artifacts")
        if not isinstance(artifacts, dict):
            failures.append(
                f"assets/backtranslation/artifact_manifest.json: "
                f"{case_id}.artifacts must be an object"
            )
            continue

        for artifact_name, artifact in artifacts.items():
            relative = artifact.get("path") if isinstance(artifact, dict) else None
            if not isinstance(relative, str):
                failures.append(
                    f"assets/backtranslation/artifact_manifest.json: "
                    f"{case_id}.{artifact_name} has no path"
                )
                continue

            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                failures.append(
                    f"assets/backtranslation/artifact_manifest.json: "
                    f"{case_id}.{artifact_name} has unsafe path {relative}"
                )
                continue

            candidate = case_root / relative_path
            if not candidate.is_file():
                failures.append(
                    f"assets/backtranslation/artifact_manifest.json: "
                    f"missing {case_id}/{relative}"
                )
                continue

            expected_size = artifact.get("size_bytes")
            actual_size = candidate.stat().st_size
            if expected_size != actual_size:
                failures.append(
                    f"assets/backtranslation/artifact_manifest.json: "
                    f"{case_id}/{relative} size {actual_size} != {expected_size}"
                )

            expected_hash = artifact.get("sha256")
            actual_hash = sha256(candidate)
            if expected_hash != actual_hash:
                failures.append(
                    f"assets/backtranslation/artifact_manifest.json: "
                    f"{case_id}/{relative} sha256 {actual_hash} != {expected_hash}"
                )
            checked += 1

    return checked


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

    public_reference_files = {ROOT / "index.html"}
    public_reference_files.update((ROOT / "data").rglob("*.json"))
    public_reference_files.update((ROOT / "assets" / "manifests").rglob("*.json"))
    public_reference_files.update(
        path
        for path in (ROOT / "assets").rglob("*.json")
        if "manifest" in path.name
    )
    for path in sorted(public_reference_files):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for label, pattern in DUMMY_REFERENCE_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative}: references {label}")

    parser = AssetParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    for tag, attribute, value in parser.assets:
        candidate = local_path(value)
        if candidate is not None and not candidate.exists():
            failures.append(f"index.html: missing {tag}[{attribute}] asset {value}")

    if parser.direct_video_sources:
        for tag, value in parser.direct_video_sources:
            failures.append(f"index.html: eager media source {tag}[src]={value}")

    backtranslation_artifacts = validate_backtranslation_manifest(failures)

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
        f"{backtranslation_artifacts} verified backtranslation artifacts, "
        f"{local['passed']}/{local['total']} tests in {local['suite_count']} suites, "
        "no eager video sources or private locators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
