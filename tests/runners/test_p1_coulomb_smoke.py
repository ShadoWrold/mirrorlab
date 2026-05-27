"""T8 (P1, coulomb): truth-form builders end-to-end smoke.

Verifies the 4 coulomb cells.

- baseline: ceiling ≈ stub (both compute k_e·q1·q2/r²; ~0 spread)
- γ-5-1 ROT: 3-D grid; baseline stub ``f(r, ...)`` filtered out by
  signature → CLAMP per point → spread ≈ 1.
- γ-5-2 sat: 3-D grid with 2 fixed sources; baseline ``k_e·q1·q2/r²``
  cannot represent the 2-source saturating field at all → spread ≈ 1.
- δ-5-1 charge dynamics: grid keys are ``{q1, q2}``; baseline stub
  ``f(r, ...)`` is filtered out → spread ≈ 1.
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_coulomb_baseline_no_spread(seed):
    sc = load("coulomb", "baseline", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.95, f"seed={seed}: ceiling {s_c:.4f} < 0.95"
    assert abs(s_c - s_s) <= 1e-3, (
        f"seed={seed}: baseline spread {abs(s_c - s_s):.4f} > 1e-3 — "
        "ceiling and stub both compute the canonical Coulomb law and must agree."
    )


@pytest.mark.parametrize("shift", ["gamma_5_1", "gamma_5_2", "delta_5_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_coulomb_shift_large_spread(shift, seed):
    sc = load("coulomb", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.90, (
        f"seed={seed}: {shift} ceiling {s_c:.4f} < 0.90 — "
        "truth-form predictor or builder is misaligned."
    )
    assert s_c - s_s >= 0.50, (
        f"seed={seed}: {shift} spread {s_c - s_s:+.4f} < 0.50 "
        f"(ceiling {s_c:.4f}, stub {s_s:.4f})"
    )
