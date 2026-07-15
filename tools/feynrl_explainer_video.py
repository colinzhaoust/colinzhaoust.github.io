#!/usr/bin/env python3
"""Generate a short FeynRL/P3O explainer animation.

This is a robust prototype renderer: it only requires Pillow, which is already
available in the workspace. It produces an animated GIF, an HTML player, and
review keyframes. If ffmpeg is installed later, the script can also create MP4.

Run:
    python3 tools/feynrl_explainer_video.py
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BG = (247, 249, 252)
INK = (31, 41, 55)
MUTED = (88, 102, 120)
GRID = (217, 224, 233)
BLUE = (47, 128, 237)
RED = (214, 69, 69)
GREEN = (44, 156, 105)
ORANGE = (239, 125, 0)
PURPLE = (126, 87, 194)
YELLOW = (243, 186, 67)
WHITE = (255, 255, 255)
BLACK = (18, 24, 33)


def parse_size(raw: str) -> tuple[int, int]:
    try:
        w, h = raw.lower().split("x", 1)
        return int(w), int(h)
    except Exception as exc:
        raise argparse.ArgumentTypeError("size must look like 960x540") from exc


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if mono:
        candidates.extend(
            [
                "/System/Library/Fonts/Menlo.ttc",
                "/System/Library/Fonts/Supplemental/Courier New.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            ]
        )
    elif bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(lerp(a[i], b[i], t)) for i in range(3))


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if text_size(draw, candidate, fnt)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    size: int = 24,
    fill: tuple[int, int, int] = INK,
    bold: bool = False,
    mono: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(xy, text, font=font(size, bold=bold, mono=mono), fill=fill, anchor=anchor)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    max_width: int,
    size: int = 22,
    fill: tuple[int, int, int] = INK,
    bold: bool = False,
    line_gap: int = 8,
) -> int:
    fnt = font(size, bold=bold)
    x, y = xy
    for line in wrap_text(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + line_gap
    return y


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    radius: int = 10,
    fill: tuple[int, int, int] = WHITE,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    fill: tuple[int, int, int] = MUTED,
    width: int = 3,
) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    head = 12
    a1 = ang + math.pi * 0.82
    a2 = ang - math.pi * 0.82
    p1 = (x2 + head * math.cos(a1), y2 + head * math.sin(a1))
    p2 = (x2 + head * math.cos(a2), y2 + head * math.sin(a2))
    draw.polygon([end, p1, p2], fill=fill)


def card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    body: str,
    accent: tuple[int, int, int],
) -> None:
    rounded(draw, box, radius=14, fill=WHITE, outline=(221, 228, 238), width=2)
    x1, y1, x2, _ = box
    draw.rectangle((x1, y1, x1 + 8, box[3]), fill=accent)
    draw_text(draw, (x1 + 22, y1 + 22), title, size=22, bold=True, fill=INK)
    draw_wrapped(draw, (x1 + 22, y1 + 58), body, x2 - x1 - 44, size=16, fill=MUTED)


def base_frame(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.rectangle((0, 0, w, 9), fill=BLUE)
    draw.rectangle((0, h - 7, w, h), fill=(229, 235, 244))
    return img, draw


def draw_footer(draw: ImageDraw.ImageDraw, w: int, h: int, scene: str, step: int, total: int) -> None:
    draw_text(draw, (32, h - 30), scene, size=14, fill=MUTED)
    x0, x1 = w - 240, w - 34
    y = h - 26
    draw.line((x0, y, x1, y), fill=(205, 214, 226), width=5)
    fill_x = x0 + (x1 - x0) * step / max(total - 1, 1)
    draw.line((x0, y, fill_x, y), fill=BLUE, width=5)


def ess(weights: list[float]) -> float:
    n = len(weights)
    sum_w = sum(weights)
    sum_w2 = sum(v * v for v in weights)
    if n == 0 or sum_w2 <= 0:
        return 1.0
    return (sum_w * sum_w) / (n * sum_w2)


def make_ratio_data() -> tuple[list[float], list[float]]:
    random.seed(42)
    fresh = [math.exp(random.gauss(0.0, 0.055)) for _ in range(460)]
    stale = [math.exp(random.gauss(-0.32, 0.52)) for _ in range(380)]
    stale += [math.exp(random.gauss(0.9, 0.33)) for _ in range(80)]
    return fresh, stale


def blended_counts(fresh: list[float], stale: list[float], t: float, bins: int = 32) -> tuple[list[float], float]:
    xmin, xmax = 0.0, 3.0
    bin_w = (xmax - xmin) / bins
    fresh_counts = [0 for _ in range(bins)]
    stale_counts = [0 for _ in range(bins)]
    for values, counts in [(fresh, fresh_counts), (stale, stale_counts)]:
        for value in values:
            if xmin <= value <= xmax:
                idx = min(bins - 1, int((value - xmin) / bin_w))
                counts[idx] += 1
    counts = [lerp(fresh_counts[i], stale_counts[i], t) for i in range(bins)]
    blend_weights = [lerp(fresh[i], stale[i % len(stale)], t) for i in range(min(len(fresh), len(stale)))]
    return counts, ess(blend_weights)


def draw_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], x_label: str, y_label: str) -> None:
    x1, y1, x2, y2 = box
    draw.line((x1, y2, x2, y2), fill=BLACK, width=2)
    draw.line((x1, y1, x1, y2), fill=BLACK, width=2)
    for i in range(6):
        y = y1 + (y2 - y1) * i / 5
        draw.line((x1, y, x2, y), fill=GRID, width=1)
    for i in range(7):
        x = x1 + (x2 - x1) * i / 6
        draw.line((x, y1, x, y2), fill=(230, 236, 244), width=1)
    draw_text(draw, ((x1 + x2) / 2, y2 + 28), x_label, size=14, fill=MUTED, anchor="mm")
    draw_text(draw, (x1 - 34, (y1 + y2) / 2), y_label, size=14, fill=MUTED, anchor="mm")


def draw_histogram(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    counts: list[float],
    color: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    max_count = max(max(counts), 1.0)
    gap = 2
    bar_w = (x2 - x1) / len(counts)
    for i, count in enumerate(counts):
        h = (count / max_count) * (y2 - y1)
        bx1 = x1 + i * bar_w + gap
        bx2 = x1 + (i + 1) * bar_w - gap
        by1 = y2 - h
        draw.rectangle((bx1, by1, bx2, y2), fill=color)


def scene_title(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    p = ease(t)
    draw_text(draw, (w / 2, 84), "FeynRL Method Explainer", size=40, bold=True, fill=INK, anchor="mm")
    draw_text(draw, (w / 2, 126), "Formula + code + toy example + comparison", size=21, fill=MUTED, anchor="mm")
    card(
        draw,
        (64, 185, 300, 366),
        "Problem",
        "RL post-training reuses rollout data. When the policy changes, old data becomes off-policy.",
        BLUE,
    )
    card(
        draw,
        (362, 185, 598, 366),
        "Mechanism",
        "Policy ratios spread out. ESS measures whether the current batch is trustworthy.",
        ORANGE,
    )
    card(
        draw,
        (660, 185, 896, 366),
        "Method",
        "P3O uses ESS to cap the score update and turn on behavioral KL.",
        GREEN,
    )
    arrow(draw, (300, 275), (362, 275), fill=mix_color(GRID, INK, p), width=3)
    arrow(draw, (598, 275), (660, 275), fill=mix_color(GRID, INK, p), width=3)
    draw_text(draw, (w / 2, 432), "Goal: make the algorithm legible from paper claim to implementation.", size=20, fill=INK, anchor="mm")
    draw_footer(draw, w, h, "Scene 1/6: what this video is", 0, 6)
    return img


def scene_loop(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    draw_text(draw, (48, 54), "RL post-training loop", size=31, bold=True)
    draw_text(draw, (50, 92), "The stale-data problem starts in the systems loop, before the loss is even computed.", size=17, fill=MUTED)
    nodes = [
        ("policy pi", 150, 188, BLUE),
        ("rollout", 390, 188, ORANGE),
        ("reward", 630, 188, GREEN),
        ("replay buffer", 390, 350, PURPLE),
        ("train update", 150, 350, RED),
    ]
    phase = (t * 5.0) % 5.0
    for label, x, y, color in nodes:
        pulse = 0.0
        idx = [n[0] for n in nodes].index(label)
        if abs(phase - idx) < 0.5:
            pulse = 1.0 - abs(phase - idx) * 2
        r = 72 + 7 * ease(pulse)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=mix_color(color, WHITE, 0.15), outline=color, width=4)
        draw_text(draw, (x, y - 8), label, size=19, bold=True, fill=WHITE, anchor="mm")
        if label == "replay buffer":
            draw_text(draw, (x, y + 22), "old logprobs", size=13, fill=WHITE, anchor="mm")
    arrow(draw, (222, 188), (318, 188), fill=INK)
    arrow(draw, (462, 188), (558, 188), fill=INK)
    arrow(draw, (630, 260), (462, 330), fill=INK)
    arrow(draw, (318, 350), (222, 350), fill=INK)
    arrow(draw, (150, 278), (150, 260), fill=INK)
    rounded(draw, (707, 310, 904, 456), radius=14, fill=WHITE, outline=(219, 227, 238), width=2)
    draw_text(draw, (728, 338), "Stored per token", size=17, bold=True)
    code = ["old_logprobs", "reward / zscore", "policy_version", "mask"]
    for i, line in enumerate(code):
        draw_text(draw, (732, 372 + i * 22), line, size=15, mono=True, fill=INK)
    draw_footer(draw, w, h, "Scene 2/6: where staleness enters", 1, 6)
    return img


def scene_ratios(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    fresh, stale = make_ratio_data()
    p = ease(t)
    counts, current_ess = blended_counts(fresh, stale, p)
    color = mix_color(BLUE, RED, p)
    draw_text(draw, (48, 54), "Policy ratios tell us how stale the batch is", size=28, bold=True)
    draw_text(draw, (50, 89), "r = pi_theta(token) / pi_old(token). Fresh rollout data clusters near r=1.", size=17, fill=MUTED)
    chart = (72, 150, 612, 420)
    draw_axes(draw, chart, "policy ratio r", "count")
    draw_histogram(draw, chart, counts, color)
    x_one = chart[0] + (1.0 / 3.0) * (chart[2] - chart[0])
    draw.line((x_one, chart[1], x_one, chart[3]), fill=INK, width=2)
    draw_text(draw, (x_one + 5, chart[1] + 12), "r=1", size=13, fill=INK)
    rounded(draw, (665, 152, 900, 423), radius=16, fill=WHITE, outline=(219, 227, 238), width=2)
    draw_text(draw, (688, 184), "Normalized ESS", size=22, bold=True)
    draw_text(draw, (688, 224), "ESS = (sum w)^2", size=22, mono=True, fill=INK)
    draw_text(draw, (748, 252), "/ (n * sum w^2)", size=22, mono=True, fill=INK)
    draw_text(draw, (688, 306), f"current ESS = {current_ess:.3f}", size=24, bold=True, fill=color)
    draw_text(draw, (688, 344), "High ESS: trust PG", size=17, fill=BLUE)
    draw_text(draw, (688, 372), "Low ESS: tighten + KL", size=17, fill=RED)
    draw_footer(draw, w, h, "Scene 3/6: ratio distribution -> ESS", 2, 6)
    return img


def draw_curve(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    xs: list[float],
    ys: list[float],
    color: tuple[int, int, int],
    y_max: float = 1.35,
    width: int = 3,
) -> None:
    x1, y1, x2, y2 = box
    pts = []
    for x, y in zip(xs, ys):
        px = x1 + (x / 3.0) * (x2 - x1)
        py = y2 - (y / y_max) * (y2 - y1)
        pts.append((px, py))
    if len(pts) > 1:
        draw.line(pts, fill=color, width=width, joint="curve")


def scene_comparison(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    draw_text(draw, (48, 54), "Same ratios, different update behavior", size=28, bold=True)
    draw_text(draw, (50, 89), "A positive-advantage token should get a useful signal without letting one ratio dominate.", size=17, fill=MUTED)
    chart = (70, 145, 630, 420)
    draw_axes(draw, chart, "policy ratio r", "update coefficient")
    xs = [i / 100 for i in range(1, 301)]
    hi = 1.2
    ppo = [x if x <= hi else 0.0 for x in xs]
    cispo = [min(max(x, 0.8), 1.2) for x in xs]
    p3o_fresh = [min(x, 0.95) for x in xs]
    p3o_stale = [min(x, 0.35) for x in xs]
    reveal = ease(t)
    series = [
        ("PPO/GRPO fixed clip", ppo, ORANGE),
        ("CISPO detached weight", cispo, GREEN),
        ("P3O fresh ESS=0.95", p3o_fresh, BLUE),
        ("P3O stale ESS=0.35", p3o_stale, RED),
    ]
    cutoff = max(2, int(len(xs) * reveal))
    for _name, ys, color in series:
        draw_curve(draw, chart, xs[:cutoff], ys[:cutoff], color)
    rounded(draw, (670, 142, 906, 422), radius=16, fill=WHITE, outline=(219, 227, 238), width=2)
    y = 172
    for name, _ys, color in series:
        draw.line((694, y, 742, y), fill=color, width=4)
        draw_text(draw, (754, y - 10), name, size=15, fill=INK)
        y += 46
    draw_text(draw, (692, 374), "P3O moves the cap with", size=16, fill=MUTED)
    draw_text(draw, (692, 398), "the batch's own ESS.", size=16, bold=True, fill=INK)
    draw_footer(draw, w, h, "Scene 4/6: related-method comparison", 3, 6)
    return img


def scene_code(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    draw_text(draw, (48, 54), "Formula and code align", size=28, bold=True)
    draw_text(draw, (50, 89), "The implementation path is small: ratio -> ESS -> capped score update -> behavioral KL.", size=17, fill=MUTED)
    rounded(draw, (56, 142, 452, 425), radius=16, fill=WHITE, outline=(219, 227, 238), width=2)
    draw_text(draw, (82, 176), "P3O objective pieces", size=22, bold=True)
    lines = [
        "ratio r = exp(logp - old_logp)",
        "ESS = (sum r)^2 / (n * sum r^2)",
        "rho = clamp(r, 0, ESS)",
        "loss = -sg(rho) * logp * A",
        "       + (1 - ESS) * KL(pi || pi_old)",
    ]
    for i, line in enumerate(lines):
        fill = [MUTED, BLUE, BLUE, INK, RED][i]
        draw_text(draw, (84, 218 + i * 36), line, size=18, mono=True, fill=fill)
    rounded(draw, (500, 142, 906, 425), radius=16, fill=BLACK, outline=(38, 47, 61), width=2)
    code = [
        "ratio = torch.exp(logprobs - old_logprobs)",
        "ess_factor = self.calculate_ess(ratio, mask)",
        "rho = torch.clamp(ratio, min=0, max=ess_factor)",
        "pi_sum = -(rho.detach() * logprobs * adv * mask).sum()",
        "loss = pi_sum + (1 - ess_factor) * kl_behavioral",
    ]
    hi = int(ease(t) * (len(code) + 0.99))
    for i, line in enumerate(code):
        y = 178 + i * 42
        if i < hi:
            draw.rectangle((520, y - 8, 884, y + 26), fill=(50, 65, 85))
        draw_text(draw, (530, y), line, size=14, mono=True, fill=(232, 239, 247))
    draw_text(draw, (520, 396), "external/FeynRL/algs/P3O/p3o.py", size=13, mono=True, fill=(154, 168, 188))
    draw_footer(draw, w, h, "Scene 5/6: formula -> implementation", 4, 6)
    return img


def scene_systems(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    draw_text(draw, (48, 54), "Why FeynRL cares about sync vs async", size=27, bold=True)
    draw_text(draw, (50, 89), "Async improves hardware usage, but it makes the replay buffer mix policy versions.", size=17, fill=MUTED)
    draw_text(draw, (70, 142), "Sync mode", size=18, bold=True)
    draw_text(draw, (70, 310), "Overlap / async mode", size=18, bold=True)
    y1 = 172
    blocks = [("rollout v", BLUE), ("train", GREEN), ("sync", PURPLE), ("rollout v+1", BLUE)]
    x = 76
    for label, color in blocks:
        rounded(draw, (x, y1, x + 150, y1 + 72), radius=12, fill=color)
        draw_text(draw, (x + 75, y1 + 36), label, size=17, bold=True, fill=WHITE, anchor="mm")
        if x < 680:
            arrow(draw, (x + 150, y1 + 36), (x + 190, y1 + 36), fill=INK, width=2)
        x += 190
    draw_text(draw, (74, 262), "mostly fresh ratios near r=1", size=15, fill=MUTED)
    y2 = 342
    blocks2 = [("rollout workers", BLUE), ("bounded replay", ORANGE), ("training workers", GREEN)]
    x = 78
    for label, color in blocks2:
        rounded(draw, (x, y2, x + 200, y2 + 78), radius=12, fill=color)
        draw_text(draw, (x + 100, y2 + 39), label, size=17, bold=True, fill=WHITE, anchor="mm")
        if x < 540:
            arrow(draw, (x + 200, y2 + 39), (x + 250, y2 + 39), fill=INK, width=2)
        x += 250
    packet_x = 78 + ease(t) * 710
    draw.ellipse((packet_x, y2 + 98, packet_x + 18, y2 + 116), fill=RED)
    draw_text(draw, (804, y2 + 108), "stale samples", size=15, fill=RED)
    draw_text(draw, (74, 457), "Fixed-clip methods need decoupling. ESS-adaptive methods respond to the batch.", size=17, fill=INK)
    draw_footer(draw, w, h, "Scene 6/6: systems mode changes the data regime", 5, 6)
    return img


def scene_end(size: tuple[int, int], t: float) -> Image.Image:
    img, draw = base_frame(size)
    w, h = size
    draw_text(draw, (w / 2, 70), "Takeaway", size=38, bold=True, anchor="mm")
    items = [
        ("Formula", "ESS turns ratio concentration into a control signal.", BLUE),
        ("Code", "FeynRL exposes this in calculate_ess and compute_policy_loss.", GREEN),
        ("Example", "Fresh and stale batches produce visibly different ESS.", ORANGE),
        ("Comparison", "P3O adapts where PPO/GRPO use fixed clipping.", RED),
    ]
    y = 134
    for i, (title, body, color) in enumerate(items):
        alpha = ease(max(0.0, min(1.0, t * 1.4 - i * 0.18)))
        x = int(120 - (1 - alpha) * 60)
        rounded(draw, (x, y, 840, y + 74), radius=14, fill=WHITE, outline=(219, 227, 238), width=2)
        draw.rectangle((x, y, x + 8, y + 74), fill=color)
        draw_text(draw, (x + 24, y + 18), title, size=20, bold=True, fill=INK)
        draw_text(draw, (x + 150, y + 21), body, size=17, fill=MUTED)
        y += 86
    draw_text(draw, (w / 2, 492), "Next: replace toy examples with real FeynRL traces, then render the scenes in Manim.", size=18, fill=INK, anchor="mm")
    draw_footer(draw, w, h, "Final scene: what the full pipeline should learn to generate", 6, 6)
    return img


SCENES = [
    ("title", 2.7, scene_title),
    ("loop", 3.2, scene_loop),
    ("ratios", 4.0, scene_ratios),
    ("comparison", 4.0, scene_comparison),
    ("code", 4.0, scene_code),
    ("systems", 3.8, scene_systems),
    ("end", 3.0, scene_end),
]


def write_html(out_dir: Path, gif_name: str, metadata: dict) -> None:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>FeynRL Explainer Prototype</title>
  <style>
    body {{ margin: 0; background: #111827; color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 32px; }}
    img {{ width: 100%; height: auto; border-radius: 12px; background: #f7f9fc; }}
    code {{ background: #1f2937; padding: 2px 6px; border-radius: 4px; }}
    .meta {{ color: #cbd5e1; }}
  </style>
</head>
<body>
<main>
  <h1>FeynRL Explainer Prototype</h1>
  <p class="meta">Generated by <code>tools/feynrl_explainer_video.py</code>. Duration: {metadata["duration_sec"]:.1f}s, FPS: {metadata["fps"]}.</p>
  <img src="{gif_name}" alt="FeynRL explainer animation">
  <p class="meta">This is a dependency-light prototype. It renders formula, code, toy examples, and comparison beats as an animated GIF.</p>
</main>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def try_write_mp4(frames_dir: Path, out_path: Path, fps: int) -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%04d.png"),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode == 0 and out_path.exists()


def render(args: argparse.Namespace) -> dict:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    keyframes_dir = out_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    if args.save_all_frames or args.try_mp4:
        frames_dir.mkdir(parents=True, exist_ok=True)

    size = args.size
    frames: list[Image.Image] = []
    scene_keyframes = []
    frame_idx = 0
    for scene_idx, (name, seconds, fn) in enumerate(SCENES):
        count = max(1, int(round(seconds * args.fps)))
        for i in range(count):
            local_t = i / max(count - 1, 1)
            img = fn(size, local_t)
            if i == count // 2:
                key_path = keyframes_dir / f"{scene_idx + 1:02d}_{name}.png"
                img.save(key_path)
                scene_keyframes.append(str(key_path))
            if args.save_all_frames or args.try_mp4:
                img.save(frames_dir / f"frame_{frame_idx:04d}.png")
            frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=96))
            frame_idx += 1

    gif_path = out_dir / "feynrl_p3o_explainer.gif"
    duration_ms = int(round(1000 / args.fps))
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )

    mp4_path = out_dir / "feynrl_p3o_explainer.mp4"
    mp4_created = False
    if args.try_mp4:
        mp4_created = try_write_mp4(frames_dir, mp4_path, args.fps)

    metadata = {
        "title": "FeynRL P3O explainer prototype",
        "fps": args.fps,
        "size": {"width": size[0], "height": size[1]},
        "frames": len(frames),
        "duration_sec": len(frames) / args.fps,
        "gif": str(gif_path),
        "mp4": str(mp4_path) if mp4_created else None,
        "keyframes": scene_keyframes,
        "scenes": [{"name": name, "seconds": seconds} for name, seconds, _ in SCENES],
        "renderer": "Pillow animated GIF prototype",
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_html(out_dir, gif_path.name, metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a FeynRL explainer animation prototype.")
    parser.add_argument("--out", default="runs/feynrl_p3o_explainer", help="Output directory.")
    parser.add_argument("--fps", type=int, default=8, help="Frames per second for GIF/MP4.")
    parser.add_argument("--size", type=parse_size, default=(960, 540), help="Canvas size, e.g. 960x540.")
    parser.add_argument("--save-all-frames", action="store_true", help="Write every PNG frame for debugging/review.")
    parser.add_argument("--try-mp4", action="store_true", help="Create MP4 too if ffmpeg is installed.")
    args = parser.parse_args()
    metadata = render(args)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
