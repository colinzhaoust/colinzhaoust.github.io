# Paper Media Pipelines: Stable Design

Status: accepted design direction, implementation pending

Last updated: 2026-07-15

Discussion record: [2026-07-15 paper media roadmap](../discussions/2026-07-15-paper-media-roadmap.md)

## 1. Purpose and scope

This document defines the durable architecture and evidence contract for the project's paper-to-video, paper-to-slides, integrated slides-plus-Manim, bottom-up formula explainer, and backtranslation work.

The words **MUST**, **SHOULD**, and **MAY** are normative:

- **MUST** is required for a result to be presented as benchmark evidence.
- **SHOULD** is the default unless a documented exception is recorded.
- **MAY** is optional.

This design does not implement a manifest schema, run a pilot, or change the website. It defines the contract those implementations must satisfy.

### 1.1 Goals

1. Replace dummy coverage claims with reproducible pipeline-by-paper evidence.
2. Compare diverse upstream video and slide pipelines without erasing their different input contracts.
3. Build a main pipeline that composes editable slides with reusable Manim scenes.
4. Connect paper claims, formulas, code, Manim primitives, scenes, and final media through typed mappings.
5. Make provenance, completion, cost, license, and review status visible at every public result.
6. Evaluate one-shot and self-refined reconstruction against source-available human Manim scenes.

### 1.2 Non-goals

- Claiming that deterministic local previews are upstream baseline reproductions.
- Treating render success as evidence of semantic or pedagogical correctness.
- Generating videos one frame at a time with an LLM. Scenes or clips are the generation unit; frames are render states and evaluation evidence.
- Rehosting ordinary YouTube videos without explicit permission.
- Turning the bottom-up formula explainer into a fifth top-level product thread.

## 2. Claim vocabulary

Every quantitative or maturity claim in reports, manifests, and the website MUST carry one of these labels:

| Label | Meaning | Example |
| --- | --- | --- |
| `[MEASURED]` | Produced by this project from a preserved run or repository snapshot | Render time, artifact hash, local rubric score |
| `[REPORTED]` | Reported by an upstream paper or repository but not reproduced here | A benchmark score from a paper |
| `[ESTIMATE]` | A forecast based on stated assumptions | Expected API cost before a run |
| `[PLANNED]` | Approved work that has not yet produced evidence | A future matrix cell |
| `[DECISION]` | A project choice, not an empirical claim | Selected baseline shortlist |

These labels are orthogonal to provenance and completion status. For example, a full upstream reproduction can still contain `[REPORTED]` metrics alongside `[MEASURED]` local costs.

## 3. Canonical benchmark inputs

The benchmark count is based on `canonical_topic_family × pipeline`, not on the number of generated artifacts. A family MAY contain multiple artifacts at different granularities.

| Canonical family | Paper | Code anchor | Expected artifact granularity |
| --- | --- | --- | --- |
| `transformer_attention` | [Attention Is All You Need, v7](https://arxiv.org/abs/1706.03762) | [Tensor2Tensor](https://github.com/tensorflow/tensor2tensor), a historical Apache-2.0 code anchor that is archived/deprecated | Topic-level Transformer artifact plus formula-unit attention/softmax child artifacts |
| `dpo` | [Direct Preference Optimization, v3](https://arxiv.org/abs/2305.18290) | [Author reference implementation](https://github.com/eric-mitchell/direct-preference-optimization), [Apache-2.0 license](https://github.com/eric-mitchell/direct-preference-optimization/blob/main/LICENSE) | Topic-level method artifact and formula-unit objective artifact |
| `feynrl_batch_adaptive` | [FeynRL](https://arxiv.org/abs/2605.12380) | [FeynRL repository](https://github.com/FeynRL-project/FeynRL), [Apache-2.0 license](https://github.com/FeynRL-project/FeynRL/blob/main/LICENSE) | Topic-level algorithm artifact plus batch-adaptation formula/code units |
| `rope` | [RoFormer](https://arxiv.org/abs/2104.09864) | [Author repository](https://github.com/ZhuiyiTechnology/roformer), [Apache-2.0 license](https://github.com/ZhuiyiTechnology/roformer/blob/main/LICENSE) | Topic-level RoPE artifact and formula/code rotation units |

`transformers_core` and `attention_softmax_lookup` are two artifacts under the single `transformer_attention` family. The latter is a formula-unit child for `softmax(QK^T / sqrt(d_k))V`; it MUST NOT be counted as a fifth paper family. `gradient_descent_control` is a pedagogical control, not a fifth paper.

Code mappings for the current FeynRL snapshot SHOULD cite the locally verified full commit `dfe85351e28a3744ab0eb02d2299fc1e6d3d5752`. A newer upstream release is separate external state and MUST NOT silently replace a run's pinned source.

## 4. Four product threads

### 4.1 Thread 1: real video pipelines

The initial baseline matrix is three pipelines by four canonical paper families.

| Baseline ID | Upstream | Native input contract | Use in this project | License and maturity note |
| --- | --- | --- | --- | --- |
| `paper2manim` | [Paper2Manim / ManimAgent paper](https://arxiv.org/abs/2606.30296), [repository](https://github.com/jwj1342/Paper2Manim) | Paper, arXiv identifier, or PDF to multi-scene Manim with planning/reflection | Paper-grounded video baseline | MIT declared in package metadata; standalone license text not found at cited revision. Redistribution requires caution until clarified. |
| `code2video` | [Code2Video paper](https://arxiv.org/abs/2510.01174), [repository](https://github.com/showlab/Code2Video), [MIT license](https://github.com/showlab/Code2Video/blob/main/LICENSE) | Knowledge point to Planner–Coder–Critic Manim video | Method baseline adapted to a paper topic | Its native input is not a paper-plus-code pair; it MUST NOT be called a paper-grounded upstream run. |
| `theorem_explain_agent` | [TheoremExplainAgent paper](https://arxiv.org/abs/2502.19400), [repository](https://github.com/TIGER-AI-Lab/TheoremExplainAgent), [MIT license](https://github.com/TIGER-AI-Lab/TheoremExplainAgent/blob/main/LICENSE) | Theorem or formula to long-form Manim explanation | Formula-unit adaptation for paper equations | DPO or FeynRL results are method adaptations, not whole-paper/code reproductions. |

The full target is 12 cells. Before broad execution, the project MUST run an Attention pilot across all three video pipelines under the budget gates in Section 11.

### 4.2 Thread 2: paper-to-slides baselines

The initial baseline matrix is three pipelines by four canonical paper families.

| Baseline ID | Upstream | Distinguishing capability | License and maturity note |
| --- | --- | --- | --- |
| `deeppresenter_current` | [DeepPresenter / PPTAgent repository](https://github.com/icip-cas/PPTAgent), [DeepPresenter paper](https://arxiv.org/abs/2602.22839), [MIT license](https://github.com/icip-cas/PPTAgent/blob/main/LICENSE) | Current presentation-generation path, including editable PPTX workflow and optional local model | The repository contains both current DeepPresenter and legacy PPTAgent code. Every run MUST name an explicit variant and revision. `pptagent_legacy` MAY be an ablation but is not interchangeable with `deeppresenter_current`. |
| `slidegen` | [SlideGen paper](https://arxiv.org/abs/2512.04529), [official repository](https://github.com/Y-Research-SBU/SlideGen), [MIT license](https://github.com/Y-Research-SBU/SlideGen/blob/main/LICENSE) | Outliner, mapper, formulizer, arranger, speaker, and refiner stages producing editable PPTX | Reproduction MUST pin its custom `python-pptx` fork and LibreOffice/runtime dependencies. |
| `arcdeck` | [ArcDeck paper](https://arxiv.org/abs/2604.11969), [project](https://arcdeck.org/), [repository](https://github.com/RehgLab/ArcDeck), [MIT license](https://github.com/RehgLab/ArcDeck/blob/cde8e15/LICENSE) | Discourse tree and commitment planning conditioned on audience and duration | Code-available, pilot-ready, experimental: few visible commits, no release/tag, and broad unpinned requirements at the cited revision. Pin commit and environment. Its visual generation acknowledges SlideGen ancestry, so the two are not independent visual backends. |

`paper2slides` is the fallback if ArcDeck cannot complete a controlled pilot or if backend independence becomes a primary experimental requirement. The full target is 12 cells. The first slide pilot MUST compare Gradient Descent control plus RoPE or FeynRL across all three pipelines, with exact pilot membership recorded before spending.

### 4.3 Thread 3: our integrated slides + Manim pipeline

This is the main project pipeline. It MUST reuse results and lessons from Threads 1 and 2 while preserving its own provenance as `in_house`.

The pipeline consists of:

1. Paper ingestion and canonical claim/topic extraction.
2. Formula, code, and dataflow alignment.
3. Bottom-up formula decomposition and primitive lookup.
4. Scene planning and Manim generation/refinement.
5. Slide outline, layout, and editable deck generation.
6. Scene embedding through explicit animation slots.
7. Joint technical, semantic, pedagogical, and presentation evaluation.

Methodology slides SHOULD receive formula and algorithm explainers. Architecture slides SHOULD receive graph/dataflow scenes. Performance slides SHOULD receive chart, comparison, uncertainty, or ablation primitives. Slides MUST have a static poster/fallback so the deck remains understandable when animation playback is unavailable.

The bottom-up formula explainer is a subtrack of Thread 3. It exposes formula-level videos and a topic-level composition, plus the mappings that made them possible.

### 4.4 Thread 4: backtranslation

Backtranslation evaluates reconstruction rather than paper explanation. It compares approximately ten source-available human Manim scenes against:

1. the official source render;
2. a one-shot reconstruction from the reference video; and
3. a self-refined reconstruction initialized from exactly the one-shot code.

The full protocol is in Section 12.

## 5. Evidence model

Every public artifact MUST carry independent provenance, completion, and review axes.

### 5.1 Provenance

| Value | Meaning |
| --- | --- |
| `upstream` | Executed from the upstream method/repository with only documented configuration or compatibility changes |
| `method_reproduction` | Reimplements or adapts the published method because the native input or runnable upstream path does not match the cell |
| `in_house` | Produced by this project's integrated pipeline |
| `synthetic_mock` | Placeholder or deterministic framework-style preview; never benchmark evidence |
| `human_reference` | Human-authored source/reference media used in backtranslation |

### 5.2 Completion

| Value | Meaning |
| --- | --- |
| `full` | Required stages and target deliverables completed |
| `partial` | Useful artifacts exist, but one or more required stages/deliverables are absent |
| `smoke` | Minimal environment or render path was exercised only |
| `failed` | Attempt terminated without the required deliverable |
| `placeholder` | No real method run occurred |

### 5.3 Review

Review state MUST distinguish `unreviewed`, `automatic_pass`, `automatic_fail`, `human_pass`, and `human_fail`. Multiple reviews MAY be stored as events rather than collapsed into one value.

`placeholder` MUST NOT be rendered as success, included in baseline completion rates, or used to populate a missing matrix cell. `full`, `partial`, and `smoke` describe completion only; none implies semantic correctness.

## 6. Typed graph architecture

The internal representation has four typed layers and three synchronized website views.

### 6.1 Internal layers

1. **Topic/Claim Graph**: paper sections, claims, assumptions, evidence, and pedagogical dependencies.
2. **Formula Operation DAG**: formulas decomposed into typed mathematical operations and intermediate values.
3. **Code/Dataflow Graph**: symbols, functions, tensors, data transformations, and execution/data dependencies.
4. **Manim Primitive/Scene Graph**: reusable visual primitives, scene states, animations, clips, and compositions.

Required node identifiers are stable within a manifest version. Graph edges MUST have a type and MAY record source spans, extraction method, confidence, and review state.

Core edge types are:

- `contains`
- `supports`
- `depends_on`
- `implements`
- `consumes`
- `visualized_by`
- `composes`
- `embedded_in`
- `renders_to`

An unresolved edge is valid evidence. The system MUST allow `paper_only`, `code_only`, `candidate`, `confirmed`, and `rejected` mapping states instead of inventing a match. Human review SHOULD be required before a low-confidence formula-to-code edge becomes a public confirmed mapping.

### 6.2 Website views

The four layers are rendered through three synchronized views:

1. **Topic and claim view**: what the paper says and how ideas depend on one another.
2. **Formula and code view**: which operations implement each equation and where they appear in code/dataflow.
3. **Manim primitive and scene view**: which visual components explain each operation, formula, and topic.

Selecting a node in one view SHOULD highlight mapped nodes in the other two. Found reusable functions and newly written functions MUST be distinguishable by both color and a text/icon badge.

## 7. Bottom-up formula explainer

The generation hierarchy is:

`Atom → Operation → Formula → Topic`

- **Atom**: a symbol, scalar, vector, matrix, distribution, index, or data object.
- **Operation**: a typed mathematical transformation such as `exp`, `softmax`, `log`, `normalize`, `dot`, `rotation`, `KL`, `ESS`, `clip`, or `expectation`.
- **Formula**: an operation DAG with semantic roles and intermediate values.
- **Topic**: an ordered composition of formulas, claims, code/dataflow, examples, and comparisons.

Mathematical operations are semantic operations, not Manim API functions. A visual implementation may compose Manim bases such as `MathTex`, `Matrix`, `Axes`, `TransformMatchingTex`, `ValueTracker`, updaters, cameras, graphs, and custom mobjects.

Each formula SHOULD produce an associated video with explicit initial, intermediate, and terminal visual states. A topic-level video SHOULD compose the formula clips with claim-level context and code/dataflow transitions. Clips or scenes are the generation unit; per-frame output is used for rendering and evaluation, not independent LLM generation.

## 8. Primitive registry

The registry is the reusable bridge between semantic operations and Manim scenes. Every primitive MUST record:

- stable `primitive_id` and semantic version;
- origin and source revision;
- source/license constraints;
- supported mathematical operations;
- typed inputs and outputs;
- initial, intermediate, and terminal visual states;
- animation contract and composability constraints;
- test or golden-scene references;
- lifecycle status and known limitations.

Origins use four public badges:

| Origin | Suggested color | Meaning |
| --- | --- | --- |
| `built_in` | green | Direct Manim Community capability |
| `project_reusable` | purple | Reusable primitive authored and tested by this project |
| `generated_one_off` | orange | Cell-specific generated implementation, not yet generalized |
| `missing_planned` | gray dashed | No implementation exists yet |

Color MUST be paired with text or icon labels for accessibility. Promotion from `generated_one_off` to `project_reusable` requires a stable interface, at least one test/golden scene, and use in more than one formula or topic.

## 9. Intermediate representations and fusion

The integrated pipeline uses three linked representations:

- **FormulaIR**: symbols, operation DAG, assumptions, intermediate values, paper spans, and code mappings.
- **SceneIR**: primitive instances, visual states, animation timeline, narration hooks, camera plan, aspect ratio, and render targets.
- **SlideIR**: deck outline, slide intent, claims, layout, citations, static elements, speaker notes, and animation slots.

An `AnimationSlot` MUST reference a versioned SceneIR or rendered artifact and specify:

- semantic purpose and slide region;
- expected duration and playback mode;
- poster frame and static fallback;
- caption/alt text;
- aspect ratio and crop policy;
- artifact hash and provenance;
- whether the animation is optional or required for comprehension.

Slide generation MUST NOT paste an untracked video URL into a deck. The final deck manifest links each slot to an artifact record so the source, revision, cost, and review can be traced.

## 10. Run and artifact manifest contract

This section is a design example, not an implemented schema. A normalized run record MUST be sufficient to reproduce the environment, identify the exact input, account for cost, and render the evidence website without hand-authored claims.

### 10.1 Required run fields

- `schema_version`, `run_id`, timestamps, and status;
- thread and pipeline ID, variant, repository URL, full commit SHA, and license note;
- canonical topic family and artifact IDs/granularity;
- paper version, code source, full code commit SHA, and input hashes;
- model roles, providers, immutable model/version identifiers, and prompt/config hashes;
- dependency lock, container image digest or environment export, renderer/Manim version, hardware, and exact command/config;
- budget limits, measured cost, estimated cost, currency, and accounting coverage;
- per-stage completion, provenance, review events, and failure/stop reason;
- artifact paths/URIs, content hashes, media metadata, and parent/child relationships;
- repair/refinement count and event history;
- evaluation results with metric versions and evidence references.

### 10.2 Example

```json
{
  "schema_version": "0.1-design",
  "run_id": "video.paper2manim.transformer_attention.20260715T120000Z",
  "thread": "real_video_pipelines",
  "pipeline": {
    "id": "paper2manim",
    "variant": "upstream_main",
    "repository": "https://github.com/jwj1342/Paper2Manim",
    "commit_sha": "FULL_SHA_REQUIRED_AT_RUN",
    "license_note": "MIT declared in package metadata; standalone license text not found at cited revision."
  },
  "input": {
    "canonical_topic_family": "transformer_attention",
    "artifact_ids": ["transformers_core", "attention_softmax_lookup"],
    "paper": {"url": "https://arxiv.org/abs/1706.03762", "version": "v7"},
    "code": {"repository": "https://github.com/tensorflow/tensor2tensor", "commit_sha": "FULL_SHA_REQUIRED_AT_RUN"},
    "content_hashes": {"paper_pdf": "sha256:...", "input_bundle": "sha256:..."}
  },
  "reproducibility": {
    "model_versions": ["IMMUTABLE_MODEL_ID_REQUIRED"],
    "prompt_hash": "sha256:...",
    "config_hash": "sha256:...",
    "environment_lock": "artifacts/environment.lock",
    "container_digest": null,
    "manim_version": "PIN_REQUIRED",
    "hardware": "RECORDED_AT_RUN"
  },
  "evidence": {
    "provenance": "upstream",
    "completion": "partial",
    "reviews": ["automatic_pass", "unreviewed"],
    "claim_label": "MEASURED"
  },
  "budget": {"cell_limit_usd": 15.0, "total_pilot_limit_usd": 200.0},
  "cost": {"measured_usd": null, "estimated_usd": 8.5, "coverage": "api_only"},
  "artifacts": [],
  "repair_events": [],
  "evaluations": []
}
```

A `null` measured cost means unknown or not yet measured; it MUST NOT be displayed as `$0`. Estimates and measurements MUST remain separate fields. Cost coverage MUST state whether labor, compute, API calls, storage, and external assets are included.

### 10.3 Pin-at-run invariants

Before a run can be called reproducible, it MUST freeze or record:

1. full upstream and input code SHAs;
2. exact paper version and content hashes;
3. immutable model identifiers for every role;
4. prompt, config, and tool-policy hashes;
5. dependency lock or container digest;
6. Manim/renderer and presentation runtime versions;
7. command, seed where supported, hardware, and relevant environment settings;
8. source/license ledger snapshot.

The website may show a friendly short SHA but the manifest MUST retain the full SHA.

## 11. Cost, stopping, and evaluation contract

### 11.1 Pilot gates

Approved hard gates are:

- maximum **$15 per matrix cell**;
- maximum **$200 total pilot spend** across the approved video and slide pilots.

A harness MUST stop initiating paid stages when either gate would be exceeded. A cell also stops on a configured time limit, unrecoverable dependency/license block, or exhausted repair budget. Partial artifacts and the stop reason MUST be preserved.

Unknown cost is `null`/`N/A`, never `$0`. Free/local execution may be `$0` only when measurement coverage proves that no billable API or external service cost occurred; compute and labor coverage still need disclosure.

The controlled slide matrix SHOULD use the same model family and budget across pipelines where their contracts permit it. Native-best model settings MAY be evaluated only on two predeclared hard topics and MUST be labeled as a separate condition.

### 11.2 Evaluation dimensions

Evaluation MUST be separated into versioned dimensions rather than collapsed into render success:

- **Technical**: process completion, compile/render success, media validity, deck editability, broken assets, timing.
- **Semantic**: claim fidelity, formula correctness, code-mapping correctness, unsupported assertions, citation coverage.
- **Pedagogical**: prerequisite ordering, explanation clarity, example quality, cognitive load, narration/visual alignment.
- **Visual/presentation**: legibility, layout, pacing, continuity, accessibility, slide density, animation usefulness.
- **Efficiency**: measured cost, wall-clock time, repair count, manual intervention, reusable primitive coverage.

Formula-to-code mappings SHOULD be scored separately for precision, coverage, confidence calibration, and human-confirmed correctness. Learner evaluation MAY be added after technical and semantic gates pass.

## 12. Backtranslation protocol

The initial set SHOULD contain approximately ten source-available scenes from the [Manim Community example gallery](https://docs.manim.community/en/stable/examples.html) and [Manim Community repository](https://github.com/ManimCommunity/manim). Both provide MIT-licensed code; each selected scene MUST still record its exact source commit, scene ID, Manim version, and asset dependencies.

The set SHOULD span formula/`MathTex`, graph/area, updater/trace, camera/zoom, boolean geometry, and 3D examples. It is a public development set, not an uncontaminated held-out benchmark; possible model training exposure MUST be disclosed.

For each scene:

- **Human**: render the official source at a fixed commit and environment.
- **One-shot**: provide only the reference MP4; hide source and metadata; permit one generation with no render feedback.
- **Self-refined**: begin from exactly the one-shot code and permit at most three fixed feedback iterations.

Model, prompt family, budget, render environment, and feedback policy MUST be held constant across comparable cells. Evaluation MUST report visual similarity, semantic/structural reconstruction, render validity, code quality, cost, and repair history.

The [Manim documentation](https://docs.manim.community/en/stable/) warns that some 3Blue1Brown-associated characters/assets are copyrighted. Branded or non-permissive assets MUST be excluded. Ordinary YouTube examples MAY be linked for context but MUST NOT be downloaded, rehosted, or treated as source-available ground truth without a verified license.

## 13. Data-driven website information architecture

The public site SHOULD render from a normalized site index derived from run/artifact manifests. Hand-written editorial context is allowed, but baseline state, cost, provenance, and artifact links MUST come from evidence records.

Top-level navigation:

1. **Overview / Evidence Ledger**
2. **Real Video Pipelines**
3. **Paper-to-Slides**
4. **Our Slides + Manim**
5. **Backtranslation**

The last four entries are the four product threads. Bottom-up formula exploration lives inside **Our Slides + Manim**.

Each matrix cell or artifact card MUST show pipeline/variant, canonical family and artifact granularity, provenance, completion, revision, model condition, measured/estimated cost, repair count, review status, license note, and manifest link. Dummy content MUST be labeled `synthetic_mock` + `placeholder`, visually separated, and excluded from baseline aggregates.

The formula explorer SHOULD show the three synchronized graph views from Section 6, allow node selection/highlighting, and associate each formula with its clip plus the overall topic video. The backtranslation page SHOULD use three aligned columns: Human, One-shot, Self-refined.

Media SHOULD use `preload="none"` or metadata-only loading, lazy posters, stable dimensions, captions, and keyboard-accessible controls. Status and primitive origin MUST never rely on color alone.

## 14. Source and license ledger

The following ledger is the minimum approved source set. Every run MUST snapshot its own exact revisions and license evidence.

| Component | Primary source | License evidence / caveat |
| --- | --- | --- |
| Paper2Manim | [Paper](https://arxiv.org/abs/2606.30296), [repo](https://github.com/jwj1342/Paper2Manim) | MIT declared in package metadata; standalone license text not found at cited revision. |
| Code2Video | [Paper](https://arxiv.org/abs/2510.01174), [repo](https://github.com/showlab/Code2Video) | [MIT](https://github.com/showlab/Code2Video/blob/main/LICENSE) |
| TheoremExplainAgent | [Paper](https://arxiv.org/abs/2502.19400), [repo](https://github.com/TIGER-AI-Lab/TheoremExplainAgent) | [MIT](https://github.com/TIGER-AI-Lab/TheoremExplainAgent/blob/main/LICENSE) |
| DeepPresenter / PPTAgent | [DeepPresenter paper](https://arxiv.org/abs/2602.22839), [PPTAgent paper](https://arxiv.org/abs/2501.03936), [repo](https://github.com/icip-cas/PPTAgent) | [MIT](https://github.com/icip-cas/PPTAgent/blob/main/LICENSE); variant must be explicit |
| SlideGen | [Paper](https://arxiv.org/abs/2512.04529), [official repo](https://github.com/Y-Research-SBU/SlideGen) | [MIT](https://github.com/Y-Research-SBU/SlideGen/blob/main/LICENSE) |
| ArcDeck | [Paper](https://arxiv.org/abs/2604.11969), [repo](https://github.com/RehgLab/ArcDeck) | [MIT at cited revision](https://github.com/RehgLab/ArcDeck/blob/cde8e15/LICENSE); experimental and visually descended in part from SlideGen |
| Manim Community | [Docs](https://docs.manim.community/en/stable/), [repo](https://github.com/ManimCommunity/manim) | [MIT](https://github.com/ManimCommunity/manim/blob/main/LICENSE); exclude separately copyrighted assets |

For every external input, the ledger SHOULD record source URL, full revision, retrieval date, declared license, license-file URL/hash, asset-level exceptions, modification/redistribution constraints, and the conclusion used by the project.

## 15. Phased backlog and gates

### Phase A: integrity and harness

- Define and validate normalized run/artifact records from this contract.
- Replace or quarantine dummy coverage claims.
- Add source/license ledger and pin-at-run capture.
- Build budget, stage-status, artifact-hash, and review plumbing.

Gate: no public matrix cell lacks provenance, completion, variant, revision, cost state, and manifest link.

### Phase B: video pilot

- Run Attention across Paper2Manim, Code2Video, and TheoremExplainAgent.
- Preserve native input differences and adaptation labels.
- Compare completion, fidelity, pedagogy, cost, and intervention.

Gate: decide whether to execute the remaining nine video cells and whether any baseline needs replacement.

### Phase C: slide pilot

- Run Gradient Descent control and one hard paper topic (RoPE or FeynRL, predeclared) across DeepPresenter, SlideGen, and ArcDeck.
- Pin DeepPresenter variant, SlideGen fork/runtime, and ArcDeck revision/environment.
- Trigger the Paper2Slides fallback if ArcDeck cannot meet the controlled pilot contract.

Gate: select three stable/diverse slide baselines for the full matrix.

### Phase D: formula graph and primitive registry

- Build typed topic, formula, code/dataflow, and scene graphs for the four families.
- Populate built-in and project-reusable primitives.
- Generate formula-level clips and topic-level compositions.

Gate: confirmed mappings and primitive origin are visible and auditable for at least one end-to-end topic.

### Phase E: integrated slides + Manim

- Implement FormulaIR, SceneIR, SlideIR, and animation slots.
- Produce methodology, architecture, and performance slide patterns.
- Evaluate static fallback and embedded animation together.

Gate: one editable deck remains coherent both with and without animation playback.

### Phase F: backtranslation

- Select and pin approximately ten gallery scenes.
- Run Human, One-shot, and Self-refined conditions.
- Publish costs, repair histories, and limitations.

Gate: protocol invariants are machine-checkable and no prohibited assets are included.

### Phase G: site refactor and full matrices

- Render Overview/Evidence Ledger and the four threads from normalized data.
- Add synchronized graph interactions and three-column backtranslation comparison.
- Execute approved full matrices under new budgets established after pilots.

Gate: public claims can be traced from UI card to manifest, artifact hash, source revision, and evaluation evidence.

## 16. Design acceptance criteria

The implementation conforms to this design when:

1. No dummy or placeholder artifact is presented or aggregated as a baseline result.
2. Each matrix cell uses one canonical topic family and one explicit pipeline variant.
3. Provenance, completion, and review are separate and visible.
4. Every external source and runtime is pinned at run time with license evidence.
5. Cost distinguishes measured, estimated, unknown, and genuinely zero values.
6. Formula-to-code-to-Manim mappings are typed, confidence-aware, and allow unresolved edges.
7. Formula clips compose into topic videos and can be linked into editable slides through versioned animation slots.
8. Backtranslation conditions share a fixed protocol and refinement starts from the exact one-shot code.
9. The website derives evidence state from manifests and exposes the four product threads plus an evidence ledger.
10. All public claims are labeled as measured, externally reported, estimated, planned, or project decisions.
