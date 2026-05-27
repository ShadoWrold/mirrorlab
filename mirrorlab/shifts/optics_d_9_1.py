"""δ-9-1 — Snell: angle-power energy non-balance.

Catalog (Domain 9, Tier-2):
    angles: Snell baseline preserved.
    intensities: R + T = 1 - ξ |sin θ_i|^p

Broken : energy conservation (R + T ≠ 1).
Retained: Snell angle law, reciprocity, SO(2), Fermat, tangential k_∥,
          polarization U(1), 1↔2 interchange.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, nan, sin
from typing import Dict

import numpy as np

from mirrorlab.shifts import ShiftImpl

XI_LO, XI_HI = -0.15, 0.40
P_MIN, P_MAX = 1.2, 3.0


@dataclass(frozen=True)
class OpticsDelta91Params:
    n1: float
    n2: float
    theta_i: float  # [rad]
    xi: float       # leakage amplitude [1]
    p: float        # angle-power exponent [1]


class OpticsDelta91Instance:
    def __init__(self, params: OpticsDelta91Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-9-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> OpticsDelta91Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        s2 = p.n1 / p.n2 * sin(p.theta_i)
        theta_t = asin(s2) if -1.0 <= s2 <= 1.0 else nan
        return {
            "t": float(t),
            "theta_i": float(p.theta_i),
            "theta_t": float(theta_t),
        }


def sampler(seed: int) -> OpticsDelta91Params:
    rng = np.random.default_rng(seed)
    n1 = float(rng.uniform(1.0, 2.0))
    n2 = float(rng.uniform(1.0, 2.0))
    xi = float(rng.uniform(XI_LO, XI_HI))
    p = float(rng.uniform(P_MIN, P_MAX))
    return OpticsDelta91Params(n1=n1, n2=n2, theta_i=0.3, xi=xi, p=p)


def validator(params: OpticsDelta91Params) -> bool:
    if not isinstance(params, OpticsDelta91Params):
        return False
    if not (XI_LO <= params.xi <= XI_HI):
        return False
    if not (P_MIN <= params.p <= P_MAX):
        return False
    if params.n1 <= 0 or params.n2 <= 0:
        return False
    return True


def build(*, params: OpticsDelta91Params | None = None, seed: int = 0) -> OpticsDelta91Instance:
    if params is None:
        params = sampler(seed)
    return OpticsDelta91Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta_i": "1"},
    "outputs": {"theta_t": "1"},
    "params": {"n1": "1", "n2": "1", "xi": "1", "p": "1"},
}

__all__ = [
    "OpticsDelta91Params", "OpticsDelta91Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
