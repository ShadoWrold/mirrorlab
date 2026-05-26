"""Catalog tests for γ-4-2 (pendulum height-graded gravity)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.pendulum_g_4_2 import (
    DIM_SIGNATURE, PendulumGamma42Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["H"] == "m"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_par_preserved_eom_invariant():
    """Under θ→−θ the EOM is preserved (height term depends on cos θ, even)."""
    p = PendulumGamma42Params(g0_over_L=9.8, alpha=0.2, L=1.0, H=10.0,
                              theta0=0.0, omega0=0.0)
    a_pos = shifted_law(0.4, p)
    a_neg = shifted_law(-0.4, p)
    assert abs(a_pos + a_neg) < 1e-9


def test_baseline_and_shift_differ():
    from mirrorlab.domains.pendulum import PendulumParams
    p = PendulumGamma42Params(g0_over_L=9.8, alpha=0.2, L=1.0, H=10.0,
                              theta0=0.5, omega0=0.0)
    sh = make("pendulum", "gamma_4_2", params=p)
    base = make("pendulum", "baseline",
                params=PendulumParams(L=1.0, g=9.8, theta0=0.5, omega0=0.0))
    diffs = [abs(base.step(t)["theta"] - sh.step(t)["theta"])
             for t in np.linspace(0.5, 5.0, 10)]
    assert max(diffs) > 1e-4
