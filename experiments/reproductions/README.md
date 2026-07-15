# Reproduction Preview Suite

This directory keeps clean, tracked inputs for external-repo reproduction experiments.
Generated outputs go under `runs/reproductions/` so the repository root stays tidy.

Current goal:

1. Reproduce the *planning shape* of three external systems:
   - Paper2Manim
   - Code2Video
   - TheoremExplainAgent
2. Compare how each style explains three papers/work families:
   - Transformers
   - FeynRL / P3O
   - RoPE / RoFormer
3. Keep the expensive dependency stacks isolated until we decide which one deserves a full environment.

Important distinction:

- These previews reproduce the **input/output contracts and prompt style** of each repo.
- They are not yet full upstream executions with each repo's exact dependency environment.
- The render baseline still uses our in-house Manim harness.

Run local deterministic previews:

```bash
./.venv-arm64/bin/python tools/run_reproduction_previews.py --provider mock
```

Run WInE-backed previews from an environment with WInE credentials:

```bash
python tools/run_reproduction_previews.py \
  --provider wine \
  --model wine-claude-haiku-4-5 \
  --max-tokens 1800
```
