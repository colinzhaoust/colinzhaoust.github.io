# Babel GPU Node Notes

Snapshot date: 2026-07-08.

Login nodes do not expose `nvidia-smi`, but Slurm running nodes do. Verified from `login2`.

## Discovery

```bash
ssh babel 'hostname; command -v srun; command -v salloc; command -v sbatch; command -v sinfo; command -v nvidia-smi || true'
```

Observed:

- host: `login2`
- Slurm tools: `srun`, `salloc`, `sbatch`, `sinfo`
- `nvidia-smi`: not present on login node

GPU partitions/nodes are visible through:

```bash
ssh babel 'sinfo -o "%P %a %D %t %G %N"'
```

Partitions include `debug`, `general`, `preempt`, and `array`, with GPU types including L40, L40S, A6000, A100, H200, RTX PRO 6000, and 6000Ada.

## Verified Short GPU Probe

```bash
ssh babel 'srun -p debug \
  --gres=gpu:1 \
  --time=00:02:00 \
  --mem=8G \
  --cpus-per-task=2 \
  --job-name=codex-nvidia-smi \
  --immediate=60 \
  nvidia-smi -L'
```

Result:

```text
srun: job 9118688 queued and waiting for resources
srun: job 9118688 has been allocated resources
GPU 0: NVIDIA L40 (UUID: GPU-7d4eaab1-5d3f-efe3-debb-3972ad509575)
```

## Implication For ManimTrainer

The official ManimTrainer SeedCoder adapter path should be run inside a Slurm allocation, not on the login node. A future smoke test should look like:

```bash
ssh babel 'cd $HOME/4blue2brown_explore/repo/external/manim-trainer && \
  srun -p debug --gres=gpu:1 --time=01:00:00 --mem=48G --cpus-per-task=8 \
  <python-env>/bin/python manim_trainer.py inference run_inference \
    --selected-model "unsloth/Seed-Coder-8B-Instruct-unsloth-bnb-4bit" \
    --peft-model-path "./output/trained_models_v2/Seed_Coder_8B_Instruct_unsloth_bnb_4bit_lora_r8_sft_grpo_rw_mean_text_visual_20251211_002632_final" \
    --load-in-4bit \
    --input-prompt "Create a short Manim animation explaining RoPE in 2D."'
```

Do not install the full Unsloth/HuggingFace stack into the shared `paper2manim` env unless we decide to dedicate that env to model inference. The safer path is a separate ManimTrainer env or container.
