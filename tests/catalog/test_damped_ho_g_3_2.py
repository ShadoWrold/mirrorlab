"""Catalog tests for γ-3-2 (damped HO parametric pumping, T-trans break)."""

from __future__ import annotations

import math
import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.damped_ho_g_3_2 import (
    DIM_SIGNATURE, DampedHOGamma32Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["Omega_p"] == "s**-1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_t_trans_broken_law_depends_on_t():
    """ω²(t) = ω₀²[1 + ε cos(Ωt)] ⇒ law(x,v,t1) ≠ law(x,v,t2)."""
    p = sampler(3)
    a1 = shifted_law(0.1, 0.0, 0.0, p)
    a2 = shifted_law(0.1, 0.0, math.pi / p.Omega_p, p)
    assert abs(a1 - a2) > 1e-6


def test_baseline_and_shift_differ():
    p = DampedHOGamma32Params(omega0=2.0, gamma=0.3, eps=0.15, Omega_p=3.0,
                              m=1.0, x0=0.2, v0=0.0)
    sh = make("damped_ho", "gamma_3_2", params=p)
    from mirrorlab.domains.damped_ho import DampedHOParams
    base = make("damped_ho", "baseline",
                params=DampedHOParams(k=4.0, c=0.6, m=1.0, x0=0.2, v0=0.0))
    diffs = [abs(base.step(t)["x"] - sh.step(t)["x"])
             for t in np.linspace(0.5, 5.0, 10)]
    assert max(diffs) > 1e-3
