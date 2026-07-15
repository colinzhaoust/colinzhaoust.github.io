# Experiment: TheoremExplainAgent on FeynRL/P3O

Date: 2026-07-04

Goal: try the official TheoremExplainAgent repo and evaluate whether its generated explanation would help us understand the FeynRL paper/repo, especially the P3O / batch-adaptive ESS mechanism.

Sources:

- TheoremExplainAgent project page: https://tiger-ai-lab.github.io/TheoremExplainAgent/
- TheoremExplainAgent GitHub: https://github.com/TIGER-AI-Lab/TheoremExplainAgent
- TheoremExplainAgent arXiv: https://arxiv.org/abs/2502.19400
- FeynRL GitHub: https://github.com/FeynRL-project/FeynRL
- FeynRL paper: https://arxiv.org/abs/2605.12380

## Status

Partial reproduction only.

What succeeded:

- Located the official repo.
- Downloaded source via GitHub zip into:
  - `external/TheoremExplainAgent-main`
- Confirmed repo architecture and entrypoints.
- Confirmed generation CLI and model/API requirements.
- Prepared a FeynRL input file compatible with TEA's batch format:
  - `data/tea_feynrl_p3o_topic.json`

What did not fully run yet:

- Full TEA generation did not run because the current shell has no model API key:
  - `OPENAI_API_KEY=not-set`
  - `GEMINI_API_KEY=not-set`
  - `AZURE_API_KEY=not-set`
- The repo asks for Python 3.12.8; this machine currently has no `python3.12` executable.
- A direct `python3 generate_video.py --help` failed immediately because system Python lacks `PIL`.
- Running with the existing Manim venv got one step further but failed on missing `python-dotenv`.
- Installing the full dependency stack is nontrivial: it includes Manim, manim-voiceover, Kokoro TTS, PyAudio/portaudio, Manim plugins, LiteLLM, ChromaDB, Transformers, and optional cloud providers.

Network note:

- `git clone https://github.com/TIGER-AI-Lab/TheoremExplainAgent.git ...` started but stalled/disconnected.
- The zip download succeeded:
  - `curl -L -o external/TheoremExplainAgent-main.zip https://github.com/TIGER-AI-Lab/TheoremExplainAgent/archive/refs/heads/main.zip`

## TEA architecture observed from source

The repo is organized as a sequential agent pipeline:

```text
topic + context
-> VideoPlanner.generate_scene_outline
-> VideoPlanner._generate_scene_implementation_single
   -> vision/storyboard plan
   -> technical implementation plan
   -> animation/narration plan
-> CodeGenerator.generate_manim_code
-> VideoRenderer.render_scene
-> error-fix loop
-> optional visual-fix loop
-> combine_videos
```

Important files:

- `generate_video.py`: CLI and orchestration.
- `src/core/video_planner.py`: scene outline and scene implementation generation.
- `src/core/code_generator.py`: Manim code generation and fix prompts.
- `src/core/video_renderer.py`: calls Manim and combines outputs.
- `task_generator/prompts_raw/prompt_scene_plan.txt`: high-level scene outline prompt.
- `task_generator/prompts_raw/prompt_scene_implementation.txt`: detailed implementation plan prompt.
- `task_generator/prompts_raw/prompt_code_generation.txt`: Manim code prompt.

The project page says TEA uses a two-agent architecture: a planner creates story plans/narration, and a coding agent generates Manim scripts. It evaluates accuracy/depth, logical flow, visual relevance, element layout, and visual consistency.

## Reproduction commands

### Minimal environment, official-ish path

The README recommends Conda:

```bash
cd external/TheoremExplainAgent-main
conda create --name tea python=3.12.8
conda activate tea
pip install -r requirements.txt
```

Then install TTS assets:

```bash
mkdir -p models
curl -L -o models/kokoro-v0_19.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
curl -L -o models/voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin
```

Then create `.env` from `.env.template` and fill at least one model provider key:

```bash
cp .env.template .env
```

Required for OpenAI run:

```bash
OPENAI_API_KEY="..."
```

Required for Gemini run:

```bash
GEMINI_API_KEY="..."
```

Set Python path:

```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### FeynRL planning-only run

This should be the first run once Python 3.12 and a key exist:

```bash
cd external/TheoremExplainAgent-main
export PYTHONPATH=$(pwd):$PYTHONPATH
python generate_video.py \
  --model "openai/o3-mini" \
  --helper_model "openai/o3-mini" \
  --output_dir "../../runs/tea_feynrl" \
  --theorems_path "../../data/tea_feynrl_p3o_topic.json" \
  --only_plan \
  --max_scene_concurrency 1 \
  --max_topic_concurrency 1
```

Planning-only is the right first checkpoint because it costs less than full render and lets us review whether the agent actually teaches the paper.

### Full FeynRL video run

Only run this after the outline and implementation plans look sane:

```bash
cd external/TheoremExplainAgent-main
export PYTHONPATH=$(pwd):$PYTHONPATH
python generate_video.py \
  --model "openai/o3-mini" \
  --helper_model "openai/o3-mini" \
  --output_dir "../../runs/tea_feynrl" \
  --theorems_path "../../data/tea_feynrl_p3o_topic.json" \
  --max_retries 3 \
  --max_scene_concurrency 1 \
  --max_topic_concurrency 1
```

Avoid `--use_visual_fix_code` for the first run. Static source inspection found a likely bug: `VideoRenderer.render_scene` references `self.scene_model`, but `VideoRenderer.__init__` does not set `self.scene_model`. This path appears reachable only when visual fixing is enabled.

## What TEA is likely to do well

The repo is better than a one-shot "write a Manim script" prompt because it separates:

- scene outline;
- visual/storyboard plan;
- technical implementation plan;
- narration plan;
- code generation;
- render-error repair.

For FeynRL, that means TEA may produce a coherent 3-7 scene explanation with:

- a policy update loop;
- a policy-ratio distribution;
- ESS formula;
- off-policy/staleness visual;
- method comparison;
- a final summary.

It should be good at creating a "presentation-shaped" explanation.

## What TEA is likely to miss on FeynRL

Unmodified TEA is theorem/topic oriented, not paper+repo grounded. Expected weak points:

1. **No source-code grounding**
   - It will not naturally inspect `algs/P3O/p3o.py`.
   - It may mention code generally without showing exact implementation anchors.

2. **No real trace/data grounding**
   - It will likely use generic conceptual diagrams rather than real or synthetic ratio batches.
   - For FeynRL, this is a big loss because ESS only becomes intuitive from numbers or histograms.

3. **May flatten the method**
   - It may say "ESS controls update trust" without explaining the two separate concerns:
     - trust-region movement;
     - off-policy reliability.

4. **May not contrast related methods enough**
   - A good FeynRL video must explain why fixed clipping in PPO/GRPO is different from an ESS-adaptive cap and behavioral KL.

5. **Could hallucinate algorithm details**
   - The paper is new and outside TEA's benchmark domain.
   - Without explicit context, it may invent a theorem-like statement or overclaim empirical findings.

6. **Likely good-looking but not enough to teach**
   - The default prompt forbids quizzes.
   - It does not model "what Colin already understands" or "what confusion remains."

## Quality rubric for evaluating generated FeynRL output

Use a 1-5 score for each dimension.

| Dimension | 1 means | 5 means |
|---|---|---|
| Paper accuracy | vague or wrong summary | matches paper abstract and central claim |
| Mechanism clarity | terms appear without causal story | explains policy ratio -> ESS -> cap/KL behavior |
| Toy example | no concrete numbers | uses a tiny ratio batch and computes ESS intuition |
| Code grounding | no repo references | maps formula to `old_logprobs`, `ratio`, `calculate_ess`, `compute_policy_loss` |
| Comparison | no baselines | clearly contrasts PPO/GRPO, CISPO, P3O |
| Visual relevance | decorative boxes | visuals show the mechanism changing |
| Layout/readability | overlap/tiny text | readable frames, no clutter, clean pacing |
| Learner usefulness | recap for experts | helps a first-time reader predict behavior |

Minimum acceptable first-pass score:

- total >= 28/40;
- no score below 3 for paper accuracy, mechanism clarity, or toy example.

## Desired TEA output outline for FeynRL

This is the target outline we should compare against TEA's actual plan.

```xml
<SCENE_OUTLINE>
  <SCENE_1>
  Scene Title: Policy Drift
  Scene Purpose: Show why RL post-training is harder than supervised learning: the policy changes the data distribution it learns from.
  Scene Description: Start with a policy generating samples, rewards/logprobs being stored, and a later policy update using old samples. Show that the same token can become more or less likely as the policy changes.
  Scene Layout: Left-to-right loop with policy, rollout, reward, replay buffer, and train update. Keep a small token table on the right.
  </SCENE_1>

  <SCENE_2>
  Scene Title: Ratio Signals
  Scene Purpose: Introduce policy ratios as the visible trace of data freshness or staleness.
  Scene Description: Use five tokens with old and new probabilities. Compute ratios and show uniform ratios versus one extreme ratio.
  Scene Layout: Top table for probabilities and ratios, bottom bar chart for ratio magnitudes.
  </SCENE_2>

  <SCENE_3>
  Scene Title: ESS Intuition
  Scene Purpose: Explain normalized effective sample size as a batch reliability statistic.
  Scene Description: Animate ESS formula. Show that equal weights produce high ESS while concentrated weights produce low ESS.
  Scene Layout: Formula on left, five weight bars on right, ESS gauge below.
  </SCENE_3>

  <SCENE_4>
  Scene Title: Adaptive Objective
  Scene Purpose: Explain how P3O uses ESS to cap the score-function weight and activate off-policy regularization.
  Scene Description: Connect ESS to two visual controls: cap height for score weight and KL regularizer strength.
  Scene Layout: Center formula decomposed into two colored branches: score term and behavioral KL term.
  </SCENE_4>

  <SCENE_5>
  Scene Title: Code Anchor
  Scene Purpose: Map the paper mechanism to FeynRL implementation.
  Scene Description: Highlight old_logprobs, ratio, calculate_ess, rho/clamp, and loss composition in `algs/P3O/p3o.py`.
  Scene Layout: Formula on left, code snippet on right, arrows between formula symbols and code variables.
  </SCENE_5>

  <SCENE_6>
  Scene Title: Why It Matters
  Scene Purpose: Compare P3O with fixed clipping under sync and async replay conditions.
  Scene Description: Show PPO/GRPO fixed clip, CISPO detached clipped weight, and P3O adaptive ESS behavior as ratio spread increases.
  Scene Layout: Method curves on left, sync/async timeline on right, final takeaway at bottom.
  </SCENE_6>
</SCENE_OUTLINE>
```

## Recommendation

Do not use TEA unmodified as the final 4blue2brown pipeline. Use it as a reference implementation for:

- staged planning;
- scene implementation specs;
- Manim code generation;
- render/fix loop;
- multimodal evaluation dimensions.

For our FeynRL use case, add three missing layers before calling a TEA-like generator:

1. **Paper/repo grounding**
   - force every scene to cite paper sections/equations and code files/functions.

2. **Toy/data example grounding**
   - generate a tiny numeric example before full formulas.

3. **Learner-centered eval**
   - add a quiz/teach-back loop, even though TEA's default prompt says not to include quiz sessions.

The most useful next experiment is a planning-only TEA run on `data/tea_feynrl_p3o_topic.json` once we have Python 3.12 and an API key. If the generated scene outline skips the five-token ratio/ESS toy example, it will likely fail our "educate me on this paper" objective even if the final Manim video renders successfully.
