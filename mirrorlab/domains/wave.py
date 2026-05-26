"""Scalar travelling-wave baseline (1-D, no dispersion).

Baseline law: u(x, t) = A sin(k x - ω t + φ), ω = c k.
`step(t)` evaluates at the probe point `params.x_probe`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from typing import Dict


@dataclass(frozen=True)
class WaveParams:
    A: float        # amplitude [m]
    k: float        # wavenumber [1/m]
    c: float        # phase speed [m/s]
    phi: float      # phase offset [rad]
    x_probe: float  # probe location [m]


class WaveBaseline:
    def __init__(self, params: WaveParams) -> None:
        if params.c <= 0 or params.k <= 0:
            raise ValueError("c, k must be positive")
        self._params = params

    @property
    def params(self) -> WaveParams:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        omega = p.c * p.k
        arg = p.k * p.x_probe - omega * t + p.phi
        u = p.A * sin(arg)
        du_dt = -p.A * omega * cos(arg)
        return {"t": float(t), "u": float(u), "du_dt": float(du_dt)}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "t": "s"},
    "outputs": {"u": "m"},
    "params": {"A": "m", "k": "m**-1", "c": "m*s**-1", "phi": "1"},
}
