"""γ-8-2 — Scalar wave: 2D anisotropic phase speed (dielectric tensor re-skin).

Catalog (Domain 8, Tier-1):
    ∂_t² u = c² ∂_i (M_{ij} ∂_j u),
    M = R(θ₀) · diag(1, 1+β) · R(θ₀)ᵀ

Broken : SO(2) planar rotation.
Retained: T-trans, S-trans, parity, T-rev, energy.

Plane wave with k = |k|(cos θ_k, sin θ_k): ω² = c² k_i M_{ij} k_j.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

BETA_MIN, BETA_MAX = 0.1, 0.8
C_MIN, C_MAX = 50.0, 5000.0


@dataclass(frozen=True)
class WaveGamma82Params:
    A: float        # amplitude [m]
    k: float        # wavenumber magnitude [1/m]
    theta_k: float  # propagation angle [rad]
    c: float        # base phase speed [m/s]
    beta: float     # anisotropy [1]
    theta0: float   # principal axis [rad]
    x_probe: float  # probe location along propagation [m]


def _M_matrix(beta: float, theta0: float) -> np.ndarray:
    R = np.array([[math.cos(theta0), -math.sin(theta0)],
                  [math.sin(theta0), math.cos(theta0)]])
    D = np.diag([1.0, 1.0 + beta])
    return R @ D @ R.T


def shifted_omega_squared(params: WaveGamma82Params) -> float:
    M = _M_matrix(params.beta, params.theta0)
    k_vec = params.k * np.array([math.cos(params.theta_k), math.sin(params.theta_k)])
    return float((params.c ** 2) * (k_vec @ M @ k_vec))


class WaveGamma82Instance:
    def __init__(self, params: WaveGamma82Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-8-2 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> WaveGamma82Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        omega = math.sqrt(max(shifted_omega_squared(p), 0.0))
        arg = p.k * p.x_probe - omega * t
        u = p.A * math.sin(arg)
        return {"t": float(t), "u": float(u)}


def sampler(seed: int) -> WaveGamma82Params:
    rng = np.random.default_rng(seed)
    beta = float(rng.uniform(BETA_MIN, BETA_MAX))
    theta0 = float(rng.uniform(0.0, math.pi))
    theta_k = float(rng.uniform(0.0, math.pi))
    c = float(np.exp(rng.uniform(np.log(C_MIN), np.log(C_MAX))))
    return WaveGamma82Params(
        A=0.1, k=2.0, theta_k=theta_k, c=c, beta=beta, theta0=theta0, x_probe=0.5,
    )


def validator(params: WaveGamma82Params) -> bool:
    if not isinstance(params, WaveGamma82Params):
        return False
    if not (BETA_MIN <= params.beta <= BETA_MAX):
        return False
    if not (C_MIN <= params.c <= C_MAX):
        return False
    if params.k <= 0 or params.A <= 0:
        return False
    return True


def build(*, params: WaveGamma82Params | None = None, seed: int = 0) -> WaveGamma82Instance:
    if params is None:
        params = sampler(seed)
    return WaveGamma82Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "t": "s"},
    "outputs": {"u": "m"},
    "params": {"A": "m", "k": "m**-1", "c": "m*s**-1", "beta": "1", "theta0": "1"},
}

__all__ = [
    "WaveGamma82Params", "WaveGamma82Instance", "shifted_omega_squared",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
