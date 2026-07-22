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
- OpenAI-compatible HTTP, for WInE `chat/completions` and Bedrock Mantle `responses`.

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

As of the implementation date, Bedrock documents GPT-5.5 as `openai.gpt-5.5` on the Mantle Responses endpoint and Qwen3 32B as `qwen.qwen3-32b-v1:0` on Bedrock Runtime. Google documents `gemini-3.1-pro-preview`; the older Gemini 3 Pro Preview is deprecated. Qwen 8B is not assumed to be a Bedrock Qwen endpoint—its actual provider/model ID must be supplied before it can enter the matrix.

## Paper-native sectioning

The generic contract requires a motivation and related-work entry and ends with findings and limits. The internal mechanism sections follow the source paper rather than a universal slide template.

FeynRL:

`motivation → related_work → ess → p3o → findings → limits → 07 Formula`

RoPE:

`motivation → related_work → formulation → rope → findings → limits → 07 Formula`

Titles, questions, and mechanism labels preserve the papers' terminology. Code is placed next to the equation or mechanism it implements instead of being separated into a generic “Code” scene. `07 Formula` is compiled deterministically after the six generated learning sections; it is not another LLM-authored section.

The formula view is a bipartite capability graph. Formula and operation nodes come from the source packet's formula IR. Manim nodes come from `data/formula_explainer/primitive_registry.json`. Edges preserve three different claims: an implemented callable mapping, a compatible candidate, or an unresolved mapping. This makes missing animation capabilities visible instead of silently improvising a scene.

## Native Manim contract

The reviewed demos use text-light micro-scenes in `scenes/explainer_pipeline_native.py`. Source grounding now produces two coverage contracts before lesson planning:

- `equation_coverage`: every numbered equation family is marked `animate`, `explain`, or `fold`; folded families require a reason.
- `finding_coverage`: every result is represented as experimental question, setting/factor, metric, evidence kind, and source-faithful takeaway.

This prevents the renderer from selecting only convenient equations or isolated result bars. The reviewed scenes include:

- equation transitions for FeynRL Eqs. 2 → 4 → 7/8 → 11/12 and RoFormer Eqs. 3–16;
- mechanism micro-scenes for normalized ESS, the P3O control coupling, and the RoPE relative identity;
- result transitions that hold setting and metric fixed while iteration or sequence length changes;
- a schematic, explicitly non-digitized long-term-decay animation for RoFormer Eqs. 35–37.

- `FeynRLEquationLineageMicro`: Eqs. 2, 4, 7, 11, and 12 as a semantic formula transition;
- `FeynRLEssMicro`: Eq. 11 with fixed token count and changing ratio concentration;
- `FeynRLP3OMicro`: the two Eq. 12 controls coupled through the same e_B;
- `FeynRLResultsMicro`: exact Table 7 iteration-15 → iteration-30 values under precision mismatch;
- `RoPEEquationLineageMicro`: additive Eqs. 3–10 → Eq. 11 requirement → Eqs. 12–16 rotation;
- `RoPERelativeMicro`: the Eq. 16 collapse from separate rotations to n−m;
- `RoPEDecayMicro`: schematic, explicitly non-digitized Eqs. 35–37 bound behavior;
- `RoPEResultsMicro`: signed GLUE deltas and the exact RoFormer-512 → RoFormer-1024 comparison.

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
