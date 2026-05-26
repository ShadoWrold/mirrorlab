"""Catalog tests for γ-5-1 (Coulomb anisotropic, ROT break)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.coulomb_g_5_1 import (
    DIM_SIGNATURE, CoulombGamma51Params, sampler, shift, shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["chi"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_rot_broken_lz_drifts():
    p = sampler(0)
    inst = make("coulomb", "gamma_5_1", params=p)
    Lz0 = inst.step(0.0)["Lz"]
    Lzs = [inst.step(float(t))["Lz"] for t in np.linspace(0.5, 20.0, 20)]
    drift = max(abs(L - Lz0) for L in Lzs)
    assert drift / max(abs(Lz0), 1e-20) > 1e-6


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
