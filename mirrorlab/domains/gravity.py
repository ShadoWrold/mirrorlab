"""Newtonian gravity baseline domain (radial two-body, central potential).

Baseline law: F(r) = -G M m / r².  1-D radial reduced ODE with m·r̈ = F(r).
NewtonBench mapping: `vendor/newtonbench/modules/m0_gravity` (baseline only;
vendor wiring deferred to the shift layer per Sprint-1 sim-engineer note).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp


G_DEFAULT = 6.67430e-11


@dataclass(frozen=True)
class GravityParams:
    M: float        # central mass [kg]
    m: float        # test mass [kg]
    r0: float       # initial radius [m]
    v0: float       # initial radial velocity [m/s]
    G: float = G_DEFAULT


def baseline_force(r: float, params: GravityParams) -> float:
    return -params.G * params.M * params.m / (r * r)


class GravityBaseline:
    def __init__(self, params: GravityParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.m <= 0 or params.M <= 0:
            raise ValueError("masses must be positive")
        if params.r0 <= 0:
            raise ValueError("r0 must be positive")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> GravityParams:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            r, v = y
            if r <= 0:
                return (v, 0.0)
            return (v, baseline_force(r, p) / p.m)

        sol = solve_ivp(rhs, (0.0, t_max), [p.r0, p.v0], method="DOP853",
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
        r, v = float(y[0]), float(y[1])
        return {"t": float(t), "r": r, "v": v, "F": float(baseline_force(r, self._params))}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"r": "m"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"G": "m**3*kg**-1*s**-2", "M": "kg", "m": "kg"},
}
