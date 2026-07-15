"""Runtime generation of tiny project-authored videos for offline dry-runs."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "backtranslation-synthetic-fixture/v1":
        raise ValueError("Unsupported synthetic fixture")
    if data.get("implementation_origin") != "synthetic_fixture" or data.get("completion") != "placeholder":
        raise ValueError("Dry-run fixture must remain synthetic_fixture + placeholder")
    return data


def _render_variant(config: dict[str, Any], variant: dict[str, Any], output: Path, ffmpeg: str) -> None:
    width = int(config["width"])
    height = int(config["height"])
    fps = int(config["fps"])
    duration = float(config["duration_seconds"])
    box_x = int(variant["box_x"])
    filter_graph = (
        f"color=c={variant['background']}:s={width}x{height}:r={fps}:d={duration},"
        f"drawbox=x={box_x}:y={(height - 40) // 2}:w=40:h=40:color={variant['box_color']}:t=fill"
    )
    proc = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            filter_graph,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-fflags",
            "+bitexact",
            "-flags:v",
            "+bitexact",
            str(output),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[-2000:])


def create_fixture_videos(config_path: Path, output_dir: Path, ffmpeg: str = "ffmpeg") -> dict[str, Path]:
    config = load_fixture(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    pending_copies: list[tuple[str, str]] = []
    for name, variant in config["variants"].items():
        output = output_dir / f"{name}.mp4"
        if "copy" in variant:
            pending_copies.append((name, str(variant["copy"])))
        else:
            _render_variant(config, variant, output, ffmpeg)
            outputs[name] = output
    for name, source_name in pending_copies:
        if source_name not in outputs:
            raise ValueError(f"Synthetic copy source not found: {source_name}")
        output = output_dir / f"{name}.mp4"
        shutil.copyfile(outputs[source_name], output)
        outputs[name] = output
    return outputs
