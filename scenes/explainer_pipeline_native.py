"""Paper-native Manim scenes for the explainer pipeline.

These scenes are deterministic consumers of sourced concepts and values. They do
not reuse the earlier self-refinement videos and do not ask a coding agent to
write scene code at runtime.

Render:
    .venv-arm64/bin/manim -qm --media_dir runs/explainer_pipeline/native_manim \
      scenes/explainer_pipeline_native.py FeynRLEssMicro FeynRLP3OMicro \
      FeynRLFindings RoPERelativeMicro RoPEFindings
"""

from __future__ import annotations

from manim import *
from explainer_primitives import (
    ADAPTIVE,
    BEHAVIOR,
    CORAL,
    CURRENT,
    EssTradeoffGauge,
    FormulaCodeBridge,
    INK,
    MUTED,
    MetricBars,
    PAPER,
    PaperNativeScene,
    RoPERelativeRotation,
    RULE,
    SOFT,
    WARNING,
)


class FeynRLEssMicro(PaperNativeScene):
    """Eq. (11) as one state change: token count fixed, concentration changes."""

    def construct(self) -> None:
        formula = MathTex(
            r"e_B=\frac{\widehat{\mathbb E}_B[\rho_t]^2}{\widehat{\mathbb E}_B[\rho_t^2]}",
            font_size=48,
            color=INK,
        ).to_edge(UP, buff=0.7)
        balanced = EssTradeoffGauge([1.0, 1.0, 1.0, 1.0]).scale(1.25).move_to(DOWN * 0.2)
        concentrated = EssTradeoffGauge([0.1, 0.1, 0.1, 3.7]).scale(1.25).move_to(balanced)
        source = self.source("FeynRL Eq. (11) · same four valid tokens")
        self.play(Write(formula), FadeIn(balanced), FadeIn(source), run_time=1.0)
        self.wait(0.45)
        self.play(Transform(balanced, concentrated), run_time=1.8)
        self.wait(0.85)


class FeynRLP3OMicro(PaperNativeScene):
    """Eq. (12) control coupling from the same batch value e_B."""

    def construct(self) -> None:
        formula = MathTex(
            r"\operatorname{sg}(\min\{\rho_t,e_B\})",
            r"\qquad",
            r"(1-e_B)\operatorname{KL}(\pi_\theta\Vert\pi_b)",
            font_size=41,
        ).to_edge(UP, buff=0.65)
        formula[0].set_color(ADAPTIVE)
        formula[2].set_color(WARNING)
        matched = EssTradeoffGauge([1.0, 1.0, 1.0, 1.0], include_controls=True).scale(0.88).move_to(DOWN * 0.25)
        mismatched = EssTradeoffGauge([0.1, 0.1, 0.1, 3.7], include_controls=True).scale(0.88).move_to(matched)
        coupling = VGroup(
            Text("cap", font="Menlo", font_size=18, color=ADAPTIVE),
            Arrow(LEFT * 0.7, RIGHT * 0.7, color=RULE, buff=0.08),
            Text("KL weight", font="Menlo", font_size=18, color=WARNING),
        ).arrange(RIGHT, buff=0.14).to_edge(DOWN, buff=0.62)
        source = self.source("FeynRL Eq. (12) · both controls use e_B")
        self.play(Write(formula), FadeIn(matched), FadeIn(source), run_time=1.0)
        self.play(FadeIn(coupling), run_time=0.45)
        self.play(Transform(matched, mismatched), run_time=1.8)
        self.wait(0.85)


class RoPERelativeMicro(PaperNativeScene):
    """Eq. (16) as a single geometric collapse from two rotations to n-m."""

    def construct(self) -> None:
        identity = MathTex(
            r"(R_m q)^\top(R_n k)=q^\top R_{n-m}k",
            font_size=47,
            color=INK,
        ).to_edge(UP, buff=0.58)
        visual = RoPERelativeRotation(m_angle=0.55, n_angle=1.2).scale(1.18).shift(DOWN * 0.25)
        source = self.source("RoFormer Eq. (16) · R_m^T R_n = R_{n-m}")
        self.play(Write(identity), FadeIn(visual.frame), FadeIn(visual.initial_vectors), FadeIn(source), run_time=1.1)
        self.wait(0.35)
        self.play(
            FadeOut(visual.initial_vectors),
            visual.rotated_vectors.animate.set_opacity(1),
            run_time=1.5,
        )
        self.play(visual.labels.animate.set_opacity(1), run_time=0.65)
        self.wait(0.9)


class FeynRLEquationLineageMicro(PaperNativeScene):
    """PPO → original P3O → FeynRL: equation ownership and adaptation."""

    def construct(self) -> None:
        tag = Text("FEYNRL · EQUATION LINEAGE", font="Menlo", font_size=17, color=WARNING, weight=BOLD).to_edge(UP, buff=0.45)
        paper = Text("PPO · Schulman et al. · 2017", font="Menlo", font_size=18, color=BEHAVIOR, weight=BOLD).next_to(tag, DOWN, buff=0.28)
        stage = Text("fixed clipping · reproduced as FeynRL Eq. 4", font_size=20, color=MUTED).next_to(paper, DOWN, buff=0.16)
        equation = MathTex(r"\min\{\rho_tA,\operatorname{clip}(\rho_t,1-\epsilon,1+\epsilon)A\}", font_size=38, color=INK).move_to(UP * 0.15)
        change = Text("fixed ε is chosen before this batch is observed", font_size=21, color=WARNING).next_to(equation, DOWN, buff=0.52)
        source = self.source("PPO (2017) → P3O (2020) → FeynRL Eqs. (4), (7), (11–12)")
        self.play(FadeIn(tag), FadeIn(paper), FadeIn(stage), Write(equation), FadeIn(change), FadeIn(source), run_time=1.4)
        self.wait(1.15)

        transitions = [
            (
                "P3O · Fakoor et al. · 2020",
                "on-policy + off-policy objective · P3O Eqs. 1, 14–16",
                MathTex(r"\mathcal J_{on}+\lambda\mathcal J_{off}(c)+\operatorname{KL},\quad c=\operatorname{ESS},\ \lambda=1-\operatorname{ESS}", font_size=34, color=INK),
                "ESS already controls both off-policy cap and mixture weight",
                ADAPTIVE,
            ),
            (
                "FeynRL · large-model post-training · 2026",
                "per-token behavior-policy correction · Eq. 7",
                MathTex(r"\rho_t(\theta)=\frac{\pi_\theta(y_t\mid x,y_{<t})}{\pi_b(y_t\mid x,y_{<t})}", font_size=43, color=INK),
                "adapt P3O's correction to every generated token",
                BEHAVIOR,
            ),
            (
                "FeynRL · large-model post-training · 2026",
                "normalized batch ESS + P3O · Eqs. 11–12",
                MathTex(r"e_B=\frac{\widehat{\mathbb E}[\rho]^2}{\widehat{\mathbb E}[\rho^2]}", r"\quad\Longrightarrow\quad", r"\min\{\rho_t,e_B\}+(1-e_B)\operatorname{KL}", font_size=37),
                "one measured e_B acts in two token-level terms",
                ADAPTIVE,
            ),
        ]
        for paper_label, label, target, note, color in transitions:
            target.move_to(equation)
            next_paper = Text(paper_label, font="Menlo", font_size=18, color=color, weight=BOLD).move_to(paper)
            next_stage = Text(label, font_size=21, color=MUTED).move_to(stage)
            next_change = Text(note, font_size=22, color=color).move_to(change)
            self.play(TransformMatchingTex(equation, target), Transform(paper, next_paper), Transform(stage, next_stage), Transform(change, next_change), run_time=2.25)
            self.wait(1.05)
            equation = target
        self.wait(1.0)


class RoPEEquationLineageMicro(PaperNativeScene):
    """Eqs. 3–16: additive terms become a multiplicative rotation."""

    def construct(self) -> None:
        tag = Text("ROFORMER · EQUATION LINEAGE", font="Menlo", font_size=17, color=WARNING, weight=BOLD).to_edge(UP, buff=0.45)
        paper = Text("Transformer · Vaswani et al. · 2017", font="Menlo", font_size=18, color=BEHAVIOR, weight=BOLD).next_to(tag, DOWN, buff=0.28)
        stage = Text("sinusoidal absolute position · RoFormer Eqs. 3–4", font_size=20, color=MUTED).next_to(paper, DOWN, buff=0.16)
        equation = MathTex(r"f_t(x_i,i)=W_t(x_i+p_i)", font_size=49, color=INK).move_to(UP * 0.45)
        change = Text("position is added before projection", font_size=22, color=CURRENT).next_to(equation, DOWN, buff=0.55)
        source = self.source("Transformer (2017) → Shaw (2018) → Transformer-XL (2019) → RoFormer (2021)")
        self.play(FadeIn(tag), FadeIn(paper), FadeIn(stage), Write(equation), FadeIn(change), FadeIn(source), run_time=1.4)
        self.wait(1.15)
        transitions = [
            ("Shaw et al. · 2018", "relative key · RoFormer Eq. 5", MathTex(r"q_m^\top(k_n+a^K_{m,n})", font_size=46, color=INK), "relative displacement is explicit, but still added to the key", BEHAVIOR),
            ("Transformer-XL · Dai et al. · 2019", "decomposed relative score · RoFormer Eqs. 6–7", MathTex(r"q_m^\top k_n+q_m^\top r_{m-n}+u^\top k_n+v^\top r_{m-n}", font_size=37, color=INK), "separate content and position terms inside an additive score", BEHAVIOR),
            ("T5 · TUPE · DeBERTa · 2020", "later relative-attention variants · RoFormer Eqs. 8–10", MathTex(r"\text{content score}+\text{selected position / bias terms}", font_size=39, color=INK), "change which additive interactions are retained or disentangled", WARNING),
            ("RoFormer · Su et al. · 2021", "functional requirement · Eq. 11", MathTex(r"\langle f_q(x_m,m),f_k(x_n,n)\rangle=g(x_m,x_n,m-n)", font_size=41, color=INK), "ask for the relative relation before choosing an operator", WARNING),
            ("RoFormer · Su et al. · 2021", "multiplicative rotary solution · Eqs. 12–16", MathTex(r"(R_mW^qx_m)^\top(R_nW^kx_n)=x_m^\top W^{q\top}R_{n-m}W^kx_n", font_size=36, color=INK), "two absolute rotations collapse into one relative rotation", ADAPTIVE),
        ]
        for paper_label, label, target, note, color in transitions:
            target.move_to(equation)
            next_paper = Text(paper_label, font="Menlo", font_size=18, color=color, weight=BOLD).move_to(paper)
            next_stage = Text(label, font_size=21, color=MUTED).move_to(stage)
            next_change = Text(note, font_size=22, color=color).move_to(change)
            self.play(TransformMatchingTex(equation, target), Transform(paper, next_paper), Transform(stage, next_stage), Transform(change, next_change), run_time=2.25)
            self.wait(1.05)
            equation = target
        self.wait(1.0)


class FeynRLResultsMicro(PaperNativeScene):
    """Experimental questions first; exact Table 7 values where available."""

    def construct(self) -> None:
        tag = Text("FEYNRL · RESULT TRAJECTORIES", font="Menlo", font_size=17, color=WARNING, weight=BOLD).to_edge(UP, buff=0.42)
        question = Text("Does BF16 Train + FP8 Rollout cause late collapse?", font_size=28, color=INK, weight=BOLD).next_to(tag, DOWN, buff=0.32)
        setting = Text("held-out average pass@1 · Table 7", font="Menlo", font_size=16, color=MUTED).next_to(question, DOWN, buff=0.16)
        bars15 = MetricBars([("GRPO · iteration 15", 0.499, BEHAVIOR), ("P3O · iteration 15", 0.478, ADAPTIVE)], maximum=0.6).scale(1.05).move_to(DOWN * 0.1)
        bars30 = MetricBars([("GRPO · iteration 30", 0.029, CORAL), ("P3O · iteration 30", 0.529, ADAPTIVE)], maximum=0.6).scale(1.05).move_to(bars15)
        marker = Text("ITERATION 15", font="Menlo", font_size=17, color=MUTED).next_to(bars15, DOWN, buff=0.45)
        source = self.source("Exact values · FeynRL Table 7")
        self.play(FadeIn(tag), FadeIn(question), FadeIn(setting), FadeIn(bars15), FadeIn(marker), FadeIn(source), run_time=1.0)
        next_marker = Text("ITERATION 30", font="Menlo", font_size=17, color=WARNING, weight=BOLD).move_to(marker)
        self.play(Transform(bars15, bars30), Transform(marker, next_marker), run_time=1.8)
        takeaway = Text("GRPO: 0.499 → 0.029     P3O: 0.478 → 0.529", font_size=24, color=INK, weight=BOLD).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(takeaway), run_time=0.55)
        self.wait(0.9)


class RoPEDecayMicro(PaperNativeScene):
    """Eqs. 35–37: paired frequencies lose alignment with distance."""

    def construct(self) -> None:
        tag = Text("ROFORMER · LONG-TERM DECAY", font="Menlo", font_size=17, color=WARNING, weight=BOLD).to_edge(UP, buff=0.42)
        equation = MathTex(r"q_m^\top k_n=\Re\!\left[\sum_j h_j e^{i(m-n)\theta_j}\right]", font_size=43, color=INK).next_to(tag, DOWN, buff=0.35)
        axes = Axes(x_range=[0, 16, 4], y_range=[0, 1.1, 0.25], x_length=8.5, y_length=3.3, axis_config={"color": RULE, "include_numbers": False}).shift(DOWN * 0.65)
        curve = axes.plot(lambda x: 1 / (1 + 0.14 * x), x_range=[0, 16], color=ADAPTIVE, stroke_width=5)
        dot = Dot(axes.c2p(0, 1), color=WARNING, radius=0.09)
        x_label = Text("relative distance |m−n|", font_size=18, color=MUTED).next_to(axes, DOWN, buff=0.16)
        note = Text("schematic bound shape · not digitized Figure 2", font="Menlo", font_size=14, color=MUTED).next_to(x_label, DOWN, buff=0.1)
        source = self.source("RoFormer Eqs. (35–37) and Fig. 2")
        self.play(FadeIn(tag), Write(equation), Create(axes), FadeIn(x_label), FadeIn(note), FadeIn(source), run_time=1.1)
        self.play(Create(curve), MoveAlongPath(dot, curve), run_time=2.3)
        self.wait(0.8)


class RoPEResultsMicro(PaperNativeScene):
    """Exact result slices reveal mixed GLUE and a long-sequence gain."""

    def construct(self) -> None:
        tag = Text("ROFORMER · RESULT TRAJECTORIES", font="Menlo", font_size=17, color=WARNING, weight=BOLD).to_edge(UP, buff=0.42)
        question = Text("Is RoFormer uniformly better across GLUE?", font_size=28, color=INK, weight=BOLD).next_to(tag, DOWN, buff=0.3)
        labels = ["MRPC", "SST-2", "QNLI", "STS-B", "QQP", "MNLI-m"]
        deltas = [0.6, -2.8, -2.5, 1.2, 15.2, -4.4]
        rows = VGroup()
        for label, delta in zip(labels, deltas):
            name = Text(label, font="Menlo", font_size=16, color=INK)
            number = Text(f"{delta:+.1f}", font="Menlo", font_size=18, color=ADAPTIVE if delta > 0 else CORAL, weight=BOLD)
            glyph = Arrow(ORIGIN, (RIGHT if delta > 0 else LEFT) * (0.35 + min(abs(delta), 6) * 0.22), buff=0, stroke_width=6, color=ADAPTIVE if delta > 0 else CORAL)
            rows.add(VGroup(name, glyph, number).arrange(RIGHT, buff=0.22))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to(DOWN * 0.28)
        note = Text("RoFormer − BERT · exact Table 2 task scores", font="Menlo", font_size=15, color=MUTED).next_to(rows, DOWN, buff=0.35)
        source = self.source("Exact values · RoFormer Tables 2 and 5")
        self.play(FadeIn(tag), FadeIn(question), LaggedStart(*[FadeIn(row, shift=RIGHT * 0.08) for row in rows], lag_ratio=0.1), FadeIn(note), FadeIn(source), run_time=1.3)
        self.wait(0.65)
        next_question = Text("Does a longer input help on CAIL2019-SCM?", font_size=28, color=INK, weight=BOLD).move_to(question)
        cail = MetricBars([("RoFormer-512", 68.29, BEHAVIOR), ("RoFormer-1024", 69.79, ADAPTIVE)], maximum=72, decimals=2).scale(1.05).move_to(rows)
        next_note = Text("test accuracy · exact Table 5", font="Menlo", font_size=15, color=MUTED).move_to(note)
        self.play(Transform(question, next_question), FadeOut(rows), FadeIn(cail), Transform(note, next_note), run_time=1.3)
        self.wait(0.9)


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
