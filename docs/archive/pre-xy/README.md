# Pre-XY archive

All sweep data here was produced **before the X+Y bench fix** (see [`docs/blueprint-xy.md`](../../blueprint-xy.md) and [`docs/blocker-consensus.md`](../../blocker-consensus.md)).

The X+Y rewrite changed:

1. **GT computation**: scorer now uses `shifted_*` from `mirrorlab/shifts/*.py` per shift_id (was: baseline-form closures keyed on `domain_id` in `loader.py`).
2. **Counterfactual sub-grid (c)**: `cf_params` is now passed to the predictor, overriding declared params at call time (was: declared params always used; `cf_params` only mutated GT).
3. **Test-grid input vocabulary**: ROT shifts now include `{x, y, z}`; T_TRANS shifts now include `t`; the prior scalar-`r` vocabulary cannot express the discriminating axes (see audit in [`docs/blocker-physics.md`](../../blocker-physics.md)).

These JSONs therefore have **incompatible grid keys, GT semantics, and submission contract** with the post-X+Y bench. They are kept for historical reference and re-analysis under the old framing only. Do not feed them to `mirrorlab/runners/rescore.py` — the version guard there will refuse files lacking `xy_version: 1`.

| File | Sprint | Notes |
|---|---|---|
| `sprint3-pilot-data.json` | 3 | Initial 1-domain pilot |
| `sprint35-pilot-data.json` | 3.5 | 4-domain expansion, gate dry-run |
| `sprint4-sweep-data.json` | 4 | Headline 5-model × 12-cell sweep |
| `sprint4-sweep-data-final.json` | 4 | Final-pass rescored variant |
| `sprint4-sweep-data-gpt41.json` | 4 | GPT-4.1 follow-up subset |
| `sprint4-sweep-data-merged.json` | 4 | Merged multi-pass |
| `sprint4-sweep-data-rescored.json` | 4 | Re-rescore against later `eval/scoring.py` revision |

Introducing commit: see `docs/blueprint-xy.md` and the X+Y T0 archival commit.
