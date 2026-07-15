# Related Papers and Systems

Snapshot date: 2026-07-01.

The exact target, "given some inputs, generate precise 3Blue1Brown-like Manim videos", is still emerging. Top venues have strong adjacent work in natural-language-to-visualization, visualization authoring, animated transitions, and text-to-video generation. Direct Manim/STEM-animation papers are currently mostly arXiv/system papers rather than established top-conference lines.

## Most Relevant Top-Venue / Top-Journal Adjacent Work

| Work | Venue / status checked | Why it matters for this project | Link |
|---|---|---|---|
| Data Formulator: AI-Powered Concept-Driven Visualization Authoring | IEEE TVCG 2024, confirmed via DBLP | Turns user intent into editable visualization specs and transformations. Relevant to the "concept -> visual structure" layer before animation. | [arXiv](https://arxiv.org/abs/2309.10094), [DBLP](https://dblp.org/rec/journals/tvcg/WangTL24) |
| NL4DV: A Toolkit for Generating Analytic Specifications for Data Visualization from Natural Language Queries | IEEE TVCG 2021, confirmed via DBLP | Earlier NL-to-visualization-spec work. Useful as a conservative baseline for parsing intent into visual analytic specs. | [arXiv](https://arxiv.org/abs/2008.10723), [DBLP](https://dblp.org/rec/journals/tvcg/NarechaniaSS21) |
| Canis: A High-Level Language for Data-Driven Chart Animations | Computer Graphics Forum 2020, confirmed via DBLP | A concrete grammar for data-driven chart animation. Useful when designing animation primitives above raw Manim calls. | [DBLP](https://dblp.org/rec/journals/cgf/GeZLRCW20) |
| Align Your Latents: High-Resolution Video Synthesis With Latent Diffusion Models | CVPR 2023, confirmed in CVF proceedings | Strong top-conference reference for high-res video generation. Useful for generated texture/b-roll/background experiments, but not precise mathematical scene control. | [CVF](https://openaccess.thecvf.com/content/CVPR2023/html/Blattmann_Align_Your_Latents_High-Resolution_Video_Synthesis_With_Latent_Diffusion_Models_CVPR_2023_paper.html), [arXiv](https://arxiv.org/abs/2304.08818) |

## Strongly Relevant Preprints / Systems

| Work | Status checked | Why it matters | Link |
|---|---|---|---|
| LLM2Manim: Pedagogy-Aware AI Generation of STEM Animations | arXiv 2026 | The closest direct match found: LLM-assisted generation of Manim-style STEM animations with pedagogical awareness. Should be read before designing our own IR/eval loop. | [arXiv](https://arxiv.org/abs/2604.05266) |
| Paper2Video: Automatic Video Generation from Scientific Papers | arXiv 2025 | End-to-end scientific-paper-to-video framing: script, visuals, narration, and structure. Useful for pipeline decomposition, even if the target visual style differs. | [arXiv](https://arxiv.org/abs/2510.05096) |
| ChartMimic: Evaluating LMM's Cross-Modal Reasoning Capability via Chart-to-Code Generation | arXiv 2024 / CoRR via OpenReview API | Benchmark for visual-to-code generation. Relevant to evaluating whether a model can produce code that matches a desired visual. | [arXiv](https://arxiv.org/abs/2406.09961) |
| LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using Large Language Models | arXiv 2023 | LLM-driven visualization and infographic generation. Useful for grammar-agnostic visual spec generation and critique loops. | [arXiv](https://arxiv.org/abs/2303.02927) |
| Gemini: A Grammar and Recommender System for Animated Transitions in Statistical Graphics | arXiv 2020 | Relevant to animation grammar: how to specify and recommend meaningful transitions between chart states. | [arXiv](https://arxiv.org/abs/2009.01429) |
| VideoPoet: A Large Language Model for Zero-Shot Video Generation | arXiv 2023 | Treats video generation as sequence modeling. Useful as contrast: powerful generative video, but weak on exact symbolic/math controllability. | [arXiv](https://arxiv.org/abs/2312.14125) |
| Emu Video: Factorizing Text-to-Video Generation by Explicit Image Conditioning | arXiv 2023 | Useful for thinking about image-conditioned video generation and reference-frame control. Not a substitute for precise Manim code. | [arXiv](https://arxiv.org/abs/2311.10709) |

## Takeaways for 4blue2brown

| Design question | What the literature suggests |
|---|---|
| Should we generate pixels directly? | Not as the primary path. Text-to-video models are impressive, but the 3b1b-like value is precision, editability, rerenderability, symbolic correctness, and timed conceptual staging. |
| Should we generate Manim code directly? | Probably yes for prototypes, but long term we likely want an intermediate scene-plan IR so that codegen is repairable and testable. |
| What should evaluation look like? | Borrow from chart-to-code and visual authoring: compare rendered output to intended structure, check object presence/positions, verify formulas, and run visual regression tests. |
| Where do captions fit? | Captions and word/sentence timing should drive beat-level alignment: a scene plan can bind narration spans to visual state changes. |
| What is still missing? | A benchmark of math-explainer tasks with ground-truth scene plans, Manim code, rendered frames, and pedagogical rubrics. The public 3b1b repos can seed this, but licensing and style/brand boundaries matter. |

## Proposed Reading Order

1. `LLM2Manim` for the nearest direct problem statement.
2. `Data Formulator` and `NL4DV` for intent-to-visual-spec design.
3. `Gemini` for animated transition grammar.
4. `ChartMimic` for visual/code evaluation ideas.
5. `Align Your Latents`, `VideoPoet`, and `Emu Video` as contrastive references for pixel video generation, not as the main architecture.
