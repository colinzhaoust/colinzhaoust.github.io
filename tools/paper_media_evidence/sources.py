"""Thread-aware typed source compatibility helpers."""

from __future__ import annotations

from typing import Any, Mapping


PAPER_THREADS = {"real_video_pipelines", "paper_to_slides", "slides_plus_manim"}


def typed_source_snapshots(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return native typed snapshots or typed views of the legacy paper/code pair."""

    inputs = document["input"]
    if "source_snapshots" in inputs:
        return [dict(item) for item in inputs["source_snapshots"]]
    converted: list[dict[str, Any]] = []
    for field, source_id, source_type in (
        ("paper_snapshot", "input:paper", "paper"),
        ("code_snapshot", "input:repository", "repository"),
    ):
        snapshot = inputs.get(field)
        if snapshot is not None:
            converted.append({"source_id": source_id, "source_type": source_type, **snapshot})
    return converted


def required_source_groups(thread: str) -> tuple[frozenset[str], ...]:
    """Each returned group requires at least one matching source type."""

    if thread in PAPER_THREADS:
        return (frozenset({"paper"}), frozenset({"repository"}))
    if thread == "backtranslation":
        return (frozenset({"repository"}), frozenset({"example_gallery", "example"}))
    return ()
