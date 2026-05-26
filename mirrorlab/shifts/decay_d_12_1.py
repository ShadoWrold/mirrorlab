"""δ-12-1 — Decay: branching loss to dark channel.

Catalog (Domain 12, Tier-2):
    dN_A/dt = -λ N_A,  dN_B/dt = +(1-ξ) λ N_A

Broken : particle conservation (N_A + N_B ≠ const).
Retained: T-trans, Markov, linearity N → aN, field-independence.

Paired with Part A δ-5-1 / Part B δ-11-1. Coordinate w/ domain-engineer-A.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

LAM_MIN, LAM_MAX = 1e-6, 1e-1
XI_MIN, XI_MAX = 0.05, 0.45


@dataclass(frozen=True)
class DecayDelta121Params:
    lam: float
    xi: float       # dark-channel branching ratio [1]
    N_A0: float
    N_B0: float


class DecayDelta121Instance:
    def __init__(self, params: DecayDelta121Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-12-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> DecayDelta121Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        N_A = p.N_A0 * math.exp(-p.lam * t)
        N_B = p.N_B0 + (1.0 - p.xi) * (p.N_A0 - N_A)
        return {"t": float(t), "N_A": float(N_A), "N_B": float(N_B)}


def sampler(seed: int) -> DecayDelta121Params:
    rng = np.random.default_rng(seed)
    lam = float(np.exp(rng.uniform(np.log(LAM_MIN), np.log(LAM_MAX))))
    xi = float(rng.uniform(XI_MIN, XI_MAX))
    return DecayDelta121Params(lam=lam, xi=xi, N_A0=1.0e6, N_B0=0.0)


def validator(params: DecayDelta121Params) -> bool:
    if not isinstance(params, DecayDelta121Params):
        return False
    if not (LAM_MIN <= params.lam <= LAM_MAX):
        return False
    if not (XI_MIN <= params.xi <= XI_MAX):
        return False
    if params.N_A0 <= 0:
        return False
    return True


def build(*, params: DecayDelta121Params | None = None, seed: int = 0) -> DecayDelta121Instance:
    if params is None:
        params = sampler(seed)
    return DecayDelta121Instance(params)


shift = ShiftImpl(law=lambda t, p: p.lam, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"N_A": "1", "N_B": "1"},
    "params": {"lam": "s**-1", "xi": "1"},
}

__all__ = [
    "DecayDelta121Params", "DecayDelta121Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
