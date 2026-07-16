#!/usr/bin/env bash
#SBATCH --job-name=q8-inhouse-v0
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/home/xinranz3/4blue2brown_explore/runs/q8_real_video_matrix/inhouse_v0/slurm-%j.out
#SBATCH --error=/home/xinranz3/4blue2brown_explore/runs/q8_real_video_matrix/inhouse_v0/slurm-%j.err

set -euo pipefail

ROOT=/home/xinranz3/4blue2brown_explore/repo
OUT=/home/xinranz3/4blue2brown_explore/runs/q8_real_video_matrix/inhouse_v0
PY=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/python
MANIM=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/manim
mkdir -p "$OUT"
cd "$ROOT"

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
start_epoch=$(date +%s)
"$MANIM" -ql --media_dir "$OUT/media" scenes/inhouse_paper_explainer_suite.py \
  TransformerCoreExplainer DPOPreferenceExplainer FeynRLESSMiniLesson RoPERotationExplainer

videos=(
  "$OUT/media/videos/inhouse_paper_explainer_suite/480p15/TransformerCoreExplainer.mp4"
  "$OUT/media/videos/inhouse_paper_explainer_suite/480p15/DPOPreferenceExplainer.mp4"
  "$OUT/media/videos/inhouse_paper_explainer_suite/480p15/FeynRLESSMiniLesson.mp4"
  "$OUT/media/videos/inhouse_paper_explainer_suite/480p15/RoPERotationExplainer.mp4"
)
"$PY" tools/probe_rendered_videos.py --videos "${videos[@]}" --out-dir "$OUT/probe"
sha256sum scenes/inhouse_paper_explainer_suite.py data/inhouse_paper_video_specs.json "${videos[@]}" > "$OUT/sha256sums.txt"
end_epoch=$(date +%s)
ended=$(date -u +%Y-%m-%dT%H:%M:%SZ)
{
  printf '{\n'
  printf '  "schema_version": "q8-babel-runtime-capture/0.2.0",\n'
  printf '  "slurm_job_id": "%s",\n' "${SLURM_JOB_ID:-unknown}"
  printf '  "host": "%s",\n' "$(hostname)"
  printf '  "started_at": "%s",\n' "$started"
  printf '  "ended_at": "%s",\n' "$ended"
  printf '  "wall_time_seconds": %s,\n' "$((end_epoch-start_epoch))"
  printf '  "source_commit": "03d970e7f1cc6ddc9f0ffd0bf3edc1a46ae0e432",\n'
  printf '  "consumed_source": "scenes/inhouse_paper_explainer_suite.py",\n'
  printf '  "reference_registry": "data/inhouse_paper_video_specs.json",\n'
  printf '  "reference_registry_consumed_at_runtime": false,\n'
  printf '  "measured_api_cost_usd": 0,\n'
  printf '  "cost_provenance": "zero provider spend only; compute recorded as wall time and not converted to USD",\n'
  printf '  "probe_report": "%s"\n' "$OUT/probe/probe_report.json"
  printf '}\n'
} > "$OUT/result.json"
