# Manim self-refinement v1

This experiment preserves five render-inspect-revise rounds for four paper
explainers: Transformer attention, DPO, normalized ESS in FeynRL/P3O, and RoPE.
It is a self-critique development exercise, not a human study and not an ICLR
acceptance claim.

## Comparison policy

- `baseline/inhouse_v0` refers to the existing project-native scene.
- Real Code2Video or Paper2Manim artifacts are included only where they exist.
- Synthetic `runs/baseline_coverage` assets are excluded.
- DPO has no qualifying external baseline, so it compares against in-house v0.
- Every round retains its MP4, sampled frames, contact sheet, media probe, source
  snapshot hash, and a short audit.

## Review rubric (20 points)

1. **Readable hierarchy (0–4):** body text is legible at 854×480; one focal
   object per beat; no overlap, crop, or color-only semantics.
2. **Mechanistic continuity (0–4):** visible objects persist through cause and
   effect instead of appearing as unrelated slides.
3. **Learner reconstruction (0–4):** a technical but non-specialist viewer can
   restate the input, transformation, output, and one limitation.
4. **Paper grounding (0–4):** the animation distinguishes the paper's claim,
   mechanism, evidence, and caveat from generic background.
5. **Oral readiness (0–4):** pacing supports narration; the visual can accompany
   a 60–90 second oral segment; the ending has one memorable claim or check.

`oral_ready` requires at least 16/20, with no category below 3. It means
presentation-ready by this internal rubric, not endorsement by ICLR.

## Round 1 audit

Round 1 replaces the old three-static-slide pattern with a shared four-part
grammar: question, worked example, causal mechanism, takeaway.

| Topic | Duration | Score | Main defects retained for round 2 |
| --- | ---: | ---: | --- |
| Transformer | 14.33 s | 12/20 | Too fast; small bar labels; paper contribution/result absent. |
| DPO | 13.13 s | 12/20 | Curve axes unexplained; beta not operational; paper evidence absent. |
| ESS | 13.60 s | 10/20 | Indicating the whole low-ESS card destroys readability; calculation too fast. |
| RoPE | 14.73 s | 11/20 | Rotation has no arc/angle trace; relative cancellation is asserted, not demonstrated. |

Common decision: do not add more formulas in round 2. Increase hold time, label
the changing quantity, preserve object identity through transformations, and
remove full-card emphasis effects.

## Five-round result

| Round | Transformer | DPO | ESS | RoPE | Main intervention |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 12 | 12 | 10 | 11 | causal worked examples |
| 2 | 14 | 14 | 13 | pacing and visual semantics |
| 3 | 16 | 15 | 14 | paper contribution and boundary |
| 4 | 17 | 17 | 16 | authors' evidence and learner check |
| 5 | 18 | 18 | 16 | final hierarchy, captions, naming repair |

Transformer, DPO, and RoPE clear the internal oral-ready threshold. ESS clears
it narrowly and should still receive spoken narration at the transition from
low effective sample size to adaptive capping and KL control. These judgments
are structured self-review, not measurements of human learning.

Round 5 uses Manim Community 0.19.0 locally at 854×480 and 15 fps. Its four
clips are silent visual segments of 29.8–31.33 seconds. Timed English narration
cues live under `captions/`; the public site attaches them as WebVTT caption
tracks. The paper-result cards paraphrase the authors' abstracts and are not
independent reproductions.

Machine-readable details are in `audits.json` and `comparison_manifest.json`.
`sources/` preserves the exact Manim program for every inspected round, while
`probes/` preserves each round's duration, size, sampled-frame statistics, and
contact-sheet references. Their source SHA-256 values are:

| Round | Source SHA-256 |
| --- | --- |
| 1 | `4eb0db36e2221e3c251b2649879dec6992ebad21230e35d5a03e8d3a79c0e69f` |
| 2 | `f7fd57c423be4ffb6e5f328d8fe5f0840285ea2346fdaf628dbecbf11b4f808b` |
| 3 | `5ae43ae705701c6bf5302951978c1a1c233dcbf398003b0cb3b83e2cc130d18f` |
| 4 | `1483adb65ac16ca38b26e0870e77ef45ceaa6a22763f61d0e47ff280e965b427` |
| 5 | `430d271e78f0867051a69af3fbf7427d9e6c7af2adaa88034a189e16829d3d14` |
