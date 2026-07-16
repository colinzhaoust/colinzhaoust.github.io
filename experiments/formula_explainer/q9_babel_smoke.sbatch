#!/bin/bash
#SBATCH --job-name=q9-formula-softmax
#SBATCH --partition=debug
#SBATCH --time=00:10:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --output=/home/xinranz3/4blue2brown_explore/q9_formula_explainer/babel-smoke-%j.log

set -euo pipefail

ROOT=/home/xinranz3/4blue2brown_explore/q9_formula_explainer
MANIM=/home/xinranz3/4blue2brown_explore/envs/paper2manim/bin/manim
SCENE_IR=runs/formula_explainer/build/scene_ir/attention_softmax_lookup/attention_softmax.json
MEDIA_DIR=runs/formula_explainer/babel_smoke

cd "$ROOT"
export FORMULA_SCENE_IR="$SCENE_IR"
"$MANIM" -ql --media_dir "$MEDIA_DIR" scenes/formula_explainer_scene.py FormulaExplainerScene

VIDEO="$ROOT/$MEDIA_DIR/videos/formula_explainer_scene/480p15/FormulaExplainerScene.mp4"
test -s "$VIDEO"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of json "$VIDEO" > "$ROOT/$MEDIA_DIR/ffprobe.json"
sha256sum "$VIDEO" > "$ROOT/$MEDIA_DIR/sha256.txt"
