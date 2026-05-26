"""γ-9-2 — Snell: interchange-asymmetric (non-reciprocal coupling re-skin).

Catalog (Domain 9, Tier-1):
    sin θ_t = (n₁/n₂) sin θ_i + κ (n₁-n₂)/(n₁+n₂) sin³ θ_i

Broken : 1↔2 interchange symmetry / reciprocity.
Retained: SO(2) about normal, Fermat, R+T=1, tangential k_∥, polarization U(1).

Paired with Part A γ-6-2 (asymmetric mutual M) — same "non-reciprocity"
motif applied at the optical interface. Coordinate w/ domain-engineer-A.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, nan, sin
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

KAPPA_MIN, KAPPA_MAX = 0.0, 0.15
N_MIN, N_MAX = 1.0, 2.0


@dataclass(frozen=True)
class OpticsGamma92Params:
    n1: float       # [1]
    n2: float       # [1]
    kappa: float    # cubic asymmetry coupling [1]
    theta_i: float  # incidence [rad]


def shifted_sin_theta_t(params: OpticsGamma92Params) -> float:
    s = sin(params.theta_i)
    anti = (params.n1 - params.n2) / (params.n1 + params.n2)
    return (params.n1 / params.n2) * s + params.kappa * anti * s ** 3


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
        return {"t": float(t), "theta_i": float(self._params.theta_i), "theta_t": float(theta_t)}


def sampler(seed: int) -> OpticsGamma92Params:
    rng = np.random.default_rng(seed)
    n1 = float(rng.uniform(N_MIN, N_MAX))
    n2 = float(rng.uniform(N_MIN, N_MAX))
    kappa = float(rng.uniform(KAPPA_MIN, KAPPA_MAX))
    return OpticsGamma92Params(n1=n1, n2=n2, kappa=kappa, theta_i=0.3)


def validator(params: OpticsGamma92Params) -> bool:
    if not isinstance(params, OpticsGamma92Params):
        return False
    if not (N_MIN <= params.n1 <= N_MAX):
        return False
    if not (N_MIN <= params.n2 <= N_MAX):
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

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta_i": "1"},
    "outputs": {"theta_t": "1"},
    "params": {"n1": "1", "n2": "1", "kappa": "1"},
}

__all__ = [
    "OpticsGamma92Params", "OpticsGamma92Instance", "shifted_sin_theta_t",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
