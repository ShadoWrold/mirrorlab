"""γ-9-1 — Snell: polarization-modulated index.

Catalog (Domain 9, Tier-1):
    n_eff(θ_pol) = n₀ + δn · sin²(2 θ_pol - φ);
    Snell: n₁ sin θ₁ = n_eff(θ_pol) sin θ₂

Broken : polarization U(1).
Retained: reciprocity, Fermat, tangential k_∥, energy R+T=1, SO(2) about normal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from math import asin, nan, sin
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

N0_MIN, N0_MAX = 1.3, 2.2
DN_MIN, DN_MAX = 0.02, 0.30


@dataclass(frozen=True)
class OpticsGamma91Params:
    n1: float       # incident-side index [1]
    n0: float       # base transmitted-side index [1]
    dn: float       # polarization modulation amplitude [1]
    phi: float      # phase [rad]
    theta1: float   # incidence angle [rad]
    theta_pol: float  # polarization angle [rad]


def n_eff(params: OpticsGamma91Params) -> float:
    return params.n0 + params.dn * math.sin(2 * params.theta_pol - params.phi) ** 2


class OpticsGamma91Instance:
    def __init__(self, params: OpticsGamma91Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-9-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> OpticsGamma91Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        ne = n_eff(p)
        s2 = p.n1 / ne * sin(p.theta1)
        theta2 = asin(s2) if -1.0 <= s2 <= 1.0 else nan
        return {"t": float(t), "theta1": float(p.theta1), "theta2": float(theta2), "n_eff": float(ne)}


def sampler(seed: int) -> OpticsGamma91Params:
    rng = np.random.default_rng(seed)
    n0 = float(rng.uniform(N0_MIN, N0_MAX))
    dn = float(rng.uniform(DN_MIN, DN_MAX))
    phi = float(rng.uniform(0.0, math.pi))
    theta_pol = float(rng.uniform(0.0, math.pi))
    return OpticsGamma91Params(n1=1.0, n0=n0, dn=dn, phi=phi, theta1=0.3, theta_pol=theta_pol)


def validator(params: OpticsGamma91Params) -> bool:
    if not isinstance(params, OpticsGamma91Params):
        return False
    if not (N0_MIN <= params.n0 <= N0_MAX):
        return False
    if not (DN_MIN <= params.dn <= DN_MAX):
        return False
    if params.n1 <= 0:
        return False
    return True


def build(*, params: OpticsGamma91Params | None = None, seed: int = 0) -> OpticsGamma91Instance:
    if params is None:
        params = sampler(seed)
    return OpticsGamma91Instance(params)


shift = ShiftImpl(law=lambda t, p: n_eff(p), sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta1": "1", "theta_pol": "1"},
    "outputs": {"theta2": "1"},
    "params": {"n1": "1", "n0": "1", "dn": "1", "phi": "1"},
}

__all__ = [
    "OpticsGamma91Params", "OpticsGamma91Instance", "n_eff",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
