"""Self-refined Manim explainers aimed at an ICLR oral presentation bar.

The scenes are deliberately TeX-free so the same source renders locally and on
Babel.  Each revision is preserved by rendering into a separate round folder;
the source itself evolves only after the previous round has been inspected.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from manim import *

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scenes.inhouse_paper_explainer_suite import (
    BG,
    BLUE,
    DARK,
    GREEN,
    GRID,
    INK,
    MUTED,
    ORANGE,
    PURPLE,
    RED,
    WHITE_ISH,
    ExplainerScene,
)


class OralExplainer(ExplainerScene):
    """Shared visual grammar with presentation-safe typography."""

    def chapter(self, index: str, title: str, subtitle: str) -> VGroup:
        badge = Circle(radius=0.34, stroke_color=BLUE, stroke_width=3)
        number = self.label(index, 18, BLUE, BOLD).move_to(badge)
        head = self.label(title, 34, INK, BOLD)
        sub = self.label(subtitle, 20, MUTED)
        copy = VGroup(head, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.09)
        group = VGroup(VGroup(badge, number), copy).arrange(RIGHT, buff=0.28)
        group.to_edge(UP, buff=0.42).to_edge(LEFT, buff=0.52)
        return group

    def takeaway(self, text: str, color: str = GREEN) -> VGroup:
        box = RoundedRectangle(
            width=11.8,
            height=0.8,
            corner_radius=0.16,
            fill_color=WHITE_ISH,
            fill_opacity=1,
            stroke_color=color,
            stroke_width=2.5,
        )
        label = self.label(text, 22, INK, BOLD)
        label.scale_to_fit_width(11.15)
        label.move_to(box)
        return VGroup(box, label).to_edge(DOWN, buff=0.36)

    def pill(self, text: str, color: str, width: float = 2.0) -> VGroup:
        box = RoundedRectangle(
            width=width,
            height=0.62,
            corner_radius=0.22,
            fill_color=color,
            fill_opacity=0.12,
            stroke_color=color,
            stroke_width=2,
        )
        label = self.label(text, 18, color, BOLD).move_to(box)
        return VGroup(box, label)

    def clear_stage(self, *groups: Mobject) -> None:
        self.play(FadeOut(VGroup(*groups)), run_time=0.45)

    def paper_context(self, paper: str, contribution: str, boundary: str, color: str) -> VGroup:
        paper_label = self.pill(paper, color, 5.1)
        contribution_card = self.make_card("paper move", contribution, color, 10.8, 1.45)
        boundary_card = self.make_card("what this clip does not prove", boundary, ORANGE, 10.8, 1.45)
        stack = VGroup(paper_label, contribution_card, boundary_card).arrange(DOWN, buff=0.28)
        stack.shift(DOWN * 0.05)
        return stack

    def evidence_check(self, result: str, question: str, answer: str, color: str) -> VGroup:
        """Separate an authors' reported result from a small learner check."""
        result_card = self.make_card("paper result · authors' abstract", result, color, 10.8, 1.38)
        question_card = self.make_card("your turn · predict before reveal", question, ORANGE, 10.8, 1.38)
        answer_pill = self.pill(answer, GREEN, 7.0)
        return VGroup(result_card, question_card, answer_pill).arrange(DOWN, buff=0.28).shift(DOWN * 0.08)


class ICLRTransformerExplainer(OralExplainer):
    def construct(self) -> None:
        head = self.chapter("1", "Transformer attention is content lookup", "Follow one query token through score, softmax, and value mixing.")
        words = ["the", "animal", "didn't", "cross", "because", "it", "was", "tired"]
        token_cards = VGroup(*[
            self.pill(word, ORANGE if word == "it" else (GREEN if word == "animal" else BLUE), 1.25)
            for word in words
        ]).arrange(RIGHT, buff=0.12).scale(0.86).shift(UP * 0.35)
        query = self.label("query: what does ‘it’ refer to?", 25, ORANGE, BOLD).next_to(token_cards, DOWN, buff=0.46)
        arrows = VGroup(*[
            Arrow(token_cards[5].get_top(), card.get_top(), buff=0.08,
                  color=GREEN if idx == 1 else GRID,
                  stroke_width=6 if idx == 1 else 2,
                  max_tip_length_to_length_ratio=0.14).shift(UP * 0.12)
            for idx, card in enumerate(token_cards) if idx != 5
        ])
        claim = self.takeaway("Attention lets every token retrieve relevant context in one parallel operation.")
        self.play(FadeIn(head), LaggedStart(*[FadeIn(card, shift=UP * 0.08) for card in token_cards], lag_ratio=0.06))
        self.play(FadeIn(query), LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=0.06), run_time=1.2)
        self.play(Indicate(token_cards[1], color=GREEN), FadeIn(claim), run_time=0.8)
        self.wait(2.0)
        self.clear_stage(head, token_cards, query, arrows, claim)

        head = self.chapter("2", "Scores become a probability distribution", "A worked three-key example makes softmax observable.")
        raw_values = [1.0, 2.0, 0.0]
        probs = [0.245, 0.665, 0.090]
        raw = self.bar_group(["animal", "cross", "tired"], raw_values, 2.2, BLUE, "raw Q·K scores")
        soft = self.bar_group(["animal", "cross", "tired"], probs, 0.75, ORANGE, "softmax weights")
        raw.to_edge(LEFT, buff=0.8).shift(DOWN * 0.15)
        soft.to_edge(RIGHT, buff=0.8).shift(DOWN * 0.15)
        arrow = Arrow(raw.get_right(), soft.get_left(), color=INK, buff=0.28)
        label = self.pill("exp + normalize", PURPLE, 2.25).next_to(arrow, UP, buff=0.12)
        equation = self.mono("[1, 2, 0]  ->  [0.245, 0.665, 0.090]", 24, INK).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(head), FadeIn(raw))
        self.play(GrowArrow(arrow), FadeIn(label), TransformFromCopy(raw, soft), run_time=1.5)
        self.play(FadeIn(equation), Indicate(soft[1][1], color=ORANGE), run_time=0.8)
        self.wait(2.2)
        self.clear_stage(head, raw, soft, arrow, label, equation)

        head = self.chapter("3", "Weights route information, not just importance", "The same weights mix value vectors into the output token state.")
        weights = VGroup(
            self.pill("0.245 × animal", BLUE, 2.65),
            self.pill("0.665 × cross", ORANGE, 2.65),
            self.pill("0.090 × tired", PURPLE, 2.65),
        ).arrange(DOWN, buff=0.25).to_edge(LEFT, buff=1.0).shift(DOWN * 0.1)
        output = self.make_card("context for ‘it’", "a weighted blend of the three value vectors", GREEN, 4.4, 1.55).to_edge(RIGHT, buff=0.9).shift(DOWN * 0.1)
        mix_arrows = VGroup(*[Arrow(item.get_right(), output.get_left(), buff=0.12, color=item[0].get_stroke_color()) for item in weights])
        claim = self.takeaway("Q chooses what to seek; K determines relevance; V supplies what gets copied.")
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=RIGHT * 0.1) for item in weights], lag_ratio=0.12))
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in mix_arrows], lag_ratio=0.1), FadeIn(output), run_time=1.2)
        self.play(Indicate(output, color=GREEN), FadeIn(claim), run_time=0.8)
        self.wait(2.4)
        self.clear_stage(head, weights, output, mix_arrows, claim)

        head = self.chapter("4", "The paper move", "Separate the attention mechanism from the full Transformer claim.")
        context = self.paper_context(
            "Attention Is All You Need · 2017",
            "Replace recurrent sequence steps with stacked self-attention and feed-forward blocks.",
            "This clip isolates one attention lookup; it does not show multi-head stacking or translation results.",
            BLUE,
        ).shift(DOWN * 0.25)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=UP * 0.08) for item in context], lag_ratio=0.16))
        self.wait(3.4)
        self.clear_stage(head, context)

        head = self.chapter("5", "Can you reconstruct the mechanism?", "First paper evidence, then a counterfactual test.")
        check = self.evidence_check(
            "28.4 BLEU on WMT14 English-to-German; the architecture also enables parallel training.",
            "If one softmax weight becomes zero, can that value vector affect this attention head?",
            "Answer: no — zero weight means zero contribution.",
            BLUE,
        )
        self.play(FadeIn(head), FadeIn(check[0], shift=UP * 0.08))
        self.play(FadeIn(check[1], shift=UP * 0.08))
        self.wait(2.0)
        self.play(FadeIn(check[2]), run_time=0.6)
        self.wait(3.0)

    def bar_group(self, names: list[str], values: list[float], scale_max: float, color: str, title: str) -> VGroup:
        box = self.panel(5.15, 3.1)
        baseline = Line(LEFT * 1.75, RIGHT * 1.75, color=INK, stroke_width=2).shift(DOWN * 0.85)
        bars = VGroup()
        for name, value in zip(names, values):
            height = 1.75 * value / scale_max
            bar = Rectangle(width=0.72, height=height, fill_color=color, fill_opacity=0.86, stroke_opacity=0)
            bar.next_to(baseline, UP, buff=0)
            value_label = self.mono(f"{value:.3f}" if value < 1 else f"{value:.1f}", 17, INK).next_to(bar, UP, buff=0.07)
            name_label = self.label(name, 17, MUTED, BOLD).next_to(baseline, DOWN, buff=0.1)
            bars.add(VGroup(bar, value_label, name_label))
        bars.arrange(RIGHT, buff=0.38).move_to(box).shift(DOWN * 0.05)
        title_obj = self.label(title, 22, INK, BOLD).next_to(box, UP, buff=-0.42)
        return VGroup(box, bars, title_obj)


class ICLRDPOExplainer(OralExplainer):
    def construct(self) -> None:
        head = self.chapter("1", "DPO asks one local question", "For the same prompt, should the policy increase the winner–loser gap?")
        prompt = self.make_card("Prompt x", "Explain why rainbows form.", BLUE, 3.3, 1.1).to_edge(LEFT, buff=0.7)
        chosen = self.make_card("Chosen y+", "refraction + reflection + dispersion", GREEN, 4.25, 1.25)
        rejected = self.make_card("Rejected y−", "sunlight simply hits rain", RED, 4.25, 1.25)
        answers = VGroup(chosen, rejected).arrange(DOWN, buff=0.34).to_edge(RIGHT, buff=0.75)
        arrows = VGroup(Arrow(prompt.get_right(), chosen.get_left(), color=GREEN, buff=0.12), Arrow(prompt.get_right(), rejected.get_left(), color=RED, buff=0.12))
        claim = self.takeaway("Preference data supplies a direction—raise y+ relative to y−—without a scalar reward label.")
        self.play(FadeIn(head), FadeIn(prompt), LaggedStart(FadeIn(chosen), FadeIn(rejected), lag_ratio=0.2))
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.15), FadeIn(claim), run_time=1.0)
        self.wait(2.3)
        self.clear_stage(head, prompt, answers, arrows, claim)

        head = self.chapter("2", "Subtract the reference policy’s preference", "This isolates how the learned policy changed relative to its anchor.")
        legend = VGroup(
            self.pill("pi: policy being trained", BLUE, 3.0),
            self.pill("pi_ref: frozen reference", PURPLE, 3.0),
            self.pill("beta: update strength", ORANGE, 3.0),
        ).arrange(DOWN, buff=0.22).to_edge(LEFT, buff=0.75).shift(DOWN * 0.15)
        policy = self.margin_panel("policy gap", "+1.4", BLUE).shift(RIGHT * 2.5 + UP * 0.62)
        ref = self.margin_panel("reference gap", "+0.6", PURPLE).shift(RIGHT * 2.5 + DOWN * 0.78)
        minus = self.label("−", 42, INK, BOLD).move_to((policy.get_bottom() + ref.get_top()) / 2)
        result = self.pill("margin = +0.8", GREEN, 2.8).to_edge(RIGHT, buff=0.9).shift(DOWN * 2.05)
        arrow = Arrow(ref.get_bottom(), result.get_top(), color=GREEN, buff=0.12)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=RIGHT * 0.1) for item in legend], lag_ratio=0.12))
        self.play(FadeIn(policy), FadeIn(ref), FadeIn(minus))
        self.play(GrowArrow(arrow), FadeIn(result), run_time=0.9)
        self.wait(2.2)
        self.clear_stage(head, legend, policy, ref, minus, result, arrow)

        head = self.chapter("3", "The log-sigmoid turns margin into a loss", "Positive margin is rewarded; negative margin is penalized smoothly.")
        axis = Axes(x_range=[-3, 3, 1], y_range=[0, 3.2, 1], x_length=6.0, y_length=3.3, tips=False, axis_config={"color": MUTED, "stroke_width": 2}).shift(DOWN * 0.25)
        curve = axis.plot(lambda x: math.log1p(math.exp(-x)), x_range=[-3, 3], color=ORANGE, stroke_width=5)
        dots = VGroup(*[Dot(axis.c2p(x, math.log1p(math.exp(-x))), color=GREEN if x > 0 else RED, radius=0.09) for x in (-1.0, 0.8)])
        labels = VGroup(
            self.label("bad margin", 18, RED, BOLD).next_to(dots[0], UP, buff=0.12),
            self.label("our +0.8", 18, GREEN, BOLD).next_to(dots[1], UP, buff=0.12),
            self.mono("loss = -log sigmoid(beta × margin)", 22, INK).next_to(axis, DOWN, buff=0.25),
            self.label("margin", 18, MUTED, BOLD).next_to(axis.x_axis, RIGHT, buff=0.1),
            self.label("loss", 18, MUTED, BOLD).next_to(axis.y_axis, UP, buff=0.1),
        )
        claim = self.takeaway("DPO increases the policy’s preference gap only relative to a frozen reference policy.")
        self.play(FadeIn(head), Create(axis), Create(curve), run_time=1.2)
        self.play(LaggedStart(*[FadeIn(dot) for dot in dots], lag_ratio=0.2), FadeIn(labels), run_time=0.9)
        self.play(FadeIn(claim))
        self.wait(2.6)
        self.clear_stage(head, axis, curve, dots, labels, claim)

        head = self.chapter("4", "The paper move", "DPO shortens the preference-optimization route.")
        context = self.paper_context(
            "Direct Preference Optimization · 2023",
            "Turn reference-relative preference learning into a supervised logistic policy objective.",
            "The outcome still depends on preference data, beta, and the reference policy; this is not a result comparison.",
            GREEN,
        ).shift(DOWN * 0.25)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=UP * 0.08) for item in context], lag_ratio=0.16))
        self.wait(3.4)
        self.clear_stage(head, context)

        head = self.chapter("5", "Can you reconstruct the mechanism?", "First paper evidence, then a counterfactual test.")
        check = self.evidence_check(
            "Matches or improves summarization and dialogue versus PPO-style RLHF, with a simpler training loop.",
            "If the policy gap and reference gap both rise by 0.5, what happens to the DPO margin?",
            "Answer: fixed — DPO uses their difference.",
            GREEN,
        )
        self.play(FadeIn(head), FadeIn(check[0], shift=UP * 0.08))
        self.play(FadeIn(check[1], shift=UP * 0.08))
        self.wait(2.0)
        self.play(FadeIn(check[2]), run_time=0.6)
        self.wait(3.0)

    def margin_panel(self, title: str, value: str, color: str) -> VGroup:
        box = self.panel(3.4, 1.0)
        label = self.label(title, 20, MUTED, BOLD)
        number = self.mono(value, 27, color)
        row = VGroup(label, number).arrange(RIGHT, buff=0.42).move_to(box)
        return VGroup(box, row)


class ICLRESExplainer(OralExplainer):
    def construct(self) -> None:
        head = self.chapter("1", "ESS measures how many samples really matter", "A replay batch may contain five rows but behave like far fewer.")
        balanced = self.ratio_batch([1.0, 0.9, 1.1, 1.0, 1.0], BLUE, "balanced ratios")
        stale = self.ratio_batch([0.2, 0.3, 0.4, 0.5, 4.0], RED, "one sample dominates")
        balanced.to_edge(LEFT, buff=0.75).shift(DOWN * 0.2)
        stale.to_edge(RIGHT, buff=0.75).shift(DOWN * 0.2)
        middle = Arrow(balanced.get_right(), stale.get_left(), color=ORANGE, buff=0.2)
        claim = self.takeaway("Importance ratios expose replay mismatch: uneven weights mean less independent evidence.")
        self.play(FadeIn(head), FadeIn(balanced))
        self.play(GrowArrow(middle), TransformFromCopy(balanced, stale), run_time=1.3)
        self.play(Indicate(stale[1][-1], color=RED), FadeIn(claim), run_time=0.8)
        self.wait(2.2)
        self.clear_stage(head, balanced, stale, middle, claim)

        head = self.chapter("2", "Square the sum, divide by squared concentration", "The normalized ESS stays in [0, 1].")
        numerator = self.make_card("sum of ratios", "5.4", BLUE, 3.3, 1.1).shift(LEFT * 3.4 + UP * 0.65)
        square = self.make_card("square it", "5.4² = 29.16", PURPLE, 3.3, 1.1).shift(UP * 0.65)
        denom = self.make_card("n × sum r²", "5 × 16.54 = 82.7", ORANGE, 3.3, 1.1).shift(RIGHT * 3.4 + UP * 0.65)
        arrows = VGroup(Arrow(numerator.get_right(), square.get_left(), color=GRID, buff=0.12), Arrow(square.get_right(), denom.get_left(), color=GRID, buff=0.12))
        result = self.pill("ESS = 29.16 / 82.7 = 0.35", RED, 4.2).shift(DOWN * 1.0)
        gauge = self.gauge(0.35).next_to(result, DOWN, buff=0.35)
        self.play(FadeIn(head), FadeIn(numerator), GrowArrow(arrows[0]), FadeIn(square))
        self.play(GrowArrow(arrows[1]), FadeIn(denom))
        self.play(FadeIn(result), FadeIn(gauge), run_time=0.9)
        self.wait(2.3)
        self.clear_stage(head, numerator, square, denom, arrows, result, gauge)

        head = self.chapter("3", "FeynRL/P3O uses ESS as a control signal", "Low ESS means the replay update is less trustworthy.")
        high = self.make_card("High ESS", "more usable evidence\nallow a wider update", GREEN, 4.2, 1.5).shift(LEFT * 3.0)
        low = self.make_card("Low ESS", "few effective samples\ntighten cap + add KL", RED, 4.2, 1.5).shift(RIGHT * 3.0)
        controller = self.pill("ESS controller", ORANGE, 2.4).move_to(ORIGIN + UP * 1.45)
        paths = VGroup(Arrow(controller.get_bottom(), high.get_top(), color=GREEN, buff=0.1), Arrow(controller.get_bottom(), low.get_top(), color=RED, buff=0.1))
        claim = self.takeaway("ESS does not score policy quality; it controls how much to trust this off-policy batch.")
        self.play(FadeIn(head), FadeIn(controller))
        self.play(LaggedStart(*[GrowArrow(path) for path in paths], lag_ratio=0.15), FadeIn(high), FadeIn(low), run_time=1.1)
        self.play(Indicate(low[2][0], color=RED), FadeIn(claim), run_time=0.8)
        self.wait(2.6)
        self.clear_stage(head, high, low, controller, paths, claim)

        head = self.chapter("4", "The paper move", "Adapt the update to the observed reliability of the replay batch.")
        context = self.paper_context(
            "Trust the Batch / FeynRL-P3O",
            "Use normalized ESS to adapt score-function capping and behavioral KL regularization.",
            "ESS is not reward or policy quality; the five-sample batch here is an explanatory toy.",
            ORANGE,
        ).shift(DOWN * 0.25)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=UP * 0.08) for item in context], lag_ratio=0.16))
        self.wait(3.4)
        self.clear_stage(head, context)

        head = self.chapter("5", "Can you reconstruct the mechanism?", "First paper evidence, then a counterfactual test.")
        check = self.evidence_check(
            "Matches or exceeds tuned baselines without adding new objective hyperparameters.",
            "Five replay rows, but one ratio dominates: does the effective sample count rise or fall?",
            "Answer: it falls — the evidence is concentrated.",
            ORANGE,
        )
        self.play(FadeIn(head), FadeIn(check[0], shift=UP * 0.08))
        self.play(FadeIn(check[1], shift=UP * 0.08))
        self.wait(2.0)
        self.play(FadeIn(check[2]), run_time=0.6)
        self.wait(3.0)

    def ratio_batch(self, values: list[float], color: str, title: str) -> VGroup:
        box = self.panel(5.2, 3.1)
        base = Line(LEFT * 1.85, RIGHT * 1.85, color=INK, stroke_width=2).shift(DOWN * 0.9)
        bars = VGroup()
        for idx, value in enumerate(values):
            bar = Rectangle(width=0.48, height=max(0.08, 1.8 * value / 4.0), fill_color=color, fill_opacity=0.85, stroke_opacity=0)
            bar.next_to(base, UP, buff=0)
            label = self.mono(f"{value:.1f}", 15, INK).next_to(bar, UP, buff=0.06)
            bars.add(VGroup(bar, label))
        bars.arrange(RIGHT, buff=0.22).move_to(box).shift(DOWN * 0.05)
        title_obj = self.label(title, 22, color, BOLD).next_to(box, UP, buff=-0.42)
        return VGroup(box, bars, title_obj)

    def gauge(self, value: float) -> VGroup:
        track = Line(LEFT * 2.0, RIGHT * 2.0, color=GRID, stroke_width=14)
        fill = Line(track.get_left(), track.get_left() + RIGHT * 4.0 * value, color=RED, stroke_width=14)
        dot = Dot(fill.get_end(), color=RED, radius=0.1)
        labels = VGroup(self.label("0", 16, MUTED), self.label("1", 16, MUTED)).arrange(RIGHT, buff=3.7).next_to(track, DOWN, buff=0.12)
        return VGroup(track, fill, dot, labels)


class ICLRRoPEExplainer(OralExplainer):
    def construct(self) -> None:
        head = self.chapter("1", "RoPE writes position into vector angle", "Each hidden-dimension pair becomes a tiny 2D clock.")
        clocks = VGroup(*[self.clock(angle, color, label) for angle, color, label in [(0.25, BLUE, "position 1"), (0.8, GREEN, "position 3"), (1.45, PURPLE, "position 6")]])
        clocks.arrange(RIGHT, buff=0.9).shift(DOWN * 0.15)
        claim = self.takeaway("The vector keeps its content identity while position changes its phase.")
        self.play(FadeIn(head), LaggedStart(*[FadeIn(clock, shift=UP * 0.1) for clock in clocks], lag_ratio=0.15))
        self.play(LaggedStart(*[Rotate(clock[2], angle=0.35, about_point=clock[0].get_center()) for clock in clocks], lag_ratio=0.12), run_time=1.2)
        self.play(FadeIn(claim))
        self.wait(2.3)
        self.clear_stage(head, clocks, claim)

        head = self.chapter("2", "Two absolute rotations become one relative rotation", "The dot product cancels the shared origin.")
        q = self.clock(0.55, BLUE, "R_m q").to_edge(LEFT, buff=0.9).shift(DOWN * 0.1)
        k = self.clock(1.25, GREEN, "R_n k").to_edge(RIGHT, buff=0.9).shift(DOWN * 0.1)
        relation = self.formula_panel(
            [("dot(R_m q, R_n k)", BLUE), ("= dot(q, R_(n-m) k)", GREEN)],
            "relative-position identity",
            5.2,
            1.8,
        ).move_to(ORIGIN).shift(DOWN * 0.1)
        arrows = VGroup(Arrow(q.get_right(), relation.get_left(), color=GRID, buff=0.1), Arrow(k.get_left(), relation.get_right(), color=GRID, buff=0.1))
        distance = self.pill("only n − m remains", ORANGE, 3.0).next_to(relation, DOWN, buff=0.35)
        self.play(FadeIn(head), FadeIn(q), FadeIn(k))
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.15), FadeIn(relation), run_time=1.1)
        self.play(FadeIn(distance), Indicate(relation[1][2], color=GREEN), run_time=0.8)
        self.wait(2.3)
        self.clear_stage(head, q, k, relation, arrows, distance)

        head = self.chapter("3", "Many clock speeds form a position fingerprint", "Slow pairs track long range; fast pairs separate nearby positions.")
        rows = VGroup(
            self.frequency_row("pair 1", 0.2, BLUE, "slow / long range"),
            self.frequency_row("pair 2", 0.8, GREEN, "medium"),
            self.frequency_row("pair 3", 1.7, PURPLE, "fast / local"),
        ).arrange(DOWN, buff=0.28).shift(DOWN * 0.05)
        claim = self.takeaway("RoPE makes relative distance available inside attention—without adding a separate position score.")
        self.play(FadeIn(head), LaggedStart(*[FadeIn(row, shift=RIGHT * 0.12) for row in rows], lag_ratio=0.15))
        self.play(LaggedStart(*[Rotate(row[2], angle=0.45, about_point=row[1].get_center()) for row in rows], lag_ratio=0.12), run_time=1.2)
        self.play(FadeIn(claim))
        self.wait(2.6)
        self.clear_stage(head, rows, claim)

        head = self.chapter("4", "The paper move", "Put relative position directly inside the attention geometry.")
        context = self.paper_context(
            "RoFormer / Rotary Position Embedding · 2021",
            "Rotate query and key pairs so their dot product exposes relative position n − m.",
            "The clocks are 2D toys; real RoPE applies block-diagonal rotations at many frequencies.",
            PURPLE,
        ).shift(DOWN * 0.25)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(item, shift=UP * 0.08) for item in context], lag_ratio=0.16))
        self.wait(3.4)
        self.clear_stage(head, context)

        head = self.chapter("5", "Can you reconstruct the mechanism?", "First paper evidence, then a counterfactual test.")
        check = self.evidence_check(
            "RoFormer consistently beats tested positional alternatives on long-text classification.",
            "Shift both token positions by the same offset: should their RoPE relative score change?",
            "Answer: no — n minus m is unchanged.",
            PURPLE,
        )
        self.play(FadeIn(head), FadeIn(check[0], shift=UP * 0.08))
        self.play(FadeIn(check[1], shift=UP * 0.08))
        self.wait(2.0)
        self.play(FadeIn(check[2]), run_time=0.6)
        self.wait(3.0)

    def clock(self, angle: float, color: str, label: str) -> VGroup:
        circle = Circle(radius=0.85, color=GRID, stroke_width=3)
        hand = Arrow(circle.get_center(), circle.get_center() + RIGHT * 0.75, buff=0, color=color, stroke_width=6).rotate(angle, about_point=circle.get_center())
        arc = Arc(radius=0.55, start_angle=0, angle=angle, color=color, stroke_width=4).move_to(circle)
        name = self.label(label, 20, color, BOLD).next_to(circle, DOWN, buff=0.18)
        angle_text = self.mono(f"angle {angle:.2f}", 17, MUTED).next_to(circle, UP, buff=0.14)
        return VGroup(circle, angle_text, hand, name, arc)

    def frequency_row(self, name: str, angle: float, color: str, meaning: str) -> VGroup:
        circle = Circle(radius=0.42, color=GRID)
        hand = Arrow(circle.get_center(), circle.get_center() + RIGHT * 0.37, buff=0, color=color, stroke_width=5).rotate(angle, about_point=circle.get_center())
        name_obj = self.pill(name, color, 1.65)
        meaning_obj = self.label(meaning, 21, INK, BOLD)
        return VGroup(name_obj, circle, hand, meaning_obj).arrange(RIGHT, buff=0.42)
