"""CLI for validation, projection, and legacy migration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .completion import derive_completion
from .migration import migrate_legacy_file
from .projection import write_public_manifest_atomic
from .validation import ManifestValidationError, validate_canonical, validate_public


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".evidence-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-media-evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--public", action="store_true")
    derive = subparsers.add_parser("derive-completion")
    derive.add_argument("manifest", type=Path)
    project = subparsers.add_parser("project")
    project.add_argument("manifest", type=Path)
    project.add_argument("output", type=Path)
    migrate = subparsers.add_parser("migrate-legacy")
    migrate.add_argument("manifest", type=Path)
    migrate.add_argument("output_dir", type=Path)
    migrate.add_argument("--artifact-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            document = _read(args.manifest)
            (validate_public if args.public else validate_canonical)(document)
            print(json.dumps({"ok": True, "manifest": str(args.manifest)}))
        elif args.command == "derive-completion":
            document = _read(args.manifest)
            validate_canonical(document)
            print(derive_completion(document))
        elif args.command == "project":
            write_public_manifest_atomic(_read(args.manifest), args.output)
            print(json.dumps({"ok": True, "output": str(args.output)}))
        elif args.command == "migrate-legacy":
            manifests = migrate_legacy_file(args.manifest, artifact_root=args.artifact_root)
            for document in manifests:
                validate_canonical(document)
            for document in manifests:
                _write_atomic(args.output_dir / f"{document['run_id']}.json", document)
            print(json.dumps({"ok": True, "count": len(manifests), "output_dir": str(args.output_dir)}))
        return 0
    except ManifestValidationError as exc:
        print(json.dumps({"ok": False, "errors": exc.errors}), file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
