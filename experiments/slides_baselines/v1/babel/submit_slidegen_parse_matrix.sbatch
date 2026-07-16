#!/usr/bin/env bash
#SBATCH --job-name=slidegen-parse-matrix
#SBATCH --partition=debug
#SBATCH --array=0-3%2
#SBATCH --time=01:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715/runs/slidegen-parse-matrix/%A_%a/slurm.out
#SBATCH --error=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715/runs/slidegen-parse-matrix/%A_%a/slurm.err

set -uo pipefail
B=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715
SRC="$B/src/SlideGen"
VENV="$B/envs/slidegen-py311"
case "$SLURM_ARRAY_TASK_ID" in
  0) PAPER=transformers; INPUT="$B/inputs/transformers_1706.03762.pdf" ;;
  1) PAPER=dpo; INPUT="$B/inputs/dpo_2305.18290.pdf" ;;
  2) PAPER=feynrl; INPUT="$B/inputs/feynrl_2605.12380.pdf" ;;
  3) PAPER=rope; INPUT="$B/inputs/rope_2104.09864.pdf" ;;
  *) exit 64 ;;
esac
RUN="$B/runs/slidegen-parse-matrix/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "$RUN"
cd "$SRC"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/started_at.txt"
git rev-parse HEAD > "$RUN/revision.txt"
sha256sum "$INPUT" > "$RUN/input.sha256"
printf '%s\n' 'provider_calls=0' 'measured_provider_cost_usd=0' > "$RUN/cost.txt"

SECONDS=0
INPUT="$INPUT" OUTPUT="$RUN/$PAPER.md" "$VENV/bin/python" - <<'PY' \
  > "$RUN/parse.log" 2>&1
import os
from pathlib import Path
from docling.document_converter import DocumentConverter

result = DocumentConverter().convert(os.environ["INPUT"])
markdown = result.document.export_to_markdown()
if len(markdown.strip()) < 500:
    raise RuntimeError("parsed markdown is unexpectedly short")
Path(os.environ["OUTPUT"]).write_text(markdown, encoding="utf-8")
print(f"markdown_chars={len(markdown)}")
PY
status=$?
printf '%s\n' "$status" > "$RUN/probe.exitcode"
printf '%s\n' "$SECONDS" > "$RUN/elapsed_seconds.txt"
if [ -f "$RUN/$PAPER.md" ]; then
  sha256sum "$RUN/$PAPER.md" > "$RUN/artifact.sha256"
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/finished_at.txt"
exit "$status"
