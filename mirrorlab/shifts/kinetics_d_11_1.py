"""δ-11-1 — Kinetics: branching loss to hidden channel.

Catalog (Domain 11, Tier-2):
    dC_A/dt = -k C_A^n,  dC_B/dt = +η · k C_A^n,  η ≠ 1

Broken : stoichiometry (C_A + C_B ≠ const).
Retained: T-trans, Arrhenius, positivity, dilution in n=1 limit, dim homogeneity.

Paired with Part A δ-5-1 (Q leakage). Coordinate w/ domain-engineer-A.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl

N_MIN, N_MAX = 0.8, 2.0
K_MIN, K_MAX = 1e-4, 1e-1


@dataclass(frozen=True)
class KineticsDelta111Params:
    k: float
    n: float
    eta: float      # ≠ 1
    C_A0: float
    C_B0: float


class KineticsDelta111Instance:
    def __init__(self, params: KineticsDelta111Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-11-1 params failed validator: {params!r}")
        self._params = params
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> KineticsDelta111Params:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            CA, CB = y
            r = p.k * max(CA, 0.0) ** p.n
            return (-r, p.eta * r)

        sol = solve_ivp(rhs, (0.0, t_max), [p.C_A0, p.C_B0], method="DOP853",
                        rtol=1e-9, atol=1e-12, dense_output=True)
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
        return {"t": float(t), "C_A": float(y[0]), "C_B": float(y[1])}


def sampler(seed: int) -> KineticsDelta111Params:
    rng = np.random.default_rng(seed)
    n = float(rng.uniform(N_MIN, N_MAX))
    k = float(np.exp(rng.uniform(np.log(K_MIN), np.log(K_MAX))))
    # two-segment η excluding [0.95, 1.05]
    if rng.random() < 0.5:
        eta = float(rng.uniform(0.55, 0.95))
    else:
        eta = float(rng.uniform(1.05, 1.45))
    return KineticsDelta111Params(k=k, n=n, eta=eta, C_A0=1.0, C_B0=0.0)


def validator(params: KineticsDelta111Params) -> bool:
    if not isinstance(params, KineticsDelta111Params):
        return False
    if not (N_MIN <= params.n <= N_MAX):
        return False
    if not (K_MIN <= params.k <= K_MAX):
        return False
    if 0.95 <= params.eta <= 1.05:
        return False
    if not (0.55 <= params.eta <= 1.45):
        return False
    if params.C_A0 <= 0:
        return False
    return True


def build(*, params: KineticsDelta111Params | None = None, seed: int = 0) -> KineticsDelta111Instance:
    if params is None:
        params = sampler(seed)
    return KineticsDelta111Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"C_A": "mol*m**-3", "C_B": "mol*m**-3"},
    "params": {"n": "1", "eta": "1"},
}

__all__ = [
    "KineticsDelta111Params", "KineticsDelta111Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
