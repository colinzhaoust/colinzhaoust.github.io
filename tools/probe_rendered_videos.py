#!/usr/bin/env python3
"""Probe rendered Manim videos and build lightweight review artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def _safe_component(value: str) -> str:
    component = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return component or "root"


def output_keys(videos: list[Path]) -> list[str]:
    """Return deterministic, collision-free output keys for input videos.

    A unique filename stem keeps the historical output layout. Duplicate stems
    gain a parent-directory prefix (for example ``bt-001__reference``), with a
    stable path digest only when those human-readable keys would still collide.
    """

    resolved = [video.resolve() for video in videos]
    if len(set(resolved)) != len(resolved):
        raise ValueError("duplicate video input resolves to the same file")

    stem_counts = Counter(video.stem for video in videos)
    candidates = [
        video.stem
        if stem_counts[video.stem] == 1
        else f"{_safe_component(video.parent.name)}__{video.stem}"
        for video in videos
    ]
    candidate_counts = Counter(candidates)
    keys = []
    for video, candidate in zip(videos, candidates):
        if candidate_counts[candidate] == 1:
            keys.append(candidate)
            continue
        identity = video.as_posix()
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        keys.append(f"{candidate}__{digest}")
    if len(set(keys)) != len(keys):
        raise ValueError("could not derive unique output keys for video inputs")
    return keys


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.strip()


def ffprobe(path: Path) -> dict:
    raw = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ]
    )
    data = json.loads(raw)
    stream = data["streams"][0]
    fmt = data["format"]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": stream["r_frame_rate"],
        "duration_sec": float(fmt["duration"]),
        "size_bytes": int(fmt["size"]),
    }


def extract_frame(video: Path, out: Path, timestamp: float) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(out),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def image_metrics(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(img)
    mean_rgb = stat.mean
    brightness = sum(mean_rgb) / 3.0
    bg = Image.new("RGB", img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, bg).convert("L")
    non_bg = sum(1 for value in diff.getdata() if value > 12) / (img.size[0] * img.size[1])
    hist = img.convert("L").histogram()
    total = sum(hist)
    entropy = 0.0
    for count in hist:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return {
        "brightness": round(brightness, 2),
        "non_background_fraction": round(non_bg, 4),
        "entropy": round(entropy, 3),
    }


def make_contact_sheet(frames: list[Path], out: Path, thumb_width: int = 360) -> None:
    images = [Image.open(path).convert("RGB") for path in frames]
    thumbs = []
    for img in images:
        ratio = thumb_width / img.width
        thumbs.append(img.resize((thumb_width, int(img.height * ratio))))
    width = thumb_width * len(thumbs)
    height = max(img.height for img in thumbs)
    sheet = Image.new("RGB", (width, height), "white")
    x = 0
    for img in thumbs:
        sheet.paste(img, (x, 0))
        x += thumb_width
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", nargs="+", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    videos = [Path(raw) for raw in args.videos]
    try:
        keys = output_keys(videos)
    except ValueError as exc:
        parser.error(str(exc))

    records = []
    for video, key in zip(videos, keys):
        meta = ffprobe(video)
        frame_dir = out_dir / "frames" / key
        times = [meta["duration_sec"] * frac for frac in (0.18, 0.52, 0.86)]
        frame_paths = []
        frame_metrics = []
        for idx, timestamp in enumerate(times):
            final_frame = frame_dir / f"{idx + 1:02d}.png"
            offsets = (-0.9, -0.45, 0.0, 0.45, 0.9)
            best: tuple[float, Path, dict] | None = None
            for cand_idx, offset in enumerate(offsets):
                candidate_time = min(max(timestamp + offset, 0.05), max(meta["duration_sec"] - 0.05, 0.05))
                candidate = frame_dir / f"{idx + 1:02d}_candidate_{cand_idx}.png"
                extract_frame(video, candidate, candidate_time)
                metrics = image_metrics(candidate)
                score = metrics["non_background_fraction"]
                if best is None or score > best[2]["non_background_fraction"]:
                    best = (candidate_time, candidate, metrics)
            assert best is not None
            shutil.copyfile(best[1], final_frame)
            frame_paths.append(final_frame)
            frame_metrics.append({"path": str(final_frame), "timestamp": round(best[0], 3), **best[2]})
        sheet = out_dir / "contact_sheets" / f"{key}.png"
        make_contact_sheet(frame_paths, sheet)
        records.append({"video": str(video), **meta, "frames": frame_metrics, "contact_sheet": str(sheet)})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe_report.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    lines = ["# Render Probe Report", ""]
    for rec in records:
        lines.append(f"## {Path(rec['contact_sheet']).stem}")
        lines.append(f"- video: `{rec['video']}`")
        lines.append(f"- duration: {rec['duration_sec']:.2f}s, size: {rec['width']}x{rec['height']}, fps: {rec['fps']}")
        lines.append(f"- contact sheet: `{rec['contact_sheet']}`")
        for frame in rec["frames"]:
            lines.append(
                f"- frame {Path(frame['path']).name} @ {frame['timestamp']:.2f}s: "
                f"brightness={frame['brightness']}, non_bg={frame['non_background_fraction']}, entropy={frame['entropy']}"
            )
        lines.append("")
    (out_dir / "probe_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
