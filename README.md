# 4blue2brown

Research and prototype workspace for an input-to-programmatic-math-explainer pipeline inspired by the 3Blue1Brown / Manim production model.

The working goal is not to clone a channel brand, voice, or assets. It is to learn from the public Manim ecosystem and build a pipeline that can turn structured inputs into precise, inspectable, rerenderable explanatory animations.

## Current phase

Phase 1 is evidence-backed offline prototyping and integration design:

- The four website/research threads and their evidence/publication rules have an accepted design.
- The q-5 canonical evidence contract validates completion, lineage, costs, licenses, and fail-closed public projection.
- The q-6 Manim gallery backtranslation harness has a pinned ten-scene registry, offline one-shot/self-refine protocol, deterministic feedback, and synthetic dry-run manifests.

This is not yet an end-to-end production pipeline. Real provider execution and cost reconciliation, bottom-up formula-graph generation, and slides-plus-Manim integration remain unimplemented.

## Artifacts

- [3b1b GitHub survey](docs/research/3b1b-github-survey.md)
- [3b1b direct source cases](docs/research/3b1b-direct-source-cases.md)
- [FeynRL visualization audit](docs/research/feynrl-visualization-audit.md)
- [Related papers](docs/research/related-papers.md)
- [Paper-with-code explainer video pipeline plan](docs/plans/paper-code-video-pipeline.md)
- [Paper media pipeline design](docs/design/paper-media-pipelines.md)
- [2026-07-15 paper media roadmap](docs/discussions/2026-07-15-paper-media-roadmap.md)
- [Canonical evidence schemas](schemas/paper-media/)
- [Offline Manim backtranslation harness](experiments/backtranslation/v1/README.md)
- [Agentic long-horizon Manim video pipeline](AGENTIC_PIPELINE.md)
- [Critical review of systems, code, papers, and gaps](CRITICAL_REVIEW.md)
- [System map diagram](SYSTEM_MAP.md)
- [Lesson source audit TSV](data/3b1b_lessons_source_audit.tsv)
- [FeynRL method SVG prototype](tools/feynrl_method_viz.py)

## Snapshot

Project snapshot date: 2026-07-15.

The earlier landscape audit found 174 lesson pages on `3Blue1Brown.com`, of which 143 have `source` fields that directly resolve into the audited `3b1b/videos` tree. Another 15 appeared stale or renamed, and 16 had no usable public source field. Since that audit, the repository has added the design/evidence layer and an offline backtranslation harness; those additions do not constitute real provider results or completed formula/slides integrations.

## Candidate next milestones

1. Produce canonical evidence for real upstream video and paper-to-slides baseline runs.
2. Implement a real-provider backtranslation path with immutable model identity, reservation/reconciliation cost evidence, and sandboxed rendering.
3. Build and evaluate the bottom-up topic/formula/Manim-function matching graph.
4. Integrate formula and performance animation slots into the slides pipeline.
5. Publish website results only from validated public manifest projections.
