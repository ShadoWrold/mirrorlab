"""1-D Fourier heat-conduction baseline (steady-state algebraic law).

Baseline law: q = -k · ΔT / L (heat flux through a slab).  Algebraic — `step(t)`
ignores `t` and returns the flux given the current params.
NewtonBench mapping: `vendor/newtonbench/modules/m3_fourier_law`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThermalParams:
    k: float        # thermal conductivity [W/(m·K)]
    L: float        # slab thickness [m]
    T_hot: float    # hot-side temperature [K]
    T_cold: float   # cold-side temperature [K]


def baseline_flux(params: ThermalParams) -> float:
    return -params.k * (params.T_cold - params.T_hot) / params.L


class ThermalBaseline:
    def __init__(self, params: ThermalParams) -> None:
        if params.L <= 0 or params.k <= 0:
            raise ValueError("L, k must be positive")
        self._params = params

    @property
    def params(self) -> ThermalParams:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "q": float(baseline_flux(self._params))}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"T_hot": "K", "T_cold": "K", "L": "m"},
    "outputs": {"q": "kg*s**-3"},
    "params": {"k": "kg*m*s**-3*K**-1"},
}
