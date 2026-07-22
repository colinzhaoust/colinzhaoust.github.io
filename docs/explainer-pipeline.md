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

`motivation → related_work → ess → p3o → findings → limits`

RoPE:

`motivation → related_work → formulation → rope → findings → limits`

Titles, questions, and mechanism labels preserve the papers' terminology. Code is placed next to the equation or mechanism it implements instead of being separated into a generic “Code” scene.

## Native Manim contract

The reviewed demos use newly authored scenes in `scenes/explainer_pipeline_native.py`:

- `FeynRLEssP3O`: trust-region concern, off-policy concern, Eq. 11, Eq. 12, and confirmed P3O code;
- `FeynRLFindings`: Section 4 experimental axes and exact Table 7 values;
- `RoPEFormulationAndCode`: Eq. 11, Eqs. 14–16, and efficient implementation;
- `RoPEFindings`: Section 3.3 properties, Table 1, and Figure 3 findings.

These scenes use a shared paper palette and reusable Manim helpers for headings, terms, formulas, ratio bars, value bars, and formula-to-code panels. They do not reuse the earlier `progress_site/assets/self-refine` media. Captions, posters, video hashes, engine version, entrypoint, and scene IDs are part of each source packet.

Render the reviewed scenes directly:

```bash
.venv-arm64/bin/manim -qm \
  --media_dir runs/explainer_pipeline/native_manim \
  scenes/explainer_pipeline_native.py \
  FeynRLEssP3O FeynRLFindings RoPEFormulationAndCode RoPEFindings
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
