# Babel execution

The preserved batch root is
`/home/xinranz3/4blue2brown_explore/slides_baselines_20260715`.

1. `submit_freeze_inputs.sbatch` freezes exact arXiv revisions
   `1706.03762v7`, `2305.18290v3`, `2605.12380v1`, and `2104.09864v5`, then
   records their content hashes. It makes no provider calls.
2. Before SlideGen parsing, pin `docling-parse==4.7.3` in its isolated Python
   3.11 environment. The upstream requirements are unconstrained, but the
   vendored backend imports `pdf_parser_v2`, removed from the resolved 5.2.0.
3. Submit `submit_slidegen_parse_matrix.sbatch` as an array after a successful
   compatibility probe. Each task is parse-only, makes no provider calls, and
   records markdown, hash, elapsed time, revision, and input hash.

The executed command was:

```bash
sbatch --dependency=afterok:9313479 submit_slidegen_parse_matrix.sbatch
```

This produced array job `9313502`. `afterok` means no array task is eligible
unless job `9313479` terminates successfully; `%2` limits concurrency to two.

The historical freeze job `9313499` used versionless arXiv URLs. A subsequent
2026-07-16 UTC verification downloaded all four exact revisions on Babel and
confirmed that their SHA-256 values equal the preserved inputs. No new freeze
job was needed; `results.json` records this binding explicitly.
