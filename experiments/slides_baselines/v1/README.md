# Paper-to-slides baseline matrix v1

This directory is the repo-native execution contract for the approved slide
baseline shortlist. It does not contain website assets.

The selected variants are `deeppresenter_current`, canonical `slidegen`, and
`arcdeck`. `paper2slides_fast_academic_short` is recorded only as the declared
fallback; it must not silently replace a selected matrix cell.

Validate and initialize a ledger with:

```bash
python tools/slides_baselines.py \
  experiments/slides_baselines/v1/matrix.json \
  --init-ledger runs/remote_checks/slides_baselines_20260715/results.json
```

The matrix is paper-native. `pipeline.repository` pins the implementation;
an input `repository` snapshot is not required and must not be invented.

## Execution gates

- A paper PDF must be content-hash frozen before its cells can run.
- A full result needs editable deck, static render, validation, review, and a
  reconciled cost record.
- Provider stages fail closed while the WInE rate card and per-run usage are
  unavailable. A free parse/import probe may proceed with provider calls and
  measured provider cost both fixed at zero.
- Slurm time/resources are recorded separately from provider dollars. Unknown
  institutional compute cost is not reported as `$0`.

The first free one-off compatibility probe is preserved by job and artifact
identity in `results.json`. The reproducible four-paper runner is
`babel/submit_slidegen_parse_matrix.sbatch`; it exercises SlideGen's native PDF
parsing stage after the dependency-only compatibility pin is validated.

## Preserved result

`results.json` records input-freeze job `9313499`, compatibility probe
`9313479`, and four-paper array `9313502`. All four array tasks completed with
exit `0:0` and content-hashed markdown outputs. Their matrix completion is
`smoke`: PDF parsing succeeded, but no editable deck or static slide render was
generated. DeepPresenter current and ArcDeck remain explicitly blocked rather
than being filled with substitute or dummy output.
