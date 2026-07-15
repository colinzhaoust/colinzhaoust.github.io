"""Validation for the pinned ten-scene Manim Community registry."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping


EXPECTED_SCENES = (
    "OpeningManim",
    "SineCurveUnitCircle",
    "BooleanOperations",
    "ArgMinExample",
    "GraphAreaPlot",
    "PointWithTrace",
    "FollowingGraphCamera",
    "MovingZoomedSceneAround",
    "ThreeDCameraRotation",
    "ThreeDSurfacePlot",
)
CASE_ID_RE = re.compile(r"^bt-[0-9]{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class RegistryError(ValueError):
    """The scene registry or supplied source checkout is not compliant."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise RegistryError(f"Missing {context}.{key}")
    return mapping[key]


def validate_registry(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != "backtranslation-scene-registry/v1":
        raise RegistryError("Unsupported registry schema_version")
    if data.get("role") != "public_development_set":
        raise RegistryError("Registry must be labelled public_development_set")

    upstream = _require(data, "upstream", "registry")
    if upstream.get("release") != "v0.20.1":
        raise RegistryError("Registry must pin ManimCE v0.20.1")
    if not GIT_SHA_RE.fullmatch(str(upstream.get("commit_sha", ""))):
        raise RegistryError("upstream.commit_sha must be a full 40-character SHA")
    if not SHA256_RE.fullmatch(str(upstream.get("source_sha256", ""))):
        raise RegistryError("upstream.source_sha256 must be a SHA-256 digest")
    if not GIT_SHA_RE.fullmatch(str(upstream.get("source_blob_git_sha1", ""))):
        raise RegistryError("upstream.source_blob_git_sha1 must be a Git blob SHA")
    if upstream.get("source_path") != "docs/source/examples.rst":
        raise RegistryError("Unexpected gallery source path")

    license_snapshot = _require(data, "license_snapshot", "registry")
    if license_snapshot.get("declared_spdx") != "MIT":
        raise RegistryError("Only the pinned MIT gallery source is allowed")
    if license_snapshot.get("redistribution_conclusion") != "allowed_with_notice":
        raise RegistryError("License conclusion must require notice preservation")
    license_files = license_snapshot.get("files")
    if not isinstance(license_files, list) or {item.get("path") for item in license_files} != {
        "LICENSE",
        "LICENSE.community",
    }:
        raise RegistryError("Both upstream MIT license files are required")
    for item in license_files:
        if not SHA256_RE.fullmatch(str(item.get("sha256", ""))):
            raise RegistryError(f"Invalid license SHA-256 for {item.get('path')}")
        if not GIT_SHA_RE.fullmatch(str(item.get("git_blob_sha1", ""))):
            raise RegistryError(f"Invalid license Git blob SHA for {item.get('path')}")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 10:
        raise RegistryError("Registry must contain exactly ten scenes")
    case_ids = [str(scene.get("case_id", "")) for scene in scenes]
    scene_classes = [str(scene.get("scene_class", "")) for scene in scenes]
    if len(set(case_ids)) != 10 or not all(CASE_ID_RE.fullmatch(case_id) for case_id in case_ids):
        raise RegistryError("Scene case IDs must be ten unique opaque bt-NNN identifiers")
    if set(scene_classes) != set(EXPECTED_SCENES):
        raise RegistryError("Scene registry does not match the accepted exact ten classes")
    if len(set(scene_classes)) != 10:
        raise RegistryError("Scene classes must be unique")
    for scene in scenes:
        if scene.get("external_assets") != []:
            raise RegistryError(f"External assets are not allowed for {scene.get('scene_class')}")
        if not isinstance(scene.get("runtime_dependencies"), list):
            raise RegistryError(f"runtime_dependencies missing for {scene.get('scene_class')}")
        if not isinstance(scene.get("class_line"), int) or not isinstance(scene.get("directive_line"), int):
            raise RegistryError(f"Pinned source lines missing for {scene.get('scene_class')}")

    contamination = _require(data, "contamination", "registry")
    if contamination.get("risk") != "high" or not contamination.get("required_public_disclosure"):
        raise RegistryError("Public-gallery contamination disclosure is mandatory")


def load_registry(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_registry(data)
    return data


def _git_head(source_root: Path) -> str | None:
    if not (source_root / ".git").exists():
        return None
    proc = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def verify_source_root(registry: Mapping[str, Any], source_root: Path) -> dict[str, Any]:
    """Verify a caller-provided source checkout/archive without fetching anything."""

    validate_registry(registry)
    source_root = source_root.resolve()
    upstream = registry["upstream"]
    source_path = source_root / upstream["source_path"]
    if not source_path.is_file():
        raise RegistryError(f"Pinned gallery source is missing: {upstream['source_path']}")
    actual_source_hash = sha256_file(source_path)
    if actual_source_hash != upstream["source_sha256"]:
        raise RegistryError("Gallery source hash does not match the pinned v0.20.1 source")

    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    for scene in registry["scenes"]:
        line_index = scene["class_line"] - 1
        expected = f"class {scene['scene_class']}("
        if line_index >= len(source_lines) or expected not in source_lines[line_index]:
            raise RegistryError(f"Pinned class line mismatch for {scene['scene_class']}")
        occurrences = sum(expected in line for line in source_lines)
        if occurrences != 1:
            raise RegistryError(f"Expected one source definition for {scene['scene_class']}, found {occurrences}")

    verified_licenses: list[dict[str, str]] = []
    for item in registry["license_snapshot"]["files"]:
        path = source_root / item["path"]
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise RegistryError(f"Pinned license mismatch: {item['path']}")
        verified_licenses.append({"path": item["path"], "sha256": item["sha256"]})

    head = _git_head(source_root)
    if head is not None and head != upstream["commit_sha"]:
        raise RegistryError(f"Source checkout HEAD {head} is not pinned commit {upstream['commit_sha']}")
    return {
        "source_root_mode": "git_checkout" if head else "verified_source_archive",
        "commit_sha": head or upstream["commit_sha"],
        "source_sha256": actual_source_hash,
        "licenses": verified_licenses,
        "scene_count": len(registry["scenes"]),
    }
