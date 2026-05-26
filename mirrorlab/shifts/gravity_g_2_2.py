"""γ-2-2 — Gravity Lorentzian range bump (SCALE/Bertrand break).

Catalog: F(r) = −G m₁ m₂ /r² · [1 + α (r/r₀)/(1 + (r/r₀)²)].
Broken: SCALE (Bertrand closure). Retained: ROT (central), T-trans, T-rev.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

G_DEFAULT = 6.67430e-11
ALPHA_MIN, ALPHA_MAX = 0.05, 0.5


@dataclass(frozen=True)
class GravityGamma22Params:
    G: float
    M: float
    m: float
    alpha: float
    r_scale: float  # r₀
    r0: float       # initial radius
    v0: float


def shifted_force(r: float, p: GravityGamma22Params) -> float:
    u = r / p.r_scale
    bump = p.alpha * u / (1.0 + u * u)
    return -p.G * p.M * p.m / (r * r) * (1.0 + bump)


def sampler(seed: int) -> GravityGamma22Params:
    rng = np.random.default_rng(seed)
    G = G_DEFAULT * loguniform(rng, 0.5, 2.0)
    M = float(10 ** rng.uniform(20.0, 24.0))
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    r0_radius = 1.0e7
    r_scale = r0_radius * loguniform(rng, 0.1, 10.0)
    return GravityGamma22Params(G=G, M=M, m=1.0, alpha=alpha,
                                r_scale=r_scale, r0=r0_radius, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, GravityGamma22Params):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if p.G <= 0 or p.M <= 0 or p.m <= 0:
        return False
    if p.r_scale <= 0 or p.r0 <= 0:
        return False
    if p.r0 < 1e-3 * p.r_scale:
        return False
    return True


class _Sim:
    def __init__(self, p: GravityGamma22Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            r, v = y
            if r <= 0:
                return (v, 0.0)
            return (v, shifted_force(r, p) / p.m)

        sol = solve_ivp(rhs, (0.0, t_max), [p.r0, p.v0],
                        method="DOP853", rtol=1e-9, atol=1e-12, dense_output=True)
        if not sol.success:
            raise RuntimeError(f"ODE failed: {sol.message}")
        self._sol = sol
        self._t_end = t_max

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        if self._sol is None or t > self._t_end:
            self._integrate(max(t * 2.0, 1.0))
        y = self._sol.sol(t)
        r, v = float(y[0]), float(y[1])
        return {"t": float(t), "r": r, "v": v,
                "F": float(shifted_force(r, self._p))}


def build(*, params: GravityGamma22Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-2-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"r": "m"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"G": "m**3*kg**-1*s**-2", "M": "kg", "m": "kg",
               "alpha": "1", "r_scale": "m"},
}

__all__ = ["GravityGamma22Params", "shifted_force", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
