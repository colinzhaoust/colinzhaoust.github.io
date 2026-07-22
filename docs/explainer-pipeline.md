# Paper + repository → sourced explainer website

The output is a website organized as paper-native learning scenes, not a slide deck and not a paper summary. FeynRL and RoPE are reviewed demonstrations of the same contracts and renderer.

## Production boundary

The live interface needs:

1. an LLM API credential;
2. a paper PDF;
3. a local checkout of the paper's git repository.

No coding agent participates. The API returns JSON only. It never returns Python, Manim source, HTML, or shell commands. Website code and Manim scene code come from fixed, reviewable renderers in this repository.

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
