"""Catalog conformance tests for γ-2-2 (Gravity Lorentzian range bump)."""

from __future__ import annotations

import math
import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.gravity_g_2_2 import (
    DIM_SIGNATURE, GravityGamma22Params, sampler, shift, shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["alpha"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_scale_broken_force_deviates_from_inverse_square():
    """Bump term ⇒ F(r)·r² is not constant (scale invariance broken)."""
    p = sampler(7)
    rs = [p.r0 * f for f in (0.5, 1.0, 2.0)]
    products = [shifted_force(r, p) * r * r for r in rs]
    spread = max(products) - min(products)
    assert abs(spread) > 1e-12 * max(abs(p) for p in products)


def test_baseline_and_shift_differ():
    p = GravityGamma22Params(G=6.674e-11, M=5.972e24, m=1.0, alpha=0.3,
                             r_scale=7e6, r0=7e6, v0=1000.0)
    sh = make("gravity", "gamma_2_2", params=p)
    from mirrorlab.domains.gravity import GravityParams
    base = make("gravity", "baseline", params=GravityParams(M=5.972e24, m=1.0,
                                                            r0=7e6, v0=1000.0))
    diffs = [abs(base.step(t)["r"] - sh.step(t)["r"])
             for t in np.linspace(100.0, 500.0, 10)]
    assert max(diffs) > 1.0


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
