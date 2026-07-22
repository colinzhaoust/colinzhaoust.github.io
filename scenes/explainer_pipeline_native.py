"""Paper-native Manim scenes for the explainer pipeline.

These scenes are deterministic consumers of sourced concepts and values. They do
not reuse the earlier self-refinement videos and do not ask a coding agent to
write scene code at runtime.

Render:
    .venv-arm64/bin/manim -qm --media_dir runs/explainer_pipeline/native_manim \
      scenes/explainer_pipeline_native.py FeynRLEssP3O FeynRLFindings \
      RoPEFormulationAndCode RoPEFindings
"""

from __future__ import annotations

import math

from manim import *


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


class PaperNativeScene(Scene):
    def setup(self) -> None:
        self.camera.background_color = PAPER

    def heading(self, title: str, section: str) -> VGroup:
        tag = Text(section, font="Menlo", font_size=18, color=WARNING, weight=BOLD)
        name = Text(title, font_size=38, color=INK, weight=BOLD)
        group = VGroup(tag, name).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(UP, buff=0.34).to_edge(LEFT, buff=0.52)
        rule = Line(LEFT * 6.15, RIGHT * 6.15, stroke_color=RULE, stroke_width=1).next_to(group, DOWN, buff=0.2)
        return VGroup(group, rule)

    def source(self, text: str) -> Text:
        return Text(text, font="Menlo", font_size=14, color=MUTED).to_edge(DOWN, buff=0.24).to_edge(RIGHT, buff=0.42)

    def term(self, title: str, body: str, color: str, width: float = 5.5) -> VGroup:
        dot = Dot(radius=0.07, color=color)
        title_mob = Text(title, font_size=25, color=INK, weight=BOLD)
        body_mob = Text(body, font_size=18, color=MUTED, line_spacing=0.9)
        if body_mob.width > width - 0.42:
            body_mob.scale_to_fit_width(width - 0.42)
        copy = VGroup(title_mob, body_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        row = VGroup(dot, copy).arrange(RIGHT, aligned_edge=UP, buff=0.17)
        return row

    def ratio_bars(self, values: list[float], labels: list[str] | None = None) -> VGroup:
        maximum = max(values)
        bars = VGroup()
        for index, value in enumerate(values):
            height = max(0.08, 1.65 * value / maximum)
            bar = Rectangle(width=0.58, height=height, fill_color=ADAPTIVE, fill_opacity=0.9, stroke_width=0)
            value_label = DecimalNumber(value, num_decimal_places=1, font_size=18, color=INK).next_to(bar, UP, buff=0.08)
            token = Text((labels or [f"t{i+1}" for i in range(len(values))])[index], font="Menlo", font_size=14, color=MUTED).next_to(bar, DOWN, buff=0.1)
            bars.add(VGroup(bar, value_label, token))
        bars.arrange(RIGHT, aligned_edge=DOWN, buff=0.18)
        baseline = Line(bars.get_left() + DOWN * 0.12, bars.get_right() + DOWN * 0.12, color=RULE, stroke_width=2)
        return VGroup(baseline, bars)

    def code_panel(self, rows: list[tuple[str, str]], width: float = 11.7) -> VGroup:
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
        return VGroup(box, lines)

    def value_bar(self, label: str, value: float, maximum: float, color: str, unit: str = "") -> VGroup:
        name = Text(label, font_size=19, color=INK)
        if name.width > 2.35:
            name.scale_to_fit_width(2.35)
        label_slot = Rectangle(width=2.45, height=0.44, stroke_opacity=0, fill_opacity=0)
        name.move_to(label_slot).align_to(label_slot, LEFT)
        track = RoundedRectangle(width=5.0, height=0.38, corner_radius=0.06, fill_color=SOFT, fill_opacity=1, stroke_width=0)
        fill = RoundedRectangle(width=max(0.08, 5.0 * value / maximum), height=0.38, corner_radius=0.06, fill_color=color, fill_opacity=1, stroke_width=0)
        fill.align_to(track, LEFT)
        number = Text(f"{value:.3f}{unit}", font="Menlo", font_size=18, color=color, weight=BOLD)
        row = VGroup(VGroup(label_slot, name), VGroup(track, fill), number).arrange(RIGHT, buff=0.22)
        return row


class FeynRLEssP3O(PaperNativeScene):
    def construct(self) -> None:
        header = self.heading("Why measure the current batch?", "FEYNRL · MOTIVATION")
        concerns = VGroup(
            self.term("Trust-region concern", "Each gradient update should not move the policy too far.", CURRENT),
            self.term("Off-policy concern", "Data from a behavior policy should influence an update only when reliable.", BEHAVIOR),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.45).next_to(header, DOWN, buff=0.55).to_edge(LEFT, buff=0.9)
        clip = MathTex(r"\rho_t \in [1-\epsilon_\ell,\,1+\epsilon_h]", font_size=44, color=INK).to_edge(RIGHT, buff=0.95).shift(UP * 0.25)
        clip_note = Text("fixed before training", font_size=21, color=WARNING, weight=BOLD).next_to(clip, DOWN, buff=0.2)
        question = Text("But behavior-policy mismatch changes batch by batch.", font_size=25, color=INK, weight=BOLD).next_to(clip_note, DOWN, buff=0.55)
        question.set(width=4.7)
        src = self.source("FeynRL, Sec. 1 and Sec. 3")
        self.play(FadeIn(header), LaggedStart(*[FadeIn(item, shift=UP * 0.08) for item in concerns], lag_ratio=0.18), run_time=1.3)
        self.play(Write(clip), FadeIn(clip_note), run_time=0.8)
        self.play(FadeIn(question, shift=UP * 0.1), FadeIn(src), run_time=0.7)
        self.wait(1.3)
        self.play(FadeOut(VGroup(header, concerns, clip, clip_note, question, src)))

        header = self.heading("Effective sample size of policy ratios", "FEYNRL · EQ. 11")
        formula = MathTex(
            r"\operatorname{ESS}(B;\theta)=\frac{\widehat{\mathbb E}_B[\rho_t]^2}{\widehat{\mathbb E}_B[\rho_t^2]}",
            font_size=46,
            color=INK,
        ).next_to(header, DOWN, buff=0.35)
        uniform = self.ratio_bars([1.0, 1.0, 1.0, 1.0]).to_edge(LEFT, buff=1.2).shift(DOWN * 1.0)
        concentrated = self.ratio_bars([0.1, 0.1, 0.1, 3.7]).move_to(uniform)
        ess_value = VGroup(Text("ESS =", font_size=29, color=MUTED), DecimalNumber(1.0, num_decimal_places=3, font_size=40, color=ADAPTIVE)).arrange(RIGHT).to_edge(RIGHT, buff=1.45).shift(DOWN * 0.65)
        arrow = Arrow(uniform.get_right(), ess_value.get_left(), color=RULE, buff=0.35)
        explanation = Text("uniform ratios: the batch has broad effective support", font_size=21, color=ADAPTIVE)
        if explanation.width > 4.5:
            explanation.scale_to_fit_width(4.5)
        explanation.next_to(ess_value, DOWN, buff=0.35)
        src = self.source("Normalized ESS, FeynRL Eq. (11)")
        self.play(FadeIn(header), Write(formula), FadeIn(uniform), GrowArrow(arrow), FadeIn(ess_value), FadeIn(explanation), FadeIn(src), run_time=1.3)
        next_explanation = Text("concentrated ratios: a few tokens dominate the estimate", font_size=21, color=WARNING)
        if next_explanation.width > 4.5:
            next_explanation.scale_to_fit_width(4.5)
        next_explanation.move_to(explanation)
        self.play(Transform(uniform, concentrated), ess_value[1].animate.set_value(0.292).set_color(WARNING), Transform(explanation, next_explanation), run_time=1.8)
        necessity = Text("ESS is the paper's batch-computed measure of behavior-policy mismatch.", font_size=25, color=INK, weight=BOLD).to_edge(DOWN, buff=0.72)
        self.play(FadeOut(src), FadeIn(necessity, shift=UP * 0.1), run_time=0.7)
        self.wait(1.4)
        self.play(FadeOut(VGroup(header, formula, uniform, arrow, ess_value, explanation, necessity)))

        header = self.heading("Policy-on Policy-off Policy Optimization", "FEYNRL · EQ. 12 + CODE")
        objective = MathTex(
            r"\mathcal L_{\mathrm{P3O}} = -\operatorname{sg}(\min\{\rho_t,e_B\})\log\pi_\theta A"
            r"+(1-e_B)\operatorname{KL}(\pi_\theta\Vert\pi_b)",
            font_size=36,
            color=INK,
            substrings_to_isolate=[r"\min\{\rho_t,e_B\}", r"(1-e_B)"],
        ).move_to([0, 2.05, 0])
        objective.set_color_by_tex(r"\min\{\rho_t,e_B\}", ADAPTIVE)
        objective.set_color_by_tex(r"(1-e_B)", WARNING)
        cap_label = Text("score-function weight", font_size=18, color=ADAPTIVE, weight=BOLD).move_to([-3.3, 1.0, 0])
        kl_label = Text("off-policy regularizer", font_size=18, color=WARNING, weight=BOLD).move_to([3.6, 1.0, 0])
        code = self.code_panel([
            ("ess_factor = calculate_ess(ratio[mask])", "Eq. 11, valid tokens"),
            ("rho = clamp(ratio, max=ess_factor)", "min{rho_t, e_B}"),
            ("policy = -(rho.detach() * logprobs * adv)", "stop-gradient score term"),
            ("trust_region = (1 - ess_factor) * kl_behavioral", "adaptive KL to behavior policy"),
        ]).move_to([0, -0.55, 0])
        takeaway = Text("Fresh batch: e_B near 1.  Mismatched batch: smaller cap and stronger KL.", font_size=24, color=INK, weight=BOLD).to_edge(DOWN, buff=0.48)
        src = self.source("FeynRL Eq. (12); algs/P3O/p3o.py @ dfe8535")
        self.play(FadeIn(header), Write(objective), run_time=1.1)
        self.play(FadeIn(cap_label), Indicate(objective, color=ADAPTIVE), run_time=0.6)
        self.play(FadeIn(kl_label), run_time=0.4)
        self.play(FadeIn(code[0]), LaggedStart(*[FadeIn(row, shift=RIGHT * 0.08) for row in code[1]], lag_ratio=0.16), run_time=1.5)
        self.play(FadeIn(takeaway), FadeIn(src), run_time=0.7)
        self.wait(2.0)


class FeynRLFindings(PaperNativeScene):
    def construct(self) -> None:
        header = self.heading("What the experiments test", "FEYNRL · SECTION 4")
        axes = VGroup(
            self.term("Clipping factor", "Sensitivity to ε ∈ {0.2, 0.4, 0.6}.", WARNING, 3.5),
            self.term("Sampling temperature", "Off-policy data from varied rollout temperature.", BEHAVIOR, 3.8),
            self.term("BF16 Train + FP8 Rollout", "Off-policy data from train–rollout precision mismatch.", CURRENT, 4.0),
        ).arrange(RIGHT, aligned_edge=UP, buff=0.5).next_to(header, DOWN, buff=0.75)
        finding = Text("Paper finding: one P3O objective is evaluated across all three regimes.", font_size=28, color=INK, weight=BOLD).to_edge(DOWN, buff=1.05)
        src = self.source("FeynRL Sec. 4, Figs. 1–4")
        self.play(FadeIn(header), LaggedStart(*[FadeIn(item, shift=UP * 0.1) for item in axes], lag_ratio=0.2), run_time=1.4)
        self.play(FadeIn(finding), FadeIn(src), run_time=0.8)
        self.wait(1.4)
        self.play(FadeOut(VGroup(header, axes, finding, src)))

        header = self.heading("Held-out benchmark findings", "FEYNRL · TABLE 7 · AMC PASS@1")
        clip_title = Text("Clip variants, 4K-token evaluation", font_size=24, color=INK, weight=BOLD).next_to(header, DOWN, buff=0.45).to_edge(LEFT, buff=0.9)
        clip_rows = VGroup(
            self.value_bar("GRPO clip average", 0.381, 0.6, BEHAVIOR),
            self.value_bar("P3O", 0.493, 0.6, ADAPTIVE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.28).next_to(clip_title, DOWN, buff=0.3).to_edge(LEFT, buff=0.9)
        note = Text("P3O is run once, without a clip-ratio choice.", font_size=21, color=ADAPTIVE).next_to(clip_rows, DOWN, buff=0.28).align_to(clip_rows, LEFT)
        self.play(FadeIn(header), FadeIn(clip_title), LaggedStart(*[FadeIn(row, shift=RIGHT * 0.12) for row in clip_rows], lag_ratio=0.25), FadeIn(note), run_time=1.6)

        fp8_title = Text("BF16 Train + FP8 Rollout", font_size=24, color=INK, weight=BOLD).next_to(note, DOWN, buff=0.52).align_to(clip_title, LEFT)
        iter15 = VGroup(
            self.value_bar("GRPO · iteration 15", 0.499, 0.6, BEHAVIOR),
            self.value_bar("P3O · iteration 15", 0.478, 0.6, ADAPTIVE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.22).next_to(fp8_title, DOWN, buff=0.25).align_to(clip_rows, LEFT)
        iter30 = VGroup(
            self.value_bar("GRPO · iteration 30", 0.029, 0.6, CORAL),
            self.value_bar("P3O · iteration 30", 0.529, 0.6, ADAPTIVE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.22).move_to(iter15).align_to(iter15, LEFT)
        src = self.source("Exact values: FeynRL Table 7")
        self.play(FadeIn(fp8_title), FadeIn(iter15), FadeIn(src), run_time=0.9)
        self.wait(0.8)
        self.play(Transform(iter15, iter30), run_time=1.8)
        conclusion = Text("The paper connects training-curve robustness to retained held-out performance.", font_size=23, color=INK, weight=BOLD).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(conclusion), run_time=0.7)
        self.wait(2.0)


class RoPEFormulationAndCode(PaperNativeScene):
    def construct(self) -> None:
        header = self.heading("Formulation of relative position encoding", "ROFORMER · EQ. 11")
        requirement = MathTex(
            r"\langle f_q(x_m,m), f_k(x_n,n)\rangle = g(x_m,x_n,m-n)",
            font_size=48,
            color=INK,
        ).next_to(header, DOWN, buff=0.55)
        left = self.term("Inputs to f_q and f_k", "word embedding and absolute position", CURRENT, 4.4).move_to([-3.5, -0.1, 0])
        right = self.term("Input to g", "word embeddings and relative position m−n", WARNING, 4.4).move_to([3.5, -0.1, 0])
        question = Text("Find f_q and f_k that satisfy this relation.", font_size=29, color=INK, weight=BOLD).to_edge(DOWN, buff=0.9)
        src = self.source("RoFormer Sec. 3.1, Eq. (11)")
        self.play(FadeIn(header), Write(requirement), run_time=1.2)
        self.play(FadeIn(left, shift=RIGHT * 0.1), FadeIn(right, shift=LEFT * 0.1), FadeIn(question), FadeIn(src), run_time=1.0)
        self.wait(1.4)
        self.play(FadeOut(VGroup(header, requirement, left, right, question, src)))

        header = self.heading("Rotary position embedding", "ROFORMER · EQS. 14–16")
        center = LEFT * 3.65 + DOWN * 0.25
        plane = VGroup(
            Circle(radius=1.5, color=RULE),
            Line(center + LEFT * 1.75, center + RIGHT * 1.75, color=RULE),
            Line(center + DOWN * 1.75, center + UP * 1.75, color=RULE),
        )
        plane.move_to(center)
        q = Arrow(center, center + RIGHT * 1.25 + UP * 0.25, buff=0, stroke_width=7, color=CURRENT)
        k = Arrow(center, center + RIGHT * 0.85 + DOWN * 0.9, buff=0, stroke_width=7, color=BEHAVIOR)
        q_label = MathTex(r"W^q x_m", font_size=27, color=CURRENT).next_to(q.get_end(), UP, buff=0.08)
        k_label = MathTex(r"W^k x_n", font_size=27, color=BEHAVIOR).next_to(k.get_end(), DOWN, buff=0.08)
        geometry = VGroup(plane, q, k, q_label, k_label)
        rotations = VGroup(
            MathTex(r"q_m=R_{\Theta,m}^d W^q x_m", font_size=35, color=CURRENT),
            MathTex(r"k_n=R_{\Theta,n}^d W^k x_n", font_size=35, color=BEHAVIOR),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.32).to_edge(RIGHT, buff=0.75).shift(UP * 0.3)
        identity = MathTex(r"q_m^\top k_n=x_m^\top W^{q\top}R_{\Theta,n-m}^dW^k x_n", font_size=35, color=INK).next_to(rotations, DOWN, buff=0.62)
        identity.set_color_by_tex(r"n-m", WARNING)
        src = self.source("RoFormer Eq. (16): (R_m)^T R_n = R_{n-m}")
        self.play(FadeIn(header), FadeIn(geometry), FadeIn(rotations), run_time=1.2)
        self.play(Rotate(q, angle=0.65, about_point=center), Rotate(k, angle=1.05, about_point=center), run_time=1.5)
        self.play(Write(identity), FadeIn(src), run_time=1.1)
        self.wait(1.3)
        self.play(FadeOut(VGroup(header, geometry, rotations, identity, src)))

        header = self.heading("Computationally efficient realization", "ROFORMER · SECTION 3.4.2 + CODE")
        algebra = VGroup(
            MathTex(r"q_\perp=(-q_2,q_1,-q_4,q_3,\ldots)", font_size=35, color=WARNING),
            MathTex(r"R_m q=q\cos(m\theta)+q_\perp\sin(m\theta)", font_size=38, color=INK),
        ).arrange(DOWN, buff=0.28).move_to([0, 1.55, 0])
        code = self.code_panel([
            ("qw2 = stack([-qw[..., 1::2], qw[..., ::2]])", "construct q_perp"),
            ("qw = qw * cos_pos + qw2 * sin_pos", "apply R_m to q"),
            ("kw = kw * cos_pos + kw2 * sin_pos", "apply R_n to k"),
            ("a = einsum('bjhd,bkhd->bhjk', qw, kw)", "ordinary dot product after rotation"),
        ]).move_to([0, -0.85, 0])
        takeaway = Text("RoPE is multiplicative; no dense rotary matrix is materialized.", font_size=25, color=INK, weight=BOLD).to_edge(DOWN, buff=0.48)
        src = self.source("Official RoFormer README @ dfc678a; paper Sec. 3.4.2")
        self.play(FadeIn(header), Write(algebra), run_time=1.1)
        self.play(FadeIn(code[0]), LaggedStart(*[FadeIn(row, shift=RIGHT * 0.08) for row in code[1]], lag_ratio=0.16), run_time=1.5)
        self.play(FadeIn(takeaway), FadeIn(src), run_time=0.7)
        self.wait(2.0)


class RoPEFindings(PaperNativeScene):
    def construct(self) -> None:
        header = self.heading("Properties studied in the paper", "ROFORMER · SECTION 3.3")
        properties = VGroup(
            self.term("Sequence length flexibility", "Position is applied through rotation rather than a learned position table.", CURRENT, 3.6),
            self.term("Long-term decay", "The paper studies decay with increasing relative distance.", WARNING, 3.6),
            self.term("Linear self-attention", "Rotation preserves vector norms and can equip linear attention with relative position encoding.", ADAPTIVE, 4.0),
        ).arrange(RIGHT, aligned_edge=UP, buff=0.45).next_to(header, DOWN, buff=0.72)
        if properties.width > 12.2:
            properties.scale_to_fit_width(12.2)
        properties.move_to([0, 0.45, 0])
        src = self.source("RoFormer Sec. 3.3 and Fig. 2")
        self.play(FadeIn(header), LaggedStart(*[FadeIn(item, shift=UP * 0.1) for item in properties], lag_ratio=0.2), FadeIn(src), run_time=1.6)
        self.wait(1.5)
        self.play(FadeOut(VGroup(header, properties, src)))

        header = self.heading("Experimental findings", "ROFORMER · SECTION 4")
        number_line = NumberLine(x_range=[27.0, 27.7, 0.1], length=7.0, color=RULE, include_numbers=True, font_size=18).shift(UP * 1.25)
        base_dot = Dot(number_line.n2p(27.3), radius=0.11, color=BEHAVIOR)
        rope_dot = Dot(number_line.n2p(27.5), radius=0.11, color=ADAPTIVE)
        base_label = Text("Transformer-base 27.3", font_size=20, color=BEHAVIOR).next_to(base_dot, UP, buff=0.2)
        rope_label = Text("RoFormer 27.5", font_size=20, color=ADAPTIVE, weight=BOLD).next_to(rope_dot, DOWN, buff=0.2)
        wmt = VGroup(number_line, base_dot, rope_dot, base_label, rope_label).next_to(header, DOWN, buff=0.55)
        findings = VGroup(
            self.term("Language-model pre-training", "Figure 3 reports faster convergence than the BERT baseline.", CURRENT, 5.2),
            self.term("Performer with RoPE", "Figure 3 reports rapid convergence and lower loss than Performer without RoPE.", ADAPTIVE, 5.2),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.34).next_to(wmt, DOWN, buff=0.55)
        boundary = Text("These are the paper's reported findings, not a universal extrapolation guarantee.", font_size=22, color=INK, weight=BOLD).to_edge(DOWN, buff=0.5)
        src = self.source("Exact BLEU: RoFormer Table 1; reported trends: Fig. 3")
        self.play(FadeIn(header), Create(number_line), FadeIn(base_dot), FadeIn(base_label), run_time=1.0)
        self.play(FadeIn(rope_dot, scale=1.5), FadeIn(rope_label), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * 0.1) for item in findings], lag_ratio=0.22), FadeIn(boundary), FadeIn(src), run_time=1.4)
        self.wait(2.0)
