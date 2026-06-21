"""Damped harmonic oscillator baseline.

Baseline law: m·ẍ + c·ẋ + k·x = 0  (force F = -k x - c v).
NewtonBench mapping: `vendor/newtonbench/modules/m6_underdamped_harmonic`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from scipy.integrate import solve_ivp
from mirrorlab.spec import P, CellSpec, register_cell


@dataclass(frozen=True)
class DampedHOParams:
    k: float = field(metadata=P.law("k"))        # stiffness [N/m]
    c: float = field(metadata=P.law("c"))        # damping coefficient [kg/s]
    m: float = field(metadata=P.mass())        # mass [kg]
    x0: float = field(metadata=P.ic())
    v0: float = field(metadata=P.ic())


def baseline_force(x: float, v: float, params: DampedHOParams) -> float:
    return -params.k * x - params.c * v


class DampedHOBaseline:
    def __init__(self, params: DampedHOParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.m <= 0:
            raise ValueError("mass must be positive")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> DampedHOParams:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            x, v = y
            return (v, baseline_force(x, v, p) / p.m)

        sol = solve_ivp(rhs, (0.0, t_max), [p.x0, p.v0], method="DOP853",
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
        x, v = float(y[0]), float(y[1])
        return {"t": float(t), "x": x, "v": v, "F": float(baseline_force(x, v, self._params))}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "v": "m*s**-1"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"k": "kg*s**-2", "c": "kg*s**-1", "m": "kg"},
}


def law(inputs, p: DampedHOParams) -> float:
    """Unified GT/oracle law: the scored channel is the acceleration
    ẍ = −(k/m)·x − (c/m)·v (matches the loader baseline GT, not the bare
    force returned by step())."""
    return -(p.k / p.m) * inputs["x"] - (p.c / p.m) * inputs["v"]


CELL = CellSpec(
    domain="damped_ho", shift="baseline",
    params_type=DampedHOParams, law=law,
    output="F", broken_symmetry="none",
)
register_cell(CELL)
