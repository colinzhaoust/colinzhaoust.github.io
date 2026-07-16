# q-8 Real Video Matrix v0.1.0

This experiment is the evidence index for the requested `3 pipelines × 4 paper families` first pass. It is not a website gallery and it never treats the synthetic baseline-coverage videos as real runs.

The axes are Code2Video, Paper2Manim, and the canonical deterministic in-house v0 across Transformers, DPO, FeynRL, and RoPE. FeynRL is the canonical family; P3O is named only as a method that is present in the pinned FeynRL repository revision. The roadmap's all-upstream third baseline, TheoremExplainAgent, remains a separate follow-up pilot.

Run the contract and evidence inventory with:

```bash
python3 -m unittest discover -s tests/real_video_matrix -v
python3 tools/real_video_matrix.py --check \
  --out experiments/real_video_matrix/v1/report.json
```

The current evidence-level result is deliberately mixed:

- In-house v0 has four deterministic rendered videos with pinned project source, zero provider spend, and technical/visual review evidence.
- Historical Code2Video results for Transformers, FeynRL, and RoPE have playable videos, token counts, probes, and VLM reviews, but are partial because the upstream Git commit and historical rate-card reconciliation were not preserved. DPO is blocked rather than filled from a dummy preview.
- Historical Paper2Manim results for Transformers, FeynRL, and RoPE have playable repaired/fanout videos and probe evidence, but are partial for the same provenance/cost reasons. DPO is blocked rather than filled from a dummy preview.

Fresh in-house renders use the retained Babel recipe in `babel/run_inhouse_v0.sbatch`. Job `9313462` completed all four renders plus probes in 320 seconds with exit `0:0`; its normalized hashes and media summary are in `babel/9313462-result.json`. Paid-provider reruns require a separate q-5-compliant reservation, immutable provider/model identity, and rate-card snapshot before submission.
