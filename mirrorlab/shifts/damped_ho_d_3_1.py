"""δ-3-1 — Damped HO amplitude-gated damping sign reversal (E break ⇒ limit cycle).

Catalog: ẍ + 2γ·(|x|/L − 1)·ẋ + ω₀² x = 0.
Broken: monotone energy dissipation. Retained: T-trans, PAR.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

OMEGA_MIN, OMEGA_MAX = 0.5, 10.0
L_MIN, L_MAX = 0.1, 2.0


@dataclass(frozen=True)
class DampedHODelta31Params:
    omega0: float
    gamma: float
    L: float
    m: float
    x0: float
    v0: float


def shifted_law(x: float, v: float, p: DampedHODelta31Params) -> float:
    gate = (abs(x) / p.L - 1.0)
    return -2.0 * p.gamma * gate * v - p.omega0 * p.omega0 * x


def sampler(seed: int) -> DampedHODelta31Params:
    rng = np.random.default_rng(seed)
    omega0 = loguniform(rng, OMEGA_MIN, OMEGA_MAX)
    gamma = omega0 * loguniform(rng, 0.01, 0.2)
    L = loguniform(rng, L_MIN, L_MAX)
    return DampedHODelta31Params(omega0=omega0, gamma=gamma, L=L,
                                 m=1.0, x0=0.5 * L, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, DampedHODelta31Params):
        return False
    if not (OMEGA_MIN <= p.omega0 <= OMEGA_MAX):
        return False
    if not (L_MIN <= p.L <= L_MAX):
        return False
    if p.gamma <= 0 or p.m <= 0:
        return False
    if not (0.01 <= p.gamma / p.omega0 <= 0.2):
        return False
    return True


class _Sim:
    def __init__(self, p: DampedHODelta31Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            x, v = y
            return (v, shifted_law(x, v, p))

        sol = solve_ivp(rhs, (0.0, t_max), [p.x0, p.v0],
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
        x, v = float(y[0]), float(y[1])
        return {"t": float(t), "x": x, "v": v}


def build(*, params: DampedHODelta31Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-3-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "v": "m*s**-1"},
    "outputs": {"a": "m*s**-2"},
    "params": {"omega0": "s**-1", "gamma": "s**-1", "L": "m", "m": "kg"},
}

__all__ = ["DampedHODelta31Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
