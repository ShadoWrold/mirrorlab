"""Inviscid incompressible fluid baseline (Bernoulli along a streamline).

Baseline law: p + ½ρv² + ρgh = const.  Given (ρ, g, h1, v1, p1, h2, v2),
`step(t)` returns p2 along the streamline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict
from mirrorlab.spec import P, CellSpec, register_cell


@dataclass(frozen=True)
class FluidParams:
    rho: float = field(metadata=P.law("rho"))      # density [kg/m³]
    g: float = field(metadata=P.law("g"))        # gravitational acceleration [m/s²]
    h1: float = field(metadata=P.ic())       # upstream elevation [m]
    v1: float = field(metadata=P.ic())       # upstream speed [m/s]
    p1: float = field(metadata=P.ic())       # upstream pressure [Pa]
    h2: float = field(metadata=P.ic())       # downstream elevation [m]
    v2: float = field(metadata=P.ic())       # downstream speed [m/s]


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
    # Inputs name the upstream/downstream station variables the loader grid
    # actually feeds (p1, v1, v2, h1, h2), not the unscripted {v, h, p}. The
    # output p2 (downstream pressure) was already correct.
    "inputs": {
        "p1": "kg*m**-1*s**-2", "v1": "m*s**-1", "v2": "m*s**-1",
        "h1": "m", "h2": "m",
    },
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "g": "m*s**-2"},
}


def law(inputs, p: FluidParams) -> float:
    """Unified GT/oracle law: Bernoulli downstream pressure
    p2 = p1 + ½ρ(v1²−v2²) + ρg(h1−h2). p1/v1/v2/h1/h2 are swept grid inputs."""
    p1, v1, v2, h1, h2 = (inputs[k] for k in ("p1", "v1", "v2", "h1", "h2"))
    return p1 + 0.5 * p.rho * (v1 * v1 - v2 * v2) + p.rho * p.g * (h1 - h2)


CELL = CellSpec(
    domain="fluid", shift="baseline",
    params_type=FluidParams, law=law,
    output="p2", break_type="none",
)
register_cell(CELL)
