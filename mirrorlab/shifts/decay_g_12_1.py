"""γ-12-1 — Decay: density-coupled decay rate (stimulated-emission re-skin).

Catalog (Domain 12, Tier-1):
    dN/dt = -λ N (1 + α (N/N₀)^p)

Broken : linearity N → aN.
Retained: T-trans, Markov, particle conservation in A→B chain, field-independence.

Half-life sampling logic preserved: when α=0, this reduces to baseline; the
sampler keeps λ on its baseline log-uniform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl

LAM_MIN, LAM_MAX = 1e-6, 1e-1
ALPHA_MIN, ALPHA_MAX = -0.4, 0.8
P_MIN, P_MAX = 0.3, 1.5
N0_MIN, N0_MAX = 1e3, 1e8


@dataclass(frozen=True)
class DecayGamma121Params:
    lam: float      # baseline rate [1/s]
    alpha: float    # nonlinearity amplitude [1]
    p: float        # power [1]
    N_scale: float  # internal density scale [1]
    N_init: float   # initial count [1]


class DecayGamma121Instance:
    def __init__(self, params: DecayGamma121Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-12-1 params failed validator: {params!r}")
        self._params = params
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> DecayGamma121Params:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            (N,) = y
            Ns = max(N, 0.0)
            return (-p.lam * Ns * (1.0 + p.alpha * (Ns / p.N_scale) ** p.p),)

        sol = solve_ivp(rhs, (0.0, t_max), [p.N_init], method="DOP853",
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
        N = float(self._sol.sol(t)[0])
        return {"t": float(t), "N": N}


def sampler(seed: int) -> DecayGamma121Params:
    rng = np.random.default_rng(seed)
    lam = float(np.exp(rng.uniform(np.log(LAM_MIN), np.log(LAM_MAX))))
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    p = float(rng.uniform(P_MIN, P_MAX))
    N_scale = float(np.exp(rng.uniform(np.log(N0_MIN), np.log(N0_MAX))))
    return DecayGamma121Params(lam=lam, alpha=alpha, p=p, N_scale=N_scale, N_init=1.0e6)


def validator(params: DecayGamma121Params) -> bool:
    if not isinstance(params, DecayGamma121Params):
        return False
    if not (LAM_MIN <= params.lam <= LAM_MAX):
        return False
    if not (ALPHA_MIN <= params.alpha <= ALPHA_MAX):
        return False
    if not (P_MIN <= params.p <= P_MAX):
        return False
    if not (N0_MIN <= params.N_scale <= N0_MAX):
        return False
    if params.N_init <= 0:
        return False
    return True


def build(*, params: DecayGamma121Params | None = None, seed: int = 0) -> DecayGamma121Instance:
    if params is None:
        params = sampler(seed)
    return DecayGamma121Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"N": "1"},
    "params": {"lam": "s**-1", "alpha": "1", "p": "1", "N_scale": "1"},
}

__all__ = [
    "DecayGamma121Params", "DecayGamma121Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
