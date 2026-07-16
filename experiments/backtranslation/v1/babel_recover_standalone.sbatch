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
STANDALONE_ARCHIVE="$ROOT/dependencies/standalone-v1.5a-texlive-r77682.tar.xz"
STANDALONE_SOURCE_ARCHIVE="$ROOT/dependencies/standalone-v1.5a-ctan-20250222.zip"
EXPECTED_STANDALONE_SHA256=6daa00b081106b1c240a11732155287d9933e612f3e9a045ee40824f68b0ba98
EXPECTED_STANDALONE_SOURCE_SHA256=25078d6ff117e08f524dad6979bf682e6b3dc8eacfa035219c279d31f439bc49
PREVIEW_ARCHIVE="$ROOT/dependencies/preview-v14.0.6-texlive-r71662.tar.xz"
PREVIEW_SOURCE_ARCHIVE="$ROOT/dependencies/preview-v14.0.6-ctan-20240630.zip"
EXPECTED_PREVIEW_SHA256=91fad28da99be4fee077ea2779f609b341c0d0e1b4816623ab85e635665e32f9
EXPECTED_PREVIEW_SOURCE_SHA256=3059a3b0a43a4cbbff029064dc9c7200c96eefc09756368758be78b4c6894cbc
DVISVGM_ARCHIVE="$ROOT/dependencies/dvisvgm-r77966-x86_64-linux.tar.xz"
DVISVGM_SOURCE_ARCHIVE="$ROOT/dependencies/dvisvgm-3.6.tar.gz"
EXPECTED_DVISVGM_SHA256=d06f6ab32aec34a40f0be0252ee8e6fb1afa8f4a5105fce0e566885b88306612
EXPECTED_DVISVGM_SOURCE_SHA256=26446bb3b10739ff0925c9e416b76d2d222075c9d5dcfafe6e214609d072ed1a
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

# The archives are pre-staged and hash-pinned official CTAN/TeX Live packages.
# Runtime archives avoid undeclared docstrip build dependencies; matching source
# archives are retained for license compliance. Extraction remains case-local;
# no global TeX tree or upstream scene source is changed.
DEPENDENCY_EXIT=0
ACTUAL_STANDALONE_SHA256=$(sha256sum "$STANDALONE_ARCHIVE" 2>/dev/null | awk '{print $1}')
ACTUAL_STANDALONE_SOURCE_SHA256=$(sha256sum "$STANDALONE_SOURCE_ARCHIVE" 2>/dev/null | awk '{print $1}')
ACTUAL_PREVIEW_SHA256=$(sha256sum "$PREVIEW_ARCHIVE" 2>/dev/null | awk '{print $1}')
ACTUAL_PREVIEW_SOURCE_SHA256=$(sha256sum "$PREVIEW_SOURCE_ARCHIVE" 2>/dev/null | awk '{print $1}')
ACTUAL_DVISVGM_SHA256=$(sha256sum "$DVISVGM_ARCHIVE" 2>/dev/null | awk '{print $1}')
ACTUAL_DVISVGM_SOURCE_SHA256=$(sha256sum "$DVISVGM_SOURCE_ARCHIVE" 2>/dev/null | awk '{print $1}')
if [ "$ACTUAL_STANDALONE_SHA256" != "$EXPECTED_STANDALONE_SHA256" ] \
  || [ "$ACTUAL_STANDALONE_SOURCE_SHA256" != "$EXPECTED_STANDALONE_SOURCE_SHA256" ] \
  || [ "$ACTUAL_PREVIEW_SHA256" != "$EXPECTED_PREVIEW_SHA256" ] \
  || [ "$ACTUAL_PREVIEW_SOURCE_SHA256" != "$EXPECTED_PREVIEW_SOURCE_SHA256" ] \
  || [ "$ACTUAL_DVISVGM_SHA256" != "$EXPECTED_DVISVGM_SHA256" ] \
  || [ "$ACTUAL_DVISVGM_SOURCE_SHA256" != "$EXPECTED_DVISVGM_SOURCE_SHA256" ]; then
  DEPENDENCY_EXIT=66
else
  tar -xJf "$STANDALONE_ARCHIVE" -C "$TEXMF_ROOT" || DEPENDENCY_EXIT=$?
  if [ "$DEPENDENCY_EXIT" -eq 0 ]; then
    tar -xJf "$PREVIEW_ARCHIVE" -C "$TEXMF_ROOT" || DEPENDENCY_EXIT=$?
  fi
  if [ "$DEPENDENCY_EXIT" -eq 0 ]; then
    tar -xJf "$DVISVGM_ARCHIVE" -C "$TEXMF_ROOT" || DEPENDENCY_EXIT=$?
  fi
fi
export TEXINPUTS="$TEXMF_ROOT/tex//:"
export PATH="$TEXMF_ROOT/bin/x86_64-linux:$PATH"
# The TeX Live binary archive is relocatable, so its embedded kpathsea would
# otherwise search beside the case-local binary. Point only data lookup at the
# compute node's existing TeX tree; the executable itself remains case-local.
export TEXMFCNF=/usr/share/texlive/texmf-dist/web2c
export TEXMFROOT=/usr/share/texlive
export TEXMFDIST=/usr/share/texlive/texmf-dist
export TEXMF=/usr/share/texlive/texmf-dist

export STANDALONE_ARCHIVE STANDALONE_SOURCE_ARCHIVE EXPECTED_STANDALONE_SHA256 EXPECTED_STANDALONE_SOURCE_SHA256
export ACTUAL_STANDALONE_SHA256 ACTUAL_STANDALONE_SOURCE_SHA256
export PREVIEW_ARCHIVE PREVIEW_SOURCE_ARCHIVE EXPECTED_PREVIEW_SHA256 EXPECTED_PREVIEW_SOURCE_SHA256
export ACTUAL_PREVIEW_SHA256 ACTUAL_PREVIEW_SOURCE_SHA256
export DVISVGM_ARCHIVE DVISVGM_SOURCE_ARCHIVE EXPECTED_DVISVGM_SHA256 EXPECTED_DVISVGM_SOURCE_SHA256
export ACTUAL_DVISVGM_SHA256 ACTUAL_DVISVGM_SOURCE_SHA256 DEPENDENCY_EXIT TEXMF_ROOT
"$PYTHON" - "$CASE_ROOT/private/dependency-provenance.json" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

texmf = Path(os.environ["TEXMF_ROOT"])

def hashes(relative_paths):
    result = {}
    for relative in relative_paths:
        path = texmf / relative
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return result

payload = {
    "schema_version": "backtranslation-job-local-dependency/v1",
    "installation_scope": "slurm_job_local_texmf",
    "system_tex_data_roots": {
        "TEXMFCNF": "/usr/share/texlive/texmf-dist/web2c",
        "TEXMFROOT": "/usr/share/texlive",
        "TEXMFDIST": "/usr/share/texlive/texmf-dist",
        "TEXMF": "/usr/share/texlive/texmf-dist",
    },
    "dependency_exit": int(os.environ["DEPENDENCY_EXIT"]),
    "packages": [
        {
            "name": "standalone",
            "version": "1.5a",
            "tex_live_revision": 77682,
            "runtime_url": "https://mirrors.ctan.org/systems/texlive/tlnet/archive/standalone.tar.xz",
            "runtime_archive_filename": Path(os.environ["STANDALONE_ARCHIVE"]).name,
            "expected_runtime_sha256": os.environ["EXPECTED_STANDALONE_SHA256"],
            "actual_runtime_sha256": os.environ.get("ACTUAL_STANDALONE_SHA256") or None,
            "source_url": "https://mirrors.ctan.org/macros/latex/contrib/standalone.zip",
            "source_archive_filename": Path(os.environ["STANDALONE_SOURCE_ARCHIVE"]).name,
            "expected_source_sha256": os.environ["EXPECTED_STANDALONE_SOURCE_SHA256"],
            "actual_source_sha256": os.environ.get("ACTUAL_STANDALONE_SOURCE_SHA256") or None,
            "license": "LPPL-1.3-or-later",
            "copyright": "Copyright (c) 2010-2025 Martin Scharrer",
            "derived_files_sha256": hashes([
                "tex/latex/standalone/standalone.cls",
                "tex/latex/standalone/standalone.sty",
                "tex/latex/standalone/standalone.cfg",
                "tex/latex/standalone/standalone.tex",
            ]),
        },
        {
            "name": "preview",
            "version": "14.0.6",
            "tex_live_revision": 71662,
            "runtime_url": "https://mirrors.ctan.org/systems/texlive/tlnet/archive/preview.tar.xz",
            "runtime_archive_filename": Path(os.environ["PREVIEW_ARCHIVE"]).name,
            "expected_runtime_sha256": os.environ["EXPECTED_PREVIEW_SHA256"],
            "actual_runtime_sha256": os.environ.get("ACTUAL_PREVIEW_SHA256") or None,
            "source_url": "https://mirrors.ctan.org/macros/latex/contrib/preview.zip",
            "source_archive_filename": Path(os.environ["PREVIEW_SOURCE_ARCHIVE"]).name,
            "expected_source_sha256": os.environ["EXPECTED_PREVIEW_SOURCE_SHA256"],
            "actual_source_sha256": os.environ.get("ACTUAL_PREVIEW_SOURCE_SHA256") or None,
            "license": "GPL-3.0-only",
            "copyright": "AUCTeX/preview-latex contributors",
            "derived_files_sha256": hashes([
                "tex/latex/preview/preview.sty",
                "tex/latex/preview/prtightpage.def",
                "tex/latex/preview/prauctex.def",
            ]),
        },
        {
            "name": "dvisvgm",
            "version": "3.6",
            "tex_live_revision": 77966,
            "runtime_url": "https://mirrors.ctan.org/systems/texlive/tlnet/archive/dvisvgm.x86_64-linux.tar.xz",
            "runtime_archive_filename": Path(os.environ["DVISVGM_ARCHIVE"]).name,
            "expected_runtime_sha256": os.environ["EXPECTED_DVISVGM_SHA256"],
            "actual_runtime_sha256": os.environ.get("ACTUAL_DVISVGM_SHA256") or None,
            "source_url": "https://github.com/mgieseki/dvisvgm/releases/download/3.6/dvisvgm-3.6.tar.gz",
            "source_archive_filename": Path(os.environ["DVISVGM_SOURCE_ARCHIVE"]).name,
            "expected_source_sha256": os.environ["EXPECTED_DVISVGM_SOURCE_SHA256"],
            "actual_source_sha256": os.environ.get("ACTUAL_DVISVGM_SOURCE_SHA256") or None,
            "license": "GPL-3.0-or-later",
            "copyright": "Copyright (c) 2005-2025 Martin Gieseking",
            "derived_files_sha256": hashes([
                "bin/x86_64-linux/dvisvgm",
            ]),
        },
    ],
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
