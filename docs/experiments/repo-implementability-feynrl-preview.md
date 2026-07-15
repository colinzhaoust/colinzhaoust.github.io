# Repo Implementability and FeynRL Preview

Snapshot date: 2026-07-07.

Question: among the GitHub repos we discussed, which ones can realistically be implemented for our paper-with-code explainer goal, and what would they generate for FeynRL/P3O?

## Short Answer

| Repo | Can we implement it? | Best use | FeynRL output quality expectation |
|---|---|---|---|
| Paper2Manim | Yes, after Python 3.11/3.12 + Manim 0.20.1 env and WInE config. | Best external baseline for paper-to-video. | Likely produces a 2-5 scene paper-style explainer; good structure, weak code grounding unless we inject code refs. |
| Code2Video | Yes, after OpenAI-compatible/WInE API patch and deps. | Best external baseline for topic-to-educational-video and VLM layout feedback. | Likely produces a polished concept video about ESS/P3O, but not a true paper-with-code explanation. |
| TheoremExplainAgent | Yes, but heavier. | Long-form theorem/concept video baseline, especially `--only_plan`. | Likely produces a longer theorem-style explanation; can cover FeynRL conceptually, but will not naturally map formulas to FeynRL code. |
| In-house 4blue2brown v0 | Already running. | Current robust anchor for render/probe/VLM loop. | Renders a real FeynRL/P3O storyboard now, but not yet automatic from paper+code. |

## What Is Actually Runnable Today?

Local current venv:

| Dependency check | Status |
|---|---|
| Python | 3.9.6 |
| Manim | 0.19.0 |
| OpenAI SDK | missing |
| cv2 / OpenCV | missing |
| langgraph / langchain_openai | missing |
| litellm / TEA stack | missing |

So the complete external repos are not directly runnable in the current local venv without installing dependencies.

What does run today:

```bash
./.venv-arm64/bin/python tools/run_inhouse_video_suite.py --review-provider mock
```

The existing in-house FeynRL video is:

```text
runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/FeynRLESSMiniLesson.mp4
```

## Paper2Manim

Implementability: high, but not in current local venv.

Why it is promising:

- It explicitly targets academic paper to Manim.
- It has `mvp1` for short text and `mvp2` for arXiv/PDF.
- It has `--no-render`, which is important because we can first inspect summaries/storyboards before paying render/debug cost.
- It has VLM review, visual revision, scene parallelism, and episodic memory bank ideas.
- Its provider abstraction supports `openai_compatible`, so WInE is a natural fit.

What FeynRL would look like:

| Scene | Likely content |
|---|---|
| `ProblemSetup` | RL post-training loop: old policy generates samples, new policy evaluates them, old logprobs are stored. |
| `EffectiveSampleSize` | Toy policy-ratio table; balanced ratios vs stale batch; normalized ESS equation. |
| `AdaptiveObjective` | P3O loss pieces: score-function cap and behavioral KL weight controlled by ESS. |
| `CodeAndTakeaway` | Mentions `calculate_ess`, `compute_policy_loss`, and a final conceptual takeaway. |

Expected gap:

Paper2Manim will not discover FeynRL implementation anchors by itself unless we pass a structured summary containing code references. It needs our `PaperCodeGraph` layer.

## Code2Video

Implementability: medium-high.

Why it is promising:

- Its repo is conceptually simpler and matches local Manim 0.19.0.
- It uses a tri-agent pattern: Planner, Coder, Critic.
- It is code-centric and has MLLM feedback over rendered video.
- The input is a `knowledge_point`, which is easy to feed.

Problems:

- No clean `--no-render`/`--only-plan` entrypoint in the current script.
- API choices are hardcoded to a small set: GPT, Claude, Gemini wrapper functions.
- It is topic-to-video, not paper+repo-to-video.
- It expects extra deps not in current venv: OpenAI SDK, OpenCV, moviepy, scipy, etc.

What FeynRL would look like:

| Section | Likely content |
|---|---|
| Fresh vs stale samples | Two policy boxes, replay buffer, old/new logprob arrows. |
| ESS compresses ratio spread | Ratio dots/gauge; high ESS means trustworthy, low ESS means stale. |
| Adaptive update | Cap line lowers as ESS drops; KL regularizer grows. |

Expected gap:

The video would probably be visually clean and beginner-friendly, but it would not naturally show the FeynRL paper findings, code files, or implementation details.

## TheoremExplainAgent

Implementability: medium, heavier than the others.

Why it is useful:

- It has `generate_video.py --only_plan`.
- It decomposes into scene outline, vision storyboard, technical implementation, animation narration, code generation, render/fix, and optional visual code fixing.
- It supports RAG/context learning.

Problems:

- Requires Python 3.12.8-style env, LiteLLM, Manim 0.18.1, TTS/Kokoro, and a larger dependency stack.
- It is theorem/concept oriented. FeynRL is not a theorem; it is a method+system+implementation paper.
- The generated plan can be good long-form pedagogy, but code grounding would still be manual/injected.

What FeynRL would look like:

1. Motivating failure: fixed clipping under stale replay.
2. Policy ratio distribution as evidence of mismatch.
3. Normalized ESS as reliability measure.
4. P3O update rule and behavioral KL.
5. Sync vs async rollout loop and final takeaway.

Expected gap:

It may sound more like a theorem lecture than a paper-with-code walkthrough.

## Current In-House Output

Our current FeynRL/P3O scene is already rendered and reviewed.

| Artifact | Path |
|---|---|
| Video | `runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/FeynRLESSMiniLesson.mp4` |
| Contact sheet | `runs/inhouse_eval/contact_sheets/FeynRLESSMiniLesson.png` |
| WInE VLM review | `runs/inhouse_eval/vlm_reviews/FeynRLESSMiniLesson.wine.json` |

What it looks like:

1. A title card and three cards: Problem, Signal, Control.
2. A five-sample ratio table showing how one large ratio shrinks ESS.
3. A P3O objective panel with score cap and behavioral KL pieces.

What the VLM critic said:

| Field | Result |
|---|---|
| Score | 3/5 |
| Verdict | Introduces P3O concepts and formulas, but lacks enough explanation and visual flow. |
| Teaching gaps | Intuitive meaning of ESS; how ESS impacts policy update. |
| Visual gaps | Dense info; unclear graph; static presentation. |
| Suggested edits | Animate calculations, explain ESS meaning, break down formulas, clarify graph. |

## Ranking for Next Work

| Priority | Repo | Why |
|---:|---|---|
| 1 | Paper2Manim | Closest to paper-to-video and easiest to run plan-only. |
| 2 | Code2Video | Best topic-to-video/code-centric baseline and likely fastest to adapt after dependencies. |
| 3 | TheoremExplainAgent | Important benchmark for long-form explanation, but heavier and less code-grounded. |
| 4 | In-house | Keep as the control harness and gradually absorb the best ideas from the above. |

## What I Would Implement Next

1. Add a WInE-compatible provider config for Paper2Manim and run `mvp1 --no-render` on the FeynRL/P3O concept text.
2. Add a `--plan-only` mode or dry-run shim to Code2Video so we can inspect outline/storyboard before rendering.
3. Run TEA `--only_plan` with the existing `data/tea_feynrl_p3o_topic.json`.
4. Compare the three generated storyboards against our in-house FeynRL scene and VLM feedback.
5. Use the best storyboard pieces to define our `PaperCodeGraph -> Scene IR` schema.

The important detail: none of the external repos alone gives the exact final product we want. They generate visually explainable math/concept videos. Our missing layer is paper-with-code grounding: formula ↔ code symbol ↔ toy batch ↔ reported finding ↔ comparison baseline.
