# 3b1b Direct Source Cases

Snapshot date: 2026-07-01.

This note zooms in on the 143 `3Blue1Brown.com` lesson pages whose `source` field directly resolves inside the current public `3b1b/videos` tree. The classification below is based on lesson titles and source paths in `data/3b1b_lessons_source_audit.tsv`; it is meant as a working map for building a render/evaluation corpus, not as an official taxonomy of the channel.

## What These 143 Cases Are Doing

The direct-source set is not 143 unrelated templates. Many finished lessons point into shared source files or source folders, so the useful unit for our project is often a reusable visual grammar: coordinate transforms, graph morphs, formula transformations, simulations, probability distributions, matrix diagrams, token/attention diagrams, and so on.

| Content family | Direct cases | Representative source areas | What the cases do | Why it matters for a generation pipeline |
|---|---:|---|---|---|
| Geometry, topology, puzzles, visual proofs | 25 | `_2015/moser_main.py`, `_2016/wcat.py`, `_2017/triples.py`, `_2018/sphere_area.py`, `_2024/puzzles/`, `_2026/hairy_ball/` | Turn a discrete or geometric question into diagrams, transformations, invariants, and reveal moments. | Good for testing whether an agent can plan a visual proof instead of only writing formulas. |
| Advanced math, analysis, transforms | 18 | `_2018/fourier.py`, `_2018/uncertainty.py`, `_2018/div_curl.py`, `_2022/convolutions/`, `_2023/clt/main.py`, `_2026/cross_entropy/` | Animate functions, transforms, distributions, vector fields, complex dynamics, and information-theoretic quantities. | Best target for scene-plan IR with equations, graphs, distributions, and semantic state. |
| Essence of Linear Algebra | 15 | `_2016/eola/` | Explain vectors, span, basis, matrices, linear transforms, determinants, inverses, dot/cross products, eigenvectors, and abstract vector spaces. | Canonical source for coordinate-plane objects, geometric linear algebra, reusable transform idioms. |
| Essence of Calculus | 15 | `_2017/eoc/` | Explain derivatives, limits, rules of differentiation, Euler's number, integration, area/slope duality, and Taylor series. | Canonical source for graph/formula/area animations and multi-video notation consistency. |
| Lockdown Math shared file | 12 | `_2020/ldm.py` | Shorter lessons on quadratics, trig, complex numbers, Euler's formula, logs, power towers, problem-solving, and DP-3T. | Shows how one large source file can support many topical clips with shared helpers. |
| Probability, algorithms, discrete systems | 11 | `_2020/covid.py`, `_2020/sir.py`, `_2020/beta/`, `_2020/hamming.py`, `_2022/puzzles/subsets.py` | Simulate epidemic spread, probability distributions, coding theory, combinatorics, and discrete puzzles. | Good place to separate state simulation from rendering, ALGOGEN-style. |
| Physics, CS, and general explanatory topics | 10 | `_2017/crypto.py`, `_2017/waves.py`, `_2020/monster.py`, `_2024/holograms/`, `_2025/cosmic_distance/` | Explain protocols, physical waves/optics, scientific measurement, group theory, and other one-off topics. | Useful stress test for mixed media: diagrams, text, formulas, historical narrative, and simulations. |
| Other early standalone explainers | 10 | `_2015/inventing_math.py`, `_2015/counting_in_binary.py`, `_2015/music_and_measure.py`, `_2016/triangle_of_power` | Early standalone lessons and channel-specific explanatory experiments. | Good for style archaeology; less ideal as first render targets because of age/version drift. |
| Differential equations / Fourier series | 5 | `_2019/diffyq/` | Explain differential equations, heat equation, Fourier series, Fourier montage, and Euler's formula dynamically. | Strong long-horizon example: simulation, graphs, physical intuition, and series structure. |
| Neural networks | 4 | `_2017/nn/` | Explain neural nets, gradient descent, backpropagation, and backprop calculus. | High-value for ML explainers; graph/layer diagrams plus optimization dynamics. |
| Transformers / LLMs | 4 | `_2024/transformers/` | Explain GPTs, attention, MLP fact storage, and compact LLM overview. | Most directly aligned with our LLM/math-explainer goal and recent ManimGL usage. |
| Colliding blocks / pi | 3 | `_2019/clacks/` | Simulate block collisions and connect dynamics to digits of pi. | Great for simulation-first, visual analogy, and exact event-trace rendering. |
| Bayes / probability reasoning | 3 | `_2019/bayes/`, `_2020/med_test.py` | Explain Bayes' theorem and medical-test intuition. | Good benchmark for conceptual probability diagrams and narration-driven visual sequencing. |
| MIT 18.S191 computational visualization | 3 | `_2020/18S191/` | Visualize image convolution, seam carving, and DFT. | Good for data/image/algorithm visualizations with concrete inputs. |
| Laplace / complex exponentials | 3 | `_2025/laplace/` | Explain complex exponentials and Laplace transforms. | Recent, math-heavy golden-set candidate with likely lower compatibility risk than older series. |
| Wordle / information theory | 2 | `_2022/wordle/simulations.py` | Run Wordle/information-theory simulations and visualize strategies. | Good for computation-backed explanation and trace-to-animation design. |

## Shared Source Hotspots

Several source paths map to more than one finished lesson:

| Shared source path | Direct lessons | Why it matters |
|---|---:|---|
| `_2020/ldm.py` | 12 | One large shared file supports many short lessons; useful for studying helper reuse and scene naming. |
| `_2024/transformers/` | 4 | Modern shared folder for LLM-related explainers. |
| `_2017/eoc/chapter7.py` | 3 | One calculus source supports limits, epsilon-delta, and L'Hopital-related lessons. |
| `_2020/18S191/` | 3 | One lecture/workshop area supports multiple computational visualization topics. |
| `_2025/laplace/` | 3 | Recent shared folder for Laplace series. |
| `_2016/brachistochrone` | 2 | Brachistochrone and Snell's law share a physical/variational visual setup. |
| `_2017/eoc/chapter10.py` | 2 | Two Taylor-series lessons share the same source. |
| `_2017/eoc/chapter3.py` | 2 | Power-rule and trig-derivative lessons share derivative-geometry source. |
| `_2017/nn/part3.py` | 2 | Backpropagation intuition and calculus lessons share source. |
| `_2020/hamming.py` | 2 | Hamming code pair shares source. |
| `_2022/some2` | 2 | SoME2 invitation/results share source. |
| `_2022/wordle/simulations.py` | 2 | Wordle pair shares simulation source. |
| `_2025/cosmic_distance/` | 2 | Cosmic distance pair shares source. |

## What The Source Code Can Recreate

For these direct cases, the public source code can usually cover the **programmatic animation layer**:

| Video layer | Covered by `3b1b/videos` source? | Notes |
|---|---|---|
| Visual object construction | Usually yes | Mobjects, equations, graphs, coordinate planes, matrices, diagrams, images, and custom helper classes. |
| Animation sequencing | Usually yes | Scene classes encode transforms, fades, waits, camera moves, updaters, and staged reveals. |
| Mathematical simulations | Often yes when central to the lesson | Examples include epidemics, Wordle, Hamming codes, clacks/collisions, Fourier/heat-style computations. |
| Visual style primitives | Yes | Colors, layout idioms, labels, camera framing, formula morphs, graph conventions, and helper abstractions. |
| Scene-level render targets | Partly | A source file/folder contains scene classes, but the website `source` field usually points to a source area, not a final render manifest. |
| Narration-aware timing | Weakly/indirectly | `wait`s and animation durations imply pacing, but exact spoken script alignment usually lives outside the Manim code. |
| Captions/subtitles | No, separate repo/data | Use `3b1b/captions` and `caption_ops` for transcripts, SRTs, timing, and retiming workflows. |
| Final YouTube edit | No | Final assembly can include cuts, exported clips, voiceover, music, sound, transitions, sponsor segments, and manual editing. |
| Voice/audio | No | Voice tracks and final audio mix are not reproduced by Manim source alone. |
| Exact historical reproducibility | Not guaranteed | Older projects may require older Manim versions, old dependencies, assets, local config, or path fixes. |
| Channel identity / authorial taste | No | The source reveals implementation patterns, but not the full editorial decision process, voice performance, or private iteration history. |

## Practical Takeaway

For `4blue2brown`, the 143 direct-source cases are best treated as a **high-quality visual-code corpus**, not a ready-made video-generation product. They are enough to build:

- a source/lesson metadata index,
- a retrieval corpus of Manim idioms,
- a golden render set,
- task-specific style recipes,
- a scene-plan-to-code benchmark,
- and renderer/VLM repair loops.

They are not enough by themselves to generate polished 3Blue1Brown-style final videos. To approach full videos, we need additional layers: lesson planning, symbol ledger, narration script, caption/audio alignment, render harness, visual review, edit/concat workflow, and compatibility management across Manim versions.
