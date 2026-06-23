"""γ-9-2 — Snell: spatial-dispersion non-reciprocal coupling.

Catalog (Domain 9, Tier-1, ROUND-2 redesign):
    sin θ_t = (n₁/n₂) sin θ_i
              + κ · anti · sin θ_i · sin(β · ν · sin θ_i),
    anti = (n₁ − n₂)/(n₁ + n₂),  β = fixed structural constant.

The earlier cubic form (+κ·anti·sin³θ_i) was a polynomial term in the SAME
family as the GT, so a free refit asin(c·sinθ + d·sin³θ) absorbed it exactly
(stub≈1.0). The break is now an oscillatory term whose phase β·ν·sinθ_i
non-separably couples the incidence angle θ_i and a second visible axis ν
(normalized optical frequency / spatial-dispersion parameter). No low-order
2-D polynomial or separable power law can represent it, and it oscillates
several periods across the ν-OOD grid, so in-domain overfits diverge on (b)/(c).

Broken : 1↔2 interchange symmetry / reciprocity (anti flips sign under n₁↔n₂).
Retained: SO(2) about normal, Fermat, R+T=1, tangential k_∥, polarization U(1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, nan, sin
from typing import Dict

import numpy as np

from mirrorlab.spec import ProbeSpec, P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

KAPPA_MIN, KAPPA_MAX = 3.0, 5.0
N_MIN, N_MAX = 1.0, 2.0
MIN_DN = 0.5            # minimum |n1−n2| so the interchange amplitude |anti| ≳ 0.13
BETA = 6.0             # fixed structural constant (NOT a perturbed law param)


@dataclass(frozen=True)
class OpticsGamma92Params:
    n1: float = field(metadata=P.law("n_1"))       # [1]
    n2: float = field(metadata=P.law("n_2"))       # [1]
    kappa: float = field(metadata=P.law("kappa"))    # spatial-dispersion coupling [1]
    theta_i: float = field(metadata=P.axis())  # incidence [rad]
    nu: float = field(metadata=P.axis())       # normalized optical frequency (probe axis) [1]


def shifted_sin_theta_t(params: OpticsGamma92Params, nu: float | None = None) -> float:
    s = sin(params.theta_i)
    anti = (params.n1 - params.n2) / (params.n1 + params.n2)
    nu_val = params.nu if nu is None else nu
    return (params.n1 / params.n2) * s + params.kappa * anti * s * sin(BETA * nu_val * s)


class OpticsGamma92Instance:
    def __init__(self, params: OpticsGamma92Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-9-2 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> OpticsGamma92Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        s = shifted_sin_theta_t(self._params)
        theta_t = asin(s) if -1.0 <= s <= 1.0 else nan
        return {"t": float(t), "theta_i": float(self._params.theta_i),
                "nu": float(self._params.nu), "theta_t": float(theta_t)}


def sampler(seed: int) -> OpticsGamma92Params:
    rng = np.random.default_rng(seed)
    while True:
        n1 = float(rng.uniform(N_MIN, N_MAX))
        n2 = float(rng.uniform(N_MIN, N_MAX))
        if abs(n1 - n2) >= MIN_DN:
            break
    kappa = float(rng.uniform(KAPPA_MIN, KAPPA_MAX))
    nu = float(rng.uniform(0.5, 2.0))
    return OpticsGamma92Params(n1=n1, n2=n2, kappa=kappa, theta_i=0.3, nu=nu)


def validator(params: OpticsGamma92Params) -> bool:
    if not isinstance(params, OpticsGamma92Params):
        return False
    if not (N_MIN <= params.n1 <= N_MAX):
        return False
    if not (N_MIN <= params.n2 <= N_MAX):
        return False
    if abs(params.n1 - params.n2) < MIN_DN:
        return False
    if not (KAPPA_MIN <= params.kappa <= KAPPA_MAX):
        return False
    if abs(sin(params.theta_i)) > 0.95:
        return False
    return True


def build(*, params: OpticsGamma92Params | None = None, seed: int = 0) -> OpticsGamma92Instance:
    if params is None:
        params = sampler(seed)
    return OpticsGamma92Instance(params)


shift = ShiftImpl(law=lambda t, p: shifted_sin_theta_t(p), sampler=sampler, validator=validator)


def law(inputs, p: OpticsGamma92Params) -> float:
    """Unified GT/oracle law: spatial-dispersion refraction angle
    θ_t = asin((n1/n2)sinθ + κ·anti·sinθ·sin(β·ν·sinθ)), clamped at TIR.
    θ (theta1) and ν (nu) are swept grid inputs."""
    s = sin(inputs["theta1"])
    anti = (p.n1 - p.n2) / (p.n1 + p.n2)
    val = (p.n1 / p.n2) * s + p.kappa * anti * s * sin(BETA * inputs["nu"] * s)
    return asin(max(-1.0, min(1.0, val)))


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta_i": "1", "nu": "1"},
    "outputs": {"theta_t": "1"},
    "params": {"n1": "1", "n2": "1", "kappa": "1"},
}

CELL = CellSpec(
    domain="optics", shift="gamma_9_2",
    params_type=OpticsGamma92Params, law=law,
    sampler=sampler, validator=validator,
    output="theta2", break_type="PAR",
    probe_spec=ProbeSpec(kind="parity", axes=('theta1',)),
)
register_cell(CELL)

__all__ = [
    "OpticsGamma92Params", "OpticsGamma92Instance", "shifted_sin_theta_t", "law",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "BETA", "CELL",
]
