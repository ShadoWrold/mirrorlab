"""γ-4-1 — Pendulum asymmetric vertical (PAR break).

Catalog (ROUND-2 FINAL): θ̈ + (g/L)·sin θ + (g/L)·α·(1 − cos θ) = 0.
Broken: PAR (θ→−θ). Retained: T-trans, T-rev.
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
ALPHA_MIN, ALPHA_MAX = 0.05, 0.5


@dataclass(frozen=True)
class PendulumGamma41Params:
    g_over_L: float
    alpha: float
    theta0: float
    omega0: float


def shifted_law(theta: float, p: PendulumGamma41Params) -> float:
    return -p.g_over_L * math.sin(theta) - p.g_over_L * p.alpha * (1.0 - math.cos(theta))


def sampler(seed: int) -> PendulumGamma41Params:
    rng = np.random.default_rng(seed)
    g_over_L = loguniform(rng, GL_MIN, GL_MAX)
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    return PendulumGamma41Params(g_over_L=g_over_L, alpha=alpha,
                                 theta0=0.3, omega0=0.0)


def validator(p) -> bool:
    if not isinstance(p, PendulumGamma41Params):
        return False
    if not (GL_MIN <= p.g_over_L <= GL_MAX):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if p.alpha >= 1.0:
        return False
    if abs(p.theta0) > math.pi / 2:
        return False
    return True


class _Sim:
    def __init__(self, p: PendulumGamma41Params) -> None:
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


def build(*, params: PendulumGamma41Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-4-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta": "rad"},
    "outputs": {"theta_ddot": "rad*s**-2"},
    "params": {"g_over_L": "s**-2", "alpha": "1"},
}

__all__ = ["PendulumGamma41Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
