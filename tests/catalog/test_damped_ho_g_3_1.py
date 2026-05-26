"""Catalog tests for γ-3-1 (damped HO amplitude-memory stiffness, LIN break)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.damped_ho_g_3_1 import (
    DIM_SIGNATURE, DampedHOGamma31Params, sampler, shift, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["kappa"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_lin_broken_amplitude_dependence():
    """Doubling IC amplitude should NOT just double the trajectory under LIN break."""
    p_small = DampedHOGamma31Params(omega0=2.0, gamma=0.05, kappa=0.5, tau=0.5,
                                    x_ref=0.1, m=1.0, x0=0.05, v0=0.0)
    p_big = DampedHOGamma31Params(omega0=2.0, gamma=0.05, kappa=0.5, tau=0.5,
                                  x_ref=0.1, m=1.0, x0=0.5, v0=0.0)
    s_small = make("damped_ho", "gamma_3_1", params=p_small)
    s_big = make("damped_ho", "gamma_3_1", params=p_big)
    # If linear, x_big(t) / x_small(t) ≈ 10 at every t. Check it deviates.
    ratios = []
    for t in np.linspace(0.5, 3.0, 10):
        xs = s_small.step(float(t))["x"]
        xb = s_big.step(float(t))["x"]
        if abs(xs) > 1e-6:
            ratios.append(xb / xs)
    spread = max(ratios) - min(ratios)
    assert spread > 0.1, f"trajectory scales linearly (spread={spread})"


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
