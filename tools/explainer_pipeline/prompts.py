from __future__ import annotations

from typing import Any

from .common import canonical_json


STAGE_CONTRACTS = {
    "concept_graph": """Return a JSON object with keys thesis, nodes, edges, and unresolved.
Each node needs id, label, kind, era, summary, source_refs. Each edge needs source, target,
relation, and teaching_point. Build a conceptual lineage, not a citation dump. Do not invent
facts, rename paper terms, or convert candidate mappings into confirmed ones. Prefer node labels
that appear verbatim in the paper or repository.""",
    "lesson_plan": """Return a JSON object with keys title, promise, sections, and appendix.
Sections must be ordered learning transitions. Each section needs id, nav_label, title,
question, learning_goal, misconception, summary, source_refs, medium, and deep_links.
Use the exact section IDs requested in the input. Phrase motivation as the paper's own question
or stated concern. Choose animation only when state change or geometry carries meaning.""",
    "section_content": """Return a JSON object with keys sections and appendix_entries.
Each section maps to blocks chosen from paper_question, prose, comparison, related_reading,
formula_steps, code, video, line_chart, bar_chart, lineage, numeric_fixture, rotation,
limitation, and learner_check.
Every factual claim needs source_refs. Result blocks must include exact source locators
and reported/inferred labels. Use related_reading blocks only for primary-source HTTPS links
present in the paper's references or source packet. Integrate confirmed code beside the formula
or mechanism it implements. Use a video block only when the source packet contains matching
video, poster, and captions media IDs. Never generate Python, Manim code, HTML, or executable code.""",
}


def build_prompt(
    stage: str,
    source_packet: dict[str, Any],
    prior_outputs: dict[str, Any],
) -> str:
    if stage not in STAGE_CONTRACTS:
        raise ValueError(f"unknown stage: {stage}")
    return "\n\n".join(
        [
            "You are one JSON-only API stage in a fail-closed paper-and-code explainer pipeline. No coding agent participates in this runtime.",
            STAGE_CONTRACTS[stage],
            "Return only the JSON object. Preserve the paper's terminology and stated motivation. Keep derivations and provenance linkable without separating code from the mechanism it realizes.",
            f"SOURCE_PACKET={canonical_json(source_packet)}",
            f"PRIOR_OUTPUTS={canonical_json(prior_outputs)}",
        ]
    )
