"""Catalog conformance tests for δ-1-1 (Hooke amplitude-conditioned drag, E break)."""

from __future__ import annotations

import numpy as np

from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.hooke_d_1_1 import (
    DIM_SIGNATURE, HookeDelta11Params, sampler, shift, shifted_force, validator,
)


def test_dim_signature_present():
    assert DIM_SIGNATURE["params"]["c"] == "kg*s**-1"
    assert DIM_SIGNATURE["params"]["L"] == "m"


def test_validator_passes_1000_samples():
    fails = [s for s in range(1000) if not validator(sampler(s))]
    assert not fails


def test_energy_decays():
    p = HookeDelta11Params(k=20.0, c=0.5, L=1.0, m=1.0, x0=0.5, v0=0.0)
    inst = make("hooke", "delta_1_1", params=p)

    def energy(t: float) -> float:
        s = inst.step(t)
        return 0.5 * p.m * s["v"] ** 2 + 0.5 * p.k * s["x"] ** 2

    e0 = energy(0.0)
    e_late = energy(5.0)
    assert e_late < e0 - 1e-6, f"E did not decay: E0={e0}, E_late={e_late}"


def test_par_preserved_under_joint_sign_flip():
    """Under (x→−x, v→−v) the force flips sign: F(-x,-v) = -F(x,v)."""
    p = HookeDelta11Params(k=20.0, c=0.5, L=1.0, m=1.0, x0=0.0, v0=0.0)
    f1 = shifted_force(0.3, 0.4, p)
    f2 = shifted_force(-0.3, -0.4, p)
    assert abs(f1 + f2) < 1e-9


def test_baseline_and_shift_differ():
    base = make("hooke", "baseline", params=__import__(
        "mirrorlab.domains.hooke", fromlist=["HookeParams"]
    ).HookeParams(k=20.0, m=1.0, x0=0.5, v0=0.0))
    shifted = make("hooke", "delta_1_1",
                   params=HookeDelta11Params(k=20.0, c=0.5, L=1.0, m=1.0,
                                             x0=0.5, v0=0.0))
    diffs = [abs(base.step(t)["x"] - shifted.step(t)["x"])
             for t in np.linspace(0.5, 5.0, 10)]
    assert max(diffs) > 1e-3
