"""Geometric optics (Snell) baseline.

Baseline law: n₁ sin θ₁ = n₂ sin θ₂.  Algebraic — `step(t)` ignores `t` and
returns the refracted angle for the configured incidence.
NewtonBench mapping: `vendor/newtonbench/modules/m4_snell_law`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, nan, sin
from typing import Dict
from mirrorlab.spec import P, CellSpec, register_cell


@dataclass(frozen=True)
class OpticsParams:
    n1: float = field(metadata=P.law("n_1"))       # incident-side refractive index [1]
    n2: float = field(metadata=P.law("n_2"))       # transmitted-side refractive index [1]
    theta1: float = field(metadata=P.ic())   # incidence angle [rad]


class OpticsBaseline:
    def __init__(self, params: OpticsParams) -> None:
        if params.n1 <= 0 or params.n2 <= 0:
            raise ValueError("indices must be positive")
        self._params = params

    @property
    def params(self) -> OpticsParams:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        s2 = p.n1 / p.n2 * sin(p.theta1)
        theta2 = asin(s2) if -1.0 <= s2 <= 1.0 else nan
        return {"t": float(t), "theta1": float(p.theta1), "theta2": float(theta2)}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta1": "1"},
    "outputs": {"theta2": "1"},
    "params": {"n1": "1", "n2": "1"},
}


def law(inputs, p: OpticsParams) -> float:
    """Unified GT/oracle law: Snell refraction angle θ_t = asin((n1/n2)·sinθ1),
    clamped at total internal reflection."""
    s = (p.n1 / p.n2) * sin(inputs["theta1"])
    return asin(max(-1.0, min(1.0, s)))


CELL = CellSpec(
    domain="optics", shift="baseline",
    params_type=OpticsParams, law=law,
    output="theta2", broken_symmetry="none",
)
register_cell(CELL)
