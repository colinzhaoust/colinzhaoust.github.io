"""Reusable, text-light Manim composites for paper-native explainers.

The classes in this module sit one level above Manim Community's stock
``MathTex``, ``Rectangle``, ``Arrow``, ``NumberLine``, and animation classes.
They are deterministic consumers of numeric or symbolic inputs; generated
paper text remains in the website.
"""

from __future__ import annotations

import math

from manim import (
    Arrow,
    Circle,
    DecimalNumber,
    Dot,
    DOWN,
    LEFT,
    Line,
    MathTex,
    NumberLine,
    ORIGIN,
    Rectangle,
    RIGHT,
    RoundedRectangle,
    Scene,
    Text,
    UP,
    VGroup,
)


PAPER = "#F6F1E7"
INK = "#18202B"
MUTED = "#657083"
RULE = "#CBD0C8"
CURRENT = "#2563A9"
BEHAVIOR = "#7652A8"
ADAPTIVE = "#16815D"
WARNING = "#D36A29"
CORAL = "#C74E45"
SOFT = "#E9E4D9"
CODE_BG = "#202735"
CODE_INK = "#ECF0EA"


def normalized_ess(values: list[float]) -> float:
    """Return the normalized ESS used in FeynRL Eq. (11)."""

    if not values:
        raise ValueError("normalized_ess needs at least one policy ratio")
    mean = sum(values) / len(values)
    mean_square = sum(value * value for value in values) / len(values)
    return 0.0 if mean_square == 0 else mean * mean / mean_square


class PaperNativeScene(Scene):
    """Shared scene chrome. Prose belongs to HTML, not this base class."""

    def setup(self) -> None:
        self.camera.background_color = PAPER

    def heading(self, title: str, section: str) -> VGroup:
        tag = Text(section, font="Menlo", font_size=18, color=WARNING, weight="BOLD")
        name = Text(title, font_size=38, color=INK, weight="BOLD")
        group = VGroup(tag, name).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(UP, buff=0.34).to_edge(LEFT, buff=0.52)
        rule = Line(LEFT * 6.15, RIGHT * 6.15, stroke_color=RULE, stroke_width=1).next_to(group, DOWN, buff=0.2)
        return VGroup(group, rule)

    def source(self, text: str) -> Text:
        return Text(text, font="Menlo", font_size=14, color=MUTED).to_edge(DOWN, buff=0.24).to_edge(RIGHT, buff=0.42)

    def term(self, title: str, body: str, color: str, width: float = 5.5) -> VGroup:
        dot = Dot(radius=0.07, color=color)
        title_mob = Text(title, font_size=25, color=INK, weight="BOLD")
        body_mob = Text(body, font_size=18, color=MUTED, line_spacing=0.9)
        if body_mob.width > width - 0.42:
            body_mob.scale_to_fit_width(width - 0.42)
        copy = VGroup(title_mob, body_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        return VGroup(dot, copy).arrange(RIGHT, aligned_edge=UP, buff=0.17)

    def ratio_bars(self, values: list[float], labels: list[str] | None = None) -> VGroup:
        return RatioBars(values, labels)

    def code_panel(self, rows: list[tuple[str, str]], width: float = 11.7) -> VGroup:
        return FormulaCodeBridge(rows, width=width)

    def value_bar(self, label: str, value: float, maximum: float, color: str, unit: str = "") -> VGroup:
        name = Text(label, font_size=19, color=INK)
        if name.width > 2.35:
            name.scale_to_fit_width(2.35)
        label_slot = Rectangle(width=2.45, height=0.44, stroke_opacity=0, fill_opacity=0)
        name.move_to(label_slot).align_to(label_slot, LEFT)
        track = RoundedRectangle(width=5.0, height=0.38, corner_radius=0.06, fill_color=SOFT, fill_opacity=1, stroke_width=0)
        fill = RoundedRectangle(width=max(0.08, 5.0 * value / maximum), height=0.38, corner_radius=0.06, fill_color=color, fill_opacity=1, stroke_width=0)
        fill.align_to(track, LEFT)
        number = Text(f"{value:.3f}{unit}", font="Menlo", font_size=18, color=color, weight="BOLD")
        return VGroup(VGroup(label_slot, name), VGroup(track, fill), number).arrange(RIGHT, buff=0.22)


class RatioBars(VGroup):
    """A fixed-order ratio histogram suitable for state-to-state transforms."""

    def __init__(self, values: list[float], labels: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        maximum = max(values) if values else 1.0
        bars = VGroup()
        token_labels = labels or [f"t{i + 1}" for i in range(len(values))]
        for value, label in zip(values, token_labels):
            height = max(0.08, 1.65 * value / maximum)
            bar = Rectangle(width=0.58, height=height, fill_color=ADAPTIVE, fill_opacity=0.9, stroke_width=0)
            value_label = DecimalNumber(value, num_decimal_places=1, font_size=18, color=INK).next_to(bar, UP, buff=0.08)
            token = Text(label, font="Menlo", font_size=14, color=MUTED).next_to(bar, DOWN, buff=0.1)
            bars.add(VGroup(bar, value_label, token))
        bars.arrange(RIGHT, aligned_edge=DOWN, buff=0.18)
        baseline = Line(bars.get_left() + DOWN * 0.12, bars.get_right() + DOWN * 0.12, color=RULE, stroke_width=2)
        self.add(baseline, bars)


class EssTradeoffGauge(VGroup):
    """Bind one ratio batch to physical count, normalized ESS, cap, and KL weight."""

    def __init__(self, values: list[float], *, include_controls: bool = False, **kwargs):
        super().__init__(**kwargs)
        ess = normalized_ess(values)
        ratios = RatioBars(values)
        physical = VGroup(
            Text("tokens", font="Menlo", font_size=16, color=MUTED),
            DecimalNumber(len(values), num_decimal_places=0, font_size=30, color=INK),
        ).arrange(DOWN, buff=0.08)
        effective = VGroup(
            MathTex(r"e_B", font_size=30, color=ADAPTIVE),
            DecimalNumber(ess, num_decimal_places=3, font_size=30, color=ADAPTIVE),
        ).arrange(DOWN, buff=0.08)
        readouts = VGroup(physical, effective).arrange(RIGHT, buff=0.65)
        core = VGroup(ratios, readouts).arrange(RIGHT, buff=0.8)
        self.add(core)
        self.ess = ess
        if include_controls:
            cap = self._meter(r"\min(\rho_t,e_B)", ess, ADAPTIVE)
            kl = self._meter(r"1-e_B", 1 - ess, WARNING)
            controls = VGroup(cap, kl).arrange(DOWN, aligned_edge=LEFT, buff=0.38)
            controls.next_to(core, RIGHT, buff=0.9)
            self.add(controls)

    @staticmethod
    def _meter(label: str, value: float, color: str) -> VGroup:
        tex = MathTex(label, font_size=25, color=INK)
        track = RoundedRectangle(width=2.7, height=0.28, corner_radius=0.05, fill_color=SOFT, fill_opacity=1, stroke_width=0)
        fill = RoundedRectangle(width=max(0.06, 2.7 * value), height=0.28, corner_radius=0.05, fill_color=color, fill_opacity=1, stroke_width=0)
        fill.align_to(track, LEFT)
        number = DecimalNumber(value, num_decimal_places=3, font_size=20, color=color)
        return VGroup(tex, VGroup(track, fill), number).arrange(RIGHT, buff=0.18)


class FormulaCodeBridge(VGroup):
    """Compact code rows with explicit formula-fragment labels."""

    def __init__(self, rows: list[tuple[str, str]], *, width: float = 11.7, **kwargs):
        super().__init__(**kwargs)
        box = RoundedRectangle(width=width, height=0.62 * len(rows) + 0.42, corner_radius=0.12, fill_color=CODE_BG, fill_opacity=1, stroke_width=0)
        lines = VGroup()
        for code, meaning in rows:
            code_mob = Text(code, font="Menlo", font_size=17, color=CODE_INK)
            meaning_mob = Text(meaning, font_size=16, color="#F1A56E")
            row = VGroup(code_mob, meaning_mob).arrange(RIGHT, buff=0.35)
            if row.width > width - 0.56:
                row.scale_to_fit_width(width - 0.56)
            lines.add(row)
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to(box).align_to(box, LEFT).shift(RIGHT * 0.28)
        self.add(box, lines)


class RoPERelativeRotation(VGroup):
    """Visualize separate m/n rotations and their relative angle in one plane."""

    def __init__(self, *, m_angle: float = 0.55, n_angle: float = 1.2, **kwargs):
        super().__init__(**kwargs)
        radius = 1.65
        circle = Circle(radius=radius, color=RULE)
        axes = VGroup(
            Line(LEFT * 1.9, RIGHT * 1.9, color=RULE),
            Line(DOWN * 1.9, UP * 1.9, color=RULE),
        )
        q0 = Arrow(ORIGIN, RIGHT * 1.35, buff=0, stroke_width=6, color=CURRENT)
        k0 = Arrow(ORIGIN, RIGHT * 1.15 + DOWN * 0.35, buff=0, stroke_width=6, color=BEHAVIOR)
        q1 = Arrow(ORIGIN, [1.35 * math.cos(m_angle), 1.35 * math.sin(m_angle), 0], buff=0, stroke_width=7, color=CURRENT)
        base_k = math.atan2(-0.35, 1.15)
        k1 = Arrow(ORIGIN, [1.2 * math.cos(base_k + n_angle), 1.2 * math.sin(base_k + n_angle), 0], buff=0, stroke_width=7, color=BEHAVIOR)
        center = Dot(radius=0.06, color=INK)
        labels = VGroup(
            MathTex(r"R_m q", font_size=26, color=CURRENT).next_to(q1.get_end(), UP, buff=0.08),
            MathTex(r"R_n k", font_size=26, color=BEHAVIOR).next_to(k1.get_end(), LEFT, buff=0.08),
            MathTex(r"R_m^\top R_n=R_{n-m}", font_size=32, color=WARNING).next_to(circle, DOWN, buff=0.3),
        )
        self.initial_vectors = VGroup(q0, k0)
        self.rotated_vectors = VGroup(q1, k1)
        self.frame = VGroup(circle, axes, center)
        self.labels = labels
        self.add(self.frame, self.initial_vectors, self.rotated_vectors, labels)
        self.rotated_vectors.set_opacity(0)
        labels.set_opacity(0)
