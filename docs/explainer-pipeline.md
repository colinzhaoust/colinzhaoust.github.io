# Paper + repository → sourced explainer website

The output is a website organized as paper-native learning scenes, not a slide deck and not a paper summary. FeynRL and RoPE are reviewed demonstrations of the same contracts and renderer.

## Production boundary

The live interface needs:

1. an LLM API credential;
2. a paper PDF;
3. a local checkout of the paper's git repository.

No coding agent participates. The API returns JSON only. It never returns Python, Manim source, HTML, or shell commands. Website code and Manim scene code come from fixed, reviewable renderers in this repository.

The responsibility split is strict:

| Model API | Harness |
| --- | --- |
| Read the frozen source packet and infer paper-native intent. | Freeze the PDF, repository revision, extracted packet, prompts, schemas, and provider configuration. |
| Produce the concept graph, lesson plan, and typed section-content JSON. | Validate every stage, locator, equation-coverage decision, media reference, hyperlink, and claim type; fail closed on mismatch. |
| Choose among allowed content/block and registered scene identifiers. | Compile Formula IR, resolve the Manim registry, render HTML and approved micro-videos, hash artifacts, and publish the static site. |
| Never emit or execute Python, HTML, Manim source, or shell. | Never silently repair a model's scientific claim by changing its meaning. |

The checked-in `reviewed-reference` is a human/Codex-reviewed target condition, not the output of a live candidate model. Its scientific narrative and teaching choices were iterated manually from paper/code evidence and user critique. On 2026-07-22, the same frozen FeynRL/RoPE packets were also run end-to-end through Gemini 3.1 Pro Preview on Vertex AI and GPT-5.5 through Bedrock Mantle. Those live outputs are preserved without manual prose editing. Qwen3 32B passed connectivity and several individual scenes but did not complete the frozen matrix: its FeynRL ESS section exceeded the 2–6 non-media block budget on all three local repair attempts, so no incomplete Qwen bundle appears in the selector.

The live matrix makes the attribution boundary measurable. The model chooses the concept graph, section split, prose/data blocks, source refs, and semantic animation plan. The harness validates and locally retries typed output, materializes registered media glue, resolves mechanical indexes, gives shared appendix/media IDs first-use ownership, removes duplicate animation reuse, renders, and hashes. The overview reports API calls, semantic repairs, harness compilation operations, and corrective normalizations separately; a structurally valid model run should not be confused with the reviewed reference's explanatory judgment.

In the reviewed demo, source packets and model-stage outputs are frozen fixtures. In a production package, `source_grounding` is also a model API stage; the same harness records and validates its result before the three planning stages begin.

```bash
python3 -m tools.explainer_pipeline.cli package \
  --paper /path/to/paper.pdf \
  --repo /path/to/repository \
  --paper-id my-paper \
  --env-file /path/to/bedrock.env
```

`--title` is needed only when the PDF has no title metadata. `--paper-url` is optional. The package command:

1. extracts page-preserving paper text with `pdftotext`;
2. records the PDF hash and page count;
3. records the repository remote and full git revision;
4. builds a bounded corpus from tracked text and code files;
5. asks an API `source_grounding` stage for the paper's own question, section path, located excerpts, and confirmed code notes;
6. runs the concept-graph, lesson-plan, and typed-section JSON stages;
7. validates claims, section order, hyperlinks, paths, code references, and media hashes;
8. renders a static website.

The run stores the extracted corpus, prompt/response hashes, source packet, stage outputs, bundle, and site. A package without an approved native animation recipe remains a searchable HTML explainer; it never falls back to runtime code generation.

## Frozen model-run comparison

The top-right selector switches complete runs, not a model-name label. Each selectable run has independent validated bundles, bundle hashes, source-packet hashes, provider/model IDs, generation mode, and per-stage prompt/response hashes. A candidate does not appear in the selector until every requested paper bundle exists and passes validation.

The reusable matrix runner takes papers and provider definitions from one local JSON specification. Credential paths may appear only in an ignored local copy; the tracked example contains placeholders.

```bash
cp data/explainer_pipeline/model_matrix.example.json runs/model-matrix.local.json
# Fill only the ignored local copy, then run three model rows in parallel.
python3 -m tools.explainer_pipeline.cli model-matrix \
  runs/model-matrix.local.json \
  --run-root runs/explainer_pipeline/model-matrix \
  --output explainer_site \
  --workers 3
```

Models run in parallel, while each model processes papers sequentially. A paper uses one concept-graph call, one lesson-plan call, then one bounded content call per planned section. Each section is validated and repaired locally before merge. This avoids regenerating an entire website because one section has a bad media index or source prefix. Transport failures retry the original prompt; semantic failures receive validator feedback and the invalid typed payload. A failed model row does not cancel or contaminate completed rows.

The first frozen live matrix produced:

| Run | Papers complete | Sections (FeynRL / RoPE) | Blocks | Unique animations | Tokens | API time | Estimated API cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemini 3.1 Pro Preview | 2/2 | 6 / 6 | 32 / 35 | 5 / 6 | 262.2K | 11.2 min | $0.62 |
| GPT-5.5 | 2/2 | 6 / 7 | 38 / 46 | 5 / 5 | 216.4K | 12.0 min | $2.97 |
| Qwen3 32B | 0/2 published | incomplete | incomplete | incomplete | not reconciled | failed boundary | unavailable |

These are recorded endpoint totals for this run, not general benchmark claims. Gemini produced a more compact curriculum; GPT-5.5 used more content blocks and split RoPE into seven sections. Both required deterministic media compilation; Qwen's incomplete row remains visible as a failure note instead of being promoted to the switcher.

The default comparison is a planner comparison:

- fixed: source packets and locators, prompts and JSON contracts, validation rules, formula compiler, Manim registry, website renderer, and published media;
- varied: `concept_graph`, `lesson_plan`, and `section_content` API responses;
- excluded: incomplete calls, invalid JSON, changed source packets, mutable aliases without a recorded resolved model, and hand-copied content presented as another model's output.

Render any number of complete runs with a manifest:

```json
{
  "schema_version": "explainer-comparison/0.1.0",
  "runs": [
    {
      "run_id": "reviewed-reference",
      "label": "Reviewed reference",
      "status": "reviewed",
      "bundles": ["../runs/reference/feynrl/explainer_bundle.json", "../runs/reference/rope/explainer_bundle.json"]
    },
    {
      "run_id": "qwen3-32b-bedrock",
      "label": "Qwen3 32B · Bedrock",
      "status": "generated",
      "bundles": ["../runs/qwen3-32b/feynrl/explainer_bundle.json", "../runs/qwen3-32b/rope/explainer_bundle.json"]
    }
  ]
}
```

```bash
python3 -m tools.explainer_pipeline.cli build-comparison comparison.json --output explainer_site
```

Supported live adapters are:

- Bedrock Runtime `Converse`, for models such as `qwen.qwen3-32b-v1:0`;
- Google Vertex `generateContent`, including `gemini-3.1-pro-preview` with a local service-account file;
- OpenAI-compatible HTTP, for WInE, Bedrock Mantle, and SSH-tunneled Babel vLLM endpoints.

Every live stage records provider/model identity, input/output/reasoning/total tokens when the endpoint returns them, wall-clock API duration, and an estimated USD cost when a region- and tier-matched public rate card is pinned. Credential values, credential file paths, authorization headers, and request bodies are never written to the trace. Replay fixtures intentionally report token and cost as “not recorded,” rather than inventing zero-cost model usage.

Examples (credentials are supplied only through the named environment variable or an untracked env file):

```bash
# Qwen3 32B through Bedrock Runtime
python3 -m tools.explainer_pipeline.cli run feynrl \
  --mode bedrock \
  --model-id qwen.qwen3-32b-v1:0 \
  --env-file /path/to/bedrock.env \
  --run-root runs/qwen3-32b/feynrl

# GPT-5.5 through Bedrock Mantle's OpenAI Responses path
python3 -m tools.explainer_pipeline.cli run feynrl \
  --mode openai-compatible \
  --provider-name amazon_bedrock_mantle \
  --base-url https://bedrock-mantle.us-east-2.api.aws/openai/v1 \
  --api-path responses \
  --api-key-env OPENAI_API_KEY \
  --model-id openai.gpt-5.5 \
  --env-file /path/to/bedrock-mantle.env \
  --run-root runs/gpt-5-5/feynrl

# Gemini 3.1 Pro Preview through Vertex AI
python3 -m tools.explainer_pipeline.cli run feynrl \
  --mode vertex \
  --model-id gemini-3.1-pro-preview \
  --credential-file /path/to/untracked-service-account.json \
  --project-id '<project id>' \
  --location global \
  --run-root runs/gemini-3-1-pro/feynrl

# WInE gateway; use the exact gateway model ID resolved for the experiment
python3 -m tools.explainer_pipeline.cli run feynrl \
  --mode openai-compatible \
  --provider-name wine \
  --base-url https://ai-gateway.andrew.cmu.edu/v1 \
  --api-path chat/completions \
  --api-key-env WINE_API_KEY \
  --model-id '<immutable WInE model ID>' \
  --env-file /path/to/wine.env \
  --run-root runs/wine-gemini/feynrl
```

The comparison matrix is intentionally limited to GPT-5.5, Gemini 3.1 Pro, Qwen3 32B, and Qwen3 8B. The 8B condition is the revision-pinned `Qwen/Qwen3-8B` checkpoint served in BF16 through vLLM on one Babel L40S. Its launcher and SSH-tunnel instructions are in `docs/ops/babel-qwen3-8b-vllm.sbatch`.

## Paper-native sectioning

The source packet carries a section policy rather than a universal slide template. In `model_proposed` mode, the model chooses 5–8 stable sections while satisfying a prerequisite sequence: motivation first, required lineage/mechanism/evidence roles covered, and limitations last. Each planned section must state its intent, learner question, learning goal, likely misconception, summary, source refs, medium, and appendix IDs before content generation begins.

The reviewed targets use:

- FeynRL: `motivation → related_work → ess → p3o → findings → limits`;
- RoPE: `motivation → related_work → formulation → rope → findings → limits`.

Live models are allowed to split differently. In the frozen run, Gemini used six RoPE sections and separated algebraic properties from the rotary mechanism; GPT-5.5 used seven and separated formulation, RoPE, and properties. The renderer reads the validated lesson plan dynamically, so model-proposed IDs become navigation without changing HTML/CSS.

Titles, questions, and mechanism labels preserve the papers' terminology. Short code excerpts can still appear beside a mechanism. Formula and Code views are compiled deterministically after the generated learning sections; neither is another LLM-authored section.

The formula view is a bipartite capability graph. Formula and operation nodes come from the source packet's formula IR. Manim nodes come from `data/formula_explainer/primitive_registry.json`. Edges preserve three different claims: an implemented callable mapping, a compatible candidate, or an unresolved mapping. This makes missing animation capabilities visible instead of silently improvising a scene.

The code-understanding view is a second evidence graph:

- formula ↔ revision-pinned symbols and line ranges in the authors' original repository;
- a concrete example lifecycle showing each artifact handoff, branch, and training loop through that repository;
- an experiment pipeline showing which factor changes, what is trained, and which metric is read.

These graphs are compiled from `code_understanding` in the source packet. A model may propose candidate links during grounding, but published confirmed edges must resolve to known formula IDs, repository IDs, lifecycle nodes, and revision-pinned upstream paths. An optional local checkout is used for validation and is never presented as the source of truth.

## Native Manim contract

The reviewed demos use text-light micro-scenes in `scenes/explainer_pipeline_native.py`. Source grounding now produces two coverage contracts before lesson planning:

- `equation_coverage`: every numbered equation family is marked `animate`, `explain`, or `fold`; folded families require a reason.
- `finding_coverage`: every result is represented as experimental question, setting/factor, metric, evidence kind, and source-faithful takeaway.

This prevents the renderer from selecting only convenient equations or isolated result bars. The reviewed scenes include:

- paper-owned equation transitions for PPO → original P3O → FeynRL and Transformer → Shaw → Transformer-XL → T5/TUPE/DeBERTa → RoFormer;
- mechanism micro-scenes for normalized ESS, the P3O control coupling, and the RoPE relative identity;
- result transitions that hold setting and metric fixed while iteration or sequence length changes;
- a schematic, explicitly non-digitized long-term-decay animation for RoFormer Eqs. 35–37.

- `FeynRLEquationLineageMicro`: PPO fixed clipping → original P3O ESS coupling → FeynRL token-level ratios and normalized e_B;
- `FeynRLOffPolicyBridgeMicro`: Eqs. 2 and 5–8, changing the sampling distribution while making the ratio and behavioral KL explicit;
- `FeynRLEssMicro`: Eq. 11 with fixed token count and changing ratio concentration;
- `FeynRLP3OMicro`: the two Eq. 12 controls coupled through the same e_B;
- `FeynRLResultsMicro`: exact Table 7 iteration-15 → iteration-30 values under precision mismatch;
- `FeynRLClipResultMicro`: exact Table 7 clipping-factor average versus P3O under one held-out metric;
- `RoPEEquationLineageMicro`: paper-by-paper positional history, with each equation held long enough to expose its role and remaining limitation;
- `RoPERelativeMicro`: the Eq. 16 collapse from separate rotations to n−m;
- `RoPEFrequencyPairsMicro`: Eqs. 20–34 as parallel 2D frequency-pair rotations inside the block-diagonal map;
- `RoPEDecayMicro`: schematic, explicitly non-digitized Eqs. 35–37 bound behavior;
- `RoPEResultsMicro`: signed GLUE deltas and the exact RoFormer-512 → RoFormer-1024 comparison;
- `RoPETranslationResultMicro`: the exact WMT14 En–De BLEU comparison on one shared number line.

The stock layer is Manim Community: `MathTex`, `TransformMatchingTex`, `Text`, `VGroup`, `Rectangle`, `Arrow`, `Axes`, and standard animations. The project layer lives in `scenes/explainer_primitives.py`: `RatioBars`, `EssTradeoffGauge`, `FormulaCodeBridge`, `MetricBars`, `RoPERelativeRotation`, and the shared paper-native scene shell. The website carries motivation, interpretation, and consequences; each micro-video is limited to one state change. The scenes do not reuse the earlier `progress_site/assets/self-refine` media. Captions, posters, video hashes, engine version, entrypoint, and scene IDs are part of each source packet.

Render the reviewed scenes directly:

```bash
.venv-arm64/bin/manim -qm \
  --media_dir runs/explainer_pipeline/native_manim \
  scenes/explainer_pipeline_native.py \
  FeynRLEquationLineageMicro FeynRLEssMicro FeynRLP3OMicro FeynRLResultsMicro \
  RoPEEquationLineageMicro RoPERelativeMicro RoPEDecayMicro RoPEResultsMicro
```

For a new paper, the API can select only registered scene/media IDs. Adding a new reusable visual grammar is an ordinary repository change with review and tests; it is not delegated to a coding agent during generation.

## Scientific claim policy

- Use exact paper terms and equation/table locators.
- Use exact values only when tied to a table or explicit text.
- Label qualitative curve readings as the authors' reported findings.
- Keep a derived teaching fixture visibly distinct from a reported experiment.
- Treat related-work links as primary-source reading, not decorative citations.
- Keep algebraic identities separate from empirical and extrapolation claims.

## Reviewed demo

```bash
python3 -m tools.explainer_pipeline.cli demo
python3 -m unittest discover -s tests/explainer_pipeline -p 'test_*.py'
python3 -m http.server 4173 --directory explainer_site
```

Open `http://127.0.0.1:4173/`.

The static build in `explainer_site/` can be copied to the `4blue2brown-demo/` directory of the GitHub Pages repository and served at `https://colinzhaoust.github.io/4blue2brown-demo/`.
