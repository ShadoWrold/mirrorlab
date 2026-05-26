"""δ-4-1 — Pendulum off-resonant g(t) modulation (T-trans break).

Catalog (ROUND-2 FINAL): θ̈ + (g(t)/L)·sin θ = 0, g(t) = g₀·[1 + ε cos(Ω t)],
phase ≡ 0 (T-rev preserved).
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
EPS_MIN, EPS_MAX = 0.05, 0.3


@dataclass(frozen=True)
class PendulumDelta41Params:
    g0_over_L: float
    eps: float
    Omega: float
    theta0: float
    omega_init: float


def shifted_law(theta: float, t: float, p: PendulumDelta41Params) -> float:
    factor = 1.0 + p.eps * math.cos(p.Omega * t)
    return -p.g0_over_L * factor * math.sin(theta)


def sampler(seed: int) -> PendulumDelta41Params:
    rng = np.random.default_rng(seed)
    g0_over_L = loguniform(rng, GL_MIN, GL_MAX)
    omega0 = math.sqrt(g0_over_L)
    Omega = omega0 * float(rng.uniform(0.3, 1.7))
    # Sub-threshold of Mathieu tongue: ε ≤ 0.4·|Ω/(2ω₀) − 1|.
    bound = 0.4 * abs(Omega / (2.0 * omega0) - 1.0)
    eps_hi = min(EPS_MAX, 0.95 * bound) if bound > EPS_MIN else EPS_MIN
    eps = float(rng.uniform(EPS_MIN, max(eps_hi, EPS_MIN + 1e-12)))
    return PendulumDelta41Params(g0_over_L=g0_over_L, eps=eps, Omega=Omega,
                                 theta0=0.3, omega_init=0.0)


def validator(p) -> bool:
    if not isinstance(p, PendulumDelta41Params):
        return False
    if not (GL_MIN <= p.g0_over_L <= GL_MAX):
        return False
    if not (EPS_MIN <= p.eps <= EPS_MAX):
        return False
    if p.Omega <= 0:
        return False
    omega_nat = math.sqrt(p.g0_over_L)
    ratio = p.Omega / omega_nat
    if not (0.3 <= ratio <= 1.7):
        return False
    # sub-threshold Mathieu: ε ≤ 0.4 · |Ω/(2ω₀) − 1|
    bound = 0.4 * abs(p.Omega / (2.0 * omega_nat) - 1.0)
    if p.eps > bound:
        return False
    if abs(p.theta0) > math.pi / 2:
        return False
    return True


class _Sim:
    def __init__(self, p: PendulumDelta41Params) -> None:
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
            return (om, shifted_law(th, t, p))

        sol = solve_ivp(rhs, (0.0, t_max), [p.theta0, p.omega_init],
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


def build(*, params: PendulumDelta41Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-4-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta": "rad", "t": "s"},
    "outputs": {"theta_ddot": "rad*s**-2"},
    "params": {"g0_over_L": "s**-2", "eps": "1", "Omega": "s**-1"},
}

__all__ = ["PendulumDelta41Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
