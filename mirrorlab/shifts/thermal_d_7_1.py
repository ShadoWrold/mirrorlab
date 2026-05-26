"""δ-7-1 — Thermal quadratic-in-excess sink, comoving reference.

Catalog (Domain 7, Tier-2):
    ∂_t T = α ∇² T - λ (T - ⟨T⟩_Ω(t))² / T_ref

Broken : energy conservation (T-rev bundled per Part A convention).
Retained: SO(3), S-trans, T-trans (autonomous), T→T+c, Onsager.

Minimal 2-node lumped model: probe and reference, with sink referencing the
instantaneous mean ⟨T⟩ = (T_probe + T_ref_node)/2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl

LAM_MIN, LAM_MAX = 1e-5, 1e-2
T_REF_MIN, T_REF_MAX = 50.0, 1000.0


@dataclass(frozen=True)
class ThermalDelta71Params:
    alpha: float    # diffusivity [m²/s]
    lam: float      # sink rate [1/s]
    T_ref: float    # reference temperature [K]
    T_a: float      # initial probe-node temperature [K]
    T_b: float      # initial sister-node temperature [K]
    dx: float       # node spacing [m]


def _rhs(t: float, y: np.ndarray, p: ThermalDelta71Params) -> np.ndarray:
    Ta, Tb = y
    Tmean = 0.5 * (Ta + Tb)
    lap_a = (Tb - Ta) / (p.dx ** 2)
    lap_b = (Ta - Tb) / (p.dx ** 2)
    sink_a = -p.lam * (Ta - Tmean) ** 2 / p.T_ref
    sink_b = -p.lam * (Tb - Tmean) ** 2 / p.T_ref
    return np.array([p.alpha * lap_a + sink_a, p.alpha * lap_b + sink_b])


class ThermalDelta71Instance:
    def __init__(self, params: ThermalDelta71Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-7-1 params failed validator: {params!r}")
        self._params = params
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> ThermalDelta71Params:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params
        sol = solve_ivp(
            lambda t, y: _rhs(t, y, p), (0.0, t_max), [p.T_a, p.T_b],
            method="DOP853", rtol=1e-9, atol=1e-12, dense_output=True,
        )
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
        Ta, Tb = float(y[0]), float(y[1])
        return {"t": float(t), "T_a": Ta, "T_b": Tb, "T_mean": 0.5 * (Ta + Tb)}


def sampler(seed: int) -> ThermalDelta71Params:
    rng = np.random.default_rng(seed)
    lam = float(np.exp(rng.uniform(np.log(LAM_MIN), np.log(LAM_MAX))))
    T_ref = float(np.exp(rng.uniform(np.log(T_REF_MIN), np.log(T_REF_MAX))))
    return ThermalDelta71Params(
        alpha=1e-4, lam=lam, T_ref=T_ref, T_a=373.0, T_b=293.0, dx=0.1,
    )


def validator(params: ThermalDelta71Params) -> bool:
    if not isinstance(params, ThermalDelta71Params):
        return False
    if not (LAM_MIN <= params.lam <= LAM_MAX):
        return False
    if not (T_REF_MIN <= params.T_ref <= T_REF_MAX):
        return False
    if params.alpha <= 0 or params.dx <= 0:
        return False
    if params.T_a <= 0 or params.T_b <= 0:
        return False
    return True


def build(*, params: ThermalDelta71Params | None = None, seed: int = 0) -> ThermalDelta71Instance:
    if params is None:
        params = sampler(seed)
    return ThermalDelta71Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"T_a": "K", "T_b": "K"},
    "params": {"alpha": "m**2*s**-1", "lam": "s**-1", "T_ref": "K"},
}

__all__ = [
    "ThermalDelta71Params", "ThermalDelta71Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
