"""γ-4-2 — Pendulum height-graded gravity (vertical S-trans break).

Catalog: θ̈ + (g₀/L)·[1 − α·(L(1−cos θ))/H]·sin θ = 0.
Broken: vertical S-trans. Retained: T-trans, PAR.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

GL_MIN, GL_MAX = 1.0, 100.0
ALPHA_MIN, ALPHA_MAX = 0.02, 0.3


@dataclass(frozen=True)
class PendulumGamma42Params:
    g0_over_L: float
    alpha: float
    L: float
    H: float
    theta0: float
    omega0: float


def shifted_law(theta: float, p: PendulumGamma42Params) -> float:
    height = p.L * (1.0 - math.cos(theta))
    g_eff = p.g0_over_L * (1.0 - p.alpha * height / p.H)
    return -g_eff * math.sin(theta)


def sampler(seed: int) -> PendulumGamma42Params:
    rng = np.random.default_rng(seed)
    g0_over_L = loguniform(rng, GL_MIN, GL_MAX)
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    L = loguniform(rng, 0.1, 2.0)
    # H ≥ 2·α·L for the safety bound α·L/H < 0.5; use comfortable factor of 4.
    H_min_safe = max(0.5 * L, 4.0 * alpha * L)
    H = H_min_safe * loguniform(rng, 1.0, 50.0)
    return PendulumGamma42Params(g0_over_L=g0_over_L, alpha=alpha, L=L, H=H,
                                 theta0=0.3, omega0=0.0)


def validator(p) -> bool:
    if not isinstance(p, PendulumGamma42Params):
        return False
    if not (GL_MIN <= p.g0_over_L <= GL_MAX):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if p.L <= 0 or p.H <= 0:
        return False
    if p.alpha * p.L / p.H >= 0.5:
        return False
    if abs(p.theta0) > math.pi / 2:
        return False
    return True


class _Sim:
    def __init__(self, p: PendulumGamma42Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            th, om = y
            return (om, shifted_law(th, p))

        sol = solve_ivp(rhs, (0.0, t_max), [p.theta0, p.omega0],
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
        theta, omega = float(y[0]), float(y[1])
        return {"t": float(t), "theta": theta, "omega": omega}


def build(*, params: PendulumGamma42Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-4-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta": "rad"},
    "outputs": {"theta_ddot": "rad*s**-2"},
    "params": {"g0_over_L": "s**-2", "alpha": "1", "L": "m", "H": "m"},
}

__all__ = ["PendulumGamma42Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
