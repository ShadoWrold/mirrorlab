"""Catalog conformance tests for shift γ-1-1 (Hooke, saturating asymmetric stiffness)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad

from mirrorlab.domains.hooke import HookeBaseline, HookeParams
from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.hooke_g_1_1 import (
    DIM_SIGNATURE,
    HookeGamma11Params,
    sampler,
    shift,
    shifted_force,
    shifted_potential,
    validator,
)


def test_dim_signature_matches_catalog():
    """[x]=m, [F]=N=kg·m·s⁻², [η]=1, [x₀]=m, [k]=N/m=kg·s⁻²."""
    sig = DIM_SIGNATURE
    assert sig["inputs"] == {"x": "m"}
    assert sig["outputs"] == {"F": "kg*m*s**-2"}
    assert sig["params"]["k"] == "kg*s**-2"
    assert sig["params"]["m"] == "kg"
    assert sig["params"]["eta"] == "1"
    assert sig["params"]["x_scale"] == "m"


def test_validator_passes_1000_random_samples():
    failures = [seed for seed in range(1000) if not validator(sampler(seed))]
    assert not failures, f"{len(failures)} sampler outputs failed validator"


def test_shift_impl_exports_contract():
    """ShiftImpl(law, sampler, validator) per spec §3.2."""
    assert callable(shift.law)
    assert callable(shift.sampler)
    assert callable(shift.validator)
    # round-trip
    p = shift.sampler(42)
    assert shift.validator(p)
    assert math.isfinite(shift.law(0.05, p))


def test_par_genuinely_broken():
    """Catalog claim: PAR (x→-x) is broken. ⇒ F(-x) ≠ -F(x) for generic x."""
    p = HookeGamma11Params(k=10.0, m=1.0, x0=0.05, v0=0.0, eta=0.5, x_scale=0.2)
    x = 0.15
    f_pos = shifted_force(x, p)
    f_neg = shifted_force(-x, p)
    # PAR-invariant ⇒ f_pos + f_neg ≈ 0. Break ⇒ |f_pos + f_neg| > 0.
    assert abs(f_pos + f_neg) > 1e-3, "PAR not broken; γ-1-1 injection inert"


def test_validator_rejects_out_of_range():
    base = sampler(0)
    bad_k = HookeGamma11Params(**{**base.__dict__, "k": 0.5})
    bad_eta = HookeGamma11Params(**{**base.__dict__, "eta": 1.0})
    bad_x_scale = HookeGamma11Params(**{**base.__dict__, "x_scale": 5.0})
    bad_mass = HookeGamma11Params(**{**base.__dict__, "m": 0.0})
    bad_ic = HookeGamma11Params(**{**base.__dict__, "x0": 100 * base.x_scale})
    for bad in (bad_k, bad_eta, bad_x_scale, bad_mass, bad_ic):
        assert not validator(bad), f"validator wrongly accepted {bad!r}"


def test_t_trans_preserved_energy_conserved():
    """Single-symmetry-break: T-translation still holds ⇒ energy conserved.

    γ-1-1 is autonomous and the force is conservative
    (F(x) = -dV/dx with V(x) = ∫₀ˣ k s [1 + η tanh(s/x₀)] ds).
    """
    p = HookeGamma11Params(k=20.0, m=1.0, x0=0.1, v0=0.0, eta=0.5, x_scale=0.2)
    inst = make("hooke", "gamma_1_1", params=p)

    def potential(x: float) -> float:
        val, _ = quad(
            lambda s: p.k * s * (1.0 + p.eta * math.tanh(s / p.x_scale)),
            0.0,
            x,
            epsabs=1e-12,
            epsrel=1e-10,
        )
        return val

    def energy(state):
        return 0.5 * p.m * state["v"] ** 2 + potential(state["x"])

    e0 = energy(inst.step(0.0))
    omega_lin = math.sqrt(p.k / p.m)
    period = 2 * math.pi / omega_lin
    drifts = [
        abs(energy(inst.step(float(t))) - e0) / max(abs(e0), 1e-12)
        for t in np.linspace(0.0, 5 * period, 25)
    ]
    assert max(drifts) < 1e-6, (
        f"energy drift {max(drifts):.2e} suggests T-trans break in γ-1-1"
    )


def test_baseline_and_shift_trajectories_differ():
    """Sanity: injecting γ-1-1 measurably changes the trajectory."""
    base = make(
        "hooke",
        "baseline",
        params=HookeParams(k=20.0, m=1.0, x0=0.5, v0=0.0),
    )
    shifted = make(
        "hooke",
        "gamma_1_1",
        params=HookeGamma11Params(
            k=20.0, m=1.0, x0=0.5, v0=0.0, eta=0.5, x_scale=0.2
        ),
    )
    diffs = [
        abs(base.step(float(t))["x"] - shifted.step(float(t))["x"])
        for t in np.linspace(0.1, 2.0, 20)
    ]
    assert max(diffs) > 1e-3, "baseline and γ-1-1 trajectories indistinguishable"


def test_registry_supports_baseline_and_shift():
    base = make("hooke", "baseline")
    sh = make("hooke", "gamma_1_1", seed=7)
    assert isinstance(base, HookeBaseline)
    assert sh.params.eta > 0
    with pytest.raises(KeyError):
        make("nonexistent", "baseline")


def test_shifted_potential_matches_force_antiderivative():
    """U(x) = -∫₀ˣ F(s) ds and -dU/dx ≈ F(x) at sample points."""
    p = HookeGamma11Params(k=20.0, m=1.0, x0=0.0, v0=0.0, eta=0.5, x_scale=0.2)
    U = shifted_potential(p)
    assert U(0.0) == 0.0
    h = 1e-5
    for x in (-0.3, -0.1, 0.05, 0.15, 0.4):
        dU_dx = (U(x + h) - U(x - h)) / (2 * h)
        f = shifted_force(x, p)
        assert abs(-dU_dx - f) < 1e-5, (
            f"-dU/dx mismatch at x={x}: {-dU_dx} vs F={f}"
        )


def test_shifted_potential_par_asymmetry():
    """Catalog claim: PAR broken in F ⇒ U has odd component ⇒ U(-x) ≠ U(x)."""
    p = HookeGamma11Params(k=20.0, m=1.0, x0=0.0, v0=0.0, eta=0.5, x_scale=0.2)
    U = shifted_potential(p)
    for x in (0.05, 0.15, 0.3):
        gap = abs(U(x) - U(-x))
        assert gap > 1e-4, f"U is even at x={x} (gap={gap:.2e}); PAR should be broken"


def test_shifted_potential_caches():
    """Repeat queries return the exact cached float."""
    p = HookeGamma11Params(k=20.0, m=1.0, x0=0.0, v0=0.0, eta=0.5, x_scale=0.2)
    U = shifted_potential(p)
    a = U(0.123)
    b = U(0.123)
    assert a == b
