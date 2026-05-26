"""γ-12-2 — Decay: parametric-modulated decay rate (pendulum / RLC motif).

Catalog (Domain 12, Tier-1):
    dN/dt = -λ(t) N,  λ(t) = λ₀ [1 + ε cos(ω t)]   (φ ≡ 0 ⇒ T-rev preserved)

Broken : T-trans.
Retained: linearity in N, Markov, particle conservation in A→B chain, T-rev.

Paired with Part A δ-4-1 / δ-6-1 (parametric drives). Coordinate w/ domain-engineer-A.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

LAM0_MIN, LAM0_MAX = 1e-6, 1e-1
EPS_MIN, EPS_MAX = 0.05, 0.40
OMEGA_MIN, OMEGA_MAX = 1e-3, 1.0


@dataclass(frozen=True)
class DecayGamma122Params:
    lam0: float
    eps: float
    omega: float
    N_init: float


def _integrated_rate(t: float, params: DecayGamma122Params) -> float:
    """∫₀ᵗ λ(s) ds = λ₀ [t + (ε/ω) sin(ω t)]  (closed form)."""
    return params.lam0 * (t + (params.eps / params.omega) * math.sin(params.omega * t))


class DecayGamma122Instance:
    def __init__(self, params: DecayGamma122Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-12-2 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> DecayGamma122Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        N = p.N_init * math.exp(-_integrated_rate(t, p))
        lam_t = p.lam0 * (1.0 + p.eps * math.cos(p.omega * t))
        return {"t": float(t), "N": float(N), "lam_t": float(lam_t)}


def sampler(seed: int) -> DecayGamma122Params:
    rng = np.random.default_rng(seed)
    lam0 = float(np.exp(rng.uniform(np.log(LAM0_MIN), np.log(LAM0_MAX))))
    eps = float(rng.uniform(EPS_MIN, EPS_MAX))
    omega = float(np.exp(rng.uniform(np.log(OMEGA_MIN), np.log(OMEGA_MAX))))
    return DecayGamma122Params(lam0=lam0, eps=eps, omega=omega, N_init=1.0e6)


def validator(params: DecayGamma122Params) -> bool:
    if not isinstance(params, DecayGamma122Params):
        return False
    if not (LAM0_MIN <= params.lam0 <= LAM0_MAX):
        return False
    if not (EPS_MIN <= params.eps <= EPS_MAX):
        return False
    if not (OMEGA_MIN <= params.omega <= OMEGA_MAX):
        return False
    if params.eps >= 0.5:
        return False   # λ(t) > 0 ∀t
    if params.N_init <= 0:
        return False
    return True


def build(*, params: DecayGamma122Params | None = None, seed: int = 0) -> DecayGamma122Instance:
    if params is None:
        params = sampler(seed)
    return DecayGamma122Instance(params)


shift = ShiftImpl(law=lambda t, p: p.lam0 * (1.0 + p.eps * math.cos(p.omega * t)),
                  sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"N": "1"},
    "params": {"lam0": "s**-1", "eps": "1", "omega": "s**-1"},
}

__all__ = [
    "DecayGamma122Params", "DecayGamma122Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
