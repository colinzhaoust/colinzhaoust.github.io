#!/usr/bin/env python3
"""Generate lightweight SVG illustrations for FeynRL-style objectives.

This is intentionally not a FeynRL training runner. The real FeynRL classes are
Ray actors that initialize model and DeepSpeed state. For explanation videos we
usually want a pure, deterministic toy model of the math:

- PPO/GRPO fixed clipping,
- CISPO detached clipped-ratio score weighting,
- P3O ESS-based score cap and adaptive KL weight,
- sync vs. async rollout/training scheduling.

Run:
    python3 tools/feynrl_method_viz.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path


OUT_DIR = Path("renders/feynrl_method_viz")


def ess(weights: list[float]) -> float:
    """Normalized effective sample size used by FeynRL's P3O implementation."""
    n = len(weights)
    if n == 0:
        return 1.0
    sum_w = sum(weights)
    sum_w2 = sum(w * w for w in weights)
    if sum_w2 <= 0:
        return 1.0
    return (sum_w * sum_w) / (n * sum_w2)


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #1f2933; }",
        ".title { font-size: 22px; font-weight: 700; }",
        ".label { font-size: 13px; }",
        ".small { font-size: 11px; fill: #52616b; }",
        ".axis { stroke: #2f3a45; stroke-width: 1.2; }",
        ".grid { stroke: #d8dee6; stroke-width: 1; }",
        ".legend { font-size: 12px; }",
        "</style>",
    ]


def svg_footer() -> str:
    return "</svg>\n"


def polyline(points: list[tuple[float, float]], color: str, width: float = 2.5, dash: str | None = None) -> str:
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{dash_attr}/>'


def line_chart(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    x_values: list[float],
    series: list[tuple[str, list[float], str, str | None]],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    annotations: list[tuple[float, str]] | None = None,
) -> None:
    width, height = 920, 560
    left, right, top, bottom = 82, 34, 72, 78
    plot_w = width - left - right
    plot_h = height - top - bottom
    xmin, xmax = x_range
    ymin, ymax = y_range

    def sx(x: float) -> float:
        return left + (x - xmin) / (xmax - xmin) * plot_w

    def sy(y: float) -> float:
        return top + (ymax - y) / (ymax - ymin) * plot_h

    lines = svg_header(width, height)
    lines.append(f'<text class="title" x="{left}" y="38">{title}</text>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>')

    for i in range(6):
        y = ymin + i * (ymax - ymin) / 5
        py = sy(y)
        lines.append(f'<line class="grid" x1="{left}" y1="{py:.2f}" x2="{left + plot_w}" y2="{py:.2f}"/>')
        lines.append(f'<text class="small" x="{left - 10}" y="{py + 4:.2f}" text-anchor="end">{y:.2f}</text>')

    for i in range(7):
        x = xmin + i * (xmax - xmin) / 6
        px = sx(x)
        lines.append(f'<line class="grid" x1="{px:.2f}" y1="{top}" x2="{px:.2f}" y2="{top + plot_h}"/>')
        lines.append(f'<text class="small" x="{px:.2f}" y="{top + plot_h + 23}" text-anchor="middle">{x:.1f}</text>')

    if annotations:
        for x, text in annotations:
            px = sx(x)
            lines.append(f'<line x1="{px:.2f}" y1="{top}" x2="{px:.2f}" y2="{top + plot_h}" stroke="#8b98a8" stroke-width="1" stroke-dasharray="4 5"/>')
            lines.append(f'<text class="small" x="{px + 5:.2f}" y="{top + 18}">{text}</text>')

    for name, values, color, dash in series:
        pts = [(sx(x), sy(y)) for x, y in zip(x_values, values)]
        lines.append(polyline(pts, color, dash=dash))

    legend_x = left + plot_w - 250
    legend_y = top + 24
    for idx, (name, _values, color, dash) in enumerate(series):
        y = legend_y + idx * 24
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 34}" y2="{y}" stroke="{color}" stroke-width="3"{dash_attr}/>')
        lines.append(f'<text class="legend" x="{legend_x + 44}" y="{y + 4}">{name}</text>')

    lines.append(f'<text class="label" x="{left + plot_w / 2}" y="{height - 24}" text-anchor="middle">{x_label}</text>')
    lines.append(f'<text class="label" x="22" y="{top + plot_h / 2}" transform="rotate(-90 22 {top + plot_h / 2})" text-anchor="middle">{y_label}</text>')
    lines.append(svg_footer())
    path.write_text("\n".join(lines), encoding="utf-8")


def histogram(path: Path) -> None:
    random.seed(7)
    fresh = [math.exp(random.gauss(0.0, 0.055)) for _ in range(500)]
    stale = [math.exp(random.gauss(-0.35, 0.55)) for _ in range(420)] + [math.exp(random.gauss(1.0, 0.35)) for _ in range(80)]
    fresh_ess = ess(fresh)
    stale_ess = ess(stale)

    width, height = 920, 560
    left, right, top, bottom = 82, 34, 78, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    xmin, xmax = 0.0, 3.0
    bins = 28
    bin_w = (xmax - xmin) / bins

    def counts(values: list[float]) -> list[int]:
        out = [0 for _ in range(bins)]
        for value in values:
            if value < xmin or value > xmax:
                continue
            idx = min(bins - 1, int((value - xmin) / bin_w))
            out[idx] += 1
        return out

    fresh_counts = counts(fresh)
    stale_counts = counts(stale)
    max_count = max(max(fresh_counts), max(stale_counts), 1)

    def sx_bin(i: int) -> float:
        return left + i / bins * plot_w

    def sy_count(c: int) -> float:
        return top + plot_h - c / max_count * plot_h

    lines = svg_header(width, height)
    lines.append(f'<text class="title" x="{left}" y="38">Policy-ratio distributions drive ESS</text>')
    lines.append(f'<text class="small" x="{left}" y="60">fresh ESS={fresh_ess:.3f}; stale/off-policy ESS={stale_ess:.3f}</text>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>')

    for i in range(7):
        x = xmin + i * (xmax - xmin) / 6
        px = left + (x - xmin) / (xmax - xmin) * plot_w
        lines.append(f'<line class="grid" x1="{px:.2f}" y1="{top}" x2="{px:.2f}" y2="{top + plot_h}"/>')
        lines.append(f'<text class="small" x="{px:.2f}" y="{top + plot_h + 23}" text-anchor="middle">{x:.1f}</text>')

    for i, c in enumerate(fresh_counts):
        x = sx_bin(i)
        w = plot_w / bins * 0.46
        y = sy_count(c)
        h = top + plot_h - y
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#2f80ed" opacity="0.62"/>')

    for i, c in enumerate(stale_counts):
        x = sx_bin(i) + plot_w / bins * 0.48
        w = plot_w / bins * 0.46
        y = sy_count(c)
        h = top + plot_h - y
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#d64545" opacity="0.58"/>')

    lines.append(f'<rect x="{left + plot_w - 232}" y="{top + 12}" width="18" height="12" fill="#2f80ed" opacity="0.62"/>')
    lines.append(f'<text class="legend" x="{left + plot_w - 206}" y="{top + 23}">fresh rollout data</text>')
    lines.append(f'<rect x="{left + plot_w - 232}" y="{top + 38}" width="18" height="12" fill="#d64545" opacity="0.58"/>')
    lines.append(f'<text class="legend" x="{left + plot_w - 206}" y="{top + 49}">stale / mixed replay</text>')
    lines.append(f'<text class="label" x="{left + plot_w / 2}" y="{height - 24}" text-anchor="middle">policy ratio r = pi_theta / pi_old</text>')
    lines.append(f'<text class="label" x="22" y="{top + plot_h / 2}" transform="rotate(-90 22 {top + plot_h / 2})" text-anchor="middle">token count</text>')
    lines.append(svg_footer())
    path.write_text("\n".join(lines), encoding="utf-8")


def objective_curves(path: Path) -> None:
    xs = [i / 100 for i in range(1, 301)]
    clip_low, clip_high = 0.2, 0.2
    lo, hi = 1.0 - clip_low, 1.0 + clip_high

    ppo_pos_grad = [x if x <= hi else 0.0 for x in xs]
    cispo_weight = [min(max(x, lo), hi) for x in xs]
    p3o_fresh = [min(x, 0.95) for x in xs]
    p3o_stale = [min(x, 0.35) for x in xs]

    line_chart(
        path=path,
        title="Update coefficient for a positive-advantage token",
        x_label="policy ratio r",
        y_label="effective score/update coefficient",
        x_values=xs,
        series=[
            ("PPO/GRPO fixed clip", ppo_pos_grad, "#ef7d00", None),
            ("CISPO detached clipped weight", cispo_weight, "#2c9c69", None),
            ("P3O ESS cap, fresh ESS=0.95", p3o_fresh, "#2f80ed", "7 5"),
            ("P3O ESS cap, stale ESS=0.35", p3o_stale, "#d64545", "7 5"),
        ],
        x_range=(0.0, 3.0),
        y_range=(0.0, 1.35),
        annotations=[(lo, "1-eps"), (hi, "1+eps")],
    )


def p3o_tradeoff(path: Path) -> None:
    xs = [i / 100 for i in range(1, 101)]
    cap = xs
    kl_weight = [1.0 - x for x in xs]
    line_chart(
        path=path,
        title="P3O uses one batch statistic for two controls",
        x_label="normalized ESS of current batch",
        y_label="control strength",
        x_values=xs,
        series=[
            ("score-function cap = ESS", cap, "#2f80ed", None),
            ("behavioral KL weight = 1 - ESS", kl_weight, "#d64545", None),
        ],
        x_range=(0.0, 1.0),
        y_range=(0.0, 1.0),
        annotations=None,
    )


def timeline(path: Path) -> None:
    width, height = 1000, 560
    lines = svg_header(width, height)
    lines.append('<text class="title" x="64" y="42">FeynRL execution modes: sync vs. overlap</text>')
    lines.append('<text class="small" x="64" y="64">The same objective can see very different policy-ratio distributions depending on scheduling.</text>')

    def block(x: int, y: int, w: int, h: int, color: str, text: str, sub: str = "") -> None:
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{color}" opacity="0.9"/>')
        lines.append(f'<text x="{x + w / 2}" y="{y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="#ffffff">{text}</text>')
        if sub:
            lines.append(f'<text x="{x + w / 2}" y="{y + 50}" text-anchor="middle" font-size="11" fill="#ffffff">{sub}</text>')

    def arrow(x1: int, y1: int, x2: int, y2: int) -> None:
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2f3a45" stroke-width="2" marker-end="url(#arrow)"/>')

    lines.append('<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#2f3a45"/></marker></defs>')

    lines.append('<text class="label" x="64" y="116" font-weight="700">Sync mode</text>')
    y = 140
    block(70, y, 160, 72, "#2f80ed", "rollout", "pi_v")
    block(270, y, 160, 72, "#2c9c69", "train", "fresh batch")
    block(470, y, 160, 72, "#8b5cf6", "sync weights", "v -> v+1")
    block(670, y, 160, 72, "#2f80ed", "rollout", "pi_v+1")
    arrow(230, y + 36, 270, y + 36)
    arrow(430, y + 36, 470, y + 36)
    arrow(630, y + 36, 670, y + 36)
    lines.append('<text class="small" x="72" y="232">Easy to reason about: rollout data is close to on-policy, so ratio mass stays near 1.</text>')

    lines.append('<text class="label" x="64" y="300" font-weight="700">Overlap / async mode</text>')
    y = 324
    block(70, y, 210, 72, "#2f80ed", "rollout workers", "continuous generation")
    block(330, y, 210, 72, "#f59e0b", "bounded replay", "versions v-k ... v")
    block(590, y, 210, 72, "#2c9c69", "training workers", "consume mixed data")
    block(420, y + 122, 210, 64, "#8b5cf6", "periodic NCCL sync", "policy version advances")
    arrow(280, y + 36, 330, y + 36)
    arrow(540, y + 36, 590, y + 36)
    arrow(695, y + 72, 630, y + 122)
    arrow(420, y + 154, 180, y + 72)
    lines.append('<text class="small" x="72" y="528">Higher throughput, but replay can be stale. Fixed-clip methods need extra decoupling; P3O adapts from ESS.</text>')
    lines.append(svg_footer())
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    histogram(OUT_DIR / "ratio_distributions_ess.svg")
    objective_curves(OUT_DIR / "objective_weight_curves.svg")
    p3o_tradeoff(OUT_DIR / "p3o_ess_tradeoff.svg")
    timeline(OUT_DIR / "sync_vs_async_timeline.svg")
    for path in sorted(OUT_DIR.glob("*.svg")):
        print(path)


if __name__ == "__main__":
    main()
