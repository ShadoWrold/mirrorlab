"""γ-3-2 — Damped HO slow parametric pumping (T-trans break).

Catalog: ẍ + 2γẋ + ω₀²·[1 + ε cos(Ω_p t)] x = 0.
Broken: T-trans. Retained: PAR, LIN.
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
EPS_MIN, EPS_MAX = 0.05, 0.3


@dataclass(frozen=True)
class DampedHOGamma32Params:
    omega0: float
    gamma: float
    eps: float
    Omega_p: float
    m: float
    x0: float
    v0: float


def shifted_law(x: float, v: float, t: float, p: DampedHOGamma32Params) -> float:
    omega2_t = p.omega0 * p.omega0 * (1.0 + p.eps * math.cos(p.Omega_p * t))
    return -2.0 * p.gamma * v - omega2_t * x


def sampler(seed: int) -> DampedHOGamma32Params:
    rng = np.random.default_rng(seed)
    omega0 = loguniform(rng, OMEGA_MIN, OMEGA_MAX)
    # ε must satisfy ε < 4γ/ω₀ (sub-threshold) AND ε ∈ [EPS_MIN, EPS_MAX].
    # Rejection-sample γ to preserve the loguniform distribution rather than
    # silently mutating it when the upper bound collapses below EPS_MIN.
    for _ in range(100):
        gamma = omega0 * loguniform(rng, 0.01, 0.3)
        if 0.95 * 4.0 * gamma / omega0 > EPS_MIN:
            break
    else:
        raise RuntimeError("γ-3-2 sampler: 100 rejection attempts failed")
    eps_hi = min(EPS_MAX, 0.95 * 4.0 * gamma / omega0)
    eps = float(rng.uniform(EPS_MIN, eps_hi))
    Omega_p = omega0 * float(rng.uniform(0.3, 1.7))
    return DampedHOGamma32Params(omega0=omega0, gamma=gamma, eps=eps,
                                 Omega_p=Omega_p, m=1.0, x0=0.1, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, DampedHOGamma32Params):
        return False
    if not (OMEGA_MIN <= p.omega0 <= OMEGA_MAX):
        return False
    if not (EPS_MIN <= p.eps <= EPS_MAX):
        return False
    if p.gamma <= 0 or p.m <= 0 or p.Omega_p <= 0:
        return False
    if p.eps >= 4.0 * p.gamma / p.omega0:
        return False
    if not (0.3 * p.omega0 <= p.Omega_p <= 1.7 * p.omega0):
        return False
    return True


class _Sim:
    def __init__(self, p: DampedHOGamma32Params) -> None:
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
            return (v, shifted_law(x, v, t, p))

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


def build(*, params: DampedHOGamma32Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-3-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "v": "m*s**-1", "t": "s"},
    "outputs": {"a": "m*s**-2"},
    "params": {"omega0": "s**-1", "gamma": "s**-1", "eps": "1",
               "Omega_p": "s**-1", "m": "kg"},
}

__all__ = ["DampedHOGamma32Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
