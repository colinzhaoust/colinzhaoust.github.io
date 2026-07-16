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
while read -r paper arxiv_revision filename expected_sha256; do
  output="$B/inputs/$filename"
  existing_sha256=""
  if [ -s "$output" ]; then
    existing_sha256="$(sha256sum "$output" | cut -d ' ' -f 1)"
  fi
  if [ "$existing_sha256" != "$expected_sha256" ]; then
    if ! curl --fail --location --retry 3 --max-time 300 \
      "https://arxiv.org/pdf/$arxiv_revision" --output "$output.download"; then
      printf '%s\t%s\n' "$paper" 'download-failed' >> "$RUN/errors.tsv"
      status=1
      continue
    fi
    mv "$output.download" "$output"
  fi
  if [ "$(head -c 5 "$output")" != '%PDF-' ]; then
    printf '%s\t%s\n' "$paper" 'not-a-pdf' >> "$RUN/errors.tsv"
    status=1
    continue
  fi
  actual_sha256="$(sha256sum "$output" | cut -d ' ' -f 1)"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    printf '%s\t%s\t%s\t%s\n' \
      "$paper" 'sha256-mismatch' "$expected_sha256" "$actual_sha256" \
      >> "$RUN/errors.tsv"
    status=1
    continue
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$paper" "$arxiv_revision" "$filename" "$(wc -c < "$output")" \
    "$actual_sha256" >> "$RUN/frozen_inputs.tsv"
done <<'EOF'
transformers 1706.03762v7 transformers_1706.03762.pdf bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697
dpo 2305.18290v3 dpo_2305.18290.pdf 92cb3a2b71362acda98a789b03d88688fd33cf5fcf13f81d2b1de30ee7d3b67a
feynrl 2605.12380v1 feynrl_2605.12380.pdf 19b66e9758e35de7988ef96a6ef7ed84dda1572bddb07efee23fa1992bf7b15e
rope 2104.09864v5 rope_2104.09864.pdf e9a481fbe1c8a20b7b1fa566b13102a1896c7829fa9a8b4c80528452a5ddaf79
EOF

date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/finished_at.txt"
exit "$status"
