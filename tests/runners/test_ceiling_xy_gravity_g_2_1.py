"""T4 (P0): ceiling γ-2-1 truth-form acceptance test.

Verifies blueprint §3.5 done criteria for the P0 cell:
- Ceiling reaches S_scen ≥ 0.99 on (a)+(b) (the truth predictor matches
  the truth-form GT to machine precision).
- Ceiling reaches S_scen ≥ 0.99 on (c) — the per-point cf_params
  override flows through Y plumbing into the predictor's kw, so the
  perturbed law is computed correctly per point.
- Ceiling reaches S_scen ≥ 0.99 on the full CAL-1 weighted mean.
- The entry exposes its law coefficients via ``params`` so Y plumbing
  has names to override (not the legacy empty list).
"""

from __future__ import annotations

import pytest

from mirrorlab.eval.numeric import evaluate_entry
from mirrorlab.runners.ceiling_agent import build_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_ceiling_gamma_2_1_full_score(seed):
    sc = load("gravity", "gamma_2_1", seed=seed)
    entry = build_submission(sc)[0]

    declared_names = {p["name"] for p in entry["params"]}
    assert declared_names == {"G", "M", "m", "xi", "nx", "ny", "nz"}, (
        f"seed={seed}: ceiling γ-2-1 entry must expose G/M/m/xi/nx/ny/nz "
        f"so Y plumbing can override on (c); got {sorted(declared_names)}"
    )

    s_ab = evaluate_entry(
        entry,
        {k: sc.test_grids[k] for k in ("a", "b")},
        weights={"a": 0.5, "b": 0.5},
    )
    s_c = evaluate_entry(
        entry, {"c": sc.test_grids["c"]}, weights={"c": 1.0}
    )
    s_all = evaluate_entry(entry, sc.test_grids)

    assert s_ab >= 0.99, f"seed={seed}: ceiling S(a+b)={s_ab:.6f} < 0.99"
    assert s_c >= 0.99, (
        f"seed={seed}: ceiling S(c)={s_c:.6f} < 0.99 — Y plumbing or "
        "cf_params canonicalization is broken"
    )
    assert s_all >= 0.99, f"seed={seed}: ceiling S_all={s_all:.6f} < 0.99"


def test_other_gravity_branches_unchanged():
    """T4 scope is γ-2-1 only; baseline / γ-2-2 / δ-2-1 must still build."""
    for shift in ("baseline", "gamma_2_2", "delta_2_1"):
        sc = load("gravity", shift, seed=0)
        sub = build_submission(sc)
        assert sub[0]["_predictor"] is not None
        # Pre-T4 behavior: params list is empty (closure-based predictor).
        # T12 will migrate the remaining shifts.
        if shift != "gamma_2_1":
            assert sub[0]["params"] == []
