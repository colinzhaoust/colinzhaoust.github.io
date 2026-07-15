# 4blue2brown

Research and prototype workspace for an input-to-programmatic-math-explainer pipeline inspired by the 3Blue1Brown / Manim production model.

The working goal is not to clone a channel brand, voice, or assets. It is to learn from the public Manim ecosystem and build a pipeline that can turn structured inputs into precise, inspectable, rerenderable explanatory animations.

## Current phase

Phase 0 is landscape research:

- What public 3b1b repositories exist, and which are useful to a generation pipeline?
- Which published 3Blue1Brown lessons have public source paths that can be mapped to `3b1b/videos`?
- Which research papers are close to this problem: natural language to visual specs, chart/code generation, animation grammar, video generation, and direct STEM animation generation?

## Artifacts

- [3b1b GitHub survey](docs/research/3b1b-github-survey.md)
- [3b1b direct source cases](docs/research/3b1b-direct-source-cases.md)
- [FeynRL visualization audit](docs/research/feynrl-visualization-audit.md)
- [Related papers](docs/research/related-papers.md)
- [Paper-with-code explainer video pipeline plan](docs/plans/paper-code-video-pipeline.md)
- [Agentic long-horizon Manim video pipeline](AGENTIC_PIPELINE.md)
- [Critical review of systems, code, papers, and gaps](CRITICAL_REVIEW.md)
- [System map diagram](SYSTEM_MAP.md)
- [Lesson source audit TSV](data/3b1b_lessons_source_audit.tsv)
- [FeynRL method SVG prototype](tools/feynrl_method_viz.py)

## Snapshot

Research snapshot date: 2026-07-01.

The current audit found 174 lesson pages on `3Blue1Brown.com`, of which 143 have `source` fields that directly resolve into the current `3b1b/videos` tree. Another 15 appear to be stale or renamed source paths that can likely be repaired manually. The remaining 16 have no usable public source field in the website frontmatter.

## Candidate next milestones

1. Build a reproducible metadata ingester for `3b1b/3Blue1Brown.com`, `3b1b/videos`, and `3b1b/captions`.
2. Choose a render baseline: 3b1b ManimGL compatibility first, or modern Manim Community target first.
3. Render a small golden set of recent scenes, starting with 2024-2026 sources that are more likely to run with fewer historical compatibility fixes.
4. Define a small scene-plan IR: narrative beats, objects, mathematical state, camera, timing, and audio alignment.
5. Prototype an LLM-assisted loop: input -> scene plan -> Manim code -> render -> visual checks -> repair.
