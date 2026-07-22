from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from .common import TEMPLATE_ROOT, resolve_repo_path, sha256_file
from .pipeline import build_catalog
from .validation import validate_bundle


class RenderError(RuntimeError):
    pass


def _copy(path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)


def render_site(bundles: Iterable[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    documents = list(bundles)
    if not documents:
        raise RenderError("at least one explainer bundle is required")
    for document in documents:
        validate_bundle(document)
    if output_dir.resolve() == Path("/") or output_dir.resolve() == Path.home().resolve():
        raise RenderError("refusing to render into a broad filesystem target")
    output_dir.mkdir(parents=True, exist_ok=True)
    for generated in (output_dir / "assets", output_dir / "data"):
        if generated.is_dir():
            shutil.rmtree(generated)
    for filename in ("index.html", "styles.css", "app.js"):
        _copy(TEMPLATE_ROOT / filename, output_dir / filename)
    data_root = output_dir / "data"
    bundle_root = data_root / "bundles"
    bundle_root.mkdir(parents=True, exist_ok=True)
    media_index: list[dict[str, Any]] = []
    for bundle in documents:
        paper_id = bundle["paper_id"]
        rendered = json.loads(json.dumps(bundle))
        for media in rendered["source_packet"].get("media", []):
            source = resolve_repo_path(media["path"])
            suffix = source.suffix.lower()
            destination = output_dir / "assets" / paper_id / f"{media['media_id']}{suffix}"
            _copy(source, destination)
            media["published_path"] = destination.relative_to(output_dir).as_posix()
            media_index.append(
                {
                    "paper_id": paper_id,
                    "media_id": media["media_id"],
                    "path": media["published_path"],
                    "sha256": sha256_file(destination),
                    "size_bytes": destination.stat().st_size,
                }
            )
        (bundle_root / f"{paper_id}.json").write_text(
            json.dumps(rendered, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    catalog = build_catalog(documents)
    (data_root / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "explainer-site-manifest/0.1.0",
        "paper_count": len(documents),
        "papers": [item["paper_id"] for item in documents],
        "media": media_index,
    }
    (data_root / "site_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
