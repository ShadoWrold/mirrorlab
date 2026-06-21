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
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

BETA_MIN, BETA_MAX = 0.55, 0.80
N_MIN, N_MAX = 0.5, 2.5
K_MIN, K_MAX = 1e-4, 1e-1


@dataclass(frozen=True)
class KineticsGamma111Params:
    k: float = field(metadata=P.law("k"))        # rate (units carry s^{-β})
    n: float = field(metadata=P.law("n"))        # order [1]
    beta: float = field(metadata=P.law("beta"))     # fractional order [1]
    C0: float = field(metadata=P.ic())       # [mol/m³]
    tau_min: float = field(metadata=P.ic())  # lower truncation [s]
    dt: float = field(metadata=P.ic())       # internal time step [s]


def _step_fractional(params: KineticsGamma111Params, t_target: float) -> List[float]:
    """Predictor-corrector for Caputo fractional ODE on uniform grid."""
    if t_target <= 0:
        return [params.C0]
    # Hard cap on the step count. The scheme is O(n_steps²) (each step builds
    # an n-length weight history), so an agent tool call that asks for a
    # measurement at a large t with a small dt — or a counterfactual-perturbed
    # dt — could blow n_steps up and wedge the process at 100% CPU. Capping
    # here protects every caller (sandbox measurement tools, the GT builder,
    # and the oracle), coarsening the grid instead of hanging.
    _MAX_STEPS = 2000
    n_steps = max(int(math.ceil(t_target / params.dt)), 1)
    n_steps = min(n_steps, _MAX_STEPS)
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


def law(inputs, p: KineticsGamma111Params) -> float:
    """Unified GT/oracle law: fractional-memory decay C(t). The fractional
    Adams-Moulton solve is O(n_steps²), so dt is enlarged to cap the step count
    (≤200) per call; fall back to the analytic n-th-order C(t) for cf-perturbed
    params the Instance refuses."""
    from dataclasses import replace
    from mirrorlab.domains.kinetics import baseline_C
    t = inputs["t"]
    try:
        dt_eff = max(float(getattr(p, "dt", 0.05)), abs(t) / 200)
        inst = KineticsGamma111Instance(replace(p, dt=dt_eff))
        return inst.step(t)["C"]
    except (ValueError, TypeError):
        return baseline_C(t, p)


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"C": "mol*m**-3"},
    "params": {"n": "1", "beta": "1"},
}

CELL = CellSpec(
    domain="kinetics", shift="gamma_11_1",
    params_type=KineticsGamma111Params, law=law,
    sampler=sampler, validator=validator,
    output="C", broken_symmetry="SCALE",
)
register_cell(CELL)

__all__ = [
    "KineticsGamma111Params", "KineticsGamma111Instance", "law",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "CELL",
]
