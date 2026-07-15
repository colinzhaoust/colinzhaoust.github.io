#!/usr/bin/env python3
"""Probe rendered Manim videos and build lightweight review artifacts."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


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
    records = []
    for raw in args.videos:
        video = Path(raw)
        meta = ffprobe(video)
        stem = video.stem
        frame_dir = out_dir / "frames" / stem
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
        sheet = out_dir / "contact_sheets" / f"{stem}.png"
        make_contact_sheet(frame_paths, sheet)
        records.append({"video": str(video), **meta, "frames": frame_metrics, "contact_sheet": str(sheet)})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe_report.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    lines = ["# Render Probe Report", ""]
    for rec in records:
        lines.append(f"## {Path(rec['video']).stem}")
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
