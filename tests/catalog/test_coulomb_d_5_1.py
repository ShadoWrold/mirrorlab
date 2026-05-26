"""Catalog tests for δ-5-1 (Coulomb charge leakage, Q break)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.coulomb_d_5_1 import (
    DIM_SIGNATURE, CoulombDelta51Params, sampler, shift, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["alpha"] == "s**-1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_q_decays():
    p = sampler(0)
    inst = make("coulomb", "delta_5_1", params=p)
    Q0 = inst.step(0.0)["Q_total"]
    q1_late = inst.step(p.T_sim * 0.9)["q1"]
    assert abs(q1_late) < abs(p.q1_0), "q1 did not decay under field-coupled leakage"


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
