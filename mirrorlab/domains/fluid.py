"""Inviscid incompressible fluid baseline (Bernoulli along a streamline).

Baseline law: p + ½ρv² + ρgh = const.  Given (ρ, g, h1, v1, p1, h2, v2),
`step(t)` returns p2 along the streamline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class FluidParams:
    rho: float      # density [kg/m³]
    g: float        # gravitational acceleration [m/s²]
    h1: float       # upstream elevation [m]
    v1: float       # upstream speed [m/s]
    p1: float       # upstream pressure [Pa]
    h2: float       # downstream elevation [m]
    v2: float       # downstream speed [m/s]


def baseline_pressure(params: FluidParams) -> float:
    p = params
    return p.p1 + 0.5 * p.rho * (p.v1 * p.v1 - p.v2 * p.v2) + p.rho * p.g * (p.h1 - p.h2)


class FluidBaseline:
    def __init__(self, params: FluidParams) -> None:
        if params.rho <= 0:
            raise ValueError("density must be positive")
        self._params = params

    @property
    def params(self) -> FluidParams:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "p2": float(baseline_pressure(self._params))}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"v": "m*s**-1", "h": "m", "p": "kg*m**-1*s**-2"},
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "g": "m*s**-2"},
}
