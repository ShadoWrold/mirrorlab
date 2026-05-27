"""δ-2-1 — Gravity slow harmonic G(t) modulation (T-trans break).

Catalog (ROUND-2 FINAL): G(t) = G₀ [1 + β cos(ω_G t)], φ ≡ 0 so T-rev preserved.
F = −G(t) m₁ m₂ r̂ / r².
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
BETA_MIN, BETA_MAX = 0.05, 0.3


@dataclass(frozen=True)
class GravityDelta21Params:
    G0: float
    M: float
    m: float
    beta: float
    omega_G: float
    r0: float
    v0: float
    T_sim: float


def G_of_t(t: float, p: GravityDelta21Params) -> float:
    return p.G0 * (1.0 + p.beta * math.cos(p.omega_G * t))


def shifted_force(r: float, t: float, p: GravityDelta21Params) -> float:
    return -G_of_t(t, p) * p.M * p.m / (r * r)


def sampler(seed: int) -> GravityDelta21Params:
    rng = np.random.default_rng(seed)
    G0 = G_DEFAULT * loguniform(rng, 0.5, 2.0)
    M = float(10 ** rng.uniform(20.0, 24.0))
    beta = float(rng.uniform(BETA_MIN, BETA_MAX))
    r0 = 1.0e7
    omega_orbit = math.sqrt(G_DEFAULT * M / r0 ** 3)
    omega_G = omega_orbit * loguniform(rng, 1e-4, 1e-2)
    T_sim = 2.0 * math.pi / omega_orbit
    return GravityDelta21Params(G0=G0, M=M, m=1.0, beta=beta,
                                omega_G=omega_G, r0=r0, v0=0.0, T_sim=T_sim)


def validator(p) -> bool:
    if not isinstance(p, GravityDelta21Params):
        return False
    if not (BETA_MIN <= p.beta <= BETA_MAX):
        return False
    if p.G0 <= 0 or p.M <= 0 or p.m <= 0:
        return False
    if p.omega_G <= 0:
        return False
    if p.r0 <= 0:
        return False
    if p.beta * p.omega_G * p.T_sim > 0.5:
        return False
    return True


class _Sim:
    def __init__(self, p: GravityDelta21Params) -> None:
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
            return (v, shifted_force(r, t, p) / p.m)

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
                "F": float(shifted_force(r, t, self._p))}


def build(*, params: GravityDelta21Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-2-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"r": "m", "t": "s"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"G0": "m**3*kg**-1*s**-2", "M": "kg", "m": "kg",
               "beta": "1", "omega_G": "s**-1"},
}

__all__ = ["GravityDelta21Params", "shifted_force", "G_of_t", "sampler",
           "validator", "build", "shift", "DIM_SIGNATURE"]
