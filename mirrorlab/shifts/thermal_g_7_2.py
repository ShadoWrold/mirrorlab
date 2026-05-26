"""γ-7-2 — Thermal power-law memory kernel.

Catalog (Domain 7, Tier-1):
    q(t) = -∫_{t₀}^{t} G(t-s) ∂_x T(s) ds,  G(τ) = k₀ τ^{-p} / Γ(1-p)

Broken : parabolic self-similar scale (kernel introduces non-classical exponent).
Retained: T-trans, SO(3), S-trans, T→T+c, energy/Onsager (divergence form).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

P_MIN, P_MAX = 0.10, 0.55
K0_MIN, K0_MAX = 0.1, 50.0


@dataclass(frozen=True)
class ThermalGamma72Params:
    k0: float       # base conductivity scale [W/(m·K)·s^{p-1}]
    p: float        # memory exponent [1]
    L: float        # slab thickness [m]
    T_hot: float    # K
    T_cold: float   # K
    tau_min: float  # lower truncation [s]


def shifted_flux(t: float, params: ThermalGamma72Params) -> float:
    """Steady ∂_x T ⇒ q(t) = -k₀ ΔT/L · ∫_{tau_min}^{t} τ^{-p}/Γ(1-p) dτ."""
    if t <= params.tau_min:
        return 0.0
    grad = (params.T_cold - params.T_hot) / params.L
    integral = (t ** (1 - params.p) - params.tau_min ** (1 - params.p)) / (1 - params.p)
    return -params.k0 * grad * integral / math.gamma(1 - params.p)


class ThermalGamma72Instance:
    def __init__(self, params: ThermalGamma72Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-7-2 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> ThermalGamma72Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        return {"t": float(t), "q": float(shifted_flux(t, self._params))}


def sampler(seed: int) -> ThermalGamma72Params:
    rng = np.random.default_rng(seed)
    p = float(rng.uniform(P_MIN, P_MAX))
    k0 = float(np.exp(rng.uniform(np.log(K0_MIN), np.log(K0_MAX))))
    return ThermalGamma72Params(
        k0=k0, p=p, L=0.1, T_hot=373.0, T_cold=293.0, tau_min=1e-3,
    )


def validator(params: ThermalGamma72Params) -> bool:
    if not isinstance(params, ThermalGamma72Params):
        return False
    if not (P_MIN <= params.p <= P_MAX):
        return False
    if not (K0_MIN <= params.k0 <= K0_MAX):
        return False
    if params.L <= 0 or params.tau_min <= 0:
        return False
    return True


def build(*, params: ThermalGamma72Params | None = None, seed: int = 0) -> ThermalGamma72Instance:
    if params is None:
        params = sampler(seed)
    return ThermalGamma72Instance(params)


shift = ShiftImpl(law=shifted_flux, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"T_hot": "K", "T_cold": "K", "L": "m", "t": "s"},
    "outputs": {"q": "kg*s**-3"},
    "params": {"k0": "kg*m*s**-3*K**-1", "p": "1", "tau_min": "s"},
}

__all__ = [
    "ThermalGamma72Params", "ThermalGamma72Instance", "shifted_flux",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
