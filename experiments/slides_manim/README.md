# Slides + Manim fusion contract (smoke)

This directory is a narrow integration layer between a slide representation and a
rendered Manim scene. It proves one methodology `AnimationSlot` can be resolved,
validated, and packaged with a static fallback. It does **not** claim that a deck,
PPTX export, or the end-to-end paper-to-slides pipeline is complete.

## What is resolved

`methodology_attention_softmax.slide-ir.json` is a concrete `SlideIR` sample with
one resolved `methodology_formula_explanation` slot. Its evidence comes from the
existing q9 formula-explainer smoke:

- Babel job: `9313551`
- Source commit: `853bb82d68f814b40e589ea8bfa086101b14e464`
- MP4: H.264, 854×480, 15 fps, 6.666 seconds
- MP4 SHA-256: `86568917ad365c1dcbdaca7187c3848e7a4fe350e4c84398dde67be416d33c87`
- Poster SHA-256: `4b304104a9f7f36d205c79c944768eb8fb77ed1d184950832d97f44c019413a0`
- SceneIR SHA-256: `153fbe6b5bf42e0c0b83c49df83c26d7399254524d9d8f4678bf037ec58de9ae`

Architecture/dataflow and performance/comparison appear only as
`planned_missing` records. Their missing SceneIR, media, fallback, poster, and
review requirements are explicit; there are no dummy resolved slots.

## Contract

`schemas/slides-manim/animation-slot-0.1.0.schema.json` makes every resolved slot
declare the SceneIR and rendered/static artifacts, semantic purpose, normalized
slide region, expected duration, playback behavior, poster, caption and alt text,
aspect/crop rules, content hash, composite lineage, and whether it is required for
comprehension.

`schemas/slides-manim/slide-ir-0.1.0.schema.json` wraps the slot in a slide-level
artifact registry, citations, layout, speaker notes, completion status, and honest
planned-work records. It also pins a hashed run-evidence manifest. Validation
requires the slot run/commit to agree with every parent artifact and requires the
manifest's completed Babel job to report the same video and poster hashes.

A `static_fallback` is not merely a second media reference: it must be a validated
`image/*` artifact that is independently understandable without playback. A video
cannot satisfy the fallback role.

## Validate and inspect

From the repository root:

```bash
python3 -m tools.slides_manim.cli
python3 -m unittest discover -s tests/slides_manim -p 'test_*.py'
```

The standalone static package is `demo/index.html`. It uses click-to-play browser
controls, a real poster as the required static fallback, and a caption track. It is
intentionally outside `progress_site/`; the main website can consume this contract
after the sample graduates from smoke evidence.

## Known limits

- Only one methodology slot is resolved.
- The underlying q9 clip is a render smoke; some labels are intentionally compact.
- No deck-level sequencing, slide generation, or PPTX/video export is implemented.
- Architecture and performance scenes still need paper-grounded designs and review.
