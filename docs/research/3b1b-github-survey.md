# 3b1b GitHub Survey

Snapshot date: 2026-07-01. Sources checked: [github.com/3b1b](https://github.com/3b1b), GitHub API, `3b1b/videos` README, `3b1b/manim` README, `3b1b/captions` README, and `3Blue1Brown.com` lesson frontmatter.

## Executive Read

The 3b1b account is a public GitHub user account, not an organization endpoint. The two core repositories for our eventual pipeline are:

- [`3b1b/manim`](https://github.com/3b1b/manim): the ManimGL animation engine for precise programmatic math animations.
- [`3b1b/videos`](https://github.com/3b1b/videos): scene code used in 3Blue1Brown videos, organized mostly by year and topic.

The other highly useful repositories are:

- [`3b1b/3Blue1Brown.com`](https://github.com/3b1b/3Blue1Brown.com): lesson metadata and article text. Most lesson frontmatter includes `video` and `source` fields.
- [`3b1b/captions`](https://github.com/3b1b/captions): deprecated in favor of Criblate, but still a large transcript/subtitle/timing corpus.
- [`3b1b/caption_ops`](https://github.com/3b1b/caption_ops): operational scripts for captions, transcription, translation, retiming, and upload workflows.

Important caveat: these repos can regenerate many animation scenes, not necessarily the final published YouTube videos. Final videos also involve voiceover, music, edits, exported assets, old Manim versions, custom local workflow, and sometimes private or external assets.

## Repository Inventory

| Repository | Snapshot role | Direct value to this project | Notes |
|---|---|---|---|
| [`manim`](https://github.com/3b1b/manim) | Animation engine for explanatory math videos | Core renderer and API reference | ManimGL, package `manimgl`, distinct from Manim Community. MIT license. |
| [`videos`](https://github.com/3b1b/videos) | Manim scene code for 3Blue1Brown videos | Primary corpus of executable/inspectable scenes | README warns older projects may require older Manim versions. Repo content is CC BY-NC-SA 4.0. |
| [`3Blue1Brown.com`](https://github.com/3b1b/3Blue1Brown.com) | Website lesson/article source | Metadata bridge from public lessons to source paths | Frontmatter includes `title`, `date`, `video`, `source`, `description`. |
| [`captions`](https://github.com/3b1b/captions) | Transcript/subtitle/timing corpus | Useful for script alignment and multilingual timing | README says deprecated in favor of Criblate. Still has thousands of `.srt`, `.json`, `.txt` files. |
| [`caption_ops`](https://github.com/3b1b/caption_ops) | Caption workflow scripts | Useful patterns for transcription, translation, retiming | Python scripts include `retime_srt.py`, `sentence_timings.py`, `transcribe_video.py`, `translate.py`. |
| [`DoublePendulumVideo`](https://github.com/3b1b/DoublePendulumVideo) | Fork used for one double-pendulum video | Reference for physics simulation visualization | Description points to `https://youtu.be/n7JK4Ht8k8M`. |
| [`moderngl`](https://github.com/3b1b/moderngl) | Fork of ModernGL | Historical graphics dependency context | Not a direct content corpus. |
| [`perseus`](https://github.com/3b1b/perseus) | Fork of Khan Academy exercise renderer | Possible interactive math UI context | Not a video generation corpus. |
| [`site_demo`](https://github.com/3b1b/site_demo) | Older site/demo artifact | Low direct value | Mostly historical. |

## What Can Be Generated?

Using `3Blue1Brown.com` frontmatter as the public lesson index and `3b1b/videos` as the source tree, the current audit found:

| Metric | Count | Interpretation |
|---|---:|---|
| Website lesson pages checked | 174 | `app/pages/lessons/**/index.mdx` in `3Blue1Brown.com` |
| Lessons with a YouTube `video` id | 169 | Good for mapping to published pages/videos |
| Lessons whose `source` directly exists in `3b1b/videos` | 143 | Best candidates for automatic source retrieval and render attempts |
| Lessons with stale/renamed `source` paths | 15 | Likely recoverable with manual path mapping |
| Lessons with no usable public source field | 16 | Likely not first-pass renderable from public source metadata alone |

The full extracted table is in [`data/3b1b_lessons_source_audit.tsv`](../../data/3b1b_lessons_source_audit.tsv).

## Coverage by Year

| Year | Website lessons | Direct source paths | Stale/renamed paths | No public source field |
|---|---:|---:|---:|---:|
| 2015 | 7 | 5 | 0 | 2 |
| 2016 | 21 | 21 | 0 | 0 |
| 2017 | 32 | 31 | 0 | 1 |
| 2018 | 16 | 15 | 0 | 1 |
| 2019 | 16 | 14 | 1 | 1 |
| 2020 | 26 | 24 | 0 | 2 |
| 2021 | 8 | 6 | 2 | 0 |
| 2022 | 8 | 8 | 0 | 0 |
| 2023 | 13 | 4 | 7 | 2 |
| 2024 | 10 | 7 | 1 | 2 |
| 2025 | 13 | 5 | 3 | 5 |
| 2026 | 4 | 3 | 1 | 0 |

## High-Value Renderable Series

These are the best first candidates because they are coherent series with public lesson metadata and public scene code.

| Series / cluster | Public source area | Example lessons | First-pass usefulness |
|---|---|---|---|
| Essence of Linear Algebra | `_2016/eola/` | Vectors, span/basis, linear transformations, matrix multiplication, determinant, eigenvalues, abstract vector spaces | Canonical 3b1b visual grammar: coordinate planes, transforms, basis vectors, geometry-first exposition |
| Essence of Calculus | `_2017/eoc/` | Essence of calculus, derivative paradox, chain rule/product rule, limits, integration, Taylor series | Strong target for an input-to-animation DSL because it repeats visual primitives across lessons |
| Neural networks | `_2017/nn/` | Neural network intro, gradient descent, backpropagation, backprop calculus | Useful for graph/network diagrams, parameter updates, staged conceptual zoom-ins |
| Differential equations | `_2019/diffyq/` | Differential equations, PDEs, heat equation, Fourier series, dynamics view of Euler's formula | Good for simulation + explanatory overlays + multi-part narrative reuse |
| Lockdown Math | `_2020/ldm.py` | Complex numbers, Euler's formula, logarithms, natural logs, power towers, problem solving | Dense set of shorter lessons sharing one file, useful for scene extraction experiments |
| MIT 18.S191-style lectures | `_2020/18S191/` | Image convolution, DFT, diffusion equation, seam carving | More lecture/workshop-like; useful for algorithm visualization |
| Wordle / information theory | `_2022/wordle/` | Wordle solver and follow-up | Good corpus for computation-driven animation plus probabilistic narration |
| Transformers / deep learning | `_2024/transformers/` | GPT, attention, MLP, mini-LLM | Modern high-value target for LLM-related visual explanation generation |
| Laplace transforms | `_2025/laplace/` | Laplace transform, Laplace for ODEs, Euler formula prelude | Recent mathematical exposition; likely useful for modern render testing |
| Cross entropy / compression | `_2026/cross_entropy/` | Reinventing entropy | Recent source and topic aligned with information theory / ML explanations |

## Known Source Drift

Some website frontmatter source fields do not directly exist in the current `videos` tree. These are likely stale names or path moves:

| Website source field | Suggested current source area |
|---|---|
| `_2019/diffyq/par $T_2$` | `_2019/diffyq/part2/` |
| `_2021/some1` | `_2021/some1.py`, `_2021/some1_winners.py` |
| `_2023/barber_pole/` | `_2023/optics_puzzles/` |
| `_2023/clt/integral.py` | `_2023/gauss_int/integral.py` |
| `_2023/prime_race.py/` | `_2023/numberphile/prime_race.py` |
| `_2023/some3` | `_2023/SoME3/main.py` |
| `_2024/manim-demo/` | `_2024/manim_demo/lorenz.py` |
| `_2025/block_and_grover/`, `_2025/blocks_and_grover/` | `_2025/colliding_blocks_v2/`, `_2025/grover/` |
| `_2026/spheres/` | `_2026/spheres_talk/` |

## Pipeline Implications

For a generation system, the public 3b1b ecosystem suggests a practical architecture:

| Pipeline layer | Public source to study | What to learn |
|---|---|---|
| Scene language | `manim`, `videos` | Objects, transforms, updaters, camera movement, animation timing |
| Lesson metadata | `3Blue1Brown.com` | Title/date/video/source mapping; topic and article structure |
| Narrative script | `3Blue1Brown.com`, `captions` | How concepts are sequenced and explained in text |
| Audio/timing alignment | `captions`, `caption_ops` | Sentence timings, word timings, SRT retiming, transcription workflow |
| Render workflow | `videos` README, `manim` README | `manimgl`, interactive checkpoint workflow, render flags, version risk |

The safest next technical move is not full end-to-end generation. It is a compatibility/render harness over a small golden set of recent sources, plus a metadata ingester that keeps the website lesson map and `videos` tree in sync.
