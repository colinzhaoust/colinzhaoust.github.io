"""In-house Manim explainer suite for paper-to-understanding experiments.

Render examples:
    manim -ql --media_dir runs/inhouse_manim_media scenes/inhouse_paper_explainer_suite.py FeynRLESSMiniLesson
    manim -ql --media_dir runs/inhouse_manim_media scenes/inhouse_paper_explainer_suite.py DPOPreferenceExplainer
    manim -ql --media_dir runs/inhouse_manim_media scenes/inhouse_paper_explainer_suite.py AttentionSoftmaxExplainer

The scenes avoid LaTeX/MathTex on purpose so the suite is robust on machines
without a full TeX installation. Formulas are rendered as monospace Text.
"""

from __future__ import annotations

import math

from manim import *


BG = "#F7F9FC"
INK = "#1F2937"
MUTED = "#5B677A"
BLUE = "#2F80ED"
GREEN = "#2C9C69"
ORANGE = "#EF7D00"
RED = "#D64545"
PURPLE = "#7E57C2"
YELLOW = "#F3BA43"
GRID = "#D9E0EA"
WHITE_ISH = "#FFFFFF"
DARK = "#111827"


class ExplainerScene(Scene):
    def construct(self) -> None:
        raise NotImplementedError

    def setup(self) -> None:
        self.camera.background_color = BG

    def label(self, text: str, size: int = 26, color: str = INK, weight: str = NORMAL) -> Text:
        return Text(text, font_size=size, color=color, weight=weight)

    def mono(self, text: str, size: int = 22, color: str = INK) -> Text:
        return Text(text, font="Menlo", font_size=size, color=color)

    def panel(self, width: float, height: float, fill: str = WHITE_ISH, stroke: str = "#DDE5EF") -> RoundedRectangle:
        return RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.12,
            fill_color=fill,
            fill_opacity=1.0,
            stroke_color=stroke,
            stroke_width=2,
        )

    def title_block(self, title: str, subtitle: str) -> VGroup:
        head = self.label(title, 36, INK, BOLD).to_edge(UP, buff=0.52)
        sub = self.label(subtitle, 21, MUTED).next_to(head, DOWN, buff=0.13)
        return VGroup(head, sub)

    def make_card(self, title: str, body: str, color: str, width: float = 3.65, height: float = 1.85) -> VGroup:
        box = self.panel(width, height)
        stripe = Rectangle(width=0.08, height=height, fill_color=color, fill_opacity=1, stroke_opacity=0)
        stripe.align_to(box, LEFT)
        t = self.label(title, 22, INK, BOLD)
        b = self.label(body, 17, MUTED)
        b.set(width=width - 0.6)
        content = VGroup(t, b).arrange(DOWN, aligned_edge=LEFT, buff=0.13)
        content.move_to(box).align_to(box, LEFT).shift(RIGHT * 0.26)
        return VGroup(box, stripe, content)

    def formula_panel(self, lines: list[tuple[str, str]], title: str, width: float = 5.7, height: float = 2.7) -> VGroup:
        box = self.panel(width, height)
        children = [self.label(title, 24, INK, BOLD)]
        for text, color in lines:
            children.append(self.mono(text, 19, color))
        content = VGroup(*children).arrange(DOWN, aligned_edge=LEFT, buff=0.13)
        content.move_to(box).align_to(box, LEFT).shift(RIGHT * 0.28)
        return VGroup(box, content)

    def tiny_table(self, headers: list[str], rows: list[list[str]], colors: list[str] | None = None) -> VGroup:
        table = VGroup()
        row_h = 0.48
        col_w = 1.25
        all_rows = [headers] + rows
        for r, row in enumerate(all_rows):
            cells = VGroup()
            for c, value in enumerate(row):
                fill = "#EEF3FA" if r == 0 else WHITE_ISH
                rect = Rectangle(width=col_w, height=row_h, fill_color=fill, fill_opacity=1, stroke_color=GRID, stroke_width=1)
                color = INK if colors is None or r == 0 else colors[min(r - 1, len(colors) - 1)]
                text = self.mono(value, 15, color) if r > 0 else self.label(value, 15, INK, BOLD)
                cells.add(VGroup(rect, text))
            cells.arrange(RIGHT, buff=0)
            table.add(cells)
        table.arrange(DOWN, buff=0)
        return table


class FeynRLESSMiniLesson(ExplainerScene):
    def construct(self) -> None:
        title = self.title_block(
            "FeynRL / P3O: trust the batch",
            "A tiny ratio batch makes ESS visible before the paper formula appears.",
        )
        cards = VGroup(
            self.make_card("Problem", "Replay samples come from an older policy.", BLUE),
            self.make_card("Signal", "Ratios show how off-policy the batch is.", ORANGE),
            self.make_card("Control", "ESS turns ratio spread into an update knob.", GREEN),
        ).arrange(RIGHT, buff=0.38).shift(DOWN * 0.3)
        arrows = VGroup(
            Arrow(cards[0].get_right(), cards[1].get_left(), buff=0.12, color=INK),
            Arrow(cards[1].get_right(), cards[2].get_left(), buff=0.12, color=INK),
        )
        self.play(FadeIn(title), LaggedStart(*(FadeIn(c, shift=UP * 0.12) for c in cards), lag_ratio=0.15))
        self.play(Create(arrows))
        self.wait(0.9)
        self.play(FadeOut(VGroup(title, cards, arrows)))

        title = self.title_block("Five samples are enough", "When one ratio dominates, the effective batch shrinks.")
        ratios_a = ["1.0", "0.9", "1.1", "1.0", "1.0"]
        ratios_b = ["0.2", "0.3", "0.4", "0.5", "4.0"]
        table_a = self.tiny_table(["token", "old p", "new p", "ratio"], [["a", ".10", ".10", ratios_a[0]], ["b", ".10", ".09", ratios_a[1]], ["c", ".10", ".11", ratios_a[2]], ["d", ".10", ".10", ratios_a[3]], ["e", ".10", ".10", ratios_a[4]]]).scale(0.95)
        table_b = self.tiny_table(["token", "old p", "new p", "ratio"], [["a", ".10", ".02", ratios_b[0]], ["b", ".10", ".03", ratios_b[1]], ["c", ".10", ".04", ratios_b[2]], ["d", ".10", ".05", ratios_b[3]], ["e", ".10", ".40", ratios_b[4]]], [MUTED, MUTED, MUTED, MUTED, RED]).scale(0.95)
        table_a.to_edge(LEFT, buff=0.75).shift(DOWN * 0.35)
        table_b.move_to(table_a)
        ess_a = self.ess_gauge(0.99, BLUE, "ESS about 0.99").to_edge(RIGHT, buff=1.0).shift(DOWN * 0.35)
        ess_b = self.ess_gauge(0.40, RED, "ESS about 0.40").move_to(ess_a)
        formula = self.formula_panel(
            [("ESS = (sum r)^2", BLUE), ("      / (n * sum r^2)", BLUE)],
            "Normalized effective sample size",
            4.65,
            1.65,
        ).next_to(ess_a, UP, buff=0.25)
        self.play(FadeIn(title), FadeIn(table_a), FadeIn(formula), FadeIn(ess_a))
        self.wait(0.9)
        self.play(Transform(table_a, table_b), Transform(ess_a, ess_b), run_time=1.5)
        self.play(Indicate(ess_a[-1], color=RED), run_time=0.7)
        self.wait(0.9)
        self.play(FadeOut(VGroup(title, table_a, formula, ess_a)))

        title = self.title_block("P3O uses ESS as a control signal", "The batch statistic changes the loss instead of relying only on a fixed clip.")
        left = self.formula_panel(
            [
                ("r = exp(logp - old_logp)", MUTED),
                ("rho = clamp(r, 0, ESS)", BLUE),
                ("loss_pg = - stopgrad(rho) * logp * A", BLUE),
                ("loss_kl = (1 - ESS) * KL(pi || pi_old)", RED),
            ],
            "Objective pieces",
            6.1,
            2.65,
        ).to_edge(LEFT, buff=0.6).shift(DOWN * 0.2)
        cap = self.cap_visual().to_edge(RIGHT, buff=0.95).shift(UP * 0.1)
        note = self.label("High ESS: trust policy-gradient signal. Low ESS: tighten and regularize.", 22, INK)
        note.to_edge(DOWN, buff=0.72)
        self.play(FadeIn(title), FadeIn(left), FadeIn(cap))
        self.play(Indicate(left[1][2], color=BLUE), Indicate(cap[1], color=BLUE), run_time=0.8)
        self.play(Indicate(left[1][4], color=RED), Indicate(cap[2], color=RED), FadeIn(note), run_time=0.8)
        self.wait(1.5)

    def ess_gauge(self, value: float, color: str, label: str) -> VGroup:
        box = self.panel(3.2, 2.0)
        track = Line(LEFT * 1.1, RIGHT * 1.1, color=GRID, stroke_width=12)
        fill = Line(track.get_left(), track.get_left() + RIGHT * 2.2 * value, color=color, stroke_width=12)
        dot = Dot(track.get_left() + RIGHT * 2.2 * value, radius=0.08, color=color)
        text = self.label(label, 24, color, BOLD).next_to(track, DOWN, buff=0.35)
        minmax = VGroup(self.label("0", 16, MUTED), self.label("1", 16, MUTED)).arrange(RIGHT, buff=2.0)
        minmax.next_to(track, UP, buff=0.15)
        group = VGroup(track, fill, dot, minmax, text).move_to(box)
        return VGroup(box, group)

    def cap_visual(self) -> VGroup:
        box = self.panel(4.25, 3.35)
        axis = VGroup(
            Line(LEFT * 1.45 + DOWN * 1.05, RIGHT * 1.45 + DOWN * 1.05, color=INK, stroke_width=2),
            Line(LEFT * 1.45 + DOWN * 1.05, LEFT * 1.45 + UP * 1.15, color=INK, stroke_width=2),
        )
        high = Line(LEFT * 1.25 + DOWN * 0.15, RIGHT * 1.25 + DOWN * 0.15, color=BLUE, stroke_width=5)
        low = Line(LEFT * 1.25 + DOWN * 0.75, RIGHT * 1.25 + DOWN * 0.75, color=RED, stroke_width=5)
        labels = VGroup(
            self.label("cap when ESS high", 17, BLUE, BOLD).next_to(high, UP, buff=0.08),
            self.label("cap when ESS low", 17, RED, BOLD).next_to(low, DOWN, buff=0.08),
            self.label("score weight cap", 17, MUTED).next_to(axis[1], LEFT, buff=0.1).rotate(PI / 2),
        )
        group = VGroup(axis, high, low, labels).move_to(box)
        return VGroup(box, high, low, group)


class DPOPreferenceExplainer(ExplainerScene):
    def construct(self) -> None:
        title = self.title_block(
            "DPO: learn from preference pairs",
            "Direct Preference Optimization turns winner-vs-loser data into a policy objective.",
        )
        pair = self.preference_pair().shift(UP * 0.15)
        self.play(FadeIn(title), FadeIn(pair, shift=UP * 0.1))
        self.wait(1.1)
        self.play(FadeOut(VGroup(title, pair)))

        title = self.title_block("The core comparison", "DPO compares how much the policy favors the winner over the loser, relative to a reference.")
        formula = self.formula_panel(
            [
                ("margin = [log pi(y+) - log pi(y-)]", BLUE),
                ("       - [log ref(y+) - log ref(y-)]", MUTED),
                ("loss = - log sigmoid(beta * margin)", ORANGE),
            ],
            "Preference log-ratio",
            6.3,
            2.35,
        ).to_edge(LEFT, buff=0.65).shift(DOWN * 0.25)
        bars = self.dpo_bars().to_edge(RIGHT, buff=1.0).shift(DOWN * 0.25)
        self.play(FadeIn(title), FadeIn(formula), FadeIn(bars))
        self.play(Indicate(formula[1][1], color=BLUE), Indicate(bars[1], color=GREEN), run_time=0.8)
        self.play(Indicate(formula[1][3], color=ORANGE), Indicate(bars[2], color=RED), run_time=0.8)
        self.wait(1.2)
        self.play(FadeOut(VGroup(title, formula, bars)))

        title = self.title_block("Why this is useful", "DPO avoids fitting an explicit reward model and then running RL.")
        steps = VGroup(
            self.make_card("RLHF route", "train reward model, then optimize policy with RL.", RED, 4.4, 1.45),
            self.make_card("DPO route", "optimize policy directly from preference pairs.", GREEN, 4.4, 1.45),
            self.make_card("Tradeoff", "simple objective, but it depends on beta and reference-policy grounding.", BLUE, 4.4, 1.45),
        ).arrange(DOWN, buff=0.28).shift(DOWN * 0.2)
        self.play(FadeIn(title), LaggedStart(*(FadeIn(s, shift=RIGHT * 0.15) for s in steps), lag_ratio=0.18))
        self.wait(2.5)

    def preference_pair(self) -> VGroup:
        prompt = self.make_card("Prompt", "Explain why rainbows form.", BLUE, 3.2, 1.25).to_edge(LEFT, buff=0.75)
        win = self.make_card("Chosen y+", "Mentions refraction, reflection, and dispersion.", GREEN, 3.9, 1.45)
        lose = self.make_card("Rejected y-", "Only says sunlight hits rain.", RED, 3.9, 1.45)
        answers = VGroup(win, lose).arrange(DOWN, buff=0.35).to_edge(RIGHT, buff=0.8)
        arrows = VGroup(
            Arrow(prompt.get_right(), win.get_left(), buff=0.12, color=GREEN),
            Arrow(prompt.get_right(), lose.get_left(), buff=0.12, color=RED),
        )
        badge = self.label("preference pair", 24, INK, BOLD).next_to(answers, UP, buff=0.35)
        return VGroup(prompt, answers, arrows, badge)

    def dpo_bars(self) -> VGroup:
        box = self.panel(4.05, 3.0)
        base = Line(LEFT * 1.45 + DOWN * 0.95, RIGHT * 1.45 + DOWN * 0.95, color=INK, stroke_width=2)
        win_bar = Rectangle(width=0.62, height=1.65, fill_color=GREEN, fill_opacity=0.9, stroke_opacity=0).next_to(base, UP, buff=0).shift(LEFT * 0.55)
        lose_bar = Rectangle(width=0.62, height=0.72, fill_color=RED, fill_opacity=0.9, stroke_opacity=0).next_to(base, UP, buff=0).shift(RIGHT * 0.55)
        labels = VGroup(
            self.label("winner", 18, GREEN, BOLD).next_to(win_bar, DOWN, buff=0.15),
            self.label("loser", 18, RED, BOLD).next_to(lose_bar, DOWN, buff=0.15),
            self.label("policy preference gap", 20, INK, BOLD).next_to(box, UP, buff=-0.45),
        )
        arrow = Arrow(lose_bar.get_top() + RIGHT * 0.25, win_bar.get_top() + LEFT * 0.25, color=ORANGE, buff=0.05)
        return VGroup(box, base, win_bar, lose_bar, labels, arrow)


class AttentionSoftmaxExplainer(ExplainerScene):
    def construct(self) -> None:
        title = self.title_block(
            "Attention is a soft lookup",
            "A query asks which keys matter, then mixes the corresponding values.",
        )
        qkv = self.qkv_blocks().shift(DOWN * 0.25)
        self.play(FadeIn(title), FadeIn(qkv))
        self.play(Indicate(qkv[0], color=BLUE), Indicate(qkv[1], color=ORANGE), run_time=0.8)
        self.wait(1.0)
        self.play(FadeOut(VGroup(title, qkv)))

        title = self.title_block("Scores become weights", "Scale the dot products, then softmax turns them into an attention distribution.")
        score_line = self.attention_scores().to_edge(LEFT, buff=0.75).shift(DOWN * 0.3)
        formula = self.formula_panel(
            [
                ("scores = Q K^T / sqrt(d_k)", BLUE),
                ("weights = softmax(scores)", ORANGE),
                ("output = weights V", GREEN),
            ],
            "Scaled dot-product attention",
            5.2,
            2.25,
        ).to_edge(RIGHT, buff=0.75).shift(DOWN * 0.3)
        self.play(FadeIn(title), FadeIn(score_line), FadeIn(formula))
        self.play(Indicate(score_line[1], color=ORANGE), Indicate(formula[1][2], color=ORANGE), run_time=0.8)
        self.wait(1.2)
        self.play(FadeOut(VGroup(title, score_line, formula)))

        title = self.title_block("The output is a mixture", "The model carries forward a weighted blend of value vectors.")
        mix = self.value_mixture().shift(DOWN * 0.15)
        takeaway = self.label("This is why attention can copy, combine, or ignore context positions.", 23, INK)
        takeaway.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(title), FadeIn(mix))
        self.play(FadeIn(takeaway), Indicate(mix[-1], color=GREEN), run_time=0.8)
        self.wait(1.8)

    def qkv_blocks(self) -> VGroup:
        q = self.make_card("Query Q", "what am I looking for?", BLUE, 3.2, 1.35)
        k = self.make_card("Keys K", "what does each position offer?", ORANGE, 3.2, 1.35)
        v = self.make_card("Values V", "what information can be copied?", GREEN, 3.2, 1.35)
        blocks = VGroup(q, k, v).arrange(RIGHT, buff=0.5)
        arrows = VGroup(Arrow(q.get_right(), k.get_left(), buff=0.12, color=INK), Arrow(k.get_right(), v.get_left(), buff=0.12, color=INK))
        return VGroup(q, k, v, arrows)

    def attention_scores(self) -> VGroup:
        box = self.panel(5.35, 3.2)
        words = ["the", "cat", "sat", "near", "fire"]
        scores = [0.05, 0.20, 0.08, 0.12, 0.55]
        bars = VGroup()
        for word, score in zip(words, scores):
            bar = Rectangle(width=0.46, height=2.1 * score / max(scores), fill_color=ORANGE, fill_opacity=0.88, stroke_opacity=0)
            lab = self.label(word, 15, INK).next_to(bar, DOWN, buff=0.12)
            num = self.mono(f"{score:.2f}", 13, MUTED).next_to(bar, UP, buff=0.08)
            bars.add(VGroup(bar, lab, num))
        bars.arrange(RIGHT, buff=0.34).move_to(box).shift(DOWN * 0.18)
        title = self.label("softmax attention weights", 20, INK, BOLD).next_to(box, UP, buff=-0.43)
        return VGroup(box, bars, title)

    def value_mixture(self) -> VGroup:
        left = self.attention_scores().scale(0.92).to_edge(LEFT, buff=0.65)
        values = VGroup(
            self.make_card("V1", "syntax", BLUE, 1.35, 0.78),
            self.make_card("V2", "subject", BLUE, 1.35, 0.78),
            self.make_card("V3", "verb", BLUE, 1.35, 0.78),
            self.make_card("V4", "place", BLUE, 1.35, 0.78),
            self.make_card("V5", "object", GREEN, 1.35, 0.78),
        ).arrange(DOWN, buff=0.12).to_edge(RIGHT, buff=2.3)
        out = self.make_card("output", "mostly object + some context", GREEN, 3.1, 1.15).to_edge(RIGHT, buff=0.65)
        arrows = VGroup()
        for v in values:
            arrows.add(Arrow(v.get_right(), out.get_left(), buff=0.08, color=GRID, stroke_width=2))
        arrows[-1].set_color(GREEN).set_stroke(width=5)
        return VGroup(left, values, arrows, out)


class TransformerCoreExplainer(ExplainerScene):
    def construct(self) -> None:
        title = self.title_block(
            "Transformer: all tokens talk at once",
            "Attention replaces recurrent stepping with a parallel lookup table.",
        )
        tokens = self.token_attention_board().shift(DOWN * 0.25)
        self.play(FadeIn(title), FadeIn(tokens))
        self.play(Indicate(tokens[2], color=ORANGE), run_time=0.8)
        self.wait(1.0)
        self.play(FadeOut(VGroup(title, tokens)))

        title = self.title_block("One lookup becomes many heads", "Each head projects Q, K, V differently, then the heads are concatenated.")
        heads = self.multi_head_board().to_edge(LEFT, buff=0.7).shift(DOWN * 0.3)
        formula = self.formula_panel(
            [
                ("head_i = Attn(QW_i^Q, KW_i^K, VW_i^V)", BLUE),
                ("MultiHead = Concat(head_1..head_h) W^O", GREEN),
            ],
            "Multi-head attention",
            5.8,
            2.15,
        ).to_edge(RIGHT, buff=0.65).shift(DOWN * 0.3)
        self.play(FadeIn(title), FadeIn(heads), FadeIn(formula))
        self.play(Indicate(heads[1], color=BLUE), Indicate(heads[2], color=GREEN), run_time=0.9)
        self.wait(1.2)
        self.play(FadeOut(VGroup(title, heads, formula)))

        title = self.title_block("But attention has no order by itself", "The original Transformer adds sinusoidal position signals to token vectors.")
        pos = self.position_encoding_board().shift(DOWN * 0.2)
        note = self.label("RoPE changes this last ingredient: position becomes rotation, not addition.", 22, INK)
        note.to_edge(DOWN, buff=0.65)
        self.play(FadeIn(title), FadeIn(pos))
        self.play(Indicate(pos[2], color=PURPLE), FadeIn(note), run_time=0.9)
        self.wait(1.6)

    def token_attention_board(self) -> VGroup:
        tokens = VGroup(
            self.make_card("the", "token 1", BLUE, 1.35, 0.82),
            self.make_card("cat", "token 2", BLUE, 1.35, 0.82),
            self.make_card("sat", "query", ORANGE, 1.35, 0.82),
            self.make_card("near", "token 4", BLUE, 1.35, 0.82),
            self.make_card("fire", "strong key", GREEN, 1.35, 0.82),
        ).arrange(RIGHT, buff=0.18)
        arrows = VGroup()
        query = tokens[2]
        for idx, tok in enumerate(tokens):
            if idx == 2:
                continue
            color = GREEN if idx == 4 else GRID
            width = 5 if idx == 4 else 2
            arrows.add(Arrow(query.get_top(), tok.get_top(), buff=0.12, color=color, stroke_width=width).shift(UP * 0.15))
        equation = self.mono("softmax(Q K^T / sqrt(d_k)) V", 23, INK).next_to(tokens, DOWN, buff=0.45)
        return VGroup(tokens, arrows, equation)

    def multi_head_board(self) -> VGroup:
        box = self.panel(5.2, 3.0)
        heads = VGroup(
            self.make_card("Head 1", "syntax", BLUE, 1.45, 0.85),
            self.make_card("Head 2", "object", GREEN, 1.45, 0.85),
            self.make_card("Head 3", "position", PURPLE, 1.45, 0.85),
        ).arrange(DOWN, buff=0.16)
        concat = self.make_card("Concat", "mix heads", ORANGE, 1.8, 1.05)
        group = VGroup(heads, concat).arrange(RIGHT, buff=0.5).move_to(box)
        arrows = VGroup(*(Arrow(h.get_right(), concat.get_left(), buff=0.08, color=GRID) for h in heads))
        return VGroup(box, heads, concat, arrows)

    def position_encoding_board(self) -> VGroup:
        box = self.panel(8.6, 3.05)
        token = self.make_card("token vector", "meaning", BLUE, 2.25, 0.95)
        plus = self.label("+", 30, INK, BOLD)
        waves = self.sinusoid_stripes()
        equals = self.label("=", 30, INK, BOLD)
        out = self.make_card("ordered vector", "meaning + position", GREEN, 2.55, 0.95)
        row = VGroup(token, plus, waves, equals, out).arrange(RIGHT, buff=0.28).move_to(box).shift(DOWN * 0.15)
        formula = self.mono("PE(pos, 2i)=sin(...), PE(pos, 2i+1)=cos(...)", 18, MUTED)
        formula.next_to(row, DOWN, buff=0.25)
        return VGroup(box, token, waves, row, formula)

    def sinusoid_stripes(self) -> VGroup:
        bars = VGroup()
        colors = [BLUE, GREEN, ORANGE, PURPLE, RED, YELLOW]
        heights = [0.35, 0.68, 0.48, 0.82, 0.55, 0.72]
        for i, h in enumerate(heights):
            bars.add(Rectangle(width=0.18, height=h, fill_color=colors[i], fill_opacity=0.85, stroke_opacity=0))
        bars.arrange(RIGHT, buff=0.08)
        label = self.label("PE(pos)", 17, INK, BOLD).next_to(bars, DOWN, buff=0.1)
        return VGroup(bars, label)


class RoPERotationExplainer(ExplainerScene):
    def construct(self) -> None:
        title = self.title_block(
            "RoPE: position as rotation",
            "Instead of adding a position vector, rotate Q and K by position-dependent angles.",
        )
        baselines = VGroup(
            self.make_card("Absolute", "x_m' = x_m + p_m", BLUE, 3.1, 1.25),
            self.make_card("Relative", "score += b_(m-n)", ORANGE, 3.1, 1.25),
            self.make_card("RoPE", "rotate pairs", GREEN, 3.1, 1.25),
        ).arrange(RIGHT, buff=0.38).shift(DOWN * 0.1)
        self.play(FadeIn(title), LaggedStart(*(FadeIn(c, shift=UP * 0.1) for c in baselines), lag_ratio=0.15))
        self.play(Indicate(baselines[2], color=GREEN), run_time=0.9)
        self.wait(1.0)
        self.play(FadeOut(VGroup(title, baselines)))

        title = self.title_block("A hidden pair rotates by m theta", "Every 2D coordinate pair gets its own rotation angle.")
        rotation = self.rotation_pair_board().to_edge(LEFT, buff=0.65).shift(DOWN * 0.25)
        formula = self.formula_panel(
            [
                ("R(m theta) = [[cos, -sin], [sin, cos]]", BLUE),
                ("RoPE(x_m) = R(m theta) x_m", GREEN),
            ],
            "2D rotary pair",
            5.6,
            2.15,
        ).to_edge(RIGHT, buff=0.65).shift(DOWN * 0.25)
        self.play(FadeIn(title), FadeIn(rotation), FadeIn(formula))
        self.play(Rotate(rotation[3], angle=0.7, about_point=rotation[1].get_center()), Indicate(formula[1][1], color=GREEN), run_time=1.0)
        self.wait(1.2)
        self.play(FadeOut(VGroup(title, rotation, formula)))

        title = self.title_block("Relative distance falls out of the dot product", "Two absolute rotations reduce to one relative rotation between positions.")
        rel = self.relative_property_board().shift(DOWN * 0.1)
        self.play(FadeIn(title), FadeIn(rel))
        self.play(Indicate(rel[1], color=GREEN), Indicate(rel[2], color=ORANGE), run_time=1.0)
        self.wait(1.5)
        self.play(FadeOut(VGroup(title, rel)))

        title = self.title_block("Many frequencies make a position fingerprint", "Different hidden pairs rotate at different speeds.")
        freq = self.frequency_board().shift(DOWN * 0.1)
        takeaway = self.label("That is why RoPE feels like sinusoidal position, but plugs directly into attention scores.", 21, INK)
        takeaway.to_edge(DOWN, buff=0.58)
        self.play(FadeIn(title), FadeIn(freq))
        self.play(Indicate(freq[1], color=PURPLE), FadeIn(takeaway), run_time=0.9)
        self.wait(1.7)

    def rotation_pair_board(self) -> VGroup:
        box = self.panel(4.6, 3.3)
        center = box.get_center() + DOWN * 0.1
        circle = Circle(radius=0.95, color=GRID).move_to(center)
        x_axis = Line(center + LEFT * 1.25, center + RIGHT * 1.25, color=MUTED, stroke_width=2)
        y_axis = Line(center + DOWN * 1.25, center + UP * 1.25, color=MUTED, stroke_width=2)
        base = Arrow(center, center + RIGHT * 0.9 + UP * 0.15, color=BLUE, buff=0, stroke_width=6)
        rotated = Arrow(center, center + RIGHT * 0.55 + UP * 0.75, color=GREEN, buff=0, stroke_width=6)
        labels = VGroup(
            self.label("x pair", 17, BLUE, BOLD).next_to(base.get_end(), RIGHT, buff=0.08),
            self.label("position m", 17, GREEN, BOLD).next_to(rotated.get_end(), UP, buff=0.08),
        )
        return VGroup(box, circle, VGroup(x_axis, y_axis), rotated, base, labels)

    def relative_property_board(self) -> VGroup:
        left = self.rotation_pair_board().scale(0.78).to_edge(LEFT, buff=0.65)
        formula = self.formula_panel(
            [
                ("dot(R_m q, R_n k)", BLUE),
                ("= dot(q, R_(n-m) k)", GREEN),
            ],
            "Key identity",
            4.95,
            1.9,
        ).move_to(ORIGIN).shift(DOWN * 0.15)
        distance = self.make_card("relative distance", "only n - m matters", ORANGE, 3.2, 1.15).to_edge(RIGHT, buff=0.8).shift(DOWN * 0.15)
        arrows = VGroup(
            Arrow(left.get_right(), formula.get_left(), buff=0.15, color=GRID),
            Arrow(formula.get_right(), distance.get_left(), buff=0.15, color=ORANGE),
        )
        return VGroup(left, formula, distance, arrows)

    def frequency_board(self) -> VGroup:
        box = self.panel(8.8, 3.15)
        rows = VGroup()
        data = [
            ("pair 1", 0.25, BLUE, "slow"),
            ("pair 2", 0.55, GREEN, "medium"),
            ("pair 3", 0.95, PURPLE, "fast"),
        ]
        for name, angle, color, speed in data:
            center = ORIGIN
            circ = Circle(radius=0.35, color=GRID)
            arrow = Arrow(center, center + RIGHT * 0.34, buff=0, color=color, stroke_width=5).rotate(angle, about_point=center)
            label = self.label(name, 17, INK, BOLD)
            tag = self.label(speed, 15, color, BOLD)
            row = VGroup(label, circ, arrow, tag).arrange(RIGHT, buff=0.26)
            rows.add(row)
        rows.arrange(DOWN, buff=0.2)
        formula = self.mono("theta_i = 10000^(-2(i-1)/d)", 21, INK)
        group = VGroup(rows, formula).arrange(RIGHT, buff=0.85).move_to(box)
        return VGroup(box, rows, formula, group)
