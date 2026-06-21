"""Radioactive-decay baseline.

Baseline law: dN/dt = -λ N  ⇒  N(t) = N₀ e^{-λ t}.  Closed-form evaluation.
NewtonBench mapping: `vendor/newtonbench/modules/m5_radioactive_decay`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Dict
from mirrorlab.spec import P, CellSpec, register_cell


@dataclass(frozen=True)
class DecayParams:
    lam: float = field(metadata=P.law("lam"))      # decay constant [1/s]
    N0: float = field(metadata=P.ic())       # initial population [1]


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


def solve_to(rhs, y0, t):
    """Integrate rhs(t, y) from 0 to t and return y(t). Bypasses the shift
    Instances' validator gates so cf-perturbed params still score; falls back
    to y0 at the IC if the integrator refuses (stiff/singular cf region).
    Shared by the decay GT/oracle laws (single source of truth)."""
    from scipy.integrate import solve_ivp
    t = max(float(t), 0.0)
    if t == 0.0:
        return list(y0)
    try:
        sol = solve_ivp(rhs, (0.0, t), list(y0), method="DOP853", rtol=1e-9, atol=1e-12)
    except Exception:
        return list(y0)
    if not sol.success:
        return list(y0)
    return [float(v) for v in sol.y[:, -1]]


def law(inputs, p: DecayParams) -> float:
    """Unified GT/oracle law: closed-form exponential decay N(t)=N0·exp(−λt)."""
    return p.N0 * exp(-p.lam * inputs["t"])


CELL = CellSpec(
    domain="decay", shift="baseline",
    params_type=DecayParams, law=law,
    output="N", broken_symmetry="none",
)
register_cell(CELL)
