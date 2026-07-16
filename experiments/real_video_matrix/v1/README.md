# q-8 Real Video Matrix v0.2.0

This experiment is the evidence index for the requested `3 pipelines × 4 paper families` first pass. It is not a website gallery and it never treats the synthetic baseline-coverage videos as real runs.

The axes are Code2Video, Paper2Manim, and the deterministic in-house v0 across Transformers, DPO, FeynRL, and RoPE. The in-house cells are explicitly **source-embedded manual method reproductions**: their pinned Manim source contains the paper concepts, while the reference JSON/PDF/code repository was not consumed at runtime. FeynRL is the canonical family; P3O is named only as a method present in the referenced FeynRL repository revision. The roadmap's all-upstream third baseline, TheoremExplainAgent, remains a separate follow-up pilot.

Run the contract and evidence inventory with:

```bash
python3 -m unittest discover -s tests/real_video_matrix -v
python3 tools/real_video_matrix.py --check \
  --out experiments/real_video_matrix/v1/report.json
python3 tools/harvest_q8_babel_evidence.py \
  --input experiments/real_video_matrix/v1/babel/9313462-harvest-input.json \
  --out /tmp/9313462-result.json
```

`completion` is not authored in `config.json`. The report derives it with the q-5 completion implementation from the versioned `q8-video-cell/0.2.0` contract, stage state, and observed/hashed artifacts. Reviews are structured events. Cost records distinguish measured API spend from explicitly excluded compute, labor, storage, and assets.

The current evidence-level result is deliberately mixed:

- In-house v0 has four deterministic source-embedded renders with pinned consumed scene source, zero provider spend, disclosed Babel wall time, excluded non-API cost categories, and technical review evidence.
- Historical Code2Video results for Transformers, FeynRL, and RoPE have playable videos, token counts, probes, and VLM reviews, but are partial because the upstream Git commit and historical rate-card reconciliation were not preserved. DPO is blocked rather than filled from a dummy preview.
- Historical Paper2Manim results for Transformers, FeynRL, and RoPE have playable repaired/fanout videos and probe evidence, but are partial for the same provenance/cost reasons. DPO is blocked rather than filled from a dummy preview.

Fresh in-house renders use the retained Babel recipe in `babel/run_inhouse_v0.sbatch`. Job `9313462` completed all four renders plus probes in 320 seconds with exit `0:0`. The retained `babel/9313462-harvest-input.json` normalizes to `babel/9313462-result.json` through `tools/harvest_q8_babel_evidence.py`; its capture note explicitly records that the original raw remote files were not committed. Paid-provider reruns require a separate q-5-compliant reservation, immutable provider/model identity, and rate-card snapshot before submission.
