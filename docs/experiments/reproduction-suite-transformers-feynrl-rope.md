# Reproduction Suite: Transformers, FeynRL, RoPE

Snapshot date: 2026-07-09.

This note records the current clean-room reproduction pass for three external paper-to-video styles:

- Paper2Manim style: paper section to Manim scene plan.
- Code2Video style: knowledge point to lecture sections and animation beats.
- TheoremExplainAgent style: theorem/concept to long-form scene implementation plan.

The comparison papers are Transformers, FeynRL/P3O, and RoPE/RoFormer. Each paper is split into multiple teaching units instead of treated as one theorem.

## Folder Contract

| Path | Role |
|---|---|
| `experiments/reproductions/README.md` | Reproduction preview overview and commands. |
| `experiments/reproductions/paper_specs/*.json` | Clean tracked paper/concept specs for Transformers, FeynRL, and RoPE. |
| `tools/run_reproduction_previews.py` | Adapter runner for Paper2Manim, Code2Video, and TheoremExplainAgent-style outputs. |
| `tools/run_tea_wine_plan.py` | Thin WInE runner for TEA's upstream `generate_video.py --only_plan`. |
| `tools/run_manimtrainer_api_reproduction.py` | Thin WInE runner for ManimTrainer/ManimAgent-style API generation plus RITL/RITL-DOC render feedback. |
| `scenes/llm2manim_inspired_suite.py` | Local LLM2Manim-inspired Manim scenes for five topics. |
| `tools/run_llm2manim_inspired_suite.py` | Batch renderer/prober/site-asset updater for the LLM2Manim-inspired reproduction row. |
| `scenes/inhouse_paper_explainer_suite.py` | Robust local Manim scenes used as our renderable baseline. |
| `data/inhouse_paper_video_specs.json` | Registry of current in-house scene specs. |
| `runs/reproductions/` | Generated previews and render probes. This stays out of the clean source tree. |
| `runs/inhouse_manim_media/` | Rendered Manim videos. |

Important distinction: this pass reproduces the input/output contracts and prompt shapes of the external repos. It does not yet install and execute each upstream repo's full dependency stack.

## What Actually Ran

This is the current ground truth, to avoid confusing topic comparisons with repo comparisons.

| Output group | Repo or code path actually used | Topics covered | Status |
|---|---|---|---|
| Code2Video videos | `external/Code2Video-main` plus `tools/run_code2video_wine.py` | Transformers, FeynRL/P3O, RoPE | Same repo/pipeline, different topic strings. These videos are expected to look stylistically similar. |
| Paper2Manim video | `external/Paper2Manim-main` plus fanout/repair tools | RoPE, FeynRL/P3O ESS, Transformers attention | Real upstream storyboard/code path with our fanout/no-LaTeX repair harness. FeynRL and Transformers were rerun on Babel Slurm on 2026-07-09. |
| TheoremExplainAgent upstream plan/render smokes | `external/TheoremExplainAgent-main/generate_video.py` via WInE/LiteLLM | RoPE plan; FeynRL/P3O ESS plan and scene1-scene2 smoke renders | Real upstream planner/code generator. Full FeynRL run hit timeout, but cached plans plus single-scene reruns produced two rendered Manim smoke videos after no-LaTeX repair. |
| TheoremExplainAgent preview outputs | `tools/run_reproduction_previews.py` mock/WInE adapter, not full upstream render | Transformers, FeynRL/P3O, RoPE previews | Plan-style adapter previews only. |
| LLM2Manim-inspired videos | `scenes/llm2manim_inspired_suite.py` plus `tools/run_llm2manim_inspired_suite.py` | FeynRL/P3O, DPO, Attention, Transformers, RoPE | Method-level reproduction of the paper pipeline. Not an official repo/checkpoint run. |
| ManimTrainer / ManimAgent API-mode video | `external/manim-trainer` prompt/RITL-DOC method via `tools/run_manimtrainer_api_reproduction.py` | RoPE relative-position identity | Real Manim render through an API-mode reproduction. This is not the official SeedCoder LoRA inference path. |
| In-house baseline videos | `scenes/inhouse_paper_explainer_suite.py` | Transformers, FeynRL/P3O, RoPE | Our own deterministic Manim scenes, not an upstream repo reproduction. |

The local `external/FeynRL` repo was cloned and inspected for paper/code grounding, but Code2Video did not ingest or execute FeynRL source code. The main FeynRL/P3O Code2Video video is still a topic-string explanation, not a source-code-grounded video.

## Why Some Repos Did Not Really Run Yet

| System | Current state | Why it did not get a full run in this pass | What a real run would require |
|---|---|---|---|
| Paper2Manim | Real upstream runs now exist for RoPE, FeynRL/P3O ESS, and Transformers attention. | The full path is still not clean: upstream MVP1 does not reliably fan out all scenes, and renderability needed no-LaTeX/code-normalization repair. | Convert the fanout/repair flow into a reusable harness with layout/readability probes and formula-safe templates. |
| TheoremExplainAgent / TEA | Repo is cloned under `external/TheoremExplainAgent-main`; RoPE planning is complete; FeynRL/P3O ESS produced scene1-scene7 plans and rendered scene1-scene2 smoke videos. | Full video rendering is not done. The full FeynRL run hit the 1200s timeout, TEA can silently exit when required CLI context is missing, and generated code still assumes `Tex`/`MathTex`/LaTeX or optional voiceover packages. | Patch/guard scene parsing and CLI status codes, set render PATH consistently, add no-LaTeX/formula-preserving code normalization, then rerun scenes one at a time. |
| LLM2Manim | No canonical upstream checkout found, but a local paper-method reproduction now exists under `runs/reproductions/llm2manim_inspired/`. | This is not a full official run because the public artifact found in this pass is the paper/method, not a runnable repo/checkpoint. | Keep the local row labeled `LLM2Manim-inspired`; if an official repo appears, clone it and compare official outputs to the method reproduction. |
| ManimTrainer | Official repo is cloned under `external/manim-trainer` locally and on Babel. API-mode RITL-DOC reproduction is complete for RoPE. | Official adapter inference was not run because it requires the SeedCoder 8B base model, Unsloth/HF stack, and a GPU-capable environment. The repo releases SeedCoder 8B adapters, not the strongest Qwen 3 Coder 30B GRPO checkpoint reported in the paper. | Use a GPU node/env to load the released SeedCoder 8B SFT and SFT+GRPO adapters, or keep using API-mode RITL-DOC as a method-level reproduction. |

Bottom line: Code2Video is still the only repo run across all three target papers in one clean batch. Paper2Manim now has true upstream evidence for RoPE, FeynRL/P3O ESS, and Transformers attention, but needs our fanout/repair harness. TEA now has true upstream FeynRL planning plus two rendered smoke scenes, but not a full assembled video. LLM2Manim has a five-topic method-level reproduction, clearly marked as non-official. ManimTrainer is cloned and method-tested through an API-mode RITL-DOC render, while official local-adapter inference still needs a proper GPU/Unsloth environment.

## 2026-07-09 Babel Upstream Batch

| Artifact | Source path | Local website asset | Result |
|---|---|---|---|
| Paper2Manim FeynRL/P3O ESS fanout | `$HOME/4blue2brown_explore/runs/reproductions/upstream_batch_20260709/paper2manim_runs/20260709-020756-ba60d6/final/feynrl_p3o_ess_fanout.mp4` | `progress_site/assets/upstream-batch-20260709/videos/paper2manim_feynrl_p3o_ess_fanout.mp4` | 86.0s, renders, but visually sparse. |
| Paper2Manim Transformers attention fanout | `$HOME/4blue2brown_explore/runs/reproductions/upstream_batch_20260709/paper2manim_runs/20260709-020953-a06b09/final/transformers_attention_fanout.mp4` | `progress_site/assets/upstream-batch-20260709/videos/paper2manim_transformers_attention_fanout.mp4` | 59.0s, renders, but elements are tiny/low-density. |
| TEA FeynRL scene1 smoke | Cached TEA plan plus generated Manim code under `tea_scene1_smoke/` | `progress_site/assets/upstream-batch-20260709/videos/tea_feynrl_scene1_smoke.mp4` | 30.9s, renders after no-LaTeX/API compatibility repair. |
| TEA FeynRL scene2 smoke | Cached TEA scene2 plan repackaged as a one-scene topic under `tea_scene_smokes/scene2/` | `progress_site/assets/upstream-batch-20260709/videos/tea_feynrl_scene2_smoke.mp4` | 33.1s, renders after no-LaTeX repair; formulas degrade to literal text. |

## Commands

Local deterministic previews:

```bash
./.venv-arm64/bin/python tools/run_reproduction_previews.py --provider mock
```

WInE-backed previews, already run on Babel:

```bash
python tools/run_reproduction_previews.py \
  --provider wine \
  --model wine-claude-haiku-4-5 \
  --max-tokens 5000 \
  --out-dir $HOME/4blue2brown_explore/runs/reproductions/previews_wine
```

Rendered local baseline scenes:

```bash
env PATH=/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin \
  ./.venv-arm64/bin/manim -ql \
  --media_dir runs/inhouse_manim_media \
  scenes/inhouse_paper_explainer_suite.py \
  TransformerCoreExplainer FeynRLESSMiniLesson RoPERotationExplainer
```

Render probe:

```bash
./.venv-arm64/bin/python tools/probe_rendered_videos.py \
  --videos \
  runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/TransformerCoreExplainer.mp4 \
  runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/FeynRLESSMiniLesson.mp4 \
  runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/RoPERotationExplainer.mp4 \
  --out-dir runs/reproductions/render_eval
```

## Paper Specs

| Paper | Teaching units currently modeled |
|---|---|
| Transformers | Scaled dot-product attention, multi-head attention, sinusoidal positional encoding. |
| FeynRL / P3O | Policy-ratio staleness, effective sample size, P3O adaptive objective. |
| RoPE / RoFormer | Baseline position strategies, 2D rotary pair, relative-position dot-product identity, multi-frequency RoPE. |

## WInE Preview Outputs

| Adapter | Paper | Output shape |
|---|---|---|
| Code2Video | FeynRL | 6 sections: staleness problem, policy ratios, ESS, P3O objective, PPO comparison, on/off-policy intuition. |
| Code2Video | RoPE | 6 sections: why position matters, 2D rotary pair, relative distance in dot product, multi-frequency RoPE, sinusoidal baseline comparison, implementation sketch. |
| Code2Video | Transformers | 6 sections: recurrence bottleneck, scaled dot-product attention, multi-head attention, position without recurrence, sinusoidal encoding, full architecture. |
| Paper2Manim | FeynRL | 4 scenes: ratio staleness, ESS computation, P3O adaptive objective, PPO vs P3O comparison. |
| Paper2Manim | RoPE | 5 scenes: baseline strategies, 2D rotary pair, relative position in attention, multi-frequency RoPE, comparison summary. |
| Paper2Manim | Transformers | 4 scenes: Q/K/V mixing, multi-head parallelism, positional encoding waves, attention vs recurrence. |
| TheoremExplainAgent | FeynRL | 8 implementation plans, from problem setup through ESS/P3O and comparison. |
| TheoremExplainAgent | RoPE | 6 implementation plans, from positional baselines through RoPE formula and implementation. |
| TheoremExplainAgent | Transformers | 6 implementation plans, covering attention, multi-head structure, and position encoding. |

Preview artifacts live under:

```text
runs/reproductions/previews_wine/<adapter>/<paper>/preview.json
```

## Rendered Baseline Videos

| Paper | Scene | Video | Probe result |
|---|---|---|---|
| Transformers | `TransformerCoreExplainer` | `runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/TransformerCoreExplainer.mp4` | 11.47s, 854x480, non-blank sampled frames. |
| FeynRL / P3O | `FeynRLESSMiniLesson` | `runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/FeynRLESSMiniLesson.mp4` | 14.27s, 854x480, non-blank sampled frames. |
| RoPE / RoFormer | `RoPERotationExplainer` | `runs/inhouse_manim_media/videos/inhouse_paper_explainer_suite/480p15/RoPERotationExplainer.mp4` | 16.53s, 854x480, non-blank sampled frames. |

Contact sheets:

```text
runs/reproductions/render_eval/contact_sheets/TransformerCoreExplainer.png
runs/reproductions/render_eval/contact_sheets/FeynRLESSMiniLesson.png
runs/reproductions/render_eval/contact_sheets/RoPERotationExplainer.png
```

The probe sampler was updated to search around target timestamps and choose the least blank frame. This avoids scoring a scene poorly only because a fixed timestamp landed inside a fade transition.

## Quality Notes

| Paper | Current video quality | What works | What is missing |
|---|---|---|---|
| Transformers | Good as a compact architectural overview. | Shows attention as token-to-token lookup, multi-head parallel views, and sinusoidal position curves. | Needs a numeric QK dot-product example, softmax normalization, and a code-level mapping to an implementation. |
| FeynRL / P3O | Good as a storyboard of the problem and control signal. | Makes ratio staleness, ESS, and P3O control visually concrete. | Still shallow on derivation, paper findings, and source-code grounding. It should point to exact training-loop variables/functions. |
| RoPE / RoFormer | Strongest paper for formula-by-formula decomposition. | The paper's baseline discussion maps well to scenes: absolute, sinusoidal, relative bias, rotary identity, multi-frequency rotation. | Needs longer baseline subclips and a worked attention-score example showing why only relative distance remains. |

## Adapter Takeaways

| Adapter | Best use | Failure mode for our goal |
|---|---|---|
| Paper2Manim | Produces the most Manim-native scene decomposition. Good for turning paper sections into visual scenes. | Does not by itself ground formulas to a code repo or guarantee robust renders. Needs provider setup and render-repair loop. |
| Code2Video | Produces the clearest lecture sequence and teachable section boundaries. Good for concept videos and examples. | Starts from knowledge points rather than full paper+repo evidence. Needs API/provider patching and paper-code ingestion. |
| TheoremExplainAgent | Produces the richest long-form implementation plans. Good when the target is theorem-like and formula-heavy. | Can over-plan, and is less naturally suited to paper findings, repo code, ablations, or empirical comparisons. |

## What This Means For Our Pipeline

The three external systems are useful, but none fully solves: "given a paper with code, generate a video series that teaches formula, code, toy example, comparison, and findings."

The in-house direction should use:

1. Paper2Manim-style scene decomposition.
2. Code2Video-style planner/coder/critic loop and TeachQuiz idea.
3. TheoremExplainAgent-style long-form theorem decomposition when formulas are central.
4. Our own PaperCodeGraph that binds paper formulas, source-code variables, toy data, rendered scenes, narration, and eval questions.

The next useful implementation step is to fully run one upstream repo end-to-end, with Paper2Manim first because it is closest to paper-to-Manim. Code2Video should be second for its planner/critic loop. TheoremExplainAgent should be kept as a formula/theorem-planning reference unless its dependency stack proves easy to stabilize.

## Next Work Items After This Pass

| Priority | Step |
|---:|---|
| 1 | Bring TheoremExplainAgent from `--only_plan` to render: fix/guard scene tag parsing, run one formula-heavy RoPE unit and one FeynRL/P3O ESS unit, then compare plan quality to Paper2Manim and Code2Video. |
| 2 | Add a paper-code grounding layer for FeynRL/P3O: bind the ratio, ESS, capping, and behavioral KL formulas to concrete files/functions in `external/FeynRL`. |
| 3 | Replace freeform Manim codegen with a stable Scene IR plus deterministic render templates for formula panels, code panels, toy examples, and comparison tables. |
| 4 | Run a full-section Code2Video pass with feedback enabled after the Scene IR exists, so VLM feedback edits structured scenes instead of regenerating arbitrary code. |
| 5 | Expand RoPE into a video series: absolute embeddings, sinusoidal baseline, relative bias, 2D rotation, relative dot-product identity, multi-frequency implementation. |
| 6 | Add a learner eval layer: generated quiz, expected misconceptions, code-trace questions, and VLM/LLM grading of whether the rendered video actually answers them. |

## Code2Video Upstream Runs

Status: completed real Code2Video runs for Transformers, FeynRL, and RoPE on Babel using WInE for the LLM calls and Manim for rendering.

These are still "knowledge point to video" runs, not full "paper plus code repo to grounded explainer" runs. The input is a compact topic string; Code2Video does not read the paper PDF, FeynRL source tree, or paper experiment tables.

Naming note: the main FeynRL result below refers to the local FeynRL/P3O spec already in this repo: policy-ratio staleness, normalized ESS, ratio capping, and behavioral KL. An earlier exploratory Code2Video run used a symbolic-regression interpretation of "FeynRL"; that artifact is kept under `runs/reproductions/code2video_feynrl/` but excluded from the main comparison because it does not match the current repo/spec.

| Item | Value |
|---|---|
| Babel source repo | `$HOME/4blue2brown_explore/repo/external/Code2Video-main` |
| Babel env | `$HOME/4blue2brown_explore/envs/paper2manim` |
| Runner | `tools/run_code2video_wine.py` |
| Model | `wine-claude-haiku-4-5` |
| Feedback/assets | Disabled for this pass: `use_feedback=false`, `use_assets=false` |
| Sections rendered | First 4 generated sections per topic |
| Evaluation | `tools/probe_rendered_videos.py` plus WInE/Gemini contact-sheet review |

Compatibility patches added:

| Patch | Why it was needed |
|---|---|
| `external/Code2Video-main/src/gpt_request.py` reads `CLAUDE_MODEL`. | Upstream hard-coded `claude-4-opus`; WInE uses gateway model names. |
| `external/Code2Video-main/src/agent.py` passes `self.API` into `ScopeRefineFixer`. | Upstream referenced an undefined local variable `api`, so any real run crashed before generation. |
| `external/Code2Video-main/prompts/stage3.py` adds no-LaTeX and compatibility constraints. | Babel Manim environment is reliable without TeX; generated `Tex`/`MathTex` is a common render failure. |
| `tools/run_code2video_wine.py` creates `src/json_files` and `src/assets` links, injects WInE env vars, runs sections serially, trims to N sections, and writes `run_summary.json`. | Upstream assumes asset folders under `src/`, and the stock CLI is less convenient for controlled paper comparisons. |
| Installed `psutil` into the Babel env and ran from the repo directory. | Code2Video imports `psutil`; running from `$HOME` also hit a local `random.py` that shadows Python's stdlib. |

Run commands:

```bash
python tools/run_code2video_wine.py \
  --knowledge-point "<topic>" \
  --folder-prefix REPRO-<paper> \
  --max-sections 4 \
  --max-code-token-length 7000 \
  --max-fix-bug-tries 3 \
  --max-regenerate-tries 2
```

Generated videos and probes:

| Topic | Success | Tokens | Duration | VLM score | Video | Contact sheet |
|---|---:|---:|---:|---:|---|---|
| Transformers | 4/4 | 31,154 | 118.06s | 2/5 | `runs/reproductions/code2video_transformer/transformer_run/Attention_Is_All_You_Need_Transformer_self-attention_computes_query-key_dot-product_weights_to_mix_value_vectors_multi-head_attention_learns_different_relations_and_positional_encoding_replaces_recurrence.mp4` | `runs/reproductions/code2video_transformer/probe/contact_sheets/Attention_Is_All_You_Need_Transformer_self-attention_computes_query-key_dot-product_weights_to_mix_value_vectors_multi-head_attention_learns_different_relations_and_positional_encoding_replaces_recurrence.png` |
| FeynRL/P3O | 4/4 | 33,424 | 133.60s | 2/5 | `runs/reproductions/code2video_feynrl_p3o/feynrl_p3o_run/FeynRL_P3O_adaptive_policy_optimization_for_RL_post-training_policy-ratio_staleness_in_replay_data_normalized_effective_sample_size_ESS_detects_stale_batches_and_P3O_uses_ESS_to_cap_score-function_ratios_and_add_behavioral_KL.mp4` | `runs/reproductions/code2video_feynrl_p3o/probe/contact_sheets/FeynRL_P3O_adaptive_policy_optimization_for_RL_post-training_policy-ratio_staleness_in_replay_data_normalized_effective_sample_size_ESS_detects_stale_batches_and_P3O_uses_ESS_to_cap_score-function_ratios_and_add_behavioral_KL.png` |
| RoPE | 4/4 | 26,852 | 49.33s | 3/5 | `runs/reproductions/code2video_rope/rope_run/Rotary_Position_Embedding_RoPE_why_rotating_queries_and_keys_makes_transformer_attention_depend_on_relative_token_distance.mp4` | `runs/reproductions/code2video_rope/probe/contact_sheets/Rotary_Position_Embedding_RoPE_why_rotating_queries_and_keys_makes_transformer_attention_depend_on_relative_token_distance.png` |

Observed render behavior:

| Topic | Render notes |
|---|---|
| Transformers | Rendered all four sections. Section 2 needed one code-fix pass. Section 3 failed repeated fixes and succeeded only after a regenerated code attempt. |
| FeynRL/P3O | Rendered all four sections. Sections 3 and 4 each needed one code-fix pass. |
| RoPE | Rendered all four sections. Sections 1 and 4 each needed one debug/fix attempt. |

Quality read:

| Topic | What works | What fails |
|---|---|---|
| Transformers | The section structure is sensible: recurrence bottleneck, Q/K/V, attention weights, value mixing. The visible frames include a token relation graph and value-mixing bars. | Because the quick run only kept four sections, it omits multi-head and positional encoding despite the stated topic. Text is tiny and section 3 visuals are abstract. VLM reviewer: "lacks visual clarity and completeness." |
| FeynRL/P3O | Covers the right paper concepts: replay staleness, new/old policy ratios, normalized ESS, and ratio capping. | It shows definitions but does not make the mechanics teachable. The ESS formula is too small, the stale-batch numbers are isolated, and the clipping diagram lacks context. VLM reviewer: "covers key concepts but is visually sparse and lacks sufficient detail." |
| RoPE | Best of the three for the retained sections: standard attention problem, rotation prerequisite, position as angle, relative-distance cancellation. | Still too text-heavy and does not visibly animate the actual query/key rotation and dot-product projection. VLM reviewer asks to animate vector rotations and show the dot product as projection/angle. |

Takeaway:

Code2Video is useful as a section planner and Manim-code generator, but it is not yet a paper-with-code explainer. It can make a renderable long-ish video from a topic string after small patches, but the result is mostly "lecture bullets plus sparse visuals." For our in-house pipeline, Code2Video's most reusable pieces are the staged outline/storyboard/code/debug loop and its idea of a multimodal critic. We still need our own paper-code grounding layer, formula extraction, code-variable mapping, toy examples, layout constraints, and a rerender loop that modifies a stable Scene IR rather than asking the model to freestyle full Manim code each time.

## Paper2Manim RoPE Upstream Run

Status: completed a real Paper2Manim MVP1 run for the RoPE relative-position identity subsection, then added a small fanout/repair harness to render the full storyboard.

| Item | Value |
|---|---|
| Babel source repo | `$HOME/4blue2brown_explore/repo/external/Paper2Manim-main` |
| Babel env | `$HOME/4blue2brown_explore/envs/paper2manim` |
| Run id | `20260707-192411-6500a3` |
| Input prompt | `experiments/reproductions/inputs/rope_relative_dot_product_paper2manim.txt` |
| Original MVP1 output | `runs/reproductions/paper2manim_rope/20260707-192411-6500a3/final/output.mp4` |
| Full fanout + repaired output | `runs/reproductions/paper2manim_rope/20260707-192411-6500a3/final/output_fanout_repaired.mp4` |
| Probe report | `runs/reproductions/paper2manim_rope/20260707-192411-6500a3/probe/probe_report.md` |
| Contact sheet | `runs/reproductions/paper2manim_rope/20260707-192411-6500a3/probe/contact_sheets/output_fanout_repaired.png` |

Environment fixes needed on Babel:

| Fix | Why it was needed |
|---|---|
| Created conda env with Python 3.12, `pango`, `cairo`, `pkg-config`, and `ffmpeg`. | Paper2Manim requires Python >=3.11,<3.13 and Manim 0.20.1. Pip build of `manimpango` needs Pango/Cairo system libraries. |
| Added `runs/reproductions/paper2manim_env/expat.pc` into the conda env pkg-config path. | Conda had `libexpat.so` but no `expat.pc`; `fontconfig`'s pkg-config chain failed without it. |
| Copied `glibconfig.h` from conda package cache into the env include path. | `manimpango` compilation found `glib.h` but not `glibconfig.h`. |
| Wrote Babel-only `.env` from `$HOME/.secrets/wine_litellm_api_key.txt`, selecting the `sk-` LiteLLM key. | The first parser picked a Google-style `AIza...` key and WInE rejected it. |

What happened:

1. Paper2Manim `mvp1` successfully generated a 6-scene storyboard for RoPE:
   `TitleScene`, `AbsoluteVsRelativeSetup`, `RoPEIntroduction`, `RotationMathIdentity`, `RelativeDistanceHighlight`, `ComparisonSummary`.
2. Upstream MVP1 rendered only scene index 0, producing a title-only `final/output.mp4`.
3. Added `tools/run_paper2manim_storyboard_fanout.py` to reuse upstream `coder_node` and render every storyboard scene.
4. Fanout rendered 5/6 scenes automatically. The common failure was generated `MathTex`/`Tex` despite the input explicitly requesting no LaTeX.
5. Added `tools/repair_paper2manim_fanout_scene.py` plus a deterministic no-LaTeX `RoPEIntroduction_repaired.py`; merged it into `output_fanout_repaired.mp4`.

Rendered video probe:

| Metric | Value |
|---|---|
| Duration | 59.73s |
| Resolution | 854x480 |
| FPS | 15 |
| Size | 713,871 bytes |
| Probe frames | Non-empty sampled frames; black background makes brightness low but expected. |

Quality read:

| Dimension | Comment |
|---|---|
| Storyboard | Good high-level decomposition of the RoPE subsection. It covers absolute vs relative setup, Q/K rotation, relative dot-product identity, relative-distance highlight, and comparison summary. |
| Render robustness | Better after fanout + one deterministic repair. Upstream retry repaired several LaTeX failures by switching to `Text`, but not all. |
| Visual quality | Usable as a reproduction artifact, weak as education. Text is too small in places, formulas are plain text, and pacing is mostly sequential writing rather than explanatory motion. |
| Main gap | Paper2Manim plans sensible scenes, but lacks hard code constraints, layout/readability checks, and an automatic no-LaTeX/code-normalization pass for environments without TeX. |

## TheoremExplainAgent RoPE Upstream Plan Run

Status: completed a real upstream TEA `generate_video.py --only_plan` run for the RoPE relative-position dot-product theorem. This is not a rendered video yet.

| Item | Value |
|---|---|
| Local source repo | `external/TheoremExplainAgent-main` |
| Babel source repo | `$HOME/4blue2brown_explore/repo/external/TheoremExplainAgent-main` |
| Babel env | `$HOME/4blue2brown_explore/envs/paper2manim` |
| Runner | `tools/run_tea_wine_plan.py` |
| Model | `openai/wine-claude-haiku-4-5` through WInE/LiteLLM |
| Local output | `runs/reproductions/tea_rope_plan_wine/` |
| Main outline | `runs/reproductions/tea_rope_plan_wine/rope_relative_position_dot_product_theorem/rope_relative_position_dot_product_theorem_scene_outline.txt` |

Compatibility patches added:

| Patch | Why it was needed |
|---|---|
| Added WInE model names to `external/TheoremExplainAgent-main/src/utils/allowed_models.json`. | TEA validates model names before calling LiteLLM. |
| Wrapped `completion_cost(...)` in `external/TheoremExplainAgent-main/mllm_tools/litellm.py`. | LiteLLM could complete WInE calls, but cost lookup failed because WInE model names are not mapped. |
| Added `tools/run_tea_wine_plan.py`. | Keeps TEA's own planner while supplying WInE secrets/base URL and running `--only_plan`. |

Run result:

| Metric | Value |
|---|---|
| Outline scenes claimed | 7 |
| Implementation plans generated | 6 |
| Generated scene dirs | `scene1`, `scene3`, `scene4`, `scene5`, `scene6`, `scene7` |
| Missing scene | `scene2` |
| Immediate cause | The outline opens `<SCENE_2>` but closes it as `</SCENE_3>`, so TEA's scene parser skips scene 2. |

Scene outline:

| Scene | TEA title | Status |
|---:|---|---|
| 1 | Attention Mechanism & Position Problem | Plan generated |
| 2 | 2D Rotation Fundamentals | Missing due malformed closing tag |
| 3 | Rotating Query and Key Separately | Plan generated |
| 4 | RoPE Theorem Statement & Proof Sketch | Plan generated |
| 5 | Relative Position Encoding in Transformers | Plan generated |
| 6 | Generalization & Frequency Dimensions | Plan generated |
| 7 | Summary & Key Takeaways | Plan generated |

Quality read:

| Dimension | Comment |
|---|---|
| Planning depth | Strong. TEA produces detailed scene goals, sub-scenes, pacing, object choices, layout bands, and implementation notes. It is much richer than the quick Code2Video lecture bullets. |
| Formula pedagogy | Good for theorem-like content. The RoPE identity is decomposed through attention motivation, 2D rotation intuition, position-dependent rotations, proof sketch, transformer pipeline, and multi-frequency extension. |
| Robustness | Weak structured-output guarantees. One malformed closing tag caused an entire scene to disappear from downstream generation. |
| Render risk | High unless constrained. Plans heavily mention `Tex`/`MathTex`, which is fragile in no-LaTeX environments and can lead to unreadable formula walls. |
| Gap for our goal | TEA is useful as a theorem planner, but it does not ground claims to a paper repo, experiment table, or code variables. It still needs parser validation, no-LaTeX/code constraints, and a render/eval loop. |

## ManimTrainer Release Audit And API-Mode Run

Status: official repo found, cloned locally and on Babel, and a method-level API-mode RITL-DOC reproduction was rendered for RoPE.

Sources checked:

| Source | What it says |
|---|---|
| [arXiv:2604.18364](https://arxiv.org/abs/2604.18364) | Introduces ManimTrainer, an SFT + GRPO training pipeline, and ManimAgent, an inference pipeline with RITL/RITL-DOC. Reports best Qwen 3 Coder 30B + GRPO + RITL-DOC at 94% render success and 85.7% visual similarity. |
| [Official GitHub: SuienS/manim-trainer](https://github.com/SuienS/manim-trainer) | Releases training/evaluation/inference code, ManimBench-format data files, and two SeedCoder 8B LoRA adapter folders. |

What is actually released:

| Artifact | Local path | Notes |
|---|---|---|
| Source code | `external/manim-trainer/src/` | Training, evaluation, inference, RAG/API-doc inspection, renderer wrapper. |
| CLI entry | `external/manim-trainer/manim_trainer.py` | Typer CLI for training, evaluation, and local model inference. |
| Dataset files | `external/manim-trainer/data/*.parquet`, `*.xlsx` | ManimBench-derived SFT train/test/all data. |
| SFT adapter | `external/manim-trainer/output/trained_models_v2/Seed_Coder_8B_Instruct_unsloth_bnb_4bit_lora_r8_sft_20251211_002632_final/adapter_model.safetensors` | 80MB LoRA adapter. |
| SFT+GRPO adapter | `external/manim-trainer/output/trained_models_v2/Seed_Coder_8B_Instruct_unsloth_bnb_4bit_lora_r8_sft_grpo_rw_mean_text_visual_20251211_002632_final/adapter_model.safetensors` | 80MB LoRA adapter plus trainer state files. |
| Strongest reported checkpoint | Not found in repo | Paper reports Qwen 3 Coder 30B + GRPO + RITL-DOC as best, but repo currently says additional adapters will be made available upon publication. |

Official adapter inference status:

| Check | Result |
|---|---|
| Repo cloned locally | Yes, `external/manim-trainer`, about 417MB apparent size. |
| Repo cloned on Babel | Yes, `$HOME/4blue2brown_explore/repo/external/manim-trainer`. |
| Existing Babel `paper2manim` env can launch official CLI | No. It lacks `typer`, `torch`, `transformers`, `peft`, `pandas`, `pyarrow`; the official CLI also imports `unsloth` for inference. |
| GPU check on current Babel shell | `nvidia-smi` not available from this shell. |
| Conclusion | Official local SeedCoder adapter inference is not impossible, but it needs a separate GPU/Unsloth/HF environment. I did not install that heavy stack into the shared Paper2Manim env. |

API-mode reproduction:

| Item | Value |
|---|---|
| Runner | `tools/run_manimtrainer_api_reproduction.py` |
| Method reproduced | ManimTrainer/ManimAgent prompt format plus generate -> render -> RITL-DOC feedback loop |
| Model | `wine-claude-haiku-4-5` |
| Prompt | RoPE: show `q`, `k`, position rotations, identity `<R_m q, R_n k> = <q, R_(n-m) k>`, and a numerical example with `m=2`, `n=5`, `alpha=30 degrees`; avoid LaTeX. |
| Local output | `runs/reproductions/manimtrainer_rope_api/` |
| Final video | `runs/reproductions/manimtrainer_rope_api/render_1783551706.mp4` |
| Contact sheet | `runs/reproductions/manimtrainer_rope_api/probe/contact_sheets/render_1783551706.png` |

Run behavior:

| Round | Mode | Result |
|---:|---|---|
| 0 | Initial codegen | Failed final success check after partial rendering. |
| 1 | RITL-DOC feedback | Succeeded and rendered `render_1783551706.mp4`. |

Probe:

| Metric | Value |
|---|---|
| Duration | 48.93s |
| Resolution | 854x480 |
| FPS | 15 |
| Size | 551,343 bytes |
| Probe frames | Non-empty sampled frames; black background makes brightness low but expected. |

Quality read:

| Dimension | Comment |
|---|---|
| What works | Concrete vector animation, position-dependent rotations, formula reveal, and numeric equality check. This is closer to "formula plus example" than the Code2Video RoPE run. |
| What is weak | It is a single concept clip, not a paper explanation. The formula is rendered as plain `Text`, not high-quality math, and the contact sheet suggests sparse frames and some mid-write formula readability issues. |
| Repro honesty | This is a method-level reproduction, not a checkpoint reproduction. It validates the RITL-DOC loop idea using WInE, but does not measure the released SeedCoder SFT vs SFT+GRPO adapters. |
| Useful pieces for us | RITL/RITL-DOC is valuable: render errors and API docs can repair generated Manim without training. The reward/eval idea, especially visual similarity plus render success, is also reusable. |

## LLM2Manim Release Audit And Method Reproduction

Status: no canonical runnable repo found in this pass. Because the paper's pipeline is well specified, I added a local method-level reproduction and marked it as `LLM2Manim-inspired` rather than an official run.

Sources checked:

| Source | What it says |
|---|---|
| [arXiv:2604.05266](https://arxiv.org/abs/2604.05266) | Presents a human-in-the-loop pipeline for narrated STEM Manim animations. It emphasizes constrained prompt templates, a symbol ledger, partial regeneration, expert review, segmentation, signaling, and dual coding. |

What appears to be released:

| Artifact type | Status |
|---|---|
| Paper/method | Released on arXiv. |
| Official GitHub repo | Not found through exact-title/GitHub search in this pass. |
| Open checkpoint | Not applicable / not found. |
| Evaluation result | Paper reports an undergraduate A/B study: animation-based instruction had higher post-test scores, higher learning gains/engagement, lower cognitive load, and higher satisfaction than slide modules. |

Local method reproduction:

| Item | Value |
|---|---|
| Scene source | `scenes/llm2manim_inspired_suite.py` |
| Runner | `tools/run_llm2manim_inspired_suite.py` |
| Output root | `runs/reproductions/llm2manim_inspired/` |
| Site assets updated | `progress_site/assets/baseline-coverage/videos/llm2manim__*.mp4` |
| Renderer | Local Manim 0.19.0, no API calls |
| Label | `method-level reproduction; not an official LLM2Manim repo/checkpoint run` |

What the local reproduction implements from the paper:

| LLM2Manim idea | Local implementation |
|---|---|
| Segmentation | Each video is split into vocabulary, formula/visual, review, and final-contract segments. |
| Symbol ledger | Each topic starts by locking down the symbols the learner will see. |
| Constrained templates | Formula panels and visual panels use fixed layouts rather than freeform full-scene generation. |
| Partial regeneration | Each clip includes an explicit "regenerate this segment only" checkpoint. |
| Human/expert review | Each clip surfaces one misconception/review gate before final render. |

Rendered outputs:

| Topic | Video | Duration | Probe |
|---|---|---:|---|
| FeynRL/P3O | `runs/reproductions/llm2manim_inspired/feynrl/llm2manim__feynrl.mp4` | 20.47s | non-empty, 854x480, 15fps |
| DPO | `runs/reproductions/llm2manim_inspired/dpo/llm2manim__dpo.mp4` | 20.47s | non-empty, 854x480, 15fps |
| Attention | `runs/reproductions/llm2manim_inspired/attention/llm2manim__attention.mp4` | 20.47s | non-empty, 854x480, 15fps |
| Transformers | `runs/reproductions/llm2manim_inspired/transformers/llm2manim__transformers.mp4` | 20.47s | non-empty, 854x480, 15fps |
| RoPE | `runs/reproductions/llm2manim_inspired/rope/llm2manim__rope.mp4` | 20.47s | non-empty, 854x480, 15fps |

Quality takeaway:

LLM2Manim is less useful for official code reproduction than Paper2Manim, Code2Video, TEA, or ManimTrainer because there is no concrete repo to run. It is very useful as a product/eval design reference: learner-facing segmentation, narration synchronization, symbol consistency, expert review, and human learning metrics. The local reproduction makes those constraints visible in actual videos, but it is still a structured template implementation, not an LLM-generated official baseline.
