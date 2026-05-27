"""γ-8-1 — Scalar wave: third-order chiral dispersion (KdV-linear motif).

Catalog (Domain 8, Tier-1):
    ∂_t² u = c² ∂_x² u + γ c² ∂_x³ u

Broken : parity x→-x (∂_x³ is odd).
Retained: T-trans, S-trans, T-rev (terms even in t), energy (Hamiltonian
          conservative dispersion), linear superposition.

Plane-wave reduction: u = A sin(k x - ω t), ω² = c² k² (1 + γ k); evaluate at probe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

GAMMA_MIN, GAMMA_MAX = 1e-4, 1e-1
C_MIN, C_MAX = 50.0, 5000.0


@dataclass(frozen=True)
class WaveGamma81Params:
    A: float        # amplitude [m]
    k: float        # wavenumber [1/m]
    c: float        # phase speed [m/s]
    gamma: float    # dispersion length [m] (signed)
    x_probe: float  # probe location [m]


def shifted_omega_squared(params: WaveGamma81Params) -> float:
    return (params.c * params.k) ** 2 * (1.0 + params.gamma * params.k)


class WaveGamma81Instance:
    def __init__(self, params: WaveGamma81Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-8-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> WaveGamma81Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        w2 = shifted_omega_squared(p)
        omega = math.sqrt(max(w2, 0.0))
        arg = p.k * p.x_probe - omega * t
        u = p.A * math.sin(arg)
        du_dt = -p.A * omega * math.cos(arg)
        return {"t": float(t), "u": float(u), "du_dt": float(du_dt)}


def sampler(seed: int) -> WaveGamma81Params:
    rng = np.random.default_rng(seed)
    L0 = float(np.exp(rng.uniform(np.log(GAMMA_MIN), np.log(GAMMA_MAX))))
    gamma = float(rng.uniform(-L0, L0))
    c = float(np.exp(rng.uniform(np.log(C_MIN), np.log(C_MAX))))
    return WaveGamma81Params(A=0.1, k=2.0, c=c, gamma=gamma, x_probe=0.5)


def validator(params: WaveGamma81Params) -> bool:
    if not isinstance(params, WaveGamma81Params):
        return False
    if abs(params.gamma) > GAMMA_MAX:
        return False
    if not (C_MIN <= params.c <= C_MAX):
        return False
    if params.k <= 0 or params.A <= 0:
        return False
    if 1.0 + params.gamma * params.k <= 0:
        return False
    return True


def build(*, params: WaveGamma81Params | None = None, seed: int = 0) -> WaveGamma81Instance:
    if params is None:
        params = sampler(seed)
    return WaveGamma81Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "t": "s"},
    "outputs": {"u": "m"},
    "params": {"A": "m", "k": "m**-1", "c": "m*s**-1", "gamma": "m"},
}

__all__ = [
    "WaveGamma81Params", "WaveGamma81Instance", "shifted_omega_squared",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
