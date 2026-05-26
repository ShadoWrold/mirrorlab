"""Catalog tests for δ-4-1 (pendulum g(t) modulation, T-trans break)."""

from __future__ import annotations

import math

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.pendulum_d_4_1 import (
    DIM_SIGNATURE, PendulumDelta41Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["eps"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_t_rev_preserved_law_even_in_t():
    """g(t) = g(-t) since cos is even ⇒ law(θ, t) = law(θ, -t)."""
    p = sampler(2)
    for t in (0.1, 0.5, 2.0):
        assert abs(shifted_law(0.3, t, p) - shifted_law(0.3, -t, p)) < 1e-12


def test_t_trans_broken():
    """law(θ, t) ≠ law(θ, t + Δt) for some Δt."""
    p = sampler(3)
    a1 = shifted_law(0.3, 0.0, p)
    a2 = shifted_law(0.3, math.pi / p.Omega, p)
    assert abs(a1 - a2) > 1e-6
