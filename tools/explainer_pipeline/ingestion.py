from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from .common import ROOT, canonical_json, sha256_file, sha256_json
from .providers import StageProvider


TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cu", ".go", ".h", ".hpp", ".java", ".js",
    ".json", ".md", ".py", ".rs", ".toml", ".ts", ".tsx", ".yaml", ".yml",
}
MAX_PAPER_CHARS = 180_000
MAX_REPO_CHARS = 140_000
MAX_FILE_CHARS = 32_000


class IngestionError(RuntimeError):
    pass


def _run(command: list[str], cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise IngestionError(f"{' '.join(command[:2])} failed: {detail.strip()}") from exc
    return completed.stdout


def _repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise IngestionError(f"package run root must remain inside {ROOT}") from exc


def _https_remote(repository: Path) -> str:
    remote = _run(["git", "remote", "get-url", "origin"], cwd=repository).strip()
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    if remote.endswith(".git"):
        remote = remote[:-4]
    if not remote.startswith("https://"):
        raise IngestionError("repository origin must resolve to an HTTPS URL")
    return remote


def _pdf_metadata(paper: Path) -> tuple[str, int]:
    raw = _run(["pdfinfo", str(paper)])
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    try:
        pages = int(fields["Pages"])
    except (KeyError, ValueError) as exc:
        raise IngestionError("pdfinfo did not report a valid page count") from exc
    return fields.get("Title", "").strip(), pages


def _paper_text(paper: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run(["pdftotext", "-layout", str(paper), str(destination)])
    text = destination.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise IngestionError("paper text extraction produced an empty document")
    return text


def _repository_corpus(repository: Path, destination: Path) -> tuple[str, int]:
    raw_files = _run(["git", "ls-files"], cwd=repository).splitlines()
    chunks: list[str] = []
    used = 0
    selected = 0
    for name in raw_files:
        path = repository / name
        if path.suffix.lower() not in TEXT_EXTENSIONS or not path.is_file():
            continue
        if any(part in {"node_modules", "vendor", "dist", "build"} for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
        except OSError:
            continue
        chunk = f"\n===== FILE {name} =====\n{content}\n"
        if used + len(chunk) > MAX_REPO_CHARS:
            break
        chunks.append(chunk)
        used += len(chunk)
        selected += 1
    if not chunks:
        raise IngestionError("repository contains no supported tracked text or code files")
    corpus = "".join(chunks)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(corpus, encoding="utf-8")
    return corpus, selected


def _grounding_prompt(
    paper_id: str,
    title: str,
    paper_text: str,
    repository_corpus: str,
) -> str:
    contract = {
        "central_question": "one question using the paper's own motivation and terms",
        "required_section_ids": "5-7 stable snake_case IDs beginning with motivation and related_work, ending with findings and limits",
        "paper_excerpts": [{"locator": "section/equation/table", "text": "source-faithful summary", "source_refs": [f"{paper_id}-paper:locator"]}],
        "code_notes": [{"locator": "path:symbol or lines", "text": "confirmed implementation observation", "source_refs": [f"{paper_id}-repo:path"]}],
    }
    return "\n\n".join(
        [
            "You are the source-grounding JSON API stage of a paper-and-repository explainer. No coding agent participates.",
            "Return only one JSON object matching the contract. Preserve the paper's terminology and stated motivation; do not coin substitute names. Put code beside the mechanism or equation it realizes. The section IDs should reflect the paper, not a universal slide template.",
            "Every paper excerpt needs a visible locator. Every code note needs a repository path or symbol. Do not generate HTML, Python, Manim code, or shell commands.",
            f"CONTRACT={canonical_json(contract)}",
            f"PAPER_TITLE={title}",
            f"PAPER_TEXT={paper_text[:MAX_PAPER_CHARS]}",
            f"REPOSITORY_CORPUS={repository_corpus[:MAX_REPO_CHARS]}",
        ]
    )


def ingest_source_packet(
    *,
    paper_id: str,
    paper: Path,
    repository: Path,
    run_root: Path,
    provider: StageProvider,
    title: str | None = None,
    paper_url: str | None = None,
    audience: str = "Technical readers learning the paper, its related work, implementation, and findings.",
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", paper_id):
        raise IngestionError("paper_id must be a stable schema identifier")
    paper = paper.resolve()
    repository = repository.resolve()
    run_root = run_root.resolve()
    if not paper.is_file() or paper.suffix.lower() != ".pdf":
        raise IngestionError("--paper must point to a readable PDF")
    if not (repository / ".git").exists():
        raise IngestionError("--repo must point to a git repository")
    run_root.mkdir(parents=True, exist_ok=True)
    extracted_path = run_root / "inputs" / "paper.txt"
    repository_path = run_root / "inputs" / "repository-corpus.txt"
    metadata_title, page_count = _pdf_metadata(paper)
    paper_text = _paper_text(paper, extracted_path)
    repository_corpus, file_count = _repository_corpus(repository, repository_path)
    resolved_title = title or metadata_title
    if not resolved_title:
        raise IngestionError("paper title is missing from PDF metadata; pass --title")
    revision = _run(["git", "rev-parse", "HEAD"], cwd=repository).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise IngestionError("repository HEAD is not a full git revision")
    remote = _https_remote(repository)
    prompt = _grounding_prompt(paper_id, resolved_title, paper_text, repository_corpus)
    grounding = provider.generate("source_grounding", paper_id, prompt)
    payload = grounding.payload
    required = {"central_question", "required_section_ids", "paper_excerpts", "code_notes"}
    if not required.issubset(payload):
        raise IngestionError(f"source grounding missing {sorted(required - set(payload))}")
    section_ids = payload["required_section_ids"]
    if not isinstance(section_ids, list) or not 5 <= len(section_ids) <= 7:
        raise IngestionError("source grounding must return 5-7 section IDs")
    if section_ids[:2] != ["motivation", "related_work"] or section_ids[-2:] != ["findings", "limits"]:
        raise IngestionError("section path must begin motivation/related_work and end findings/limits")
    line_count = repository_corpus.count("\n") + 1
    packet = {
        "schema_version": "explainer-source-packet/0.1.0",
        "paper_id": paper_id,
        "title": resolved_title,
        "short_title": resolved_title if len(resolved_title) <= 36 else resolved_title[:33] + "…",
        "audience": audience,
        "central_question": payload["central_question"],
        "required_section_ids": section_ids,
        "sources": [{
            "source_id": f"{paper_id}-paper",
            "kind": "paper",
            "url": paper_url,
            "revision": f"local PDF sha256:{sha256_file(paper)[:16]}",
            "sha256": sha256_file(paper),
            "page_count": page_count,
            "retrieved_at": date.today().isoformat(),
        }],
        "code_sources": [{
            "code_id": f"{paper_id}-repo",
            "repository": remote,
            "revision": revision,
            "mapping_state": "confirmed",
            "excerpts": [{
                "path": _repo_relative(repository_path),
                "symbol": f"selected tracked sources ({file_count} files)",
                "line_start": 1,
                "line_end": line_count,
            }],
        }],
        "formula_refs": [],
        "scene_renderer": {
            "engine": "Manim Community 0.19.0",
            "entrypoint": "scenes/explainer_pipeline_native.py",
            "coding_agent_required": False,
            "scene_ids": [],
        },
        "media": [],
        "agent_input": {
            "paper_excerpts": payload["paper_excerpts"],
            "code_notes": payload["code_notes"],
            "claim_policy": "Preserve paper terminology. Cite equation, table, figure, section, and code locators. Separate exact results, authors' reported findings, derived explanations, and open questions.",
        },
    }
    record = {
        "trace": {
            "provider": grounding.provider,
            "model": grounding.model,
            "generation_mode": grounding.generation_mode,
            "prompt_sha256": sha256_json({"prompt": prompt}),
            "response_sha256": grounding.response_sha256,
        },
        "source_packet": packet,
    }
    (run_root / "source_grounding.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_root / "source_packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return packet
