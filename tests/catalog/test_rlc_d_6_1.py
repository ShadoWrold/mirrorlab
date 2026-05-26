"""Catalog tests for δ-6-1 (RLC parametric L(t), T-trans break)."""

from __future__ import annotations

import math

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.rlc_d_6_1 import (
    DIM_SIGNATURE, RLCDelta61Params, _L_of_t, sampler, shift, shifted_law,
    validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["Omega_p"] == "s**-1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_L_modulates_in_time():
    p = sampler(0)
    L0_val = _L_of_t(0.0, p)
    Lq = _L_of_t(math.pi / p.Omega_p, p)
    assert abs(L0_val - Lq) > 1e-12


def test_t_rev_preserved_law_even_in_t():
    """L(t) and L'(t) under t→-t: L is even, L' is odd ⇒ the i·L' term flips sign,
    but the EOM is for di/dt; pure t-reversal symmetry of trajectory is what matters.
    Here, simply assert L(t) = L(-t) (cos even).
    """
    p = sampler(1)
    for t in (1e-5, 1e-4, 1e-3):
        assert abs(_L_of_t(t, p) - _L_of_t(-t, p)) < 1e-15
