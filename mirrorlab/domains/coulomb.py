"""Coulomb electrostatics baseline (radial reduced ODE, like gravity).

Baseline law: F(r) = k_e q₁ q₂ / r².
NewtonBench mapping: `vendor/newtonbench/modules/m1_coulomb_force`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from scipy.integrate import solve_ivp


K_E_DEFAULT = 8.9875517873681764e9


@dataclass(frozen=True)
class CoulombParams:
    q1: float       # [C]
    q2: float       # [C]
    m: float        # reduced mass [kg]
    r0: float       # initial separation [m]
    v0: float       # initial radial velocity [m/s]
    k_e: float = K_E_DEFAULT


def baseline_force(r: float, params: CoulombParams) -> float:
    return params.k_e * params.q1 * params.q2 / (r * r)


class CoulombBaseline:
    def __init__(self, params: CoulombParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.m <= 0:
            raise ValueError("mass must be positive")
        if params.r0 <= 0:
            raise ValueError("r0 must be positive")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> CoulombParams:
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
    "params": {"k_e": "kg*m**3*s**-4*A**-2", "q1": "A*s", "q2": "A*s", "m": "kg"},
}
