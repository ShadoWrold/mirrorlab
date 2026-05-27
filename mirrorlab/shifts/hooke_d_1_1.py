"""δ-1-1 — Hooke amplitude-conditioned drag (E break).

Catalog: F(x, ẋ) = −k x − c (x²/L²) ẋ.
Broken: Energy. Retained: T-trans, PAR (x→−x, ẋ→−ẋ).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

K_MIN, K_MAX = 1.0, 100.0
C_MIN, C_MAX = 1e-3, 1.0
L_MIN, L_MAX = 0.5, 5.0


@dataclass(frozen=True)
class HookeDelta11Params:
    k: float
    c: float
    L: float
    m: float
    x0: float
    v0: float


def shifted_force(x: float, v: float, p: HookeDelta11Params) -> float:
    return -p.k * x - p.c * (x * x / (p.L * p.L)) * v


def sampler(seed: int) -> HookeDelta11Params:
    rng = np.random.default_rng(seed)
    k = loguniform(rng, K_MIN, K_MAX)
    c = loguniform(rng, C_MIN, C_MAX)
    L = loguniform(rng, L_MIN, L_MAX)
    return HookeDelta11Params(k=k, c=c, L=L, m=1.0, x0=0.1, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, HookeDelta11Params):
        return False
    if not (K_MIN <= p.k <= K_MAX):
        return False
    if not (C_MIN <= p.c <= C_MAX):
        return False
    if not (L_MIN <= p.L <= L_MAX):
        return False
    if p.m <= 0.0:
        return False
    # Safe: c · x_max² / (L²·√(km)) ≤ 0.3, with x_max ≈ |x0|
    x_max = max(abs(p.x0), 1e-12)
    if p.c * x_max * x_max / (p.L * p.L * math.sqrt(p.k * p.m)) > 0.3:
        return False
    return True


class _Sim:
    def __init__(self, p: HookeDelta11Params) -> None:
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
            return (v, shifted_force(x, v, p) / p.m)

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
        return {"t": float(t), "x": x, "v": v,
                "F": float(shifted_force(x, v, self._p))}


def build(*, params: HookeDelta11Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-1-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "v": "m*s**-1"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"k": "kg*s**-2", "c": "kg*s**-1", "L": "m", "m": "kg"},
}

__all__ = ["HookeDelta11Params", "shifted_force", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
