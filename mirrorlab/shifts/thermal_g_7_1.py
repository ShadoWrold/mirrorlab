"""γ-7-1 — Thermal constant-β anisotropic conductivity.

Catalog (Domain 7, Tier-1):
    q_i = -K_{ij} ∂_j T,  K_{ij} = k₀ [δ_{ij} + β n_i n_j]

Broken : SO(3) isotropy.
Retained: S-trans, T-trans, T→T+c, energy conservation (K symmetric PD,
          divergence form), Onsager, parabolic self-similar scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

K0_MIN, K0_MAX = 0.1, 50.0
BETA_MIN, BETA_MAX = 0.8, 5.0


@dataclass(frozen=True)
class ThermalGamma71Params:
    k0: float = field(metadata=P.law("k"))           # base conductivity [W/(m·K)]
    beta: float = field(metadata=P.law("beta"))         # anisotropy amplitude [1]
    n: Tuple[float, float, float] = field(metadata=P.ic())  # unit vector
    L: float = field(metadata=P.ic())            # slab thickness [m]
    T_hot: float = field(metadata=P.ic())        # K
    T_cold: float = field(metadata=P.ic())       # K
    grad_dir: Tuple[float, float, float] = field(default=(1.0, 0.0, 0.0), metadata=P.ic())  # ∇T direction


def _flux_components(params: ThermalGamma71Params) -> np.ndarray:
    n = np.asarray(params.n, dtype=float)
    d = np.asarray(params.grad_dir, dtype=float)
    K = params.k0 * (np.eye(3) + params.beta * np.outer(n, n))
    grad_T = (params.T_cold - params.T_hot) / params.L * d
    return -K @ grad_T


def shifted_flux_magnitude(params: ThermalGamma71Params) -> float:
    return float(np.linalg.norm(_flux_components(params)))


class ThermalGamma71Instance:
    def __init__(self, params: ThermalGamma71Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-7-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> ThermalGamma71Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        q = _flux_components(self._params)
        return {
            "t": float(t),
            "q_norm": float(np.linalg.norm(q)),
        }


def sampler(seed: int) -> ThermalGamma71Params:
    rng = np.random.default_rng(seed)
    k0 = float(np.exp(rng.uniform(np.log(K0_MIN), np.log(K0_MAX))))
    beta = float(np.exp(rng.uniform(np.log(BETA_MIN), np.log(BETA_MAX))))
    n = rng.standard_normal(3)
    n /= np.linalg.norm(n)
    return ThermalGamma71Params(
        k0=k0, beta=beta, n=tuple(float(x) for x in n),
        L=0.1, T_hot=373.0, T_cold=293.0,
    )


def validator(params: ThermalGamma71Params) -> bool:
    if not isinstance(params, ThermalGamma71Params):
        return False
    if not (K0_MIN <= params.k0 <= K0_MAX):
        return False
    if not (BETA_MIN <= params.beta <= BETA_MAX):
        return False
    if params.L <= 0:
        return False
    n_norm = float(np.linalg.norm(params.n))
    if abs(n_norm - 1.0) > 1e-6:
        return False
    return True


def build(*, params: ThermalGamma71Params | None = None, seed: int = 0) -> ThermalGamma71Instance:
    if params is None:
        params = sampler(seed)
    return ThermalGamma71Instance(params)


shift = ShiftImpl(law=lambda x, p: shifted_flux_magnitude(p), sampler=sampler, validator=validator)


def law(inputs, p: ThermalGamma71Params) -> float:
    """Unified GT/oracle law: anisotropic flux magnitude |K·∇T| with
    K=k₀(I+β·n̂n̂ᵀ). T_hot/T_cold/L and the gradient direction (dx,dy,dz) are
    swept grid inputs; fold them into the params and evaluate the magnitude."""
    from dataclasses import replace
    p_eff = replace(
        p,
        T_hot=inputs["T_hot"], T_cold=inputs["T_cold"], L=inputs["L"],
        grad_dir=(inputs["dx"], inputs["dy"], inputs["dz"]),
    )
    return shifted_flux_magnitude(p_eff)


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"T_hot": "K", "T_cold": "K", "L": "m"},
    "outputs": {"q_norm": "kg*s**-3"},
    "params": {"k0": "kg*m*s**-3*K**-1", "beta": "1", "n": "1"},
}

CELL = CellSpec(
    domain="thermal", shift="gamma_7_1",
    params_type=ThermalGamma71Params, law=law,
    sampler=sampler, validator=validator,
    output="q", broken_symmetry="ROT",
)
register_cell(CELL)

__all__ = [
    "ThermalGamma71Params", "ThermalGamma71Instance",
    "shifted_flux_magnitude", "law", "sampler", "validator", "build", "shift",
    "DIM_SIGNATURE", "CELL",
]
