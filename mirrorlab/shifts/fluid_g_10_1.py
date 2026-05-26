"""γ-10-1 — Fluid: anisotropic kinetic inertia (effective-mass tensor re-skin).

Catalog (Domain 10, Tier-1):
    Bernoulli: ½ v_i M_{ij} v_j + ρ g h + p = const
    M_{ij} = ρ [δ_{ij} + α (n_i n_j - δ_{ij}/3)]   (traceless anisotropy)

Broken : SO(3) isotropy.
Retained: ∇·v=0, horizontal Galilean, h→h+c, T-trans (steady), streamline E,
          inviscid reversibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from mirrorlab.shifts import ShiftImpl

ALPHA_MIN, ALPHA_MAX = -0.4, 1.4
RHO_MIN, RHO_MAX = 50.0, 5e3


@dataclass(frozen=True)
class FluidGamma101Params:
    rho: float                    # [kg/m³]
    alpha: float                  # [1]
    n: Tuple[float, float, float] # unit vector
    g: float                      # [m/s²]
    h1: float                     # [m]
    p1: float                     # [Pa]
    v1: Tuple[float, float, float]  # upstream velocity
    h2: float
    v2: Tuple[float, float, float]


def _M_over_rho(params: FluidGamma101Params) -> np.ndarray:
    n = np.asarray(params.n, dtype=float)
    return np.eye(3) + params.alpha * (np.outer(n, n) - np.eye(3) / 3.0)


def shifted_pressure(params: FluidGamma101Params) -> float:
    """Bernoulli closure: p2 = p1 + ½(v1·M·v1 - v2·M·v2)/ρ·ρ + ρ g (h1-h2)."""
    Mor = _M_over_rho(params)
    v1 = np.asarray(params.v1, dtype=float)
    v2 = np.asarray(params.v2, dtype=float)
    ke1 = 0.5 * params.rho * (v1 @ Mor @ v1)
    ke2 = 0.5 * params.rho * (v2 @ Mor @ v2)
    return params.p1 + (ke1 - ke2) + params.rho * params.g * (params.h1 - params.h2)


class FluidGamma101Instance:
    def __init__(self, params: FluidGamma101Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-10-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> FluidGamma101Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "p2": float(shifted_pressure(self._params))}


def sampler(seed: int) -> FluidGamma101Params:
    rng = np.random.default_rng(seed)
    rho = float(np.exp(rng.uniform(np.log(RHO_MIN), np.log(RHO_MAX))))
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    n = rng.standard_normal(3)
    n /= np.linalg.norm(n)
    return FluidGamma101Params(
        rho=rho, alpha=alpha, n=tuple(float(x) for x in n),
        g=9.81, h1=2.0, p1=1.01e5,
        v1=(1.0, 0.0, 0.0), h2=0.0, v2=(3.0, 0.0, 0.0),
    )


def validator(params: FluidGamma101Params) -> bool:
    if not isinstance(params, FluidGamma101Params):
        return False
    if not (ALPHA_MIN <= params.alpha <= ALPHA_MAX):
        return False
    if not (RHO_MIN <= params.rho <= RHO_MAX):
        return False
    n_norm = float(np.linalg.norm(params.n))
    if abs(n_norm - 1.0) > 1e-6:
        return False
    # M/ρ positive-definite: eigenvalues are 1 - α/3 (perp, mult 2) and 1 + 2α/3 (along n).
    if 1.0 - params.alpha / 3.0 <= 0:
        return False
    if 1.0 + 2.0 * params.alpha / 3.0 <= 0:
        return False
    return True


def build(*, params: FluidGamma101Params | None = None, seed: int = 0) -> FluidGamma101Instance:
    if params is None:
        params = sampler(seed)
    return FluidGamma101Instance(params)


shift = ShiftImpl(law=lambda t, p: shifted_pressure(p), sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"v": "m*s**-1", "h": "m", "p": "kg*m**-1*s**-2"},
    "outputs": {"p2": "kg*m**-1*s**-2"},
    "params": {"rho": "kg*m**-3", "alpha": "1", "g": "m*s**-2"},
}

__all__ = [
    "FluidGamma101Params", "FluidGamma101Instance", "shifted_pressure",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
