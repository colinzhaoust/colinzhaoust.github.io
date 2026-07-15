"""Manim-first prototype for a FeynRL/P3O explainer video.

Render with Manim Community:
    manim -ql scenes/feynrl_p3o_explainer.py FeynRLP3OExplainer

This scene intentionally avoids MathTex/LaTeX so it is easier to render on a
fresh machine. Formulas are shown with Text in a monospace style for now.
"""

from __future__ import annotations

import math
import random

from manim import *


BLUE_C = "#2F80ED"
RED_C = "#D64545"
GREEN_C = "#2C9C69"
ORANGE_C = "#EF7D00"
PURPLE_C = "#7E57C2"
YELLOW_C = "#F3BA43"
INK_C = "#1F2937"
MUTED_C = "#586678"
GRID_C = "#D9E0EA"


def normalized_ess(weights: list[float]) -> float:
    if not weights:
        return 1.0
    sum_w = sum(weights)
    sum_w2 = sum(w * w for w in weights)
    if sum_w2 <= 0:
        return 1.0
    return (sum_w * sum_w) / (len(weights) * sum_w2)


def ratio_data() -> tuple[list[float], list[float]]:
    random.seed(42)
    fresh = [math.exp(random.gauss(0.0, 0.055)) for _ in range(420)]
    stale = [math.exp(random.gauss(-0.32, 0.52)) for _ in range(350)]
    stale += [math.exp(random.gauss(0.9, 0.33)) for _ in range(70)]
    return fresh, stale


def histogram_counts(values: list[float], bins: int = 28, xmin: float = 0.0, xmax: float = 3.0) -> list[int]:
    counts = [0 for _ in range(bins)]
    width = (xmax - xmin) / bins
    for value in values:
        if xmin <= value <= xmax:
            idx = min(bins - 1, int((value - xmin) / width))
            counts[idx] += 1
    return counts


class FeynRLP3OExplainer(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#F7F9FC"
        self.intro()
        self.rl_loop()
        self.ratio_to_ess()
        self.method_comparison()
        self.formula_to_code()
        self.systems_view()
        self.takeaway()

    def label(self, text: str, size: int = 28, color: str = INK_C, weight: str = NORMAL) -> Text:
        return Text(text, font_size=size, color=color, weight=weight)

    def mono(self, text: str, size: int = 24, color: str = INK_C) -> Text:
        return Text(text, font="Menlo", font_size=size, color=color)

    def panel(self, width: float, height: float, color: str = WHITE, stroke: str = "#DDE5EF") -> RoundedRectangle:
        return RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.14,
            fill_color=color,
            fill_opacity=1.0,
            stroke_color=stroke,
            stroke_width=2,
        )

    def intro(self) -> None:
        title = self.label("FeynRL Method Explainer", 44, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("Formula + code + toy example + comparison", 24, MUTED_C).next_to(title, DOWN, buff=0.18)

        cards = VGroup(
            self.make_card("Problem", "Replay data can become stale as the policy changes.", BLUE_C),
            self.make_card("Signal", "Policy ratios reveal how trustworthy the batch is.", ORANGE_C),
            self.make_card("Method", "P3O uses ESS to adapt the update.", GREEN_C),
        ).arrange(RIGHT, buff=0.45).shift(DOWN * 0.35)

        arrows = VGroup(
            Arrow(cards[0].get_right(), cards[1].get_left(), buff=0.14, color=INK_C),
            Arrow(cards[1].get_right(), cards[2].get_left(), buff=0.14, color=INK_C),
        )

        footer = self.label("Goal: make the algorithm legible from paper claim to implementation.", 24, INK_C)
        footer.next_to(cards, DOWN, buff=0.65)

        self.play(FadeIn(title, shift=DOWN * 0.2), FadeIn(subtitle, shift=DOWN * 0.2))
        self.play(LaggedStart(*(FadeIn(card, shift=UP * 0.15) for card in cards), lag_ratio=0.18))
        self.play(Create(arrows))
        self.play(FadeIn(footer))
        self.wait(0.6)
        self.play(FadeOut(VGroup(title, subtitle, cards, arrows, footer)))

    def make_card(self, title: str, body: str, accent: str) -> VGroup:
        box = self.panel(3.7, 2.25)
        stripe = Rectangle(width=0.09, height=2.25, fill_color=accent, fill_opacity=1, stroke_opacity=0)
        stripe.align_to(box, LEFT)
        title_mob = self.label(title, 26, INK_C, BOLD)
        body_mob = self.label(body, 18, MUTED_C)
        body_mob.set(width=3.0)
        content = VGroup(title_mob, body_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        content.move_to(box.get_center()).shift(RIGHT * 0.1)
        return VGroup(box, stripe, content)

    def rl_loop(self) -> None:
        title = self.label("Where staleness enters", 36, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("FeynRL stores old logprobs and policy versions in replay.", 22, MUTED_C).next_to(title, DOWN, buff=0.12)

        node_specs = [
            ("policy pi", LEFT * 4.4 + UP * 0.7, BLUE_C),
            ("rollout", LEFT * 1.45 + UP * 0.7, ORANGE_C),
            ("reward", RIGHT * 1.45 + UP * 0.7, GREEN_C),
            ("replay buffer", LEFT * 1.45 + DOWN * 1.65, PURPLE_C),
            ("train update", LEFT * 4.4 + DOWN * 1.65, RED_C),
        ]
        nodes = VGroup()
        for text, pos, color in node_specs:
            circ = Circle(radius=0.82, color=color, fill_color=color, fill_opacity=0.92)
            label = self.label(text, 22, WHITE, BOLD)
            group = VGroup(circ, label).move_to(pos)
            nodes.add(group)

        arrows = VGroup(
            Arrow(nodes[0].get_right(), nodes[1].get_left(), buff=0.15, color=INK_C),
            Arrow(nodes[1].get_right(), nodes[2].get_left(), buff=0.15, color=INK_C),
            Arrow(nodes[2].get_bottom(), nodes[3].get_right(), buff=0.15, color=INK_C),
            Arrow(nodes[3].get_left(), nodes[4].get_right(), buff=0.15, color=INK_C),
            Arrow(nodes[4].get_top(), nodes[0].get_bottom(), buff=0.15, color=INK_C),
        )

        replay_panel = self.panel(3.2, 1.65).move_to(RIGHT * 4.15 + DOWN * 0.75)
        stored = VGroup(
            self.label("stored per token", 22, INK_C, BOLD),
            self.mono("old_logprobs", 19),
            self.mono("reward / zscore", 19),
            self.mono("policy_version", 19),
            self.mono("mask", 19),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).move_to(replay_panel)

        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(LaggedStart(*(FadeIn(node, scale=0.9) for node in nodes), lag_ratio=0.12))
        self.play(Create(arrows), FadeIn(replay_panel), FadeIn(stored))
        for node in nodes:
            self.play(Indicate(node[0], color=YELLOW_C, scale_factor=1.08), run_time=0.35)
        self.wait(0.3)
        self.play(FadeOut(VGroup(title, subtitle, nodes, arrows, replay_panel, stored)))

    def ratio_to_ess(self) -> None:
        title = self.label("Policy ratios drive ESS", 36, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("Fresh data clusters near r=1; stale replay spreads out.", 22, MUTED_C).next_to(title, DOWN, buff=0.12)
        fresh, stale = ratio_data()
        fresh_counts = histogram_counts(fresh)
        stale_counts = histogram_counts(stale)
        fresh_chart = self.histogram(fresh_counts, BLUE_C, "fresh rollout data")
        stale_chart = self.histogram(stale_counts, RED_C, "stale mixed replay")
        fresh_chart.to_edge(LEFT, buff=0.75).shift(DOWN * 0.25)
        stale_chart.move_to(fresh_chart)

        ess_panel = self.panel(4.2, 2.7).to_edge(RIGHT, buff=0.75).shift(DOWN * 0.05)
        formula = VGroup(
            self.label("Normalized ESS", 28, INK_C, BOLD),
            self.mono("ESS = (sum w)^2", 23, BLUE_C),
            self.mono("      / (n * sum w^2)", 23, BLUE_C),
            self.label(f"fresh ESS = {normalized_ess(fresh):.3f}", 24, BLUE_C, BOLD),
            self.label(f"stale ESS = {normalized_ess(stale):.3f}", 24, RED_C, BOLD),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to(ess_panel)

        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(FadeIn(fresh_chart), FadeIn(ess_panel), FadeIn(formula[:4]))
        self.wait(0.4)
        self.play(Transform(fresh_chart, stale_chart), FadeIn(formula[4]), run_time=1.7)
        self.play(Indicate(formula[4], color=RED_C), run_time=0.7)
        self.wait(0.4)
        self.play(FadeOut(VGroup(title, subtitle, fresh_chart, ess_panel, formula)))

    def histogram(self, counts: list[int], color: str, legend: str) -> VGroup:
        axes = VGroup(
            Line(LEFT * 3.15 + DOWN * 1.55, RIGHT * 3.15 + DOWN * 1.55, color=INK_C, stroke_width=2),
            Line(LEFT * 3.15 + DOWN * 1.55, LEFT * 3.15 + UP * 1.55, color=INK_C, stroke_width=2),
        )
        max_count = max(counts)
        bars = VGroup()
        for i, count in enumerate(counts):
            h = 2.9 * count / max_count
            bar = Rectangle(
                width=6.1 / len(counts) * 0.7,
                height=max(h, 0.02),
                fill_color=color,
                fill_opacity=0.82,
                stroke_opacity=0,
            )
            x = -3.0 + (i + 0.5) * 6.0 / len(counts)
            bar.move_to([x, -1.55 + h / 2, 0])
            bars.add(bar)
        one_line = Line(LEFT * 1.05 + DOWN * 1.55, LEFT * 1.05 + UP * 1.55, color=INK_C, stroke_width=2)
        one_label = self.label("r=1", 16, INK_C).next_to(one_line, UP, buff=0.05)
        x_label = self.label("policy ratio r", 18, MUTED_C).next_to(axes[0], DOWN, buff=0.22)
        legend_mob = self.label(legend, 20, color, BOLD).next_to(axes, UP, buff=0.2)
        return VGroup(axes, bars, one_line, one_label, x_label, legend_mob)

    def method_comparison(self) -> None:
        title = self.label("Same ratios, different update behavior", 34, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("Compare the effective score/update coefficient for a positive-advantage token.", 21, MUTED_C)
        subtitle.next_to(title, DOWN, buff=0.12)
        axes = Axes(
            x_range=[0, 3, 0.5],
            y_range=[0, 1.4, 0.35],
            x_length=7.0,
            y_length=3.6,
            axis_config={"color": INK_C, "stroke_width": 2},
            tips=False,
        ).to_edge(LEFT, buff=0.9).shift(DOWN * 0.35)
        x_lab = self.label("policy ratio r", 18, MUTED_C).next_to(axes, DOWN, buff=0.15)
        y_lab = self.label("update coefficient", 18, MUTED_C).next_to(axes, LEFT, buff=0.2).rotate(PI / 2)
        funcs = [
            ("PPO/GRPO fixed clip", lambda x: x if x <= 1.2 else 0.0, ORANGE_C),
            ("CISPO detached weight", lambda x: min(max(x, 0.8), 1.2), GREEN_C),
            ("P3O fresh ESS=0.95", lambda x: min(x, 0.95), BLUE_C),
            ("P3O stale ESS=0.35", lambda x: min(x, 0.35), RED_C),
        ]
        graphs = VGroup()
        legend = VGroup()
        for name, fn, color in funcs:
            graph = axes.plot(fn, x_range=[0.01, 3], color=color, stroke_width=4, use_smoothing=False)
            graphs.add(graph)
            mark = Line(ORIGIN, RIGHT * 0.42, color=color, stroke_width=5)
            row = VGroup(mark, self.label(name, 18, INK_C)).arrange(RIGHT, buff=0.16)
            legend.add(row)
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.2).to_edge(RIGHT, buff=0.75).shift(DOWN * 0.25)
        self.play(FadeIn(title), FadeIn(subtitle), Create(axes), FadeIn(x_lab), FadeIn(y_lab))
        self.play(LaggedStart(*(Create(g) for g in graphs), lag_ratio=0.18), FadeIn(legend), run_time=2.3)
        self.play(Indicate(legend[-1], color=RED_C), run_time=0.8)
        self.wait(0.4)
        self.play(FadeOut(VGroup(title, subtitle, axes, x_lab, y_lab, graphs, legend)))

    def formula_to_code(self) -> None:
        title = self.label("Formula and code align", 36, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("The video should show where the paper mechanism lives in the repo.", 22, MUTED_C)
        subtitle.next_to(title, DOWN, buff=0.12)
        formula_panel = self.panel(5.75, 3.7).to_edge(LEFT, buff=0.65).shift(DOWN * 0.25)
        formula_lines = VGroup(
            self.label("P3O objective pieces", 27, INK_C, BOLD),
            self.mono("r = exp(logp - old_logp)", 22),
            self.mono("ESS = (sum r)^2 / (n * sum r^2)", 21, BLUE_C),
            self.mono("rho = clamp(r, 0, ESS)", 21, BLUE_C),
            self.mono("loss = -sg(rho) * logp * A", 21),
            self.mono("     + (1 - ESS) * KL(pi || pi_old)", 21, RED_C),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to(formula_panel)

        code_panel = self.panel(6.35, 3.7, color="#111827", stroke="#263244").to_edge(RIGHT, buff=0.65).shift(DOWN * 0.25)
        code_lines = [
            "ratio = torch.exp(logprobs - old_logprobs)",
            "ess_factor = self.calculate_ess(ratio, mask)",
            "rho = torch.clamp(ratio, min=0, max=ess_factor)",
            "pi_sum = -(rho.detach() * logprobs * adv * mask).sum()",
            "loss = pi_sum + (1 - ess_factor) * kl_behavioral",
        ]
        code_mobs = VGroup()
        for line in code_lines:
            code_mobs.add(self.mono(line, 16, "#E8EFF7"))
        code_mobs.arrange(DOWN, aligned_edge=LEFT, buff=0.23).move_to(code_panel).shift(UP * 0.1)
        path = self.mono("external/FeynRL/algs/P3O/p3o.py", 15, "#9AA8BC").next_to(code_mobs, DOWN, buff=0.3).align_to(code_mobs, LEFT)

        self.play(FadeIn(title), FadeIn(subtitle), FadeIn(formula_panel), FadeIn(formula_lines))
        self.play(FadeIn(code_panel), FadeIn(code_mobs), FadeIn(path))
        for mob in code_mobs:
            highlight = SurroundingRectangle(mob, color=YELLOW_C, buff=0.06)
            self.play(Create(highlight), run_time=0.24)
            self.play(FadeOut(highlight), run_time=0.18)
        self.wait(0.4)
        self.play(FadeOut(VGroup(title, subtitle, formula_panel, formula_lines, code_panel, code_mobs, path)))

    def systems_view(self) -> None:
        title = self.label("Systems mode changes the data regime", 34, INK_C, BOLD).to_edge(UP, buff=0.55)
        subtitle = self.label("Sync keeps data fresh; async improves throughput but mixes policy versions.", 22, MUTED_C)
        subtitle.next_to(title, DOWN, buff=0.12)

        sync_label = self.label("Sync mode", 25, INK_C, BOLD).move_to(LEFT * 5.2 + UP * 1.8)
        async_label = self.label("Overlap / async mode", 25, INK_C, BOLD).move_to(LEFT * 4.75 + DOWN * 0.85)
        sync_blocks = self.timeline_blocks(["rollout v", "train", "sync", "rollout v+1"], [BLUE_C, GREEN_C, PURPLE_C, BLUE_C])
        sync_blocks.move_to(UP * 0.9)
        async_blocks = self.timeline_blocks(["rollout workers", "bounded replay", "training workers"], [BLUE_C, ORANGE_C, GREEN_C])
        async_blocks.move_to(DOWN * 1.65)

        packet = Dot(color=RED_C, radius=0.09).move_to(async_blocks[0].get_bottom() + DOWN * 0.45)
        packet_label = self.label("stale samples", 18, RED_C, BOLD).next_to(packet, RIGHT, buff=0.15)
        takeaway = self.label("P3O adapts from the batch statistic; fixed-clip methods need extra decoupling.", 22, INK_C)
        takeaway.to_edge(DOWN, buff=0.62)

        self.play(FadeIn(title), FadeIn(subtitle), FadeIn(sync_label), FadeIn(async_label))
        self.play(FadeIn(sync_blocks), FadeIn(async_blocks))
        self.play(packet.animate.move_to(async_blocks[-1].get_bottom() + DOWN * 0.45), FadeIn(packet_label), run_time=1.4)
        self.play(FadeIn(takeaway))
        self.wait(0.4)
        self.play(FadeOut(VGroup(title, subtitle, sync_label, async_label, sync_blocks, async_blocks, packet, packet_label, takeaway)))

    def timeline_blocks(self, labels: list[str], colors: list[str]) -> VGroup:
        blocks = VGroup()
        for label, color in zip(labels, colors):
            box = RoundedRectangle(width=2.35, height=0.8, corner_radius=0.1, fill_color=color, fill_opacity=1, stroke_opacity=0)
            text = self.label(label, 18, WHITE, BOLD)
            blocks.add(VGroup(box, text))
        blocks.arrange(RIGHT, buff=0.55)
        arrows = VGroup()
        for left, right in zip(blocks[:-1], blocks[1:]):
            arrows.add(Arrow(left.get_right(), right.get_left(), buff=0.1, color=INK_C, stroke_width=3))
        return VGroup(blocks, arrows)

    def takeaway(self) -> None:
        title = self.label("Takeaway", 44, INK_C, BOLD).to_edge(UP, buff=0.75)
        rows = VGroup(
            self.takeaway_row("Formula", "ESS turns ratio concentration into a control signal.", BLUE_C),
            self.takeaway_row("Code", "FeynRL implements this in calculate_ess and compute_policy_loss.", GREEN_C),
            self.takeaway_row("Example", "Fresh and stale batches make the mechanism visible.", ORANGE_C),
            self.takeaway_row("Comparison", "P3O adapts where PPO/GRPO use fixed clipping.", RED_C),
        ).arrange(DOWN, buff=0.28).shift(DOWN * 0.2)
        next_step = self.label("Next: feed real traces into the same Manim scenes.", 24, MUTED_C).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(title))
        self.play(LaggedStart(*(FadeIn(row, shift=RIGHT * 0.2) for row in rows), lag_ratio=0.16))
        self.play(FadeIn(next_step))
        self.wait(1.0)

    def takeaway_row(self, head: str, body: str, color: str) -> VGroup:
        box = self.panel(10.2, 0.72)
        stripe = Rectangle(width=0.08, height=0.72, fill_color=color, fill_opacity=1, stroke_opacity=0).align_to(box, LEFT)
        head_mob = self.label(head, 22, INK_C, BOLD)
        body_mob = self.label(body, 20, MUTED_C)
        text = VGroup(head_mob, body_mob).arrange(RIGHT, buff=0.45).move_to(box).align_to(box, LEFT).shift(RIGHT * 0.35)
        return VGroup(box, stripe, text)
