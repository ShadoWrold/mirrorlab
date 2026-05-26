"""Catalog tests for γ-4-1 (pendulum asymmetric vertical, PAR break)."""

from __future__ import annotations

import math
import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.pendulum_g_4_1 import (
    DIM_SIGNATURE, PendulumGamma41Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["alpha"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_par_broken_under_theta_flip():
    """θ̈(θ) ≠ −θ̈(−θ) due to even (1−cos θ) term."""
    p = PendulumGamma41Params(g_over_L=9.8, alpha=0.3, theta0=0.0, omega0=0.0)
    a_pos = shifted_law(0.5, p)
    a_neg = shifted_law(-0.5, p)
    # PAR-invariant ⇒ a(-θ) = -a(θ); break ⇒ |a(θ) + a(-θ)| > 0
    assert abs(a_pos + a_neg) > 1e-3


def test_baseline_and_shift_differ():
    from mirrorlab.domains.pendulum import PendulumParams
    p = PendulumGamma41Params(g_over_L=9.8, alpha=0.3, theta0=0.3, omega0=0.0)
    sh = make("pendulum", "gamma_4_1", params=p)
    base = make("pendulum", "baseline",
                params=PendulumParams(L=1.0, g=9.8, theta0=0.3, omega0=0.0))
    diffs = [abs(base.step(t)["theta"] - sh.step(t)["theta"])
             for t in np.linspace(0.5, 5.0, 10)]
    assert max(diffs) > 1e-3
