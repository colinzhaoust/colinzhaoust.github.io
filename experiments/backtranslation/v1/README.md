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

## What was actually downloaded

No YouTube video was downloaded or rehosted. The human/reference videos are
new renders of exact scene bodies extracted from the pinned Manim Community
source. The only network-fetched inputs are source/license snapshots and the
following job-local TeX runtime packages needed by Babel:

- Manim Community v0.20.1 source at commit
  `1157b746c37130685e0a02d8aa0871d1f164d5f4`, with both MIT notices;
- CTAN `standalone` v1.5a source plus TeX Live revision 77682 runtime;
- CTAN `preview` v14.0.6 source plus TeX Live revision 71662 runtime; and
- upstream `dvisvgm` v3.6 source plus TeX Live revision 77966 x86_64 runtime.

`babel_recover_standalone.sbatch` verifies every source/runtime archive hash,
extracts runtime files into the individual case's private directory, and adds
only that directory to `TEXINPUTS`/`PATH`. It does not modify the system TeX
installation, the Python environment, or the pinned scene source.

## Failure-preserving recovery ledger

Recovery runs are additive. They do not overwrite the first attempt:

| Babel array | Scheduled | Observed outcome |
| --- | ---: | --- |
| `9314456` | 10 | 5 normalized references; 4 missing `standalone.cls`; 1 source-exact static scene with no MP4 |
| `9329170` | 4 | CTAN source archive verified, but docstrip exposed missing `ydocstrip.tex` |
| `9329201` | 4 | `standalone` runtime loaded; LaTeX exposed missing `preview.sty` |
| `9329605` | 4 | `standalone` and `preview` loaded; Manim exposed missing `dvisvgm` |
| `9329857` | 4 | case-local `dvisvgm` ran, but relocatable kpathsea could not find the compute node's TeX data roots |

The combined inventory command retains every persisted attempt and selects the
latest successful attempt per case. Missing rows in a subset recovery array do
not count as attempts:

```sh
python -m tools.backtranslation.reference_batch combine \
  --registry experiments/backtranslation/v1/scene_registry.json \
  --protocol experiments/backtranslation/v1/protocol.json \
  --retrieval-root babel:/home/xinranz3/4blue2brown_explore/backtranslation_refs_20260715 \
  --run 9314456=/local/mirror/9314456 \
  --run 9329170=/local/mirror/9329170 \
  --run 9329201=/local/mirror/9329201 \
  --run 9329605=/local/mirror/9329605 \
  --output combined_reference_inventory.json
```

The output is deterministic for immutable run directories: `observed_at` is
derived from the status manifests rather than the current wall clock.

## Static cases

`static_scene_replacements.json` recommends exact pinned animated replacements
for the next registry version. The v1 outcomes remain failures, because a
`:save_last_frame:` directive cannot truthfully become a video after the fact.
The file also records the coverage loss of replacing the Gaussian `Surface`
example with an upstream-exact camera-animation example; a project-authored
animated surface may be added only as a separately labeled derived stress test.
