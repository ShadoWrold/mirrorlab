"""Catalog tests for γ-6-2 (RLC non-reciprocal mutual inductance)."""

from __future__ import annotations

from mirrorlab.shifts.rlc_g_6_2 import (
    DIM_SIGNATURE, RLCGamma62Params, sampler, shift, shifted_law, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["dM"] == "kg*m**2*s**-2*A**-2"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_onsager_broken_asymmetric_response():
    """Driving loop 1 should give a different loop-2 response than the swap case."""
    p = sampler(0)
    # response of di_2 to (q1=0, i1=1, q2=0, i2=0):
    _, di2_a = shifted_law(0.0, 1.0, 0.0, 0.0, p)
    # response of di_1 to (q1=0, i1=0, q2=0, i2=1) — Onsager would equate these
    di1_b, _ = shifted_law(0.0, 0.0, 0.0, 1.0, p)
    # Onsager symmetric ⇒ di2_a from i1-drive equals di1_b from i2-drive (up to L_eff norm)
    # Asymmetric mutual ⇒ they differ.
    assert abs(di2_a - di1_b) > 1e-12


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
