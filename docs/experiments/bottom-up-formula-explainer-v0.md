# Bottom-up Formula Explainer v0

Status: implemented pilot; one real Manim smoke rendered on Babel

Date: 2026-07-15

## Scope and counting

This pilot implements the `Atom -> Operation -> Formula -> Topic` path for five
demo topics:

1. `transformers_core`
2. `attention_softmax_lookup`
3. `dpo`
4. `feynrl`
5. `rope`

These are five demo artifacts but only four benchmark paper families. The first
two belong to the same Transformer/attention family. This build must not be used
to revive a "five papers" coverage claim.

The v0 inventory contains seven core formulas, not every formula in every paper.
Each formula has a FormulaIR and generated SceneIR clip plan; each topic has an
ordered composition plan. The current real render is the attention-softmax clip.

## Implemented path

```text
primary-source formula anchor
  -> FormulaIR atoms and operation DAG
  -> primitive registry lookup
  -> SceneIR initial/intermediate/terminal beats
  -> per-formula Manim render target
  -> per-topic ordered composition
  -> canonical graph fragment for later manifest embedding
```

The focused schemas live under `schemas/formula-explainer/`. They do not copy the
full canonical run manifest. The generated graph fragment uses the existing
canonical node types (`formula`, `operation`, `code`, `primitive`, `scene`) and
edge types (`contains`, `implements`, `visualized_by`). Its non-structural
evidence refs are reserved canonical artifact IDs; a later run manifest must
materialize those artifact records before publication.

Canonical schema limitation: canonical graph nodes intentionally carry only ID,
type, coverage, aliases, and publication state. Formula text, source locators,
operation inputs/outputs, primitive origin, visual states, and clip timelines
therefore remain in versioned FormulaIR/SceneIR artifacts rather than being
duplicated into graph nodes.

## Source anchors

| Topic/formula | Primary source anchor | Mapping state |
| --- | --- | --- |
| Transformer scaled attention | `arXiv:1706.03762v7`, Section 3.2.1, page 4, Eq. (1) | formula observed; visual mapping candidate |
| Transformer multi-head | `arXiv:1706.03762v7`, Section 3.2.2, page 5 | formula observed; missing fanout primitive visible |
| Attention scalar softmax | project decomposition of Transformer Eq. (1) | candidate, not a separately numbered paper equation |
| DPO objective | `arXiv:2305.18290v3`, Section 4, page 4, Eq. (7) | formula observed; visual mapping unresolved |
| FeynRL normalized ESS | `arXiv:2605.12380v1`, Section 3, page 5, Eq. (11) | paper observed; code mapping candidate |
| FeynRL-adopted P3O objective | `arXiv:2605.12380v1`, Section 3, page 5, Eq. (12) | paper observed; code mapping candidate |
| RoPE relative score | `arXiv:2104.09864v5`, Section 3.2.2, page 5, Eq. (16) | formula observed; visual mapping unresolved |

The FeynRL topic is named `FeynRL batch adaptation`. P3O is not used as a
synonym for FeynRL. The source paper explicitly says it adopts P3O, and the local
repo at commit `dfe85351e28a3744ab0eb02d2299fc1e6d3d5752` contains candidate
implementations at `algs/P3O/p3o.py::calculate_ess` and
`P3O.compute_policy_loss`. They remain `candidate` until a canonical review event
confirms the edge.

## Primitive origins

The registry exposes both color and text/icon badges:

- green `Manim built-in` / `LIB`;
- purple `Project reusable` / `OURS`;
- orange `Authored one-off` / `1-OFF`;
- gray `Missing / planned` / `TODO`.

Semantic operations such as `exp`, `softmax`, `ESS`, and `KL` are not falsely
presented as Manim API calls. They map to visual implementations composed from
Manim mobjects and animations.

`project_reusable` is a promotion state, not a naming preference. The registry
requires both a test reference and a completed golden-scene reference before a
primitive can use that origin. The two promoted v0 primitives point to the
operation-contract regression test and Babel job `9313551`; one-off and missing
primitives carry empty verification sets until they earn promotion.

## Build and validation

```bash
python3 -m tools.formula_explainer.cli build \
  --output runs/formula_explainer/build
python3 -m tools.formula_explainer.cli validate \
  --build-dir runs/formula_explainer/build
python3 -m unittest discover -s tests/formula_explainer -v
```

Render one compiled formula:

```bash
FORMULA_SCENE_IR=runs/formula_explainer/build/scene_ir/attention_softmax_lookup/attention_softmax.json \
  manim -ql --media_dir runs/formula_explainer/render \
  scenes/formula_explainer_scene.py FormulaExplainerScene
```

## Babel evidence and portability bug

- Job `9313500`: failed. Manim `BarChart` silently constructed `MathTex` axis
  labels, so a chart that looked dependency-light failed in the Babel environment
  without a working LaTeX toolchain.
- Job `9313535`: completed `0:0` in 43 seconds after replacing that chart with a
  reusable `Rectangle + Line + Text` implementation. Output: H.264, 854x480,
  15 fps, 6.667 seconds, SHA-256
  `a8ac69f1340b9e2b26deb2506c247f428b79cfc1b7bb189e17c25ba854ff43ec`.
- Job `9313551`: final layout refinement; see
  `experiments/formula_explainer/babel_smoke_manifest.json` for terminal state and
  final artifact hash.

The observed Babel render environment used Manim `0.20.1`. The registry records
that as render provenance and deliberately leaves the minimum supported version
unset; it no longer presents `0.19.0` as the exact environment or as a tested
lower compatibility bound.

The failed job is useful evidence: using Manim built-ins still requires recording
their transitive renderer dependencies. The project primitive is deliberately
no-LaTeX so it can be reused in slide and video workers with smaller environments.
The final contact sheet is a render smoke, not a pedagogical-quality acceptance:
the source locator, value labels, and origin legend are small at 480p/contact-sheet
scale and need a typography pass before website publication.

## Remaining work

1. Render all seven clip plans, then compose all five topic videos.
2. Add reviewed numeric fixtures for DPO, FeynRL ESS/P3O, and RoPE.
3. Implement and golden-test the missing multi-head fanout primitive.
4. Add canonical artifact records and review events before any edge becomes
   `confirmed` or enters the public evidence ledger.
5. Connect SceneIR renders to SlideIR AnimationSlots with poster frames and static
   fallbacks.
