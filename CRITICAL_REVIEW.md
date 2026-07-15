# Critical Review: LLM + Manim Long-Horizon Video Generation

Snapshot date: 2026-07-01.

这份笔记是对前面收集到的 papers / GitHub repos / pipeline ideas 的主观但可追溯评论：quality 怎么样，能做什么，不能做什么，效果如何，gap 在哪里，以及不同 model backbone 大概会带来什么差异。

## TL;DR

这个方向已经能做出“可运行的、多场景的、几分钟级别的 Manim 教学视频原型”，但离稳定的 3Blue1Brown-quality 自动生成还有明显距离。现在最靠谱的路线不是端到端 pixel video，也不是让 LLM 一口气写完整视频，而是：

```text
plan -> scene IR -> per-scene codegen -> render -> log repair -> VLM review -> visual repair -> memory/retrieval
```

目前公开结果里比较有说服力的点：

| Claim | Evidence | Comment |
|---|---|---|
| Long-horizon Manim video is possible | TheoremExplainAgent reports 5+ minute theorem explanation videos, 240-theorem benchmark, o3-mini success rate 93.8%, overall score 0.77 | 说明 agentic planning + retry 能跨过“能不能生成完整视频”的坎，但 visual layout 仍是常见短板 |
| Renderer-in-the-loop 很关键 | ManimTrainer reports RITL/RITL-DOC gains larger than fine-tuning alone | 对我们最实用：先做 render harness，再谈模型 |
| Code-specialized open models can be competitive | ManimTrainer: Qwen 3 Coder 30B + GRPO + RITL-DOC reaches 94% render success, 85.7% visual similarity; SeedCoder 8B + GRPO is strong under vanilla inference | Backbone matters, but inference loop matters often more |
| Trace-first beats end-to-end for algorithms | ALGOGEN reports 99.8% success vs 82.5% for end-to-end on 200 LeetCode AV tasks | 对算法/仿真类内容，先生成 state trace 再 render 是应该直接采用的路线 |
| Pedagogy constraints matter | LLM2Manim uses constrained templates, symbol ledger, partial regeneration, expert review; student study reports 83% vs 78% post-test | 它提醒我们：教学质量不是 render success，最终还要看 learning outcomes |

My take: for `4blue2brown`, the fastest credible path is to build a small, measurable agent harness before any training. Model choice should be role-specific: reasoning model for planning, code model for Manim, multimodal model for review, deterministic renderers for algorithmic traces.

## Quality Review by System

| System | Quality | Can do | Cannot do well yet | Reported effect | My comment |
|---|---|---|---|---|---|
| [TheoremExplainAgent](https://arxiv.org/abs/2502.19400) / [GitHub](https://github.com/TIGER-AI-Lab/TheoremExplainAgent) | High as a long-horizon proof-of-concept; has benchmark and generated video data | Multi-scene theorem explanation videos, voiceover, retry-based code repair, VLM/GPT evaluation | Consistent professional layout; complex domain-specific visuals; fully trusted correctness | o3-mini success 93.8%, overall 0.77; papers says most videos still have minor layout issues | Best evidence that “long-horizon Manim agent” is real. But it still produces visually imperfect educational artifacts, not polished 3b1b-level edits |
| [ManimTrainer](https://arxiv.org/abs/2604.18364) / [GitHub](https://github.com/SuienS/manim-trainer) | Strongest model/backbone study; good quantitative framing | Compare SFT, GRPO, renderer-in-loop, API-doc augmented repair across 17 open models | Does not solve full pedagogy/narrative; benchmark seems closer to reference-video similarity than open-ended teaching quality | Qwen 3 Coder 30B + GRPO + RITL-DOC: 85.7% visual similarity, 94% render success; GPT-4.1 baseline 81.9% / 92% | Most useful for model strategy. Key lesson: training helps, but render-loop + docs + retry helps more |
| [LLM2Manim](https://arxiv.org/abs/2604.05266) | Strong pedagogy framing, weaker as autonomy proof | Semi-automated narrated STEM animations with symbol ledger, constrained templates, partial regeneration, expert review | Fully autonomous generation; broad generalization; long-term retention proof | 100-student within-subject study; animation condition 83% vs 78% post-test, higher engagement, lower load | The “human-in-the-loop” stance is honest. Use its symbol ledger + pedagogy rules, but do not treat it as evidence that autonomous generation is solved |
| [ManimAgent / Paper2Manim](https://arxiv.org/abs/2606.30296) / [GitHub](https://github.com/jwj1342/Paper2Manim) | Architecturally interesting; experimental claims still early | Paper section -> scenes; VLM review; positive/negative episodic memory; per-scene retrieval | Public proof of broad, stable quality is still developing; README says main RQ experiments remain | Abstract says human Pass@1 rises and reflection rounds fall as memory grows; repo says MVPs validated and tests pass | Very relevant to our future memory bank. Treat as architecture inspiration more than settled empirical evidence |
| [ALGOGEN](https://arxiv.org/abs/2605.12159) | Very strong for algorithm visualization | Generate verifiable algorithm traces, then deterministic renderer to Manim/TikZ/Three.js | Open-ended conceptual videos, narration, pedagogy beyond algorithm steps | 200 LeetCode AV tasks, 99.8% success vs 82.5% end-to-end | This is the clearest “avoid hallucination by narrowing the problem” result. We should use trace-first for algorithms, probability simulations, and symbolic derivations |
| [Paper2Video / PaperTalker](https://arxiv.org/abs/2510.05096) | Strong long-document/multi-channel framing | Paper -> slides/subtitles/speech/talking-head presentation; metrics like PresentQuiz and IP Memory | 3b1b-style math animation; precise Manim visual reasoning | 101-paper benchmark; claims more faithful/informative than baselines | Not Manim, but its evaluation ideas are useful: generated videos should be judged by what viewers can answer afterward |
| [manim-generator](https://github.com/makefinks/manim-generator) | Practical harness, less research-grade evidence | Code Writer + Code Reviewer + LiteLLM + execution logs + optional vision | Deep pedagogy; benchmarked long-form quality | Provides Manim Bench style practical workflow | Good MVP baseline. We can copy the shape: writer/reviewer/render loop before inventing too much |
| Product/prototype repos: [Math-To-Manim](https://github.com/HarleyCoops/Math-To-Manim), [ManimCat](https://github.com/Wing900/ManimCat), [Manimator](https://github.com/HyperCluster-Tech/manimator) | Mixed / hard to judge externally | Natural-language to math animation demos, UI ideas, auto-fix ergonomics | Reproducible eval, proof of correctness, long-horizon robustness | Stars and demos, but less peer-reviewed evidence | Useful for product UX inspiration; not enough for method selection |
| 3b1b public data: [manim](https://github.com/3b1b/manim), [videos](https://github.com/3b1b/videos), [captions](https://github.com/3b1b/captions) | Extremely high-value corpus, but not a ready benchmark | Source-code examples, scene idioms, captions/timing, real lesson metadata | Automatic rerendering across all years; final published video reproduction; voice/edit/assets | Our audit: 174 lessons, 143 direct source paths, 15 likely stale/renamed, 16 no source field | Best local corpus, but must handle license, version drift, and not overfit to 3b1b branding |

## What These Systems Can Actually Do

| Capability | Current status |
|---|---|
| Generate a short Manim clip from a prompt | Plausible today with a strong code model + render repair |
| Generate a multi-scene 2-5 minute rough explainer | Plausible with planning, per-scene isolation, retries, and concat |
| Generate theorem/algorithm explanation videos | Plausible; theorem explanation needs layout review, algorithm explanation is much safer with trace-first rendering |
| Use VLMs to judge frames | Useful for overlap/offscreen/missing-object checks; weaker for math correctness and long temporal causality |
| Use training/fine-tuning | Useful after a renderer/eval dataset exists; not the first bottleneck |
| Reproduce final 3Blue1Brown-quality videos | Not solved. Public source can generate many scenes, but final videos involve editing, voice, timing, assets, taste, and lots of manual iteration |
| Guarantee mathematical correctness | Not solved. Need symbolic checks, theorem/proof validators, trace verifiers, or human review |
| Maintain style and notation across a long video | Partially solved with symbol ledger/memory; still a major gap |

## Main Gaps

| Gap | Why it matters | Likely fix |
|---|---|---|
| Layout and spatial reasoning | Most systems still hit overlap, misalignment, inconsistent sizes | Add deterministic layout primitives, safe-area constraints, screenshot checks, VLM layout rubric |
| Semantic correctness | A pretty animation can explain the wrong thing | Use symbolic validators, trace/state checks, unit tests for generated data, human review for hard math |
| Long-horizon coherence | Scene 1 and scene 5 may use different notation, colors, or assumptions | Shared symbol ledger, object registry, scene contracts, global reviewer |
| Evaluation is still fuzzy | Render success is too weak; VLM scores can be noisy | Multi-layer eval: render, layout, semantic object checks, human spot checks, viewer quiz |
| Dataset mismatch | Existing Manim benchmarks may be short/reference-based, while our goal is open-ended explainers | Build our own accepted/rejected attempts from 3b1b-derived tasks and new prompts |
| Version compatibility | `3b1b/videos` spans many years and old Manim APIs | Start with recent scenes; build compatibility profiles by year |
| Audio/timing | Generated visuals often ignore narration pacing | Use captions/timing data; make beats first-class in IR |
| Memory quality | Agents can retrieve bad fixes and make future outputs worse | Store only validated memories; separate success examples from failure pitfalls |
| Cost and latency | Multi-agent render/review loops are slow | Parallelize per scene; use cheaper models for log repair; cache renders and retrieval |
| Legal/style boundary | 3b1b source and visual style are not a license to clone the brand | Learn programmatic animation patterns; avoid exact channel identity, assets, voice, or branding |

## Model Backbone Differences

The best pattern is not “pick one model”. Use different backbones for different roles.

| Role | What matters | Current evidence / intuition |
|---|---|---|
| Planner | Long-context reasoning, decomposition, pedagogy | TheoremExplainAgent shows agentic planning is essential for long-form videos; o3-mini performs robustly across theorem difficulty |
| Scene coder | Python + Manim API fluency | ManimTrainer suggests code-specialized models dominate: Qwen 3 Coder 30B + GRPO + RITL-DOC is strongest reported open setup |
| Small/cheap coder | Fast repair, local experiments | SeedCoder 8B + GRPO is a good efficiency point; 7B-8B models can be surprisingly strong after domain tuning |
| Log fixer | Traceback reading, API correction | Does not need the strongest reasoning model; RITL can be cheaper than first-pass generation |
| Visual reviewer | Frame understanding, layout, formula reading | GPT-4o/Gemini-style VLMs are useful; TEA uses GPT-4o for text/frame metrics and Gemini for video consistency |
| Pedagogy/narration | Explanation quality and pacing | Frontier language models help, but style constraints and beat structure matter more than raw fluency |
| Trace generator | Correct simulation state | For algorithms, correctness beats aesthetics; generated traces should be executable/verifiable |

Model-specific comments from current evidence:

| Backbone / family | Observed behavior |
|---|---|
| `o3-mini` | Strong for theorem planning in TEA; reported 93.8% success / 0.77 overall. Good candidate for planner/helper roles |
| `GPT-4o` / GPT-4.1 | Strong baseline; ManimTrainer reports GPT-4.1 no fine-tuning with RITL-DOC at 81.9% VS / 92% RSR. Good generalist and evaluator |
| Gemini 2.0 Flash | TEA reports it is fast/cheap; human preference study ranked Gemini outputs highly for clarity/visual appeal, but paper also notes weaker structured metrics in some settings |
| Claude 3.5 Sonnet | Capable but TEA appendix reports slower and more expensive in their setup, especially with RAG |
| Qwen 3 Coder 30B | Best reported open model in ManimTrainer when combined with GRPO + RITL-DOC; good candidate if we later self-host or fine-tune |
| SeedCoder 8B | Efficient sweet spot after GRPO; useful for local/cheap generation and repair experiments |
| Very small models `<4B` | Can be hurt by long RAG/API-doc contexts; likely need compact retrieval and strict templates |
| Bigger generic base models | Size alone does not solve Manim; domain APIs, renderer feedback, and visual repair matter more |

## My Quality Bar for This Project

For `4blue2brown`, I would not call a result “good” just because it renders. Suggested quality tiers:

| Tier | Definition | Use |
|---|---|---|
| T0 Rendered | Code runs and outputs video | Debugging only |
| T1 Legible | No major overlap/offscreen/blank-frame issues | Internal demos |
| T2 Faithful | Visuals match requested concepts and formulas | Usable snippets |
| T3 Coherent | Multi-scene notation, colors, and narrative stay consistent | Rough explainer videos |
| T4 Pedagogical | Learner can answer target questions better than baseline | Real teaching/content |
| T5 Polished | Human-level pacing, taste, timing, voice, editing | Aspirational; not near-term autonomous |

Most current systems are between T1 and T3. LLM2Manim tries to evaluate T4 with human-in-the-loop. None convincingly reaches autonomous T5.

## Recommended Work Plan

1. Build a render harness first. It should capture code, logs, artifacts, sampled frames, timeout, and render success.
2. Create a tiny eval set from 3 clusters: one algorithm/trace task, one math transform task, one LLM/attention diagram task.
3. Start with a direct codegen baseline plus log-repair loop.
4. Add a scene-plan IR and symbol ledger before scaling to multi-scene.
5. Add VLM review only after render success; do not ask VLM to fix code directly, ask it to produce structured critique.
6. Add retrieval over Manim docs and selected 3b1b snippets.
7. For algorithmic content, use ALGOGEN-style trace-first rendering immediately.
8. Only consider SFT/GRPO after we have at least hundreds of logged attempts and a stable evaluation rubric.

The major bet: **agentic infrastructure will matter more than the first model choice**. A mediocre code model with renderer feedback, small examples, and a good IR will beat a stronger model asked to write a whole long video in one shot.
