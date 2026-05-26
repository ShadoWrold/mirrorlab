"""Simple gravity pendulum baseline.

Baseline law: θ̈ + (g/L) sin θ = 0.  No NewtonBench module — self-contained;
the spec lists it under "NewtonBench pendulum" but the upstream catalog does
not ship one in commit 912a4ba.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sin
from typing import Dict

from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class PendulumParams:
    L: float        # length [m]
    g: float        # gravitational acceleration [m/s²]
    theta0: float   # initial angle [rad]
    omega0: float   # initial angular velocity [rad/s]


class PendulumBaseline:
    def __init__(self, params: PendulumParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.L <= 0 or params.g <= 0:
            raise ValueError("L, g must be positive")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> PendulumParams:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params
        coef = p.g / p.L

        def rhs(t, y):
            th, om = y
            return (om, -coef * sin(th))

        sol = solve_ivp(rhs, (0.0, t_max), [p.theta0, p.omega0], method="DOP853",
                        rtol=self._rtol, atol=self._atol, dense_output=True)
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


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"theta": "1", "omega": "s**-1"},
    "params": {"L": "m", "g": "m*s**-2"},
}
