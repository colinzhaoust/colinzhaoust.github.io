# FeynRL Visualization Audit

Snapshot date: 2026-07-02.

- Repo: <https://github.com/FeynRL-project/FeynRL>
- Paper cited by repo: <https://arxiv.org/abs/2605.12380>
- Local clone: `external/FeynRL` at commit `dfe8535`
- Babel clone: `$HOME/repos/FeynRL` at commit `dfe8535`

## Executive Read

FeynRL is not a video or Manim repository. It is an algorithm-first post-training framework for LLMs and VLMs. Its useful material for `4blue2brown` is therefore not a renderer; it is a clean collection of algorithm implementations, formulas, pseudocode, configs, tests, and system architecture that can be turned into explanatory visuals.

The repo README cites the 2026 paper "Trust the Batch, On- or Off-Policy: Adaptive Policy Optimization for RL Post-Training." In the codebase, the main batch-adaptive / ESS-based mechanism is exposed through `algs/P3O`, with `algs/P4O` as an additional experimental ESS/mixed-anchor variant. I did not find a separate `APO` module name.

## What We Can Reuse Directly

| Source area | Reusable for visualization? | Why |
|---|---|---|
| `algs/*/README.md` | High | These files already contain formulas, algorithm boxes, implementation notes, and references for PPO, GRPO, CISPO, P3O, DPO, SFT. |
| `algs/P3O/p3o.py` | High for toy math; low for direct runtime reuse | `calculate_ess` and `compute_policy_loss` encode the paper-relevant idea: policy ratios -> normalized ESS -> score cap plus adaptive behavioral KL. The class itself is a Ray actor, so direct import as a normal object is awkward. |
| `algs/P4O/p4o.py` | Medium | Similar ESS machinery plus a behavior/proximal mixture trust region. Useful for explaining extensions, less central as a first explainer. |
| `algs/GRPO/grpo.py`, `algs/PPO/ppo.py`, `algs/CISPO/cispo.py` | High | Good baselines for contrasting fixed clipping, decoupled loss, and detached clipped-ratio weighting. |
| `algs/RL/common.py` | High | Shared KL estimator, global-token normalization, proximal-policy snapshot logic, health checks. |
| `run_rl_sync.py`, `run_rl_async.py`, `core/rl_engines.py` | Medium-high | Good source for system diagrams: sync rollout/train/sync loop vs async overlap with bounded replay and weight sync. |
| `rollouts/replay_buffer.py` | Medium | Useful for visualizing staleness, policy versions, FIFO/age eviction, and mixed replay. |
| `unit_tests/unit/*_loss.py` | High | Tests show how to call algorithm methods with `SimpleNamespace` without initializing full model/Ray state. Good seed for a pure explainer harness. |
| `examples/` | Medium | Includes configs and reward curves. Useful as empirical context, not enough for detailed per-token method animation. |

## What The Existing Source Can Illustrate

| Explanation target | Can use FeynRL source as-is? | Comment |
|---|---|---|
| P3O / batch-adaptive objective math | Mostly yes | Use formulas from README and code from `calculate_ess` / `compute_policy_loss`. Best shown with synthetic policy-ratio batches. |
| PPO / GRPO fixed clipping | Yes | `compute_policy_loss` and README explain ratio clipping and `clipfrac`. |
| CISPO vs PPO/GRPO | Yes | Very visual: PPO/GRPO can zero gradients past clip boundary; CISPO keeps gradient through `log pi` with detached clipped weight. |
| DPO/SFT loss normalization | Yes | Good for formula/gradient-accumulation explainers; less central to the paper. |
| Sync vs async FeynRL system | Yes for diagrams | Code makes the architecture explicit, especially `run_rl_sync.py`, `run_rl_async.py`, replay buffer, and weight sync. |
| Real training dynamics | Not without running jobs | Need GPUs, models, datasets, and logs. The repo has examples, but no ready trace dataset with ratio histograms/ESS over time. |
| Manim/3Blue1Brown-style animation | No | There is no Manim adapter, storyboard, visual IR, or educational scene renderer in FeynRL. |

## Prototype Tool Added Here

I added a small pure-Python SVG generator:

```bash
python3 tools/feynrl_method_viz.py
```

It writes:

| Generated asset | Purpose |
|---|---|
| `renders/feynrl_method_viz/ratio_distributions_ess.svg` | Shows how fresh vs stale policy-ratio distributions change normalized ESS. |
| `renders/feynrl_method_viz/objective_weight_curves.svg` | Compares PPO/GRPO fixed clipping, CISPO detached clipped weights, and P3O ESS caps. |
| `renders/feynrl_method_viz/p3o_ess_tradeoff.svg` | Shows the core P3O idea: score cap = ESS, behavioral KL weight = `1 - ESS`. |
| `renders/feynrl_method_viz/sync_vs_async_timeline.svg` | Shows sync vs overlap scheduling and why async creates staleness. |

This tool deliberately avoids Ray, DeepSpeed, vLLM, Torch, and Manim. It is a cheap bridge from paper/code formulas to visual assets.

## Gaps In FeynRL For Our Use Case

The biggest blocker is not understanding the method; it is extracting explainable traces.

| Missing tool | Why we need it |
|---|---|
| Pure objective API | Current algorithm classes are Ray actors that initialize training state. We need importable pure functions for ESS, KL, clipping, and per-token loss components. |
| Trace exporter | Real videos need data: per-step ratio histograms, ESS, clipfrac, KL terms, replay policy-version ages, sync events, and reward curves in JSONL. |
| Toy batch simulator | Before real GPU runs, we need deterministic synthetic batches that show fresh/on-policy, mildly stale, and highly stale regimes. |
| Scene-plan IR for optimization explainers | We need a structured storyboard format: distributions, formulas, timeline events, token tables, and moving policy snapshots. |
| Manim adapter | Convert the visual IR into Manim scenes with axes, histograms, formulas, timelines, and annotations. |
| Paper-reference mapper | Map claims in the paper to repo files/functions and to visual beats. This is retrieval glue for an agentic explainer. |

## Recommended Explainer Storyboard

1. Start with the RL post-training loop: policy samples completions, rewards are computed, old logprobs are stored, policy updates.
2. Show why off-policy replay is hard: as policy changes, ratios `pi_theta / pi_old` spread out.
3. Show fixed clipping in PPO/GRPO: useful near 1, but stale high-ratio tokens can get clipped out.
4. Show CISPO: clipped ratio becomes a detached score-function weight, so gradient does not fully vanish.
5. Show P3O: compute normalized ESS from the batch; use the same scalar to cap the score-function term and activate behavioral KL.
6. Show FeynRL systems view: sync mode keeps data fresh; async mode improves throughput but needs staleness-aware objectives or decoupled losses.
7. End with why this matters for large-model post-training: the objective adapts to the batch instead of relying only on fixed clipping knobs.

## Work Plan

1. Keep `tools/feynrl_method_viz.py` as the no-dependency sanity-check visualizer.
2. Build `tools/feynrl_trace_exporter.py` or patch FeynRL with optional JSONL metric export.
3. Define a `method_scene_ir.yaml` schema for formulas, charts, policy-ratio histograms, and system timelines.
4. Generate the first Manim scene from the SVG prototype: P3O ESS tradeoff.
5. Later, run a small FeynRL config on Babel and feed real traces into the same scene generator.
