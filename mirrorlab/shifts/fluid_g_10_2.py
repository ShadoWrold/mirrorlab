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

from dataclasses import dataclass, field
from typing import Dict

import numpy as np

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

Q_MIN, Q_MAX = 0.5, 2.0
H0_MIN, H0_MAX = 1.0, 100.0
H_MAX = 5.0  # physical envelope


@dataclass(frozen=True)
class FluidGamma102Params:
    rho: float = field(metadata=P.law("rho"))      # [kg/m³]
    g: float = field(metadata=P.law("g"))        # [m/s²]
    h0: float = field(metadata=P.law("h_0"))       # length scale [m]
    lam: float = field(metadata=P.law("lam"))      # nonlinearity amplitude [1]
    q: float = field(metadata=P.law("q"))        # exponent [1]
    h1: float = field(metadata=P.ic())
    v1: float = field(metadata=P.ic())       # [m/s]
    p1: float = field(metadata=P.ic())       # [Pa]
    h2: float = field(metadata=P.ic())
    v2: float = field(metadata=P.ic())


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
    # Force |lam| into the upper half [0.6·eps, eps] with a random sign,
    # instead of uniform(-eps, eps) which clustered near 0. The h-potential
    # nonlinearity λ(h/h0)^q was otherwise too weak to show against the
    # textbook Bernoulli term.
    mag = float(rng.uniform(0.6 * eps, eps))
    lam = mag if rng.uniform() < 0.5 else -mag
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


def law(inputs, p: FluidGamma102Params) -> float:
    """Unified GT/oracle law: depth-stratified Bernoulli pressure. p1/v1/v2/h1/h2
    are swept grid inputs; fold them in and evaluate the shift pressure formula."""
    from dataclasses import replace
    p_eff = replace(p, p1=inputs["p1"], v1=inputs["v1"], v2=inputs["v2"],
                    h1=inputs["h1"], h2=inputs["h2"])
    return shifted_pressure(p_eff)


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"v": "m*s**-1", "h": "m", "p": "kg*m**-1*s**-2"},
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "g": "m*s**-2", "h0": "m", "lam": "1", "q": "1"},
}

CELL = CellSpec(
    domain="fluid", shift="gamma_10_2",
    params_type=FluidGamma102Params, law=law,
    sampler=sampler, validator=validator,
    output="p2", break_type="S_TRANS",
)
register_cell(CELL)

__all__ = [
    "FluidGamma102Params", "FluidGamma102Instance", "shifted_pressure", "law",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "CELL",
]
