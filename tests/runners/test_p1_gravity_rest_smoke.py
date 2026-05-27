"""T11 (P1, gravity baseline + γ-2-2 + δ-2-1) end-to-end smoke.

γ-2-1 covered in test_p0_gravity_g_2_1_smoke.py (T3+T4).

- baseline: ceiling ≈ stub (both Newton; spread ~0)
- γ-2-2 Lorentzian bump (1-D): truth-form GT, but α is small in
  the catalog sampler → spread is small (< 1%) by physics; the cliff
  is shallow on this cell and that is expected (paper 1 finding:
  scale-break shifts are harder to detect than structural breaks).
- δ-2-1 G(t) modulation (1-D + t): same story — β is small, spread
  is small. The stub does not know about t but happens to get the
  baseline-r dependency right per point, so stub ≈ ceiling.
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("shift", ["baseline", "gamma_2_2", "delta_2_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_gravity_ceiling_high(shift, seed):
    sc = load("gravity", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    assert s_c >= 0.90, f"seed={seed}: gravity/{shift} ceiling {s_c:.4f} < 0.90"


@pytest.mark.parametrize("shift", ["baseline", "gamma_2_2", "delta_2_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_gravity_truth_not_worse_than_baseline(shift, seed):
    """For these 1-D shifts the truth form must at least tie the baseline
    stub (truth ≥ stub − epsilon). Spread can be tiny — that is a real
    physics result, not a bench bug."""
    sc = load("gravity", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= s_s - 1e-3, (
        f"seed={seed}: gravity/{shift} truth {s_c:.4f} < stub {s_s:.4f}"
    )
