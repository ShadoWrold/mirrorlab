"""Catalog conformance tests for γ-1-2 (Hooke 2D anisotropic, ROT break)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.hooke_g_1_2 import (
    DIM_SIGNATURE, HookeGamma12Params, potential, sampler, shift,
    shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["inputs"] == {"x": "m", "y": "m"}
    assert DIM_SIGNATURE["params"]["xi"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_rot_broken_lz_drifts():
    """L_z not conserved under γ-1-2."""
    p = HookeGamma12Params(k0=10.0, xi=0.5, phi=0.3, m=1.0,
                           x0=0.2, y0=0.1, vx0=0.0, vy0=0.5)
    inst = make("hooke", "gamma_1_2", params=p)

    def lz(t: float) -> float:
        s = inst.step(t)
        return p.m * (s["x"] * s["vy"] - s["y"] * s["vx"])

    Lz0 = lz(0.0)
    Lzs = [lz(float(t)) for t in np.linspace(0.1, 5.0, 25)]
    drift = max(abs(L - Lz0) for L in Lzs)
    assert drift > 1e-3, f"L_z conserved (drift={drift:.2e}); ROT not broken"


def test_shift_differs_from_baseline_force():
    """At a generic (x,y), γ-1-2 force differs from isotropic Hooke."""
    p = HookeGamma12Params(k0=10.0, xi=0.5, phi=0.0, m=1.0,
                           x0=0.0, y0=0.0, vx0=0.0, vy0=0.0)
    Fx, Fy = shifted_force((0.3, 0.4), p)
    base_Fx, base_Fy = -p.k0 * 0.3, -p.k0 * 0.4
    assert abs(Fx - base_Fx) + abs(Fy - base_Fy) > 1e-3


def test_shift_impl_contract():
    assert callable(shift.law)
    assert callable(shift.sampler)
    assert callable(shift.validator)
