# 2026-07-15 Paper Media Roadmap Discussion

Status: decisions recorded; implementation pending

Stable specification: [Paper Media Pipelines: Stable Design](../design/paper-media-pipelines.md)

Source-link policy: upstream links in this dated record are mutable navigation references and `non_snapshot` unless a full revision, retrieval timestamp, and content/license hash are explicitly recorded. They do not satisfy run reproducibility or publication gates.

## 1. Why this discussion happened

The website section titled **Baseline coverage run — Five Topics Across Five Framework Styles** currently overstates its evidence. `[MEASURED]` The checked-in baseline manifest contains 25 entries: 20 use `provider=mock` and five use `provider=local`. Those artifacts are useful previews, but they are not 25 real upstream baseline reproductions.

The immediate integrity rule is therefore:

- mock or deterministic framework-style output has `implementation_origin=synthetic_fixture` + completion `placeholder`;
- an in-house result has `implementation_origin=project_native`, not `upstream_repository`;
- only a real upstream run or an explicitly labeled method reproduction may enter a baseline comparison;
- render success alone is not semantic, pedagogical, or reproduction success.

This record captures the July 15 decisions that turn the project from a collection of demos into an evidence-backed set of media pipelines.

## 2. Decisions approved on July 15

### 2.1 Benchmark topics

`[DECISION]` Use four canonical paper families for the cross-pipeline matrices:

1. Transformer attention
2. DPO
3. FeynRL batch adaptation
4. RoPE

`transformers_core` and `attention_softmax_lookup` remain distinct artifacts under one Transformer family. Gradient Descent remains a pedagogical control, not a fifth paper family.

### 2.2 Video baselines

`[DECISION]` The initial shortlist is:

- [Paper2Manim / ManimAgent](https://github.com/jwj1342/Paper2Manim)
- [Code2Video](https://github.com/showlab/Code2Video)
- [TheoremExplainAgent](https://github.com/TIGER-AI-Lab/TheoremExplainAgent)

The target matrix is three pipelines by four paper families. The first pilot is Attention across all three pipelines.

The baselines have intentionally different native contracts. Paper2Manim is paper-grounded. Code2Video starts from a knowledge point. TheoremExplainAgent starts from a theorem/formula. Adapted runs must say so; we will not erase the difference by calling every run “upstream paper-to-video.”

### 2.3 Slide baselines

`[DECISION]` The initial shortlist is:

- `deeppresenter_current` from the [DeepPresenter / PPTAgent repository](https://github.com/icip-cas/PPTAgent)
- [SlideGen](https://github.com/Y-Research-SBU/SlideGen)
- [ArcDeck](https://github.com/RehgLab/ArcDeck)

Paper2Slides is the fallback if ArcDeck cannot complete the controlled pilot or if visual-backend independence becomes a decisive requirement.

The target matrix is three pipelines by four paper families. The first pilot uses Gradient Descent control plus one predeclared hard paper topic, RoPE or FeynRL, across all three pipelines.

### 2.4 Main pipeline and bottom-up exploration

`[DECISION]` The main in-house pipeline integrates slide generation with Manim generation. It will represent:

- topic/claim structure;
- formula operation structure;
- code/dataflow structure;
- Manim primitive and scene structure.

These four internal layers will appear as three synchronized public views: topic/claim, formula+code, and Manim primitive/scene.

`[DECISION]` Bottom-up formula explanation is part of the **Our Slides + Manim** thread, not a fifth top-level thread. It decomposes Atom → Operation → Formula → Topic, looks up reusable visual primitives, generates a video for each formula, and composes formula clips into an overall topic video.

Built-in Manim capabilities, reusable functions written by the project, one-off generated functions, and missing/planned functions will use distinct badges. Color will not be the sole indicator.

### 2.5 Backtranslation

`[DECISION]` Use approximately ten source-available [Manim Community gallery](https://docs.manim.community/en/stable/examples.html) scenes as a public development set. Compare:

1. Human: official source render at a fixed commit;
2. One-shot: MP4-only reconstruction with hidden source/metadata and no render feedback;
3. Self-refined: exact one-shot code plus at most three fixed feedback iterations under a versioned feedback/early-stop policy.

The gallery set is not a clean held-out benchmark because model training exposure is plausible. Ordinary YouTube videos may be linked for context but will not be downloaded or rehosted without an explicit compatible license.

### 2.6 Website structure

`[DECISION]` Refactor toward an Overview/Evidence Ledger plus four top-level product threads:

1. Real Video Pipelines
2. Paper-to-Slides
3. Our Slides + Manim
4. Backtranslation

The site should be rendered from an allowlisted public projection of the private canonical manifest rather than hand-maintained completion claims. Each result should show its pipeline variant, family, granularity, composite lineage, machine-derived completion, revision, model condition, cost state, repair history, review, license conclusion, and public manifest.

### 2.7 Budget

`[DECISION]` Budget policy `pilot-budget-2026-07-15/v1` has hard limits of **$15 per cell** and **$200 total**. Before execution, its experiment config must define shared-setup allocation and rate-card snapshot; the harness uses atomic pre-stage reservations and fails closed when a paid stage's projected cost is unknown. Unknown measured cost is not `$0`; it is `N/A`/`null`. Measured and estimated cost remain separate.

## 3. Evidence and terminology decisions

`[DECISION]` Public claims use six labels:

- `[MEASURED]`: reproduced in this project from preserved evidence;
- `[OBSERVED]`: directly inspected state with retrieval time/evidence, but not a benchmark measurement;
- `[REPORTED]`: stated by an upstream paper/repository but not reproduced here;
- `[ESTIMATE]`: forecast with assumptions;
- `[PLANNED]`: approved but not yet executed;
- `[DECISION]`: project choice rather than experiment result.

`[DECISION]` Lineage is composite, not a single provenance enum. Run and artifact records independently store implementation origin, native/adapted input contract, patch level and patchset hash, derivation/repair stage, and parent-artifact lineage. Completion (`full`, `partial`, `smoke`, `failed`, `placeholder`) is machine-derived from a versioned pipeline-specific completion contract. Review is a structured event with a rubric/evaluator/evidence/timestamp. A full render can still fail semantic review; a high-quality project-native clip is still not an upstream reproduction.

## 4. Source review and caveats

Unless a full revision and content/license hash are stated, links in this section are mutable navigation references and the accompanying statements are `non_snapshot`. They document July 15 research observations but do not satisfy a run's source/license gate. Each executed run must create its own immutable source and license snapshot.

### 4.1 Paper2Manim license

`[OBSERVED]` At the reviewed revision, Paper2Manim declares MIT in package metadata, but a standalone license text was not found in the repository root. The approved wording is:

> MIT declared in package metadata; standalone license text not found at cited revision.

We will not describe it as unlicensed, but we will also not make an unconditional redistribution claim until the license evidence is clarified. Exact commit and package metadata must be preserved for each run.

### 4.2 DeepPresenter versus PPTAgent

`[OBSERVED]` The current repository contains both `deeppresenter/` and `pptagent/` paths. “DeepPresenter/PPTAgent” is not a sufficient run identifier. We will use explicit IDs such as `deeppresenter_current`; `pptagent_legacy` is an optional ablation.

### 4.3 Correct SlideGen repository

`[DECISION]` The canonical repository is [Y-Research-SBU/SlideGen](https://github.com/Y-Research-SBU/SlideGen). Older references to a different namespace are stale and must not be used for reproduction or license claims.

### 4.4 ArcDeck maturity and ancestry

`[OBSERVED]` ArcDeck is code-available and suitable for a pilot, but it is experimental: the reviewed repository has limited visible history, no release/tag, and broad unpinned requirements. Every run must pin a full commit and environment.

`[REPORTED]` ArcDeck's official repository acknowledges that part of its visual generation prompts/code is adapted from SlideGen. ArcDeck and SlideGen are therefore not independent visual backends. ArcDeck remains shortlisted because its discourse-tree and commitment-planning approach is meaningfully different. Paper2Slides remains the fallback.

### 4.5 Manim assets

`[REPORTED]` Manim Community code/examples are MIT-licensed, while its documentation warns that some 3Blue1Brown-associated characters or assets are separately copyrighted. Backtranslation selection will exclude branded or non-permissive assets and record scene-level dependencies.

### 4.6 Code anchors

`[DECISION]` Paper and code references must be versioned independently. Tensor2Tensor is a historical code anchor, not a current maintained Transformer runtime. FeynRL mappings found in the current local audit cite commit `dfe85351e28a3744ab0eb02d2299fc1e6d3d5752`; later upstream releases do not silently alter those measured mappings.

## 5. Alternatives considered

### 5.1 ArcDeck or Paper2Slides

ArcDeck was selected for the pilot because audience/duration-conditioned discourse and commitment planning diversify the slide-planning approaches. Its visual ancestry and experimental packaging weaken independence and reproducibility. Paper2Slides is retained as an explicit fallback rather than quietly swapped in after a failed run.

### 5.2 ManimTrainer as a baseline

ManimTrainer/refinement-style work is better treated as a refinement ablation than a full paper-to-video baseline. The research question is whether refinement improves the exact one-shot artifact under a fixed budget, not whether a refinement loop can stand in for an end-to-end paper pipeline.

### 5.3 Bottom-up as a fifth website thread

Rejected. Bottom-up formula explanation is a core capability of the integrated Slides + Manim pipeline. Making it top-level would split one architecture into two product narratives and obscure how formula clips enter slides.

### 5.4 YouTube as backtranslation ground truth

Rejected as the default. Public visibility does not establish download, modification, or redistribution rights. Source-available Manim Community scenes provide auditable code, environment, and license evidence. YouTube can remain link-only qualitative context.

### 5.5 Five topics versus four paper families

Rejected as a benchmark count. The current five local specs include two Transformer artifacts. Counting artifacts as paper families inflates coverage. The matrix uses four families, while each family may expose topic- and formula-level artifacts.

## 6. Planned experiment sequence

### Phase A — integrity and evidence harness

`[PLANNED]`

- Define normalized run/artifact records and validation.
- Quarantine or explicitly label dummy coverage.
- Capture source/license evidence and pin-at-run state.
- Add stage status, cost, artifact hash, and review events.
- Generate a redacted allowlisted public projection from the private canonical manifest.

Gate evidence: schema/completion validators pass; publication validator passes with canonical/public hashes and redaction summary; every public card resolves to a public manifest and artifact hash.

### Phase B — video pilot

`[PLANNED]`

- Run Transformer Attention with Paper2Manim, Code2Video, and TheoremExplainAgent.
- Preserve native input differences and method-reproduction labels.
- Review technical, semantic, pedagogical, visual, cost, and intervention evidence.

Gate evidence: all pilot cells have reconciled budget ledgers, completion-contract outputs, required technical-validator results, and semantic/pedagogical rubric events. The recorded decision uses those evidence refs to continue, replace, or narrow.

### Phase C — slide pilot

`[PLANNED]`

- Run Gradient Descent control and one predeclared hard topic across `deeppresenter_current`, SlideGen, and ArcDeck.
- Use a controlled model/budget condition; evaluate native-best only on two hard topics as a separate condition.
- Exercise the Paper2Slides fallback only under the declared criteria.

Gate evidence: each pilot cell has validated PPTX/static deliverables, completion-contract output, reconciled cost, and versioned semantic/presentation rubric events. The baseline-lock decision references those records.

### Phase D — formula/code/Manim graph

`[PLANNED]`

- Build typed graphs and confidence-aware mappings.
- Create a primitive registry with origin badges and tests.
- Produce formula clips and one topic-level composition.

Gate evidence: graph-schema/typed-edge validators pass with no dangling refs; every confirmed mapping has a permitted review event; required formula and topic artifacts pass media validation.

### Phase E — integrated Slides + Manim

`[PLANNED]`

- Link FormulaIR, SceneIR, and SlideIR through versioned animation slots.
- Use formula explainers for methodology, graph/dataflow scenes for architecture, and chart/comparison primitives for performance.
- Verify static fallbacks and editable deck behavior.

Gate evidence: PPTX structure validator passes; every required AnimationSlot resolves `scene_ir_ref`, rendered artifact, and static fallback; both media and static-fallback rubrics meet predeclared thresholds.

### Phase F — backtranslation

`[PLANNED]`

- Select and pin approximately ten gallery scenes across diverse visual categories.
- Run fixed Human, One-shot, and Self-refined conditions.
- Publish repair histories, costs, source/license caveats, and contamination limitations.

Gate evidence: protocol-policy validator passes; each self-refined chain begins at the exact one-shot hash and complies with its feedback policy; publication/license validators pass for all source assets.

### Phase G — website refactor and scale-up

`[PLANNED]`

- Render the evidence ledger and four product threads from normalized data.
- Add synchronized mapping views and three-column backtranslation comparison.
- Expand to full matrices only after pilot review and a new approved budget.

Gate evidence: site build consumes only the validated public projection; claim-to-evidence link checks and accessibility/media checks pass; no synthetic fixture enters baseline aggregates.

## 7. Open risks

1. **Upstream reproducibility:** repositories may lack releases, locks, or stable APIs; pinning may still require compatibility patches.
2. **License ambiguity:** Paper2Manim's metadata-only license declaration needs clarification before broad artifact redistribution.
3. **Baseline independence:** ArcDeck's SlideGen ancestry may reduce the diversity of slide visual generation even if planning differs.
4. **Input-contract fairness:** paper-, topic-, and formula-native systems cannot be compared honestly without preserving adaptation labels.
5. **Model/version drift:** mutable provider aliases can invalidate later comparisons unless immutable versions and prompt hashes are recorded.
6. **Cost coverage:** API-only totals can look artificially cheap if compute, assets, and manual repair are omitted.
7. **Semantic evaluation:** automatic render and VLM checks may miss subtle formula or code errors; targeted human review remains necessary.
8. **Graph matching:** paper formulas and code often differ by notation, approximation, batching, or implementation detail; unresolved mappings must remain visible.
9. **Primitive overfitting:** one-off scenes may be mislabeled reusable before their interface and tests stabilize.
10. **Backtranslation contamination:** public gallery examples may be present in model training data, limiting claims about generalization.
11. **Deck portability:** embedded video behavior varies across viewers; static fallbacks and playback contracts are mandatory.
12. **Website performance:** many video cells and interactive graphs can regress loading/accessibility without lazy media and normalized data.

## 8. Questions deferred to pilots

- Which hard topic, RoPE or FeynRL, should be the first slide pilot alongside Gradient Descent?
- Does ArcDeck complete the controlled environment reliably enough to retain its slot?
- Which formula/code matching thresholds require human confirmation?
- What primitive promotion test is sufficient beyond reuse in two formulas/topics?
- Which semantic and pedagogical rubrics correlate with learner outcomes strongly enough to become gates?
- What post-pilot budget supports the full 24 baseline cells and in-house integrated runs?

These are intentionally not resolved by prose. The pilot manifests and reviews should provide the evidence for the next decision record.
