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
5. Make lineage, completion, cost, license, and review status visible at every public result.
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
| `[MEASURED]` | Produced by this project from a preserved run under a versioned measurement contract | Render time, artifact hash, local rubric score |
| `[OBSERVED]` | Directly inspected state with a retrieval time and evidence reference, but not a benchmark measurement | Repository contents or packaging state seen during research |
| `[REPORTED]` | Reported by an upstream paper or repository but not reproduced here | A benchmark score from a paper |
| `[ESTIMATE]` | A forecast based on stated assumptions | Expected API cost before a run |
| `[PLANNED]` | Approved work that has not yet produced evidence | A future matrix cell |
| `[DECISION]` | A project choice, not an empirical claim | Selected baseline shortlist |

These labels are orthogonal to lineage and completion status. For example, a full upstream reproduction can still contain `[REPORTED]` metrics alongside `[MEASURED]` local costs.

## 3. Benchmark identity contract

A benchmark cell is counted by `canonical_topic_family × pipeline_variant × experiment_condition × replicate`, never by the number of generated artifacts. A canonical family MAY contain multiple topic-, section-, formula-, scene-, or slide-level artifacts.

The versioned experiment configuration MUST define:

- canonical topic-family IDs and control IDs;
- paper and code input records with immutable versions and hashes;
- pipeline and variant IDs;
- experiment conditions and replicate policy;
- expected artifact granularity;
- the pipeline-specific completion contract;
- budget-policy and evaluation-policy IDs.

A control is not a paper family. Adding a formula-level child artifact does not create another benchmark cell. Current paper families, control topics, baseline shortlists, pilot membership, and source revisions are mutable research choices and therefore live in the dated discussion record or a versioned experiment configuration, not in this stable contract.

## 4. Four product threads

### 4.1 Thread 1: real video pipelines

This thread compares external or reproduced paper/topic/formula-to-video pipelines. Each run MUST preserve the pipeline's declared native input contract and record whether the benchmark input is `native` or `adapted`. Adapted input MUST NOT be described as a native upstream paper-grounded run.

### 4.2 Thread 2: paper-to-slides baselines

This thread compares external or reproduced paper-to-slide pipelines. Each run MUST use an explicit pipeline variant: a repository that contains legacy and current implementations is not itself a sufficient variant ID. Editable deck, static export, citations, and speaker notes count as separate deliverables under a versioned completion contract.

### 4.3 Thread 3: our integrated slides + Manim pipeline

This is the main project pipeline. It MUST reuse results and lessons from Threads 1 and 2 while recording its implementation origin as `project_native`.

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

Backtranslation evaluates reconstruction rather than paper explanation. It compares a versioned set of source-available human Manim scenes against:

1. the official source render;
2. a one-shot reconstruction from the reference video; and
3. a self-refined reconstruction initialized from exactly the one-shot code.

The full protocol is in Section 12.

## 5. Lineage, completion, and review model

A single provenance enum cannot represent how software, inputs, repairs, and outputs relate. Every run and every artifact MUST carry orthogonal lineage fields.

### 5.1 Lineage

| Field | Required values or semantics |
| --- | --- |
| `implementation_origin` | `upstream_repository`, `project_reimplementation`, `project_native`, `synthetic_fixture`, or `human_authored_reference` |
| `input_contract_mode` | `native` or `adapted`; adapted records MUST reference the adapter/config and explain the semantic change |
| `patch_level` | `none`, `config_only`, `compatibility`, or `method_change` |
| `patchset_hash` | Content hash of the empty or applied patchset; required even when `patch_level=none` |
| `derivation_stage` | A typed stage such as `source`, `generated`, `rendered`, `composed`, `one_shot`, or `self_refined` |
| `parent_artifact_refs` | Ordered artifact IDs with relation types such as `derived_from`, `rendered_from`, `composed_from`, or `refined_from` |

Run lineage describes execution context. Artifact lineage MUST repeat the fields that apply to that artifact and MUST NOT be inferred only from the parent run. A repaired or composed child therefore retains its upstream ancestry while explicitly recording its project repair/derivation stage and parent artifacts.

### 5.2 Completion

| Value | Meaning |
| --- | --- |
| `full` | Required stages and target deliverables completed |
| `partial` | Useful artifacts exist, but one or more required stages/deliverables are absent |
| `smoke` | Minimal environment or render path was exercised only |
| `failed` | Attempt terminated without the required deliverable |
| `placeholder` | No real method run occurred |

Every pipeline variant MUST reference a versioned `completion_contract_id`. That contract lists required stages, terminal stage states, required deliverable roles, and the rule that maps stage/artifact state to the five completion values. Completion MUST be machine-derived from stage records and artifact validation; authors MUST NOT hand-set `full` or `partial` independently of the contract. A contract change requires a new version and MUST NOT retroactively change preserved run results.

### 5.3 Claim evidence and review

Every public factual claim MUST have a claim-evidence record with a stable claim ID, one label from Section 2, exact evidence refs, and an observation/measurement timestamp. Source-reported claims MUST identify the source snapshot or state explicitly that the link is mutable and non-snapshot.

Reviews MUST be structured append-only events containing event ID, subject ref, rubric ID/version, evaluator type and identifier, result, evidence refs, timestamp, and optional notes. A summary review state MAY be machine-derived; a contradictory array such as simultaneous `automatic_pass` and `unreviewed` is invalid.

`placeholder` MUST NOT be rendered as success, included in baseline completion rates, or used to populate a missing matrix cell. `full`, `partial`, and `smoke` describe completion only; none implies semantic correctness.

## 6. Typed graph architecture

The internal representation has four typed layers and three synchronized website views.

### 6.1 Internal layers

1. **Topic/Claim Graph**: paper sections, claims, assumptions, evidence, and pedagogical dependencies.
2. **Formula Operation DAG**: formulas decomposed into typed mathematical operations and intermediate values.
3. **Code/Dataflow Graph**: symbols, functions, tensors, data transformations, and execution/data dependencies.
4. **Manim Primitive/Scene Graph**: reusable visual primitives, scene states, animations, clips, and compositions.

Node identity, node coverage, and edge matching are separate concepts.

- Node IDs MUST be content-addressable or registry-stable across manifest versions. A renamed or merged node MUST retain an `aliases` list and a migration record containing old ID, new ID, reason, version, and timestamp.
- `coverage_state` belongs to nodes and uses `observed`, `inferred`, `planned_missing`, or `not_applicable`. A node observed only in paper or only in code remains a node coverage fact, not an edge state.
- `match_state` belongs to mapping edges and uses `candidate`, `confirmed`, `rejected`, or `unresolved`.

Allowed typed edges are:

| Edge | Allowed source → target |
| --- | --- |
| `contains` | topic → claim/formula; formula → operation; scene → primitive |
| `supports` | evidence/claim/formula → claim |
| `depends_on` | claim/formula/operation/code/scene → same compatible node class |
| `implements` | code/dataflow → formula/operation |
| `consumes` | code/operation/primitive/scene → data/value/artifact |
| `visualized_by` | claim/formula/operation/code/dataflow → primitive/scene |
| `composes` | formula/scene/slide/topic → child artifact of the compatible class |
| `embedded_in` | scene/rendered artifact → animation slot/slide |
| `renders_to` | SceneIR/SlideIR/source → rendered artifact |

Every non-structural edge MUST reference evidence records. Extractor confidence is a calibrated numeric score in `[0,1]`, not a truth value. `confirmed` requires a structured human or policy-authorized automatic review event whose rubric permits confirmation; `rejected` requires a review event; `candidate` and `unresolved` remain visible and MUST NOT be rendered as confirmed. Validators MUST reject disallowed source/target combinations and dangling aliases, migrations, evidence refs, or review refs.

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

An `AnimationSlot` MUST specify:

- a versioned `scene_ir_ref`;
- a validated `rendered_artifact_ref`;
- a validated `static_fallback_artifact_ref` that remains understandable without playback;
- semantic purpose and slide region;
- expected duration and playback mode;
- poster-frame reference;
- caption/alt text;
- aspect ratio and crop policy;
- artifact hash and composite lineage;
- whether the animation is optional or required for comprehension.

All three references are required before a slot can be published. Slide generation MUST NOT paste an untracked video URL into a deck. The final deck manifest links each slot to artifact records so the source, revision, cost, and review can be traced.

## 10. Run and artifact manifest contract

This section defines the logical contract; implementing its schema and validators is separate work. A canonical manifest MUST be sufficient to reproduce the environment, identify the exact input, derive completion, account for cost, trace each claim, and generate a safe public projection.

### 10.1 Required run fields

- schema/version, run/cell IDs, start/end timestamps, status, and experiment configuration ID;
- pipeline ID/variant, repository and full SHA, composite lineage, completion contract, and stage records;
- input paper/code snapshots, content hashes, canonical family, artifact granularity, and adapter record when applicable;
- license snapshot with retrieval timestamp, source revision, license-content hash, and redistribution conclusion;
- immutable model identifiers, prompt/tool-policy hashes, dependency/container state, hardware, exact command, and hashed config references;
- budget policy, atomic reservations, rate-card snapshot, measured/estimated costs, currency, and accounting coverage;
- artifacts with role, repo-relative or private path, content hash, validation, completion, and artifact-level lineage;
- per-claim evidence records and structured review events;
- repair/refinement events with parent artifacts and policy IDs.

### 10.2 Example

```json
{
  "schema_version": "paper-media-manifest/0.2-design",
  "visibility": "private_canonical",
  "run_id": "run.video.example.example_topic_family.20260715T120000Z",
  "cell_id": "pilot-video-v1:example_topic_family:example_upstream:controlled:r1",
  "experiment_config_id": "pilot-video-v1",
  "thread": "real_video_pipelines",
  "started_at": "2026-07-15T12:00:00Z",
  "ended_at": "2026-07-15T12:08:30Z",
  "status": "completed",
  "pipeline": {
    "id": "example_upstream",
    "variant": "upstream_main",
    "repository": "https://example.org/upstream/pipeline",
    "commit_sha": "0123456789abcdef0123456789abcdef01234567",
    "completion_contract": {
      "id": "video-upstream/v1",
      "required_stages": ["plan", "generate", "render", "evaluate"],
      "required_deliverable_roles": ["source_code", "rendered_video"]
    }
  },
  "lineage": {
    "implementation_origin": "upstream_repository",
    "input_contract_mode": "native",
    "adapter_ref": null,
    "patch_level": "compatibility",
    "patchset_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "derivation_stage": "generated",
    "parent_artifact_refs": []
  },
  "input": {
    "canonical_topic_family": "example_topic_family",
    "granularity": "topic",
    "paper_snapshot": {
      "source_url": "https://arxiv.org/abs/1706.03762",
      "version": "v7",
      "retrieved_at": "2026-07-15T11:00:00Z",
      "content_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
    },
    "code_snapshot": {
      "repository": "https://example.org/input/code",
      "commit_sha": "89abcdef0123456789abcdef0123456789abcdef",
      "content_hash": "sha256:3333333333333333333333333333333333333333333333333333333333333333"
    }
  },
  "license_snapshot": {
    "source_revision": "0123456789abcdef0123456789abcdef01234567",
    "retrieved_at": "2026-07-15T11:05:00Z",
    "declared_spdx": "MIT",
    "license_text_ref": "private/evidence/licenses/example-upstream-LICENSE",
    "license_text_hash": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
    "redistribution_conclusion": "allowed_with_notice"
  },
  "execution": {
    "command": ["uv", "run", "pipeline", "--config", "configs/pilot-video-v1.yaml"],
    "config_ref": "configs/pilot-video-v1.yaml",
    "config_hash": "sha256:5555555555555555555555555555555555555555555555555555555555555555",
    "prompt_bundle_hash": "sha256:6666666666666666666666666666666666666666666666666666666666666666",
    "tool_policy_hash": "sha256:7777777777777777777777777777777777777777777777777777777777777777",
    "model_versions": ["provider/model@immutable-version"],
    "environment_lock_ref": "env/uv.lock",
    "environment_lock_hash": "sha256:8888888888888888888888888888888888888888888888888888888888888888",
    "container_digest": "sha256:9999999999999999999999999999999999999999999999999999999999999999",
    "renderer_versions": {"manim": "0.19.0", "ffmpeg": "7.1"},
    "hardware": {"platform": "linux-x86_64", "accelerator": "none"}
  },
  "budget": {
    "policy_id": "pilot-budget-2026-07-15/v1",
    "rate_card_snapshot_id": "provider-rates-2026-07-15T110000Z",
    "reservation_ids": ["reservation:pilot-video-v1:0001"],
    "measured_usd": 6.42,
    "estimated_usd": 8.5,
    "coverage": ["api", "local_compute"]
  },
  "stages": [
    {"id": "plan", "status": "succeeded", "started_at": "2026-07-15T12:00:00Z", "ended_at": "2026-07-15T12:01:00Z", "evidence_refs": ["configs/pilot-video-v1.yaml"]},
    {"id": "generate", "status": "succeeded", "started_at": "2026-07-15T12:01:00Z", "ended_at": "2026-07-15T12:05:00Z", "evidence_refs": ["artifact:source"]},
    {"id": "render", "status": "succeeded", "started_at": "2026-07-15T12:05:00Z", "ended_at": "2026-07-15T12:08:00Z", "evidence_refs": ["artifact:video"]},
    {"id": "evaluate", "status": "succeeded", "started_at": "2026-07-15T12:08:00Z", "ended_at": "2026-07-15T12:08:30Z", "evidence_refs": ["review:technical"]}
  ],
  "completion": {"contract_id": "video-upstream/v1", "derived_value": "full", "derived_at": "2026-07-15T12:08:31Z"},
  "artifacts": [
    {
      "artifact_id": "artifact:source",
      "role": "source_code",
      "public_path": "progress_site/assets/runs/example/source.py",
      "content_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "media_type": "text/x-python",
      "completion": "full",
      "validation_refs": ["validator:python-compile@1:pass"],
      "lineage": {
        "implementation_origin": "upstream_repository",
        "input_contract_mode": "native",
        "patch_level": "compatibility",
        "patchset_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "derivation_stage": "generated",
        "parent_artifact_refs": []
      }
    },
    {
      "artifact_id": "artifact:video",
      "role": "rendered_video",
      "public_path": "progress_site/assets/runs/example/video.mp4",
      "content_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "media_type": "video/mp4",
      "completion": "full",
      "validation_refs": ["validator:media-probe@2:pass"],
      "lineage": {
        "implementation_origin": "upstream_repository",
        "input_contract_mode": "native",
        "patch_level": "compatibility",
        "patchset_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "derivation_stage": "rendered",
        "parent_artifact_refs": [{"artifact_id": "artifact:source", "relation": "rendered_from"}]
      }
    }
  ],
  "validations": [
    {
      "validation_id": "validator:python-compile@1:pass",
      "validator_id": "python-compile@1.0.0",
      "subject_ref": "artifact:source",
      "result": "pass",
      "evidence_ref": "progress_site/assets/runs/example/evidence/python-compile.json",
      "validated_at": "2026-07-15T12:05:05Z"
    },
    {
      "validation_id": "validator:media-probe@2:pass",
      "validator_id": "media-probe@2.1.0",
      "subject_ref": "artifact:video",
      "result": "pass",
      "evidence_ref": "progress_site/assets/runs/example/evidence/media-probe.json",
      "validated_at": "2026-07-15T12:08:20Z"
    }
  ],
  "claims": [
    {
      "claim_id": "claim:render-valid",
      "label": "MEASURED",
      "statement": "The required video artifact passed the versioned media validator.",
      "evidence_refs": ["artifact:video", "validator:media-probe@2:pass"],
      "observed_at": "2026-07-15T12:08:20Z"
    }
  ],
  "reviews": [
    {
      "review_id": "review:technical",
      "subject_ref": "artifact:video",
      "rubric_id": "video-technical/v2",
      "evaluator": {"type": "automatic", "id": "media-probe@2.1.0"},
      "result": "pass",
      "evidence_refs": ["artifact:video", "validator:media-probe@2:pass"],
      "reviewed_at": "2026-07-15T12:08:25Z",
      "notes": null
    }
  ],
  "repair_events": []
}
```

A `null` measured cost means unknown or not yet measured; it MUST NOT be displayed as `$0`. Estimates and measurements MUST remain separate fields. Cost coverage MUST state whether labor, compute, API calls, storage, and external assets are included.

### 10.3 Private canonical manifest and public projection

The private canonical manifest is the source of truth. The public manifest MUST be generated from it with an explicit field allowlist; it MUST NOT be maintained as an independent hand-edited copy.

Credential values MUST never be stored even in the private manifest. Before publication, the generator MUST remove or transform secrets and secret references, absolute/local paths, usernames, email addresses and other PII, private-repository URLs/revisions, provider request IDs, unpublished prompts/data, internal hostnames, and artifacts not explicitly marked publishable. Public filesystem references MUST be repository-relative paths; external references MUST use approved `https` URLs.

The publication validator is fail-closed. It MUST reject unknown fields, non-allowlisted paths or artifacts, absolute paths, parent traversal, `file:` URLs, secret/token patterns, private-source markers, PII patterns, dangling references, missing hashes, and license conclusions that do not allow the requested publication. Any validation error produces no public projection. The generated projection MUST record canonical-manifest hash, projection-policy ID/version, validator version, generation timestamp, and redaction summary without disclosing redacted values.

### 10.4 Pin-at-run invariants

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

### 11.1 Enforceable cost gates

Monetary limits are mutable experiment policy and MUST live in a versioned budget configuration referenced by every run. The dated discussion records the currently approved pilot values.

A `cell_id` MUST be deterministically derived from experiment-config ID, canonical topic/control ID, pipeline variant, condition, and replicate. Retries remain in the same cell unless the experiment config declares a new condition. Shared setup cost MUST use a predeclared allocation rule (`dedicated_setup_cell`, `equal_allocation`, or a documented weighted allocation); it may not disappear from totals.

Before every paid stage, the harness MUST atomically reserve the projected next-stage cost against both cell and experiment ledgers. The projection MUST use a rate-card snapshot with provider, currency, effective/retrieval timestamp, and content hash. A stage may start only if `measured_spend + active_reservations + projected_next_stage_cost` remains within both limits. Completion reconciles reservation against measured cost; crash recovery expires or reconciles stale reservations without double spending.

Unknown price, usage, currency conversion, or projected paid-stage cost fails closed: the paid stage does not start. A cell also stops on configured time, dependency/license, or repair limits. Stage state, partial artifacts, unused reservation, and stop reason MUST be preserved.

Unknown cost is `null`/`N/A`, never `$0`. Free/local execution may be `$0` only when measurement coverage proves that no billable API or external service cost occurred; compute and labor coverage still need disclosure.

Controlled and native-best model policies, if used, MUST be separate experiment conditions with independent cell IDs.

### 11.2 Evaluation dimensions

Evaluation MUST be separated into versioned dimensions rather than collapsed into render success:

- **Technical**: process completion, compile/render success, media validity, deck editability, broken assets, timing.
- **Semantic**: claim fidelity, formula correctness, code-mapping correctness, unsupported assertions, citation coverage.
- **Pedagogical**: prerequisite ordering, explanation clarity, example quality, cognitive load, narration/visual alignment.
- **Visual/presentation**: legibility, layout, pacing, continuity, accessibility, slide density, animation usefulness.
- **Efficiency**: measured cost, wall-clock time, repair count, manual intervention, reusable primitive coverage.

Formula-to-code mappings SHOULD be scored separately for precision, coverage, confidence calibration, and human-confirmed correctness. Learner evaluation MAY be added after technical and semantic gates pass.

## 12. Backtranslation protocol

The experiment configuration MUST identify a source-available scene set and snapshot each scene's source revision, scene ID, renderer version, assets, license evidence, and contamination limitations. The set size, source shortlist, and category mix are mutable and belong in that configuration or the dated record.

For each scene:

- **Human**: render the official source at a fixed commit and environment.
- **One-shot**: provide only the reference MP4; hide source and metadata; permit one generation with no render feedback.
- **Self-refined**: begin from exactly the one-shot code and follow a versioned refinement policy.

The run MUST record `feedback_policy_id`, allowed feedback inputs/evaluators, maximum iterations, per-iteration budget, and an exact early-stop rule. Early stopping is allowed only when the versioned policy's validator/rubric predicates pass; all iterations and evidence are retained. No unlogged manual edit is permitted, and the first self-refined artifact MUST reference the exact one-shot code artifact as `refined_from`.

Model, prompt family, budget, render environment, and feedback policy MUST be held constant across comparable cells. Evaluation MUST report visual similarity, semantic/structural reconstruction, render validity, code quality, cost, and repair history.

Branded or non-permissive assets MUST be excluded under the source/license ledger. Ordinary hosted videos MAY be linked for context but MUST NOT be downloaded, rehosted, or treated as source-available ground truth without a verified compatible license snapshot.

## 13. Data-driven website information architecture

The public site SHOULD render from a normalized site index derived only from validated public projections. Hand-written editorial context is allowed, but baseline state, cost, lineage, and artifact links MUST come from projected evidence records.

Top-level navigation:

1. **Overview / Evidence Ledger**
2. **Real Video Pipelines**
3. **Paper-to-Slides**
4. **Our Slides + Manim**
5. **Backtranslation**

The last four entries are the four product threads. Bottom-up formula exploration lives inside **Our Slides + Manim**.

Each matrix cell or artifact card MUST show pipeline/variant, canonical family and artifact granularity, composite lineage, completion contract/result, revision, model condition, measured/estimated cost, repair count, review status, license conclusion, and public-manifest link. Synthetic fixtures MUST show `implementation_origin=synthetic_fixture` and completion `placeholder`, remain visually separated, and be excluded from baseline aggregates.

The formula explorer SHOULD show the three synchronized graph views from Section 6, allow node selection/highlighting, and associate each formula with its clip plus the overall topic video. The backtranslation page SHOULD use three aligned columns: Human, One-shot, Self-refined.

Media SHOULD use `preload="none"` or metadata-only loading, lazy posters, stable dimensions, captions, and keyboard-accessible controls. Status and primitive origin MUST never rely on color alone.

## 14. Source and license ledger contract

Mutable source shortlists and maturity assessments live in dated records. For every external paper, repository, model, dataset, example, and asset actually used, the canonical manifest MUST snapshot source URL, full revision/version, retrieval timestamp, content hash, declared license, license-text reference and hash, asset-level exceptions, modification/redistribution constraints, reviewer/conclusion, and evidence refs.

A branch link, repository home page, or `main` license URL is a mutable non-snapshot claim. It MAY aid navigation but MUST NOT satisfy pin-at-run or publication requirements. If a full revision or license-content hash is unavailable, the claim MUST be labeled `OBSERVED` or `REPORTED`, marked `non_snapshot`, and excluded from reproducibility/license gates.

## 15. Acceptance evidence contract

Phase plans are mutable and belong in the dated record. Any phase exit or release gate MUST instead provide machine-readable acceptance evidence:

| Gate area | Required evidence |
| --- | --- |
| Manifest integrity | Canonical-manifest schema validator ID/version and pass artifact; completion-contract validator pass |
| Publication safety | Projection-policy ID/version, fail-closed publication-validator pass, canonical/public hashes, redaction summary |
| Media technical | Artifact hash plus versioned compile/render/media-probe validator pass |
| Semantic/pedagogical | Rubric ID/version, structured evaluator event, evidence refs, and threshold result from experiment config |
| Graph mapping | Graph-schema validator pass, zero dangling refs, typed-edge validation, and required confirmation-review events |
| Slides + animation | PPTX structure validator, required AnimationSlot refs, rendered-artifact validator, static-fallback validator |
| Cost | Budget policy/rate-card snapshot, reservation-ledger reconciliation, and cell/experiment gate pass |
| Backtranslation | Protocol-policy validator, exact one-shot parent hash, refinement-event chain, and feedback-policy compliance |

An exit statement such as “looks coherent,” “pilot-ready,” or “auditable” is commentary, not gate evidence. The versioned experiment configuration MUST name the required validator/rubric IDs, artifact roles, thresholds, and aggregation rule before execution.

## 16. Design acceptance criteria

The implementation conforms to this design when:

1. No dummy or placeholder artifact is presented or aggregated as a baseline result.
2. Each matrix cell uses one canonical topic family and one explicit pipeline variant.
3. Composite lineage, machine-derived completion, claim evidence, and review are separate and visible at run and artifact level.
4. Every external source and runtime is pinned at run time with license evidence.
5. Cost distinguishes measured, estimated, unknown, and genuinely zero values.
6. Formula-to-code-to-Manim mappings separate node coverage from edge match state, validate edge types, and preserve aliases/migrations.
7. Formula clips compose into topic videos and enter slides only through AnimationSlots with SceneIR, rendered, and static-fallback refs.
8. Backtranslation conditions share versioned protocol/refinement policies and refinement starts from the exact one-shot code.
9. The website derives evidence state only from a validated allowlisted public projection and exposes the four product threads plus an evidence ledger.
10. All public claims are labeled as measured, observed, externally reported, estimated, planned, or project decisions and reference evidence.
