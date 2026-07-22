# 4blue2brown

Research and prototype workspace for an input-to-programmatic-math-explainer pipeline inspired by the 3Blue1Brown / Manim production model.

The working goal is not to clone a channel brand, voice, or assets. It is to learn from the public Manim ecosystem and build a pipeline that can turn structured inputs into precise, inspectable, rerenderable explanatory animations.

## Current phase

Phase 1 is evidence-backed offline prototyping and integration design:

- The four website/research threads and their evidence/publication rules have an accepted design.
- The q-5 canonical evidence contract validates completion, lineage, costs, licenses, and fail-closed public projection.
- The q-6 Manim gallery backtranslation harness has a pinned ten-scene registry, offline one-shot/self-refine protocol, deterministic feedback, and synthetic dry-run manifests.
- The paper + code explainer has reviewed FeynRL/RoPE bundles, model-proposed section policies, paper-native equation and finding coverage, a Formula-IR-to-Manim capability graph, deterministic micro-videos, and a comparison-ready static website.
- Live JSON adapters cover Bedrock Runtime, Vertex AI, and OpenAI-compatible endpoints such as WInE and Bedrock Mantle. Complete Gemini 3.1 Pro and GPT-5.5 FeynRL/RoPE runs are frozen; the incomplete Qwen3 32B row is reported but excluded from the selector.

This is still a research pipeline rather than a production service. The first cross-model API matrix is complete for Gemini 3.1 Pro and GPT-5.5 with recorded tokens, API time, estimated cost, repairs, and harness normalizations. Generalizing the reviewed FeynRL/RoPE visual grammar to arbitrary papers—and defining a fair comprehension evaluation beyond schema validity—remains open.

## Artifacts

- [3b1b GitHub survey](docs/research/3b1b-github-survey.md)
- [3b1b direct source cases](docs/research/3b1b-direct-source-cases.md)
- [FeynRL visualization audit](docs/research/feynrl-visualization-audit.md)
- [Related papers](docs/research/related-papers.md)
- [Paper-with-code explainer video pipeline plan](docs/plans/paper-code-video-pipeline.md)
- [Paper + repository explainer harness and model comparison](docs/explainer-pipeline.md)
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

Project snapshot date: 2026-07-22.

The earlier landscape audit found 174 lesson pages on `3Blue1Brown.com`, of which 143 have `source` fields that directly resolve into the audited `3b1b/videos` tree. Another 15 appeared stale or renamed, and 16 had no usable public source field. Since that audit, the repository has added the design/evidence layer and an offline backtranslation harness; those additions do not constitute real provider results or completed formula/slides integrations.

## Candidate next milestones

1. Add reservation/reconciliation cost evidence and resolved provider-version metadata to every paid comparison run.
2. Evaluate model differences in intent recovery, equation coverage, finding coverage, and learner comprehension—not just prose style or schema validity.
3. Test smaller-model recovery with section budgets and source-prefix contracts without relaxing the frozen comparison boundary.
4. Generalize the Formula-IR/Manim registry and native scene selection to new papers without runtime coding agents.
5. Continue publishing only complete validated runs from public manifest projections.
