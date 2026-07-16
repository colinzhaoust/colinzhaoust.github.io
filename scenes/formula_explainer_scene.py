"""Generic deterministic renderer for a compiled formula-explainer SceneIR.

Usage:
  FORMULA_SCENE_IR=runs/formula_explainer/build/scene_ir/attention_softmax_lookup/attention_softmax.json \
    manim -ql --media_dir runs/formula_explainer/render scenes/formula_explainer_scene.py FormulaExplainerScene
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from manim import *

ROOT = Path(__file__).resolve().parents[1]
BG = "#08111F"
INK = "#F8FAFC"
MUTED = "#94A3B8"
BUILT_IN = "#16A34A"
PROJECT = "#7C3AED"
ONE_OFF = "#EA580C"
MISSING = "#6B7280"


def load_scene_bundle() -> tuple[dict, dict, dict]:
    scene_ref = os.environ.get(
        "FORMULA_SCENE_IR",
        "runs/formula_explainer/build/scene_ir/attention_softmax_lookup/attention_softmax.json",
    )
    scene_path = Path(scene_ref)
    if not scene_path.is_absolute():
        scene_path = ROOT / scene_path
    scene_ir = json.loads(scene_path.read_text(encoding="utf-8"))
    formula_ir = json.loads((ROOT / scene_ir["formula_ir_ref"]).read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "data/formula_explainer/primitive_registry.json").read_text(encoding="utf-8"))
    return scene_ir, formula_ir, registry


class OperationWalk(VGroup):
    def __init__(self, operations: list[dict], primitives: dict[str, dict], **kwargs):
        super().__init__(**kwargs)
        cards = []
        for operation in operations:
            primitive = primitives[operation["primitive_ref"]]
            origin = primitive["origin"]
            color = {
                "built_in": BUILT_IN,
                "project_reusable": PROJECT,
                "generated_one_off": ONE_OFF,
                "missing_planned": MISSING,
            }[origin]
            badge = {
                "built_in": "LIB",
                "project_reusable": "OURS",
                "generated_one_off": "1-OFF",
                "missing_planned": "TODO",
            }[origin]
            box = RoundedRectangle(width=1.62, height=0.86, corner_radius=0.12, stroke_color=color, fill_color="#111C2E", fill_opacity=1)
            label = Text(operation["operation_type"], font_size=19, color=INK).move_to(box.get_center() + UP * 0.13)
            tag = Text(badge, font_size=12, color=color, weight=BOLD).move_to(box.get_center() + DOWN * 0.23)
            cards.append(VGroup(box, label, tag))
        row = VGroup(*cards).arrange(RIGHT, buff=0.22)
        if row.width > 12.6:
            row.scale_to_fit_width(12.6)
        arrows = VGroup(*[
            Arrow(cards[i].get_right(), cards[i + 1].get_left(), buff=0.06, color=MUTED, stroke_width=2, max_tip_length_to_length_ratio=0.22)
            for i in range(len(cards) - 1)
        ])
        self.add(row, arrows)


class SoftmaxProbabilityFlow(VGroup):
    RAW = [1.0, 2.0, 0.0]
    EXP = [2.72, 7.39, 1.0]
    PROBS = [0.245, 0.665, 0.090]

    @staticmethod
    def chart(values: list[float], title: str, y_range: list[float]) -> VGroup:
        # Manim's BarChart creates MathTex for axis labels, which makes a
        # conceptually simple chart depend on a full LaTeX installation.  This
        # reusable primitive deliberately composes Rectangle/Line/Text instead.
        colors = ["#38BDF8", "#A78BFA", "#FB7185"]
        scale_max = max(float(y_range[1]), max(values), 1e-6)
        baseline = Line(LEFT * 2.6, RIGHT * 2.6, color=MUTED, stroke_width=2)
        bars = VGroup()
        labels = VGroup()
        value_labels = VGroup()
        for index, (value, color) in enumerate(zip(values, colors)):
            height = max(0.06, 2.15 * float(value) / scale_max)
            bar = Rectangle(width=1.05, height=height, fill_color=color, fill_opacity=0.88, stroke_width=0)
            x = -1.55 + index * 1.55
            bar.move_to([x, height / 2, 0])
            bars.add(bar)
            labels.add(Text(f"token {chr(65 + index)}", font_size=18, color=MUTED).move_to([x, -0.30, 0]))
            value_labels.add(Text(f"{value:.3g}", font_size=17, color=INK).next_to(bar, UP, buff=0.06))
        chart = VGroup(baseline, bars, labels, value_labels)
        heading = Text(title, font_size=24, color=INK, weight=BOLD).next_to(chart, UP, buff=0.18)
        return VGroup(chart, heading)


class FormulaExplainerScene(Scene):
    def construct(self):
        self.camera.background_color = BG
        scene_ir, formula, registry = load_scene_bundle()
        primitives = {item["primitive_id"]: item for item in registry["primitives"]}

        title = Text(scene_ir["title"], font_size=38, color=INK, weight=BOLD).to_edge(UP, buff=0.35)
        formula_text = Text(formula["display"]["plain_text"], font_size=27, color="#BAE6FD")
        formula_text.scale_to_fit_width(min(12.4, formula_text.width))
        formula_text.next_to(title, DOWN, buff=0.25)
        source = Text(formula["source_anchor"]["locator"], font_size=16, color=MUTED).next_to(formula_text, DOWN, buff=0.16)
        self.play(Write(title), FadeIn(formula_text, shift=UP * 0.15), FadeIn(source), run_time=1.0)

        walk = OperationWalk(formula["operations"], primitives).next_to(source, DOWN, buff=0.36)
        self.play(LaggedStart(*[FadeIn(card, shift=RIGHT * 0.12) for card in walk[0]], lag_ratio=0.12), Create(walk[1]), run_time=1.2)

        if formula["formula_id"] in {"formula:attention.softmax", "formula:transformers.attention"}:
            raw = SoftmaxProbabilityFlow.chart(SoftmaxProbabilityFlow.RAW, "raw scores", [0, 8, 2]).scale(0.72).move_to([-1.25, -1.65, 0])
            exp = SoftmaxProbabilityFlow.chart(SoftmaxProbabilityFlow.EXP, "exp(score)", [0, 8, 2]).scale(0.72).move_to(raw)
            probs = SoftmaxProbabilityFlow.chart(SoftmaxProbabilityFlow.PROBS, "normalized weights", [0, 1, 0.25]).scale(0.72).move_to(raw)
            self.play(FadeIn(raw, shift=UP * 0.15), run_time=0.7)
            self.play(Transform(raw, exp), run_time=0.9)
            self.play(Transform(raw, probs), run_time=0.9)
            sum_label = Text("0.245 + 0.665 + 0.090 = 1.000", font_size=22, color="#86EFAC", weight=BOLD).move_to([3.85, -0.72, 0])
            self.play(FadeIn(sum_label, shift=LEFT * 0.15), run_time=0.5)
        else:
            evidence = Text("candidate mappings stay visible until review", font_size=25, color="#FDBA74").to_edge(DOWN, buff=0.7)
            self.play(FadeIn(evidence), run_time=0.6)

        legend = VGroup(
            Text("LIB = Manim built-in", font_size=15, color=BUILT_IN),
            Text("OURS = project reusable", font_size=15, color=PROJECT),
            Text("1-OFF = authored candidate", font_size=15, color=ONE_OFF),
            Text("TODO = missing", font_size=15, color=MISSING),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to([4.7, -1.78, 0])
        self.play(FadeIn(legend), run_time=0.5)
        self.wait(0.8)
