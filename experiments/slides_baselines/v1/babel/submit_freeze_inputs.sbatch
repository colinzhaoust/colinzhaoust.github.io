#!/usr/bin/env bash
#SBATCH --job-name=freeze-slide-inputs
#SBATCH --partition=debug
#SBATCH --time=00:30:00
#SBATCH --mem=2G
#SBATCH --cpus-per-task=1
#SBATCH --output=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715/runs/input-freeze/slurm-%j.out
#SBATCH --error=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715/runs/input-freeze/slurm-%j.err

set -uo pipefail
B=/home/xinranz3/4blue2brown_explore/slides_baselines_20260715
RUN="$B/runs/input-freeze"
mkdir -p "$B/inputs" "$RUN"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/started_at.txt"
printf '%s\n' 'provider_calls=0' 'measured_provider_cost_usd=0' > "$RUN/cost.txt"

status=0
while read -r paper arxiv_id filename; do
  output="$B/inputs/$filename"
  if [ ! -s "$output" ]; then
    curl --fail --location --retry 3 --max-time 300 \
      "https://arxiv.org/pdf/$arxiv_id" --output "$output"
  fi
  if [ "$(head -c 5 "$output")" != '%PDF-' ]; then
    printf '%s\t%s\n' "$paper" 'not-a-pdf' >> "$RUN/errors.tsv"
    status=1
    continue
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$paper" "$arxiv_id" "$filename" "$(wc -c < "$output")" \
    "$(sha256sum "$output" | cut -d ' ' -f 1)" >> "$RUN/frozen_inputs.tsv"
done <<'EOF'
transformers 1706.03762 transformers_1706.03762.pdf
dpo 2305.18290 dpo_2305.18290.pdf
feynrl 2605.12380 feynrl_2605.12380.pdf
rope 2104.09864 rope_2104.09864.pdf
EOF

date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/finished_at.txt"
exit "$status"
