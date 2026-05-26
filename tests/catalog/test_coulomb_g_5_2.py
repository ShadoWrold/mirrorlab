"""Catalog tests for γ-5-2 (Coulomb saturating potential, LIN break)."""

from __future__ import annotations

from mirrorlab.shifts.coulomb_g_5_2 import (
    DIM_SIGNATURE, CoulombGamma52Params, sampler, shift, shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["xi"] == "1"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_superposition_broken():
    """E from sources (q1) alone + (q2) alone ≠ E from both together under γ-5-2."""
    p_all = sampler(0)
    p_only1 = CoulombGamma52Params(**{**p_all.__dict__, "src2_q": 0.0})
    p_only2 = CoulombGamma52Params(**{**p_all.__dict__, "src1_q": 0.0})
    pos = (0.2, 0.3, 0.0)
    F_all = shifted_force(pos, p_all)
    F_1 = shifted_force(pos, p_only1)
    F_2 = shifted_force(pos, p_only2)
    sum_sep = tuple(a + b for a, b in zip(F_1, F_2))
    diff = max(abs(F_all[i] - sum_sep[i]) for i in range(3))
    assert diff > 1e-30, f"superposition holds; LIN not broken (diff={diff})"


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
