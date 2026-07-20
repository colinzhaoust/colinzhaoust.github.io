# 4blue2brown Progress Site

Static, evidence-led progress brief for the `4blue2brown` project. The page is
organized as an overview/ledger plus four research threads:

1. real video pipelines;
2. paper-to-slides baselines;
3. the integrated Slides + Manim pipeline and bottom-up formula graph;
4. backtranslation references and blocked generation conditions.

Open locally:

```bash
python3 -m http.server 8765 --directory progress_site
```

Then visit `http://localhost:8765/`. Serving over HTTP is required for the JSON
ledger and nested checkpoint links to behave like the published site.

Before publication:

```bash
python3 progress_site/check_site.py
```

The checker validates local assets and JSON, verifies every Backtranslation
artifact against its declared size and SHA-256, reconciles the six-suite
aggregate, rejects private filesystem locators and baseline-coverage dummy
references, and verifies that video URLs remain lazy until a visitor explicitly
loads a clip.

Key source material:

- `README.md`
- `AGENTIC_PIPELINE.md`
- `CRITICAL_REVIEW.md`
- `docs/experiments/paper-video-agent-codebase-implementation.md`
- `docs/experiments/reproduction-suite-transformers-feynrl-rope.md`
- `docs/plans/paper-code-video-pipeline.md`
- `runs/inhouse_eval/`
- `runs/reproductions/`
- `renders/feynrl_method_viz/`
- `experiments/real_video_matrix/v1/report.json`
- `experiments/slides_baselines/v1/results.json`
- `runs/formula_explainer/build/`
- `experiments/slides_manim/methodology_attention_softmax.slide-ir.json`
- `experiments/backtranslation/v1/evidence/babel_20260716/`

The machine-readable public snapshot is `progress_site/data/evidence.json`.
Public Backtranslation media retains both Manim MIT notices under
`progress_site/assets/backtranslation/`.

Published target:

```text
https://colinzhaoust.github.io/4blue2brown-progress/
```
