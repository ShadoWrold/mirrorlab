"""Catalog conformance tests for δ-2-1 (Gravity G(t) modulation, T-trans break)."""

from __future__ import annotations

import math
import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.gravity_d_2_1 import (
    DIM_SIGNATURE, GravityDelta21Params, G_of_t, sampler, shift, shifted_force,
    validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["beta"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_G_modulates_in_time():
    p = sampler(0)
    G0 = G_of_t(0.0, p)
    G_q = G_of_t(math.pi / (2.0 * p.omega_G), p)
    assert abs(G0 - G_q) > 1e-12


def test_T_rev_preserved_cos_even():
    """G(t) = G(-t) since cos is even."""
    p = sampler(1)
    for t in (1.0, 10.0, 100.0):
        assert abs(G_of_t(t, p) - G_of_t(-t, p)) < 1e-12


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
