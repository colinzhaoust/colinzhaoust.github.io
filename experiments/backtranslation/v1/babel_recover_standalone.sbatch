#!/usr/bin/env bash
#SBATCH --job-name=bt-ref-tex-recovery
#SBATCH --partition=debug
#SBATCH --array=0-3%2
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
ARCHIVE="$ROOT/dependencies/standalone-v1.5a-texlive-r77682.tar.xz"
EXPECTED_ARCHIVE_SHA256=6daa00b081106b1c240a11732155287d9933e612f3e9a045ee40824f68b0ba98
MANIM=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/manim
PYTHON=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/python
FFMPEG=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/ffmpeg
FFPROBE=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/ffprobe

case "$SLURM_ARRAY_TASK_ID" in
  0) CASE_ID=bt-001; SCENE_CLASS=OpeningManim; INITIAL_TASK=9314456_0 ;;
  1) CASE_ID=bt-002; SCENE_CLASS=SineCurveUnitCircle; INITIAL_TASK=9314456_1 ;;
  2) CASE_ID=bt-004; SCENE_CLASS=ArgMinExample; INITIAL_TASK=9314456_3 ;;
  3) CASE_ID=bt-005; SCENE_CLASS=GraphAreaPlot; INITIAL_TASK=9314456_4 ;;
  *) exit 64 ;;
esac

CASE_ROOT="$RUN_ROOT/cases/$CASE_ID"
DEPENDENCY_ROOT="$CASE_ROOT/private/dependencies"
TEXMF_ROOT="$DEPENDENCY_ROOT/standalone/texmf"
TEX_INSTALL="$TEXMF_ROOT/tex/latex/standalone"
mkdir -p "$CASE_ROOT/raw_media" "$CASE_ROOT/private" "$TEXMF_ROOT"
cd "$PROJECT"

export PYTHONPATH="$PROJECT"
export PATH="$(dirname "$FFMPEG"):$PATH"
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PIPELINE_COMMIT=${BACKTRANSLATION_PIPELINE_COMMIT:-$(git rev-parse HEAD 2>/dev/null || printf unknown)}
UPSTREAM_COMMIT=$(git -C "$SOURCE_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)

# The archive is pre-staged and hash-pinned. It is CTAN's official TeX Live
# runtime package, avoiding an undeclared ydocstrip build dependency. Extraction
# remains case-local; no global TeX tree or upstream scene source is changed.
DEPENDENCY_EXIT=0
ACTUAL_ARCHIVE_SHA256=$(sha256sum "$ARCHIVE" 2>/dev/null | awk '{print $1}')
if [ "$ACTUAL_ARCHIVE_SHA256" != "$EXPECTED_ARCHIVE_SHA256" ]; then
  DEPENDENCY_EXIT=66
else
  tar -xJf "$ARCHIVE" -C "$TEXMF_ROOT" || DEPENDENCY_EXIT=$?
fi
export TEXINPUTS="$TEXMF_ROOT/tex//:"

export ARCHIVE EXPECTED_ARCHIVE_SHA256 ACTUAL_ARCHIVE_SHA256 DEPENDENCY_EXIT TEX_INSTALL
"$PYTHON" - "$CASE_ROOT/private/dependency-provenance.json" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

install = Path(os.environ["TEX_INSTALL"])
derived = {}
for name in ("standalone.cls", "standalone.sty", "standalone.cfg", "standalone.tex"):
    path = install / name
    derived[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
payload = {
    "schema_version": "backtranslation-job-local-dependency/v1",
    "name": "standalone",
    "version": "1.5a",
    "tex_live_revision": 77682,
    "source": "https://mirrors.ctan.org/systems/texlive/tlnet/archive/standalone.tar.xz",
    "archive_filename": Path(os.environ["ARCHIVE"]).name,
    "expected_archive_sha256": os.environ["EXPECTED_ARCHIVE_SHA256"],
    "actual_archive_sha256": os.environ.get("ACTUAL_ARCHIVE_SHA256") or None,
    "license": "LPPL-1.3-or-later",
    "copyright": "Copyright (c) 2010-2025 Martin Scharrer",
    "installation_scope": "slurm_job_local_texmf",
    "dependency_exit": int(os.environ["DEPENDENCY_EXIT"]),
    "derived_files_sha256": derived,
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

VERIFY_EXIT=125
RENDER_EXIT=125
PREP_EXIT=125
RAW_VIDEO=
if [ "$DEPENDENCY_EXIT" -eq 0 ]; then
  "$PYTHON" tools/run_backtranslation.py validate-registry \
    --registry experiments/backtranslation/v1/scene_registry.json \
    --source-root "$SOURCE_ROOT" > "$CASE_ROOT/private/source-verification.json" 2> "$CASE_ROOT/private/source-verification.stderr"
  VERIFY_EXIT=$?
fi
if [ "$DEPENDENCY_EXIT" -eq 0 ] && [ "$VERIFY_EXIT" -eq 0 ]; then
  "$MANIM" -ql --media_dir "$CASE_ROOT/raw_media" "$ROOT/generated/scenes.py" "$SCENE_CLASS" \
    > "$CASE_ROOT/private/render.stdout" 2> "$CASE_ROOT/private/render.stderr"
  RENDER_EXIT=$?
  RAW_VIDEO=$(find "$CASE_ROOT/raw_media" -type f -name "${SCENE_CLASS}.mp4" -print -quit)
fi
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
if [ "$DEPENDENCY_EXIT" -ne 0 ]; then
  FAILURE_CODE=job_local_dependency_error
elif [ "$VERIFY_EXIT" -ne 0 ]; then
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

export CASE_ID SCENE_CLASS INITIAL_TASK STATUS FAILURE_CODE RAW_HASH REFERENCE_HASH RAW_VIDEO
export DEPENDENCY_EXIT VERIFY_EXIT RENDER_EXIT PREP_EXIT STARTED_AT PIPELINE_COMMIT UPSTREAM_COMMIT
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
    "recovery": {
        "initial_slurm_task": os.environ["INITIAL_TASK"],
        "reason": "missing_runtime_dependency_standalone_cls",
        "dependency_provenance": "private/dependency-provenance.json",
    },
    "slurm": {
        "array_job_id": os.environ["SLURM_ARRAY_JOB_ID"],
        "array_task_id": os.environ["SLURM_ARRAY_TASK_ID"],
        "job_id": os.environ["SLURM_JOB_ID"],
    },
    "exit_codes": {
        "job_local_dependency": int(os.environ["DEPENDENCY_EXIT"]),
        "source_verification": int(os.environ["VERIFY_EXIT"]),
        "render": int(os.environ["RENDER_EXIT"]),
        "normalization": int(os.environ["PREP_EXIT"]),
    },
    "raw_render": {"path": os.environ.get("RAW_VIDEO") or None, "sha256": optional_hash(os.environ["RAW_HASH"])},
    "reference": {
        "remote_relative_path": f"cases/{os.environ['CASE_ID']}/model_input/{os.environ['CASE_ID']}/reference.mp4",
        "sha256": optional_hash(os.environ["REFERENCE_HASH"]),
    },
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

test "$STATUS" = completed
