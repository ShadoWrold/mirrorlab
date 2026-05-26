"""Catalog tests for γ-6-1 (RLC saturable inductor, LIN break)."""

from __future__ import annotations

import math
import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.rlc_g_6_1 import (
    DIM_SIGNATURE, RLCGamma61Params, sampler, shift, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["I_sat"] == "A"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_lin_broken_amplitude_dependence():
    """Period of oscillation under γ-6-1 depends on amplitude — LIN is broken."""
    # I_sat=1.0 A; small q gives i ≪ I_sat (linear regime), big q approaches I_sat.
    p_small = RLCGamma61Params(L0=1e-2, R=1.0, C=1e-6, I_sat=1.0,
                               q0=1e-7, i0=0.0)
    p_big = RLCGamma61Params(L0=1e-2, R=1.0, C=1e-6, I_sat=1.0,
                             q0=4e-5, i0=0.0)
    s_small = make("rlc", "gamma_6_1", params=p_small)
    s_big = make("rlc", "gamma_6_1", params=p_big)
    ts = np.linspace(0.0, 5e-4, 20)
    qs_small = np.array([s_small.step(float(t))["q"] / p_small.q0 for t in ts])
    qs_big = np.array([s_big.step(float(t))["q"] / p_big.q0 for t in ts])
    diff = float(np.max(np.abs(qs_small - qs_big)))
    assert diff > 1e-3, f"q(t)/q0 identical across amplitudes (diff={diff})"


def test_shift_impl_contract():
    assert callable(shift.law) and callable(shift.sampler) and callable(shift.validator)
