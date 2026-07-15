from __future__ import annotations

from manim import *
import numpy as np


config.background_color = "#f7f4ed"


PAPER = "#f7f4ed"
INK = "#2d2a24"
MUTED = "#6d6a62"
BLUE = "#2f6fbb"
GREEN = "#2b8a6f"
CORAL = "#c85f42"
VIOLET = "#7a5ab8"
AMBER = "#c9902e"
LINE = "#d8d0c2"
WHITE = "#fffdf8"


TOPICS = {
    "feynrl": {
        "title": "FeynRL / P3O",
        "question": "How does ESS tell us when replay data became stale?",
        "symbols": [
            ("r", "new policy prob / old policy prob"),
            ("ESS", "effective batch size after ratio skew"),
            ("KL", "penalty that grows when ESS falls"),
        ],
        "formulas": [
            "r_i = exp(log pi_new - log pi_old)",
            "ESS = (sum r_i)^2 / (n * sum r_i^2)",
            "low ESS -> cap ratios + add behavioral KL",
        ],
        "example": [
            "fresh batch: ratios cluster near 1, ESS high",
            "stale replay: one large ratio dominates, ESS drops",
            "P3O responds by trusting the batch less",
        ],
        "misconception": "Do not read low ESS as smaller data. It means the weighted batch behaves like fewer samples.",
        "visual": "ess",
    },
    "dpo": {
        "title": "DPO Preference Objective",
        "question": "How can a policy learn from chosen vs rejected answers without a reward model?",
        "symbols": [
            ("x", "prompt"),
            ("y_w", "chosen response"),
            ("y_l", "rejected response"),
            ("beta", "strength of preference update"),
        ],
        "formulas": [
            "Delta_pi = log pi(y_w|x) - log pi(y_l|x)",
            "Delta_ref = log pi_ref(y_w|x) - log pi_ref(y_l|x)",
            "L = -log sigmoid(beta * (Delta_pi - Delta_ref))",
        ],
        "example": [
            "compare current policy gap to reference gap",
            "increase chosen likelihood only relative to rejected",
            "avoid a separate reward-model training stage",
        ],
        "misconception": "DPO is not just supervised learning on chosen answers; the rejected answer and reference model set the margin.",
        "visual": "dpo",
    },
    "attention": {
        "title": "Scaled Dot-Product Attention",
        "question": "How do query-key scores become weights that mix values?",
        "symbols": [
            ("Q", "what the token asks for"),
            ("K", "what each context token advertises"),
            ("V", "information carried forward"),
        ],
        "formulas": [
            "scores = Q K^T / sqrt(d_k)",
            "weights = softmax(scores)",
            "output = weights * V",
        ],
        "example": [
            "raw scores prefer the matching key",
            "softmax turns scores into a distribution",
            "values are blended by those weights",
        ],
        "misconception": "Attention does not choose one token; it forms a weighted mixture.",
        "visual": "attention",
    },
    "transformers": {
        "title": "Transformer Core",
        "question": "How does the model replace recurrence with attention plus position signals?",
        "symbols": [
            ("head_i", "one attention view"),
            ("PE", "positional signal"),
            ("W_O", "projection after concatenating heads"),
        ],
        "formulas": [
            "head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)",
            "MultiHead = Concat(head_1, ..., head_h) W_O",
            "x_pos = token_embedding + positional_encoding",
        ],
        "example": [
            "parallel heads read syntax, locality, and object links",
            "position stripes keep token order visible",
            "feed-forward layers refine each token independently",
        ],
        "misconception": "Self-attention removes recurrence, not sequence order. Position still enters the representation.",
        "visual": "transformer",
    },
    "rope": {
        "title": "RoPE / RoFormer",
        "question": "Why do rotating Q and K make attention depend on relative distance?",
        "symbols": [
            ("R_m", "rotation by position m"),
            ("q, k", "query and key vector pairs"),
            ("n - m", "relative token offset"),
        ],
        "formulas": [
            "RoPE(x_m) = R_m x_m",
            "<R_m q, R_n k> = <q, R_(n-m) k>",
            "many 2D pairs rotate at different frequencies",
        ],
        "example": [
            "rotate q by m and k by n",
            "shared rotation cancels inside the dot product",
            "attention sees the offset n - m",
        ],
        "misconception": "RoPE is not adding a position vector; it rotates coordinate pairs before attention.",
        "visual": "rope",
    },
}


def wrapped_text(text: str, max_chars: int = 46) -> str:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def card(width: float, height: float, color: str = WHITE, stroke: str = LINE) -> RoundedRectangle:
    return RoundedRectangle(
        width=width,
        height=height,
        corner_radius=0.12,
        fill_color=color,
        fill_opacity=1,
        stroke_color=stroke,
        stroke_width=1.4,
    )


def label(text: str, size: int = 24, color: str = INK, weight: str = NORMAL) -> Text:
    return Text(text, font_size=size, color=color, weight=weight, should_center=True)


class LLM2ManimInspiredScene(Scene):
    topic_key = "attention"

    def construct(self):
        self.camera.background_color = PAPER
        data = TOPICS[self.topic_key]
        self.show_header(data)
        self.show_segment_one(data)
        self.show_segment_two(data)
        self.show_segment_three(data)
        self.show_closing(data)

    def show_header(self, data):
        tag = label("LLM2Manim-inspired reproduction", 24, CORAL, BOLD).to_edge(UP, buff=0.35)
        title = label(data["title"], 42, INK, BOLD).next_to(tag, DOWN, buff=0.3)
        subtitle = label(wrapped_text(data["question"], 58), 24, MUTED).next_to(title, DOWN, buff=0.25)
        note = label("Paper-method reconstruction: segmentation, symbol ledger, partial regeneration checkpoint", 18, MUTED)
        note.to_edge(DOWN, buff=0.35)
        self.play(FadeIn(tag, shift=DOWN * 0.2), Write(title), FadeIn(subtitle, shift=UP * 0.15), run_time=1.4)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(0.8)
        self.play(FadeOut(tag), FadeOut(title), FadeOut(subtitle), FadeOut(note), run_time=0.6)

    def pipeline_rail(self, active: int) -> VGroup:
        steps = ["Segment", "Ledger", "Template", "Review", "Render"]
        group = VGroup()
        y = 3.15
        x0 = -5.65
        for idx, step in enumerate(steps):
            color = GREEN if idx <= active else "#b8b0a2"
            dot = Dot(point=[x0 + idx * 1.15, y, 0], radius=0.075, color=color)
            text = label(step, 14, color if idx == active else MUTED, BOLD if idx == active else NORMAL)
            text.next_to(dot, DOWN, buff=0.12)
            group.add(dot, text)
            if idx < len(steps) - 1:
                line = Line(dot.get_right(), [x0 + (idx + 1) * 1.15 - 0.08, y, 0], color="#cfc7ba", stroke_width=2)
                group.add(line)
        return group

    def show_segment_one(self, data):
        rail = self.pipeline_rail(1)
        title = label("Segment 1: lock vocabulary before motion", 28, INK, BOLD).to_edge(UP, buff=0.55)
        ledger_title = label("Symbol ledger", 24, GREEN, BOLD)
        ledger_title.move_to([-3.6, 1.8, 0])
        ledger_cards = VGroup()
        for idx, (sym, meaning) in enumerate(data["symbols"]):
            box = card(3.15, 0.78)
            sym_text = label(sym, 22, BLUE, BOLD).move_to(box.get_left() + RIGHT * 0.45)
            meaning_text = label(wrapped_text(meaning, 28), 15, INK).move_to(box.get_center() + RIGHT * 0.38)
            row = VGroup(box, sym_text, meaning_text).move_to([-3.6, 0.95 - idx * 0.95, 0])
            ledger_cards.add(row)

        script_box = card(4.55, 3.05)
        script_box.move_to([2.35, 0.45, 0])
        script_title = label("Narration segment", 22, CORAL, BOLD).move_to(script_box.get_top() + DOWN * 0.35)
        script_body = label(
            wrapped_text(
                "First, name every symbol the learner will see. Then animate only one idea per segment so a later bad segment can be regenerated without changing the whole video.",
                43,
            ),
            19,
            INK,
        )
        script_body.move_to(script_box.get_center() + DOWN * 0.05)
        self.play(FadeIn(rail), Write(title), run_time=0.8)
        self.play(FadeIn(ledger_title), LaggedStart(*[FadeIn(row, shift=UP * 0.15) for row in ledger_cards], lag_ratio=0.2), run_time=1.4)
        self.play(FadeIn(script_box), Write(script_title), FadeIn(script_body), run_time=1.0)
        self.wait(1.1)
        self.play(FadeOut(VGroup(rail, title, ledger_title, ledger_cards, script_box, script_title, script_body)), run_time=0.6)

    def show_segment_two(self, data):
        rail = self.pipeline_rail(2)
        title = label("Segment 2: pair formula with a concrete visual", 28, INK, BOLD).to_edge(UP, buff=0.55)
        formula_panel = self.make_formula_panel(data["formulas"]).move_to([-3.2, 0.3, 0])
        visual = self.make_visual(data).move_to([2.65, 0.05, 0])
        self.play(FadeIn(rail), Write(title), run_time=0.8)
        self.play(FadeIn(formula_panel, shift=RIGHT * 0.15), run_time=0.8)
        self.play(FadeIn(visual, shift=LEFT * 0.15), run_time=0.9)
        self.wait(1.2)
        self.play(FadeOut(VGroup(rail, title, formula_panel, visual)), run_time=0.6)

    def make_formula_panel(self, formulas: list[str]) -> VGroup:
        panel = card(5.0, 3.55)
        title = label("Constrained formula template", 22, BLUE, BOLD).move_to(panel.get_top() + DOWN * 0.36)
        lines = VGroup()
        for idx, formula in enumerate(formulas[:3]):
            line_box = card(4.35, 0.68, color="#fbf8f0")
            formula_text = label(wrapped_text(formula, 38), 15, INK)
            formula_text.move_to(line_box)
            row = VGroup(line_box, formula_text).move_to(panel.get_center() + UP * (0.72 - idx * 0.88))
            lines.add(row)
        return VGroup(panel, title, lines)

    def make_visual(self, data) -> VGroup:
        method = getattr(self, f"visual_{data['visual']}")
        return method()

    def visual_ess(self) -> VGroup:
        panel = card(4.7, 3.55)
        title = label("Ratio skew -> lower ESS", 21, GREEN, BOLD).move_to(panel.get_top() + DOWN * 0.35)
        bars = VGroup()
        vals = [0.9, 1.0, 1.1, 3.8, 0.7]
        for idx, val in enumerate(vals):
            bar = Rectangle(width=0.34, height=0.35 + val * 0.35, fill_color=CORAL if val > 2 else BLUE, fill_opacity=0.78, stroke_width=0)
            bar.move_to([-1.25 + idx * 0.55, -0.15 + bar.height / 2, 0])
            bars.add(bar)
        gauge = Arc(radius=0.8, start_angle=PI, angle=0.72 * PI, color=AMBER, stroke_width=8)
        gauge.move_to([1.35, -0.1, 0])
        pointer = Line(gauge.get_center(), gauge.get_center() + 0.65 * np.array([np.cos(1.72 * PI), np.sin(1.72 * PI), 0]), color=INK, stroke_width=5)
        text = label("ESS drops", 18, INK, BOLD).next_to(gauge, DOWN, buff=0.12)
        return VGroup(panel, title, bars, gauge, pointer, text)

    def visual_dpo(self) -> VGroup:
        panel = card(4.7, 3.55)
        title = label("Chosen vs rejected margin", 21, GREEN, BOLD).move_to(panel.get_top() + DOWN * 0.35)
        prompt = card(1.35, 0.68, color="#fefbf2").move_to([0, 0.75, 0])
        prompt_text = label("prompt x", 15, INK, BOLD).move_to(prompt)
        chosen = card(1.45, 0.68, color="#e9f7ef", stroke=GREEN).move_to([-0.9, -0.2, 0])
        rejected = card(1.45, 0.68, color="#fff0ea", stroke=CORAL).move_to([0.9, -0.2, 0])
        chosen_text = label("chosen", 15, GREEN, BOLD).move_to(chosen)
        rejected_text = label("rejected", 15, CORAL, BOLD).move_to(rejected)
        arrows = VGroup(Arrow(prompt.get_bottom(), chosen.get_top(), color=GREEN, buff=0.06), Arrow(prompt.get_bottom(), rejected.get_top(), color=CORAL, buff=0.06))
        margin = label("policy gap - ref gap", 18, BLUE, BOLD).move_to([0, -1.2, 0])
        return VGroup(panel, title, arrows, prompt, prompt_text, chosen, rejected, chosen_text, rejected_text, margin)

    def visual_attention(self) -> VGroup:
        panel = card(4.7, 3.55)
        title = label("Scores -> softmax -> mix", 21, GREEN, BOLD).move_to(panel.get_top() + DOWN * 0.35)
        bars = VGroup()
        colors = [BLUE, AMBER, GREEN, CORAL]
        heights = [0.55, 1.35, 0.85, 0.35]
        for idx, height in enumerate(heights):
            bar = Rectangle(width=0.38, height=height, fill_color=colors[idx], fill_opacity=0.8, stroke_width=0)
            bar.move_to([-1.35 + idx * 0.56, -0.2 + height / 2, 0])
            bars.add(bar)
        softmax = label("softmax sums to 1", 18, BLUE, BOLD).move_to([1.1, 0.25, 0])
        mix = VGroup(
            Circle(radius=0.18, fill_color=BLUE, fill_opacity=0.8, stroke_width=0),
            Circle(radius=0.24, fill_color=AMBER, fill_opacity=0.8, stroke_width=0).shift(RIGHT * 0.38),
            Circle(radius=0.2, fill_color=GREEN, fill_opacity=0.8, stroke_width=0).shift(RIGHT * 0.74),
        ).move_to([1.12, -0.65, 0])
        return VGroup(panel, title, bars, softmax, mix)

    def visual_transformer(self) -> VGroup:
        panel = card(4.7, 3.55)
        title = label("Parallel heads, shared tokens", 21, GREEN, BOLD).move_to(panel.get_top() + DOWN * 0.35)
        heads = VGroup()
        for idx, color in enumerate([BLUE, GREEN, CORAL]):
            box = card(1.1, 0.62, color="#fbf8f0", stroke=color).move_to([-1.15 + idx * 1.15, 0.45, 0])
            txt = label(f"head {idx+1}", 14, color, BOLD).move_to(box)
            heads.add(VGroup(box, txt))
        concat = card(3.0, 0.55, color="#eef4fb", stroke=BLUE).move_to([0, -0.35, 0])
        concat_text = label("concat then project", 16, BLUE, BOLD).move_to(concat)
        pos = label("position signal keeps order visible", 17, MUTED).move_to([0, -1.15, 0])
        return VGroup(panel, title, heads, concat, concat_text, pos)

    def visual_rope(self) -> VGroup:
        panel = card(4.7, 3.55)
        title = label("Relative rotation survives", 21, GREEN, BOLD).move_to(panel.get_top() + DOWN * 0.35)
        axes = Axes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], x_length=2.6, y_length=2.2, tips=False, axis_config={"color": "#b8b0a2", "stroke_width": 2})
        axes.move_to([-0.65, -0.15, 0])
        q = Arrow(axes.c2p(0, 0), axes.c2p(1.25, 0.55), color=BLUE, buff=0, stroke_width=5)
        k = Arrow(axes.c2p(0, 0), axes.c2p(-0.25, 1.35), color=CORAL, buff=0, stroke_width=5)
        arc = Arc(radius=0.7, start_angle=0.42, angle=0.9, color=GREEN, stroke_width=5).move_to(axes.c2p(0, 0))
        identity = label("<R_m q, R_n k> depends on n-m", 17, INK, BOLD).move_to([0.95, -1.2, 0])
        return VGroup(panel, title, axes, q, k, arc, identity)

    def show_segment_three(self, data):
        rail = self.pipeline_rail(3)
        title = label("Segment 3: review checkpoint before final render", 28, INK, BOLD).to_edge(UP, buff=0.55)
        example_panel = card(5.25, 3.65).move_to([-2.85, 0.05, 0])
        example_title = label("Worked example beat", 22, BLUE, BOLD).move_to(example_panel.get_top() + DOWN * 0.36)
        rows = VGroup()
        for idx, row in enumerate(data["example"]):
            bullet = Dot(radius=0.055, color=GREEN)
            text = label(wrapped_text(row, 42), 17, INK)
            line = VGroup(bullet, text).arrange(RIGHT, buff=0.16)
            line.move_to(example_panel.get_center() + UP * (0.55 - idx * 0.62))
            rows.add(line)

        review_panel = card(4.55, 3.65, color="#fffaf0").move_to([3.05, 0.05, 0])
        review_title = label("HITL / partial regen note", 22, CORAL, BOLD).move_to(review_panel.get_top() + DOWN * 0.36)
        review_body = label(wrapped_text(data["misconception"], 39), 17, INK).move_to(review_panel.get_center() + UP * 0.25)
        regen = label("If this check fails: regenerate this segment only.", 16, VIOLET, BOLD).move_to(review_panel.get_bottom() + UP * 0.52)
        self.play(FadeIn(rail), Write(title), run_time=0.8)
        self.play(FadeIn(example_panel), Write(example_title), LaggedStart(*[FadeIn(row, shift=UP * 0.1) for row in rows], lag_ratio=0.18), run_time=1.3)
        self.play(FadeIn(review_panel), Write(review_title), FadeIn(review_body), FadeIn(regen), run_time=1.1)
        self.wait(1.1)
        self.play(FadeOut(VGroup(rail, title, example_panel, example_title, rows, review_panel, review_title, review_body, regen)), run_time=0.6)

    def show_closing(self, data):
        title = label("Final render contract", 34, INK, BOLD).to_edge(UP, buff=0.9)
        checks = VGroup(
            label("1. Symbols consistent across segments", 24, GREEN, BOLD),
            label("2. Formula paired with visual evidence", 24, BLUE, BOLD),
            label("3. Misconception check recorded", 24, CORAL, BOLD),
            label("4. Output marked as LLM2Manim-inspired, not official", 23, VIOLET, BOLD),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.34)
        checks.move_to([0, 0.15, 0])
        footer = label(data["question"], 19, MUTED).to_edge(DOWN, buff=0.55)
        self.play(Write(title), LaggedStart(*[FadeIn(check, shift=RIGHT * 0.15) for check in checks], lag_ratio=0.16), run_time=1.4)
        self.play(FadeIn(footer), run_time=0.4)
        self.wait(1.2)


class LLM2ManimFeynRL(LLM2ManimInspiredScene):
    topic_key = "feynrl"


class LLM2ManimDPO(LLM2ManimInspiredScene):
    topic_key = "dpo"


class LLM2ManimAttention(LLM2ManimInspiredScene):
    topic_key = "attention"


class LLM2ManimTransformers(LLM2ManimInspiredScene):
    topic_key = "transformers"


class LLM2ManimRoPE(LLM2ManimInspiredScene):
    topic_key = "rope"
