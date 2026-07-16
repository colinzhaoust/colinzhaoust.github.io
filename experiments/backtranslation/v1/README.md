# Manim gallery backtranslation v1

The harness is offline-first. It does not download gallery assets or call a
provider. `ffmpeg` and `ffprobe` must already be available on `PATH`.

Create the declared combined Python 3.9 environment:

```sh
python3.9 -m venv .venv-backtranslation
.venv-backtranslation/bin/python -m pip install -r requirements-backtranslation-evidence.txt
```

Run both evidence-contract and harness suites from that same environment:

```sh
.venv-backtranslation/bin/python -m unittest discover -s tests/paper_media_evidence -v
.venv-backtranslation/bin/python -m unittest discover -s tests/backtranslation -v
```

Run the synthetic bridge without provider calls:

```sh
.venv-backtranslation/bin/python tools/run_backtranslation.py dry-run --work-dir /tmp/backtranslation-dry-run
```

The dry-run emits three q-5-validated canonical/public manifests and labels all
synthetic artifacts as placeholders.

## Babel human/reference renders

`babel_render_references.sbatch` is the reproducible ten-case array job for the
real human/reference condition. It consumes only the pinned Manim Community
checkout declared by `scene_registry.json`; it does not download YouTube or any
other gallery video. Before submission, use `reference_batch.py extract` to
verify the checkout and extract the exact RST scene bodies:

```sh
python -m tools.backtranslation.reference_batch extract \
  --registry experiments/backtranslation/v1/scene_registry.json \
  --source-root /path/to/manim-at-1157b746 \
  --output-source /remote/root/generated/scenes.py \
  --output-manifest /remote/root/generated/source_manifest.json
```

Each array task retains render stdout/stderr, exit codes, source verification,
raw and normalized hashes, and an ffprobe record. Harvest all ten rows (including
failures and missing tasks) with:

```sh
python -m tools.backtranslation.reference_batch harvest \
  --registry experiments/backtranslation/v1/scene_registry.json \
  --protocol experiments/backtranslation/v1/protocol.json \
  --run-root /remote/root/runs/JOB_ID \
  --output /remote/root/runs/JOB_ID/reference_inventory.json
```

Two selected upstream directives (`GraphAreaPlot`, `ThreeDSurfacePlot`) are
declared `:save_last_frame:` examples. The array still attempts all ten without
modifying their source and keeps any no-video outcome in the denominator. The
one-shot and self-refined columns remain blocked until a true video-input model
adapter and external network-disabled generated-code sandbox are configured.
