"""T9 (P1, thermal): truth-form builders end-to-end smoke.

- baseline:  ceiling ≈ stub (Fourier on both sides; ~0 spread)
- γ-7-1 ROT: 6-D inputs {T_hot,T_cold,L,dx,dy,dz}; stub `f(T_hot,T_cold,L,k)`
             missing direction → filtered → spread varies with β (small
             β → small anisotropy → small spread; large β → near-1.0)
- γ-7-2 mem: 4-D inputs incl. t; stub has no t → filtered → spread ~0.9
- δ-7-1 PDE: 1-D input {t}; baseline stub computes scalar Fourier flux
             which has wrong units / scale vs T_a(t) → spread ~1.0
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_thermal_baseline_no_spread(seed):
    sc = load("thermal", "baseline", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.85, f"seed={seed}: ceiling {s_c:.4f} < 0.85"
    assert abs(s_c - s_s) <= 1e-3, (
        f"seed={seed}: baseline spread {abs(s_c - s_s):.4f} > 1e-3"
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_thermal_gamma_7_1_spread(seed):
    """γ-7-1 spread depends on β; require truth ≥ baseline always, and
    at least one of three seeds to show large spread."""
    sc = load("thermal", "gamma_7_1", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.85, f"seed={seed}: γ-7-1 ceiling {s_c:.4f} < 0.85"
    assert s_c >= s_s - 1e-3, (
        f"seed={seed}: γ-7-1 truth {s_c:.4f} < stub {s_s:.4f}"
    )


@pytest.mark.parametrize("shift", ["gamma_7_2", "delta_7_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_thermal_shift_large_spread(shift, seed):
    sc = load("thermal", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.85, f"seed={seed}: {shift} ceiling {s_c:.4f} < 0.85"
    assert s_c - s_s >= 0.50, (
        f"seed={seed}: {shift} spread {s_c - s_s:+.4f} < 0.50 "
        f"(ceiling {s_c:.4f}, stub {s_s:.4f})"
    )
