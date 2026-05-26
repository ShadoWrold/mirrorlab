"""Radioactive-decay baseline.

Baseline law: dN/dt = -λ N  ⇒  N(t) = N₀ e^{-λ t}.  Closed-form evaluation.
NewtonBench mapping: `vendor/newtonbench/modules/m5_radioactive_decay`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Dict


@dataclass(frozen=True)
class DecayParams:
    lam: float      # decay constant [1/s]
    N0: float       # initial population [1]


class DecayBaseline:
    def __init__(self, params: DecayParams) -> None:
        if params.lam < 0 or params.N0 < 0:
            raise ValueError("lam, N0 must be non-negative")
        self._params = params

    @property
    def params(self) -> DecayParams:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        N = p.N0 * exp(-p.lam * t)
        return {"t": float(t), "N": float(N), "rate": float(-p.lam * N)}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"N": "1", "rate": "s**-1"},
    "params": {"lam": "s**-1", "N0": "1"},
}
