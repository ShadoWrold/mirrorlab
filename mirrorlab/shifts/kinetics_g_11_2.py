"""γ-11-2 — Kinetics: density-saturating rate.

Catalog (Domain 11, Tier-1):
    dC/dt = -k C^n / (1 + (C/C_sat)^m)

Broken : dilution self-similar scale C → λC.
Retained: T-trans, Arrhenius, stoichiometry, positivity, dim homogeneity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl

N_MIN, N_MAX = 1.0, 3.0
M_MIN, M_MAX = 0.5, 3.0
C_SAT_MIN, C_SAT_MAX = 1.0, 1e4
K_MIN, K_MAX = 1e-4, 1e-1


@dataclass(frozen=True)
class KineticsGamma112Params:
    k: float
    n: float
    m: float
    C_sat: float
    C0: float


class KineticsGamma112Instance:
    def __init__(self, params: KineticsGamma112Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-11-2 params failed validator: {params!r}")
        self._params = params
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> KineticsGamma112Params:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            (C,) = y
            Cs = max(C, 0.0)
            return (-p.k * Cs ** p.n / (1.0 + (Cs / p.C_sat) ** p.m),)

        sol = solve_ivp(rhs, (0.0, t_max), [p.C0], method="DOP853",
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
        C = float(self._sol.sol(t)[0])
        return {"t": float(t), "C": C}


def sampler(seed: int) -> KineticsGamma112Params:
    rng = np.random.default_rng(seed)
    n = float(rng.uniform(N_MIN, N_MAX))
    # ensure m < n + 1 for high-C asymptotic well-posedness
    m = float(rng.uniform(M_MIN, min(M_MAX, n + 1.0 - 1e-3)))
    C_sat = float(np.exp(rng.uniform(np.log(C_SAT_MIN), np.log(C_SAT_MAX))))
    k = float(np.exp(rng.uniform(np.log(K_MIN), np.log(K_MAX))))
    return KineticsGamma112Params(k=k, n=n, m=m, C_sat=C_sat, C0=1.0)


def validator(params: KineticsGamma112Params) -> bool:
    if not isinstance(params, KineticsGamma112Params):
        return False
    if not (N_MIN <= params.n <= N_MAX):
        return False
    if not (M_MIN <= params.m <= M_MAX):
        return False
    if not (C_SAT_MIN <= params.C_sat <= C_SAT_MAX):
        return False
    if not (K_MIN <= params.k <= K_MAX):
        return False
    if params.C0 <= 0:
        return False
    if params.m >= params.n + 1.0:
        return False
    return True


def build(*, params: KineticsGamma112Params | None = None, seed: int = 0) -> KineticsGamma112Instance:
    if params is None:
        params = sampler(seed)
    return KineticsGamma112Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"C": "mol*m**-3"},
    "params": {"n": "1", "m": "1", "C_sat": "mol*m**-3"},
}

__all__ = [
    "KineticsGamma112Params", "KineticsGamma112Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
