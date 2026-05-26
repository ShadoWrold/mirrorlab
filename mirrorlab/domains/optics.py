"""Geometric optics (Snell) baseline.

Baseline law: n₁ sin θ₁ = n₂ sin θ₂.  Algebraic — `step(t)` ignores `t` and
returns the refracted angle for the configured incidence.
NewtonBench mapping: `vendor/newtonbench/modules/m4_snell_law`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, nan, sin
from typing import Dict


@dataclass(frozen=True)
class OpticsParams:
    n1: float       # incident-side refractive index [1]
    n2: float       # transmitted-side refractive index [1]
    theta1: float   # incidence angle [rad]


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
