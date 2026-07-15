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
