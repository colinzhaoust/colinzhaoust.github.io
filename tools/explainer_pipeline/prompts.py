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
Sections must be an ordered prerequisite chain. Each section needs id, role, nav_label, title,
intent, question, learning_goal, misconception, summary, source_refs, medium, and deep_links.
deep_links must be an array of stable appendix entry ID strings (for example "p3o-derivation"),
never URL objects; section_content will create one appendix entry with each exact ID.
When section_policy.mode is model_proposed, choose the section split yourself within its min/max
range, cover every required role, and follow sequence_rule. Use stable snake_case IDs. One section
must do one cognitive job; split only when the prerequisite, mechanism, or evidence question changes.
Phrase motivation as the paper's own question or stated concern. Intent must explain why this section
is needed at this point in the paper's argument. Choose animation only when state change, geometry,
or a controlled result transition carries meaning.""",
    "section_content": """Return a JSON object with keys sections, animation_plan, and appendix_entries.
Each section maps to blocks chosen from paper_question, prose, comparison, related_reading,
formula_steps, code, video, micro_video, equation_thread, result_story, line_chart, bar_chart,
lineage, numeric_fixture, rotation, limitation, and learner_check.
Every factual claim needs source_refs. Result blocks must include exact source locators
and reported/inferred labels. Findings must be organized as question, setting, metric, evidence,
and takeaway. Equation threads must account for every equation_coverage item, including an
explicit folded list. Use related_reading blocks only for primary-source HTTPS links
present in the paper's references or source packet. Integrate confirmed code beside the formula
or mechanism it implements. Use a video block only when the source packet contains matching
video, poster, and captions media IDs.

Balance media deliberately: HTML carries motivation, definitions, comparisons, and interpretation;
Manim carries one visible state change, geometric action, or controlled metric change; code verifies
where the mechanism acts. Use 2-6 non-media content blocks per section; harness-materialized animation
slots are counted separately. Do not begin a section with video. Place a
formula or result explanation immediately before its animation and interpretation immediately after.
Use at most two animations in a non-evidence section and at most three in an evidence section. Avoid
repeating the same equation history in lineage, equation_thread, prose, and video. Prefer one complete
representation plus one animation. Mechanism and limitation roles should end with learner_check.

animation_plan lists every selected animation with section_id, media_id, purpose, before_state,
after_state, and adjacent_block_index pointing to the explanatory block it should follow. The harness
materializes a standard micro_video block from that semantic decision, so do not duplicate video or
micro_video blocks yourself. Only choose registered media from the packet; an empty list is valid.
appendix_entries use {id,title,body,source_refs}. Never generate Python,
Manim code, HTML, or executable code.""",
}


BLOCK_CONTRACTS = """Use these exact block shapes; omit unused block types:
paper_question {type,label,question,context,source_refs}
prose {type,eyebrow?,heading,paragraphs:[string],source_refs}
comparison {type,columns:[{label,question,answer,accent:green|violet|orange|cyan}],source_refs}
lineage {type,nodes:[{label,note}],edges:[object],source_refs}
equation_thread {type,title,stages:[{paper?,year?,source_url?,equation,formula,intent,change}],folded:[{equations,reason}],source_refs}
formula_steps {type,formula,claim_label,steps:[{label,expression,meaning,primitive:{id,origin:manim_builtin|project_inherited|project_new|unresolved}}],source_refs}
numeric_fixture {type,title,formula,fixtures:[{label,values:[number],ess:number,accent}],note,claim_label,source_refs}
rotation {type,title,angle_label,formula,note,claim_label,source_refs}
code {type,code_source_id,path,symbol,lines:[{number,code,maps_to}],source_refs}
result_story {type,question,setting,metric,evidence_kind,evidence,takeaway,source_refs}
bar_chart {type,title,axis_min:number,axis_max:number,unit,groups:[{label,value:number,uncertainty?,accent}],claim_label,source_refs}
line_chart {type,title,x_label,y_label,series:[{label,accent,points:[{x:number,y:number}]}],claim_label,source_refs}
reported_trends {type,title,items:[{label,finding,source_ref}],claim_label,source_refs}
related_reading {type,title,items:[{title,url,relation}],source_refs}
limitation {type,items:[{label,detail}],source_refs}
learner_check {type,prompt,answer}
video {type,media_id,poster_id,captions_id,title,caption,beats:[string],source_refs}
micro_video {type,media_id,poster_id,captions_id,title,intro,observation,consequence,beats:[string],source_refs}"""


def build_prompt(
    stage: str,
    source_packet: dict[str, Any],
    prior_outputs: dict[str, Any],
) -> str:
    if stage not in STAGE_CONTRACTS:
        raise ValueError(f"unknown stage: {stage}")
    block_contract = BLOCK_CONTRACTS if stage == "section_content" else ""
    return "\n\n".join(
        [
            "You are one JSON-only API stage in a fail-closed paper-and-code explainer pipeline. No coding agent participates in this runtime.",
            STAGE_CONTRACTS[stage],
            block_contract,
            "Return only the JSON object. Preserve the paper's terminology and stated motivation. Keep derivations and provenance linkable without separating code from the mechanism it realizes. Optimize for a reader learning the entire paper thread, not for slide density or visual novelty.",
            f"SOURCE_PACKET={canonical_json(source_packet)}",
            f"PRIOR_OUTPUTS={canonical_json(prior_outputs)}",
        ]
    )


def build_section_content_prompt(
    source_packet: dict[str, Any],
    prior_outputs: dict[str, Any],
    section: dict[str, Any],
) -> str:
    """Build a bounded content prompt for one already-planned lesson section."""
    section_id = section["id"]
    prior_sections = prior_outputs.get("lesson_plan", {}).get("sections", [])
    appendix_owner: dict[str, str] = {}
    for planned_section in prior_sections:
        for deep_link in planned_section.get("deep_links", []):
            appendix_owner.setdefault(deep_link, planned_section["id"])
    required_appendix_ids = [
        deep_link
        for deep_link in section.get("deep_links", [])
        if appendix_owner.get(deep_link, section_id) == section_id
    ]
    allowed_source_prefixes = [
        item["source_id"] for item in source_packet.get("sources", [])
    ] + [item["code_id"] for item in source_packet.get("code_sources", [])]
    return "\n\n".join(
        [
            "You are one JSON-only API stage in a fail-closed paper-and-code explainer pipeline. No coding agent participates in this runtime.",
            STAGE_CONTRACTS["section_content"],
            BLOCK_CONTRACTS,
            f"Generate ONLY the section whose exact ID is {section_id!r}. The sections object must contain exactly one key, {section_id!r}, and preserve that spelling. Do not use source_packet.required_section_ids or invent another ID.",
            f"Use this exact outer shape: {{\"sections\":{{\"{section_id}\":{{\"blocks\":[...]}}}},\"animation_plan\":[],\"appendix_entries\":[]}}. The section value is an object with a blocks array; it is never a bare array.",
            "Do not add video or micro_video blocks. Select animation semantically in animation_plan; adjacent_block_index is the zero-based index of the explanatory formula/result block AFTER WHICH the harness should insert it. If no animation helps, animation_plan must be empty.",
            f"Every source_ref must begin with one of these exact source/code prefixes: {canonical_json(allowed_source_prefixes)}. Media IDs and formula IDs are never source_ref prefixes; attach their underlying paper or code locator instead.",
            f"The section role is {section.get('role')!r}. Follow this exact plan: {canonical_json(section)}",
            f"appendix_entries must contain one grounded entry for every requested deep-link ID and no unrelated entries. Shared IDs are owned by their first lesson section; do not recreate entries owned elsewhere. REQUIRED_APPENDIX_IDS={canonical_json(required_appendix_ids)}",
            "Return only the JSON object. Preserve the paper's terminology and stated motivation. This fragment will be merged with other independently validated sections, so do not summarize or regenerate their content.",
            f"SOURCE_PACKET={canonical_json(source_packet)}",
            f"PRIOR_CONCEPT_GRAPH={canonical_json(prior_outputs.get('concept_graph', {}))}",
        ]
    )


def build_repair_prompt(
    stage: str,
    original_prompt: str,
    invalid_payload: dict[str, Any] | None,
    validation_error: str,
) -> str:
    """Ask the same API stage to repair its own typed output without changing evidence."""
    return "\n\n".join(
        [
            original_prompt,
            "Your previous response did not pass the fixed harness. Return a complete replacement JSON object, not a patch and not an explanation.",
            f"VALIDATION_ERROR={validation_error[:4000]}",
            f"PREVIOUS_PAYLOAD={canonical_json(invalid_payload) if invalid_payload is not None else 'unavailable because the response was not valid JSON'}",
            f"REPAIR_STAGE={stage}",
        ]
    )
