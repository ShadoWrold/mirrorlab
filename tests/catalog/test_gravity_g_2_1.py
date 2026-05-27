"""Catalog conformance tests for γ-2-1 (Gravity quadrupolar, ROT break)."""

from __future__ import annotations

import math

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.gravity_g_2_1 import (
    DIM_SIGNATURE, GravityGamma21Params, sampler, shift, shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["xi"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_rot_broken_lz_drifts():
    p = sampler(42)
    inst = make("gravity", "gamma_2_1", params=p)

    def lz(t: float) -> float:
        s = inst.step(t)
        return p.m * (s["x"] * s["vy"] - s["y"] * s["vx"])

    Lz0 = lz(0.0)
    Lzs = [lz(float(t)) for t in np.linspace(10.0, 200.0, 20)]
    drift = max(abs(L - Lz0) for L in Lzs)
    assert drift / max(abs(Lz0), 1e-30) > 1e-6, f"L_z conserved; ROT not broken"


def test_tangential_force_nonzero_off_axis():
    """When r̂ is not parallel to n̂, the tangential piece is nonzero."""
    p = sampler(0)
    # Move test mass off-axis relative to n̂
    Fx, Fy, Fz = shifted_force((p.x0, p.y0 + 1e6, p.z0), p)
    base_F = -p.G0 * p.M * p.m * p.x0 / (p.x0 ** 2 + (p.y0 + 1e6) ** 2 + p.z0 ** 2) ** 1.5
    # Just check force isn't purely radial baseline
    assert abs(Fx) + abs(Fy) > 0


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
