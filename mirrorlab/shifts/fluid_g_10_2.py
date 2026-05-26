"""γ-10-2 — Fluid: nonlinear gravitational potential (stratified buoyancy re-skin).

Catalog (Domain 10, Tier-1):
    ½ ρ v² + ρ g h (1 + λ (h/h₀)^q) + p = const

Broken : vertical S-trans (h → h + c).
Retained: horizontal S-trans, SO(2) horizontal, ∇·v=0, T-trans, streamline E.

Paired with Part A γ-4-2 (height-graded gravity pendulum) — same nonuniform g
motif. Coordinate w/ domain-engineer-A.

Sampling-level constraint: |λ| (h_max/h₀)^q < 0.5 (enforced in sampler).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

Q_MIN, Q_MAX = 0.5, 2.0
H0_MIN, H0_MAX = 1.0, 100.0
H_MAX = 5.0  # physical envelope


@dataclass(frozen=True)
class FluidGamma102Params:
    rho: float      # [kg/m³]
    g: float        # [m/s²]
    h0: float       # length scale [m]
    lam: float      # nonlinearity amplitude [1]
    q: float        # exponent [1]
    h1: float
    v1: float       # [m/s]
    p1: float       # [Pa]
    h2: float
    v2: float


def _gh_potential_per_rho(h: float, params: FluidGamma102Params) -> float:
    return params.g * h * (1.0 + params.lam * (h / params.h0) ** params.q)


def shifted_pressure(params: FluidGamma102Params) -> float:
    p = params
    return p.p1 + 0.5 * p.rho * (p.v1 ** 2 - p.v2 ** 2) + p.rho * (
        _gh_potential_per_rho(p.h1, p) - _gh_potential_per_rho(p.h2, p)
    )


class FluidGamma102Instance:
    def __init__(self, params: FluidGamma102Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-10-2 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> FluidGamma102Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "p2": float(shifted_pressure(self._params))}


def sampler(seed: int) -> FluidGamma102Params:
    rng = np.random.default_rng(seed)
    q = float(rng.uniform(Q_MIN, Q_MAX))
    h0 = float(np.exp(rng.uniform(np.log(H0_MIN), np.log(H0_MAX))))
    eps = min(0.5, 0.5 / (H_MAX / h0) ** q)
    while True:
        lam = float(rng.uniform(-eps, eps))
        if abs(lam) >= 0.01:
            break
    rho = float(rng.uniform(800.0, 1200.0))
    return FluidGamma102Params(
        rho=rho, g=9.81, h0=h0, lam=lam, q=q,
        h1=2.0, v1=1.0, p1=1.01e5, h2=0.0, v2=3.0,
    )


def validator(params: FluidGamma102Params) -> bool:
    if not isinstance(params, FluidGamma102Params):
        return False
    if not (Q_MIN <= params.q <= Q_MAX):
        return False
    if not (H0_MIN <= params.h0 <= H0_MAX):
        return False
    if params.rho <= 0:
        return False
    if abs(params.lam) < 0.01 or abs(params.lam) > 0.5:
        return False
    # Sampling-level constraint
    if abs(params.lam) * (H_MAX / params.h0) ** params.q >= 0.5:
        return False
    return True


def build(*, params: FluidGamma102Params | None = None, seed: int = 0) -> FluidGamma102Instance:
    if params is None:
        params = sampler(seed)
    return FluidGamma102Instance(params)


shift = ShiftImpl(law=lambda t, p: shifted_pressure(p), sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"v": "m*s**-1", "h": "m", "p": "kg*m**-1*s**-2"},
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "g": "m*s**-2", "h0": "m", "lam": "1", "q": "1"},
}

__all__ = [
    "FluidGamma102Params", "FluidGamma102Instance", "shifted_pressure",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
