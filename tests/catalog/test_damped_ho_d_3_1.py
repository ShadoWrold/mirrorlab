"""Catalog tests for δ-3-1 (damped HO amplitude-gated damping, limit cycle)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.damped_ho_d_3_1 import (
    DIM_SIGNATURE, DampedHODelta31Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["L"] == "m"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_anti_damping_inside_core():
    """For |x| < L the gate (|x|/L − 1) < 0 ⇒ anti-damping ⇒ energy can grow from small IC."""
    p = DampedHODelta31Params(omega0=2.0, gamma=0.1, L=1.0, m=1.0,
                              x0=0.01, v0=0.0)
    inst = make("damped_ho", "delta_3_1", params=p)
    e0 = inst.step(0.0)["E"]
    e_late = inst.step(10.0)["E"]
    assert e_late > e0, f"core anti-damping not observed: E0={e0}, E_late={e_late}"


def test_par_invariant_force():
    """Under (x,v) → (-x,-v) the EOM is invariant."""
    p = DampedHODelta31Params(omega0=2.0, gamma=0.1, L=1.0, m=1.0, x0=0.0, v0=0.0)
    a1 = shifted_law(0.3, 0.4, p)
    a2 = shifted_law(-0.3, -0.4, p)
    assert abs(a1 + a2) < 1e-9
