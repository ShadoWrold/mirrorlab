"""δ-6-1 — RLC parametric inductance modulation (T-trans break).

Catalog: d/dt [L(t) · i] + R i + q/C = 0, L(t) = L₀ · [1 + ε cos(Ω_p t)].
Expanding: L(t) di/dt + L'(t) i + R i + q/C = 0  ⇒
  di/dt = -[L'(t) i + R i + q/C] / L(t).
Broken: T-trans. Retained: LIN, q↔−q parity, T-rev (cos even about t=0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

L0_MIN, L0_MAX = 1e-3, 1.0
R_MIN, R_MAX = 0.01, 1e5
C_MIN, C_MAX = 1e-9, 1e-5
EPS_MIN, EPS_MAX = 0.05, 0.3


@dataclass(frozen=True)
class RLCDelta61Params:
    L0: float
    R: float
    C: float
    eps: float
    Omega_p: float
    q0: float
    i0: float


def _L_of_t(t: float, p: RLCDelta61Params) -> float:
    return p.L0 * (1.0 + p.eps * math.cos(p.Omega_p * t))


def _Lp_of_t(t: float, p: RLCDelta61Params) -> float:
    return -p.L0 * p.eps * p.Omega_p * math.sin(p.Omega_p * t)


def shifted_law(q: float, i: float, t: float, p: RLCDelta61Params) -> float:
    L_t = _L_of_t(t, p)
    Lp_t = _Lp_of_t(t, p)
    return -(Lp_t * i + p.R * i + q / p.C) / L_t


def sampler(seed: int) -> RLCDelta61Params:
    rng = np.random.default_rng(seed)
    L0 = loguniform(rng, L0_MIN, L0_MAX)
    C = loguniform(rng, C_MIN, C_MAX)
    eps = float(rng.uniform(EPS_MIN, EPS_MAX))
    omega_LC = 1.0 / math.sqrt(L0 * C)
    # Avoid ±10% around 2 ω_LC: sample in (0.5, 1.5) ω_LC then exclude near 2 ω_LC
    # Since 2 ω_LC > 1.5 ω_LC already, exclusion band is automatically avoided.
    ratio = float(rng.uniform(0.5, 1.5))
    Omega_p = ratio * omega_LC
    # Sub-threshold parametric amplification: R/(2√(L₀/C)) ≥ ε·Ω_p/(2 ω_LC).
    # Choose damping ratio above threshold, with a safety margin.
    sqrt_L_over_C = math.sqrt(L0 / C)
    threshold = eps * Omega_p / (2.0 * omega_LC)
    # damping_ratio must be ≥ threshold; sample in [1.1·threshold, max(0.5, 1.5·threshold)]
    dr_min = 1.1 * threshold
    dr_max = max(0.5, 1.5 * threshold)
    damping_ratio = float(rng.uniform(dr_min, dr_max))
    R = damping_ratio * 2.0 * sqrt_L_over_C
    return RLCDelta61Params(L0=L0, R=R, C=C, eps=eps, Omega_p=Omega_p,
                            q0=1e-7, i0=0.0)


def validator(p) -> bool:
    if not isinstance(p, RLCDelta61Params):
        return False
    if not (L0_MIN <= p.L0 <= L0_MAX):
        return False
    if not (R_MIN <= p.R <= R_MAX):
        return False
    if not (C_MIN <= p.C <= C_MAX):
        return False
    if not (EPS_MIN <= p.eps <= EPS_MAX):
        return False
    if p.Omega_p <= 0:
        return False
    omega_LC = 1.0 / math.sqrt(p.L0 * p.C)
    ratio = p.Omega_p / omega_LC
    if not (0.5 <= ratio <= 1.5):
        return False
    # Avoid ±10% band around 2 ω_LC (here Ω_p < 1.5 ω_LC < 2 ω_LC, but check anyway)
    if abs(p.Omega_p - 2.0 * omega_LC) < 0.1 * 2.0 * omega_LC:
        return False
    # Sub-threshold of parametric amp: R/(2√(L₀/C)) ≥ ε·Ω_p / (2 ω_LC)
    damping_ratio = p.R / (2.0 * math.sqrt(p.L0 / p.C))
    threshold = p.eps * p.Omega_p / (2.0 * omega_LC)
    if damping_ratio < threshold:
        return False
    return True


class _Sim:
    def __init__(self, p: RLCDelta61Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            q, i = y
            return (i, shifted_law(q, i, t, p))

        sol = solve_ivp(rhs, (0.0, t_max), [p.q0, p.i0],
                        method="DOP853", rtol=1e-9, atol=1e-14, dense_output=True)
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
        q, i = float(y[0]), float(y[1])
        return {"t": float(t), "q": q, "i": i}


def build(*, params: RLCDelta61Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-6-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"q": "A*s", "i": "A", "t": "s"},
    "outputs": {"di_dt": "A*s**-1"},
    "params": {"L0": "kg*m**2*s**-2*A**-2", "R": "kg*m**2*s**-3*A**-2",
               "C": "kg**-1*m**-2*s**4*A**2", "eps": "1", "Omega_p": "s**-1"},
}

__all__ = ["RLCDelta61Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
