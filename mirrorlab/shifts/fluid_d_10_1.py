"""δ-10-1 — Fluid: path-integral streamline loss.

Catalog (Domain 10, Tier-2):
    ½ ρ v² + ρ g h + p + ζ ∫_streamline |v - v_∞|^m ds = const

Broken : streamline energy (dissipative, T-rev bundled).
Retained: ∇·v=0, horizontal Galilean, T-trans, SO(3), h→h+c.

Minimal model: straight streamline of length L_path from inlet to probe;
v interpolated linearly between v1 and v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import quad

from mirrorlab.shifts import ShiftImpl

ZETA_MIN, ZETA_MAX = 1e-4, 1e-1
M_MIN, M_MAX = 1.5, 2.8


@dataclass(frozen=True)
class FluidDelta101Params:
    rho: float
    g: float
    h1: float
    v1: float
    p1: float
    h2: float
    v2: float
    zeta: float
    m: float
    v_inf: float
    L_path: float   # streamline length [m]


def _loss_integral(params: FluidDelta101Params) -> float:
    def integrand(s: float) -> float:
        v_s = params.v1 + (params.v2 - params.v1) * (s / params.L_path)
        return abs(v_s - params.v_inf) ** params.m

    val, _ = quad(integrand, 0.0, params.L_path, epsabs=1e-10, epsrel=1e-8)
    return val


def shifted_pressure(params: FluidDelta101Params) -> float:
    p = params
    loss = p.zeta * _loss_integral(p)
    return p.p1 + 0.5 * p.rho * (p.v1 ** 2 - p.v2 ** 2) + p.rho * p.g * (p.h1 - p.h2) - loss


class FluidDelta101Instance:
    def __init__(self, params: FluidDelta101Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-10-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> FluidDelta101Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "p2": float(shifted_pressure(self._params))}


def sampler(seed: int) -> FluidDelta101Params:
    rng = np.random.default_rng(seed)
    zeta = float(np.exp(rng.uniform(np.log(ZETA_MIN), np.log(ZETA_MAX))))
    m = float(rng.uniform(M_MIN, M_MAX))
    v_inf = float(rng.uniform(0.0, 2.0))
    rho = float(rng.uniform(800.0, 1200.0))
    return FluidDelta101Params(
        rho=rho, g=9.81, h1=2.0, v1=1.0, p1=1.01e5, h2=0.0, v2=3.0,
        zeta=zeta, m=m, v_inf=v_inf, L_path=1.0,
    )


def validator(params: FluidDelta101Params) -> bool:
    if not isinstance(params, FluidDelta101Params):
        return False
    if not (ZETA_MIN <= params.zeta <= ZETA_MAX):
        return False
    if not (M_MIN <= params.m <= M_MAX):
        return False
    if params.rho <= 0 or params.L_path <= 0:
        return False
    return True


def build(*, params: FluidDelta101Params | None = None, seed: int = 0) -> FluidDelta101Instance:
    if params is None:
        params = sampler(seed)
    return FluidDelta101Instance(params)


shift = ShiftImpl(law=lambda t, p: shifted_pressure(p), sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"v": "m*s**-1", "h": "m", "p": "kg*m**-1*s**-2"},
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "g": "m*s**-2", "zeta": "1", "m": "1", "v_inf": "m*s**-1"},
}

__all__ = [
    "FluidDelta101Params", "FluidDelta101Instance", "shifted_pressure",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
