#!/usr/bin/env bash
#SBATCH --job-name=bt-reference-v1
#SBATCH --partition=debug
#SBATCH --array=0-9%3
#SBATCH --time=01:00:00
#SBATCH --mem=12G
#SBATCH --cpus-per-task=2
#SBATCH --output=/home/xinranz3/4blue2brown_explore/backtranslation_refs_20260715/logs/%A_%a.out
#SBATCH --error=/home/xinranz3/4blue2brown_explore/backtranslation_refs_20260715/logs/%A_%a.err

set -uo pipefail

ROOT=${BACKTRANSLATION_BABEL_ROOT:-/home/xinranz3/4blue2brown_explore/backtranslation_refs_20260715}
PROJECT="$ROOT/project"
SOURCE_ROOT="$ROOT/upstream/manim"
RUN_ROOT="$ROOT/runs/${SLURM_ARRAY_JOB_ID}"
MANIM=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/manim
PYTHON=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/python
FFMPEG=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/ffmpeg
FFPROBE=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/ffprobe

case "$SLURM_ARRAY_TASK_ID" in
  0) CASE_ID=bt-001; SCENE_CLASS=OpeningManim ;;
  1) CASE_ID=bt-002; SCENE_CLASS=SineCurveUnitCircle ;;
  2) CASE_ID=bt-003; SCENE_CLASS=BooleanOperations ;;
  3) CASE_ID=bt-004; SCENE_CLASS=ArgMinExample ;;
  4) CASE_ID=bt-005; SCENE_CLASS=GraphAreaPlot ;;
  5) CASE_ID=bt-006; SCENE_CLASS=PointWithTrace ;;
  6) CASE_ID=bt-007; SCENE_CLASS=FollowingGraphCamera ;;
  7) CASE_ID=bt-008; SCENE_CLASS=MovingZoomedSceneAround ;;
  8) CASE_ID=bt-009; SCENE_CLASS=ThreeDCameraRotation ;;
  9) CASE_ID=bt-010; SCENE_CLASS=ThreeDSurfacePlot ;;
  *) exit 64 ;;
esac

CASE_ROOT="$RUN_ROOT/cases/$CASE_ID"
mkdir -p "$CASE_ROOT/raw_media" "$CASE_ROOT/private"
cd "$PROJECT"

export PYTHONPATH="$PROJECT"
export PATH="$(dirname "$FFMPEG"):$PATH"
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PIPELINE_COMMIT=${BACKTRANSLATION_PIPELINE_COMMIT:-$(git rev-parse HEAD 2>/dev/null || printf unknown)}
UPSTREAM_COMMIT=$(git -C "$SOURCE_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)

"$PYTHON" tools/run_backtranslation.py validate-registry \
  --registry experiments/backtranslation/v1/scene_registry.json \
  --source-root "$SOURCE_ROOT" > "$CASE_ROOT/private/source-verification.json" 2> "$CASE_ROOT/private/source-verification.stderr"
VERIFY_EXIT=$?

RENDER_EXIT=125
RAW_VIDEO=
if [ "$VERIFY_EXIT" -eq 0 ]; then
  "$MANIM" -ql --media_dir "$CASE_ROOT/raw_media" "$ROOT/generated/scenes.py" "$SCENE_CLASS" \
    > "$CASE_ROOT/private/render.stdout" 2> "$CASE_ROOT/private/render.stderr"
  RENDER_EXIT=$?
  RAW_VIDEO=$(find "$CASE_ROOT/raw_media" -type f -name "${SCENE_CLASS}.mp4" -print -quit)
fi

PREP_EXIT=125
if [ "$RENDER_EXIT" -eq 0 ] && [ -n "$RAW_VIDEO" ] && [ -s "$RAW_VIDEO" ]; then
  "$PYTHON" tools/run_backtranslation.py prepare-reference \
    --protocol experiments/backtranslation/v1/protocol.json \
    --input-video "$RAW_VIDEO" \
    --output-root "$CASE_ROOT/model_input" \
    --case-id "$CASE_ID" \
    --private-manifest "$CASE_ROOT/private/reference-preparation.json" \
    > "$CASE_ROOT/private/prepare.stdout" 2> "$CASE_ROOT/private/prepare.stderr"
  PREP_EXIT=$?
fi

REFERENCE="$CASE_ROOT/model_input/$CASE_ID/reference.mp4"
STATUS=failed
FAILURE_CODE=render_error
RAW_HASH=null
REFERENCE_HASH=null
if [ "$VERIFY_EXIT" -ne 0 ]; then
  FAILURE_CODE=source_verification_error
elif [ "$RENDER_EXIT" -ne 0 ] || [ -z "$RAW_VIDEO" ] || [ ! -s "$RAW_VIDEO" ]; then
  FAILURE_CODE=render_error
elif [ "$PREP_EXIT" -ne 0 ] || [ ! -s "$REFERENCE" ]; then
  FAILURE_CODE=reference_normalization_error
else
  STATUS=completed
  FAILURE_CODE=null
  RAW_HASH=$(sha256sum "$RAW_VIDEO" | awk '{print $1}')
  REFERENCE_HASH=$(sha256sum "$REFERENCE" | awk '{print $1}')
  "$FFPROBE" -v error -show_entries format=duration,size,format_name:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate -of json "$REFERENCE" > "$CASE_ROOT/private/reference-ffprobe.json"
fi

export CASE_ID SCENE_CLASS STATUS FAILURE_CODE RAW_HASH REFERENCE_HASH RAW_VIDEO
export VERIFY_EXIT RENDER_EXIT PREP_EXIT STARTED_AT PIPELINE_COMMIT UPSTREAM_COMMIT
export FINISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
export SLURM_ARRAY_JOB_ID SLURM_ARRAY_TASK_ID SLURM_JOB_ID
"$PYTHON" - "$CASE_ROOT/status.json" <<'PY'
import json
import os
import sys
from pathlib import Path

def optional_hash(value):
    return None if value == "null" else value

payload = {
    "schema_version": "backtranslation-reference-case/v1",
    "case_id": os.environ["CASE_ID"],
    "scene_class": os.environ["SCENE_CLASS"],
    "status": os.environ["STATUS"],
    "failure_code": None if os.environ["FAILURE_CODE"] == "null" else os.environ["FAILURE_CODE"],
    "started_at": os.environ["STARTED_AT"],
    "finished_at": os.environ["FINISHED_AT"],
    "pipeline_commit": os.environ["PIPELINE_COMMIT"],
    "upstream_commit": os.environ["UPSTREAM_COMMIT"],
    "slurm": {
        "array_job_id": os.environ["SLURM_ARRAY_JOB_ID"],
        "array_task_id": os.environ["SLURM_ARRAY_TASK_ID"],
        "job_id": os.environ["SLURM_JOB_ID"],
    },
    "exit_codes": {
        "source_verification": int(os.environ["VERIFY_EXIT"]),
        "render": int(os.environ["RENDER_EXIT"]),
        "normalization": int(os.environ["PREP_EXIT"]),
    },
    "raw_render": {
        "path": os.environ.get("RAW_VIDEO") or None,
        "sha256": optional_hash(os.environ["RAW_HASH"]),
    },
    "reference": {
        "remote_relative_path": f"cases/{os.environ['CASE_ID']}/model_input/{os.environ['CASE_ID']}/reference.mp4",
        "sha256": optional_hash(os.environ["REFERENCE_HASH"]),
    },
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

test "$STATUS" = completed
