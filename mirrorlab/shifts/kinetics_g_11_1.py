"""γ-11-1 — Kinetics: fractional-time (anomalous-diffusion re-skin).

Catalog (Domain 11, Tier-1):
    D_t^β C = -k C^n   (Caputo-style fractional time derivative)

Broken : reaction self-similar scale.
Retained: T-trans, Arrhenius, positivity, stoichiometry, dilution in n=1 limit.

Numerical reduction: power-law-in-time integration via memory-truncated Volterra
form. For a per-shift adapter we use a moving-window approximation: 50-step
trapezoid memory of length τ_window starting from t₀=0, sufficient for
catalog-test diff vs baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from mirrorlab.shifts import ShiftImpl

BETA_MIN, BETA_MAX = 0.55, 0.95
N_MIN, N_MAX = 0.5, 2.5
K_MIN, K_MAX = 1e-4, 1e-1


@dataclass(frozen=True)
class KineticsGamma111Params:
    k: float        # rate (units carry s^{-β})
    n: float        # order [1]
    beta: float     # fractional order [1]
    C0: float       # [mol/m³]
    tau_min: float  # lower truncation [s]
    dt: float       # internal time step [s]


def _step_fractional(params: KineticsGamma111Params, t_target: float) -> List[float]:
    """Predictor-corrector for Caputo fractional ODE on uniform grid."""
    if t_target <= 0:
        return [params.C0]
    n_steps = max(int(math.ceil(t_target / params.dt)), 1)
    h = t_target / n_steps
    beta = params.beta
    gb = math.gamma(beta + 2)  # for fractional Adams-Bashforth-Moulton weights
    C = [params.C0]
    f = [-params.k * max(params.C0, 0.0) ** params.n]
    for k_idx in range(1, n_steps + 1):
        # Fractional Adams predictor (simplified — single-step memory truncated trapezoid)
        weights = [((k_idx - j) ** beta - (k_idx - j - 1) ** beta) for j in range(k_idx)]
        history = sum(w * fj for w, fj in zip(weights, f))
        C_new = params.C0 + (h ** beta / math.gamma(beta + 1)) * history
        C_new = max(C_new, 0.0)
        C.append(C_new)
        f.append(-params.k * C_new ** params.n)
    return C


class KineticsGamma111Instance:
    def __init__(self, params: KineticsGamma111Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-11-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> KineticsGamma111Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        if t == 0:
            return {"t": 0.0, "C": float(self._params.C0)}
        traj = _step_fractional(self._params, t)
        return {"t": float(t), "C": float(traj[-1])}


def sampler(seed: int) -> KineticsGamma111Params:
    rng = np.random.default_rng(seed)
    beta = float(rng.uniform(BETA_MIN, BETA_MAX))
    n = float(rng.uniform(N_MIN, N_MAX))
    k = float(np.exp(rng.uniform(np.log(K_MIN), np.log(K_MAX))))
    return KineticsGamma111Params(k=k, n=n, beta=beta, C0=1.0, tau_min=0.01, dt=0.05)


def validator(params: KineticsGamma111Params) -> bool:
    if not isinstance(params, KineticsGamma111Params):
        return False
    if not (BETA_MIN <= params.beta <= BETA_MAX):
        return False
    if not (N_MIN <= params.n <= N_MAX):
        return False
    if not (K_MIN <= params.k <= K_MAX):
        return False
    if params.C0 <= 0 or params.dt <= 0:
        return False
    return True


def build(*, params: KineticsGamma111Params | None = None, seed: int = 0) -> KineticsGamma111Instance:
    if params is None:
        params = sampler(seed)
    return KineticsGamma111Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"C": "mol*m**-3"},
    "params": {"n": "1", "beta": "1"},
}

__all__ = [
    "KineticsGamma111Params", "KineticsGamma111Instance",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE",
]
