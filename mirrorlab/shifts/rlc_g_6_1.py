"""γ-6-1 — RLC saturable inductor (LIN break).

Catalog: d/dt [L(i) · i] + R i + q/C = 0, L(i) = L₀ / (1 + (i/I_sat)²).
EOM (expanding the d/dt with chain rule):
  L_eff(i) · di/dt = -R i - q/C
  where L_eff(i) = L₀ · (1 − u²) / (1 + u²)², u = i/I_sat.
Broken: LIN. Retained: T-trans, q↔−q parity, Onsager.

Validator bounds IC so |i| stays strictly inside (−I_sat, +I_sat) where
L_eff > 0, keeping the ODE non-singular.
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
R_MIN, R_MAX = 0.1, 100.0
C_MIN, C_MAX = 1e-9, 1e-5
I_SAT_MIN_FACTOR, I_SAT_MAX_FACTOR = 0.1, 10.0


@dataclass(frozen=True)
class RLCGamma61Params:
    L0: float
    R: float
    C: float
    I_sat: float
    q0: float
    i0: float


def _L_eff(i: float, p: RLCGamma61Params) -> float:
    u = i / p.I_sat
    return p.L0 * (1.0 - u * u) / (1.0 + u * u) ** 2


def shifted_law(q: float, i: float, p: RLCGamma61Params) -> float:
    L_eff = _L_eff(i, p)
    return -(p.R * i + q / p.C) / L_eff


def sampler(seed: int) -> RLCGamma61Params:
    rng = np.random.default_rng(seed)
    L0 = loguniform(rng, L0_MIN, L0_MAX)
    R = loguniform(rng, R_MIN, R_MAX)
    C = loguniform(rng, C_MIN, C_MAX)
    omega = 1.0 / math.sqrt(L0 * C)
    # i_typ from a moderate charge oscillation: i_typ = q0 * omega
    q_init = 1e-7
    i_typ = q_init * omega
    I_sat = i_typ * loguniform(rng, I_SAT_MIN_FACTOR, I_SAT_MAX_FACTOR)
    # Make sure I_sat is comfortably above i_typ
    if I_sat < 3.0 * i_typ:
        I_sat = 3.0 * i_typ
    return RLCGamma61Params(L0=L0, R=R, C=C, I_sat=I_sat,
                            q0=q_init, i0=0.0)


def validator(p) -> bool:
    if not isinstance(p, RLCGamma61Params):
        return False
    if not (L0_MIN <= p.L0 <= L0_MAX):
        return False
    if not (R_MIN <= p.R <= R_MAX):
        return False
    if not (C_MIN <= p.C <= C_MAX):
        return False
    if p.I_sat <= 0:
        return False
    omega = 1.0 / math.sqrt(p.L0 * p.C)
    i_typ = abs(p.q0) * omega
    if i_typ >= 0.5 * p.I_sat:
        return False
    if abs(p.i0) >= 0.5 * p.I_sat:
        return False
    return True


class _Sim:
    def __init__(self, p: RLCGamma61Params) -> None:
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
            return (i, shifted_law(q, i, p))

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


def build(*, params: RLCGamma61Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-6-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"q": "A*s", "i": "A"},
    "outputs": {"di_dt": "A*s**-1"},
    "params": {"L0": "kg*m**2*s**-2*A**-2", "R": "kg*m**2*s**-3*A**-2",
               "C": "kg**-1*m**-2*s**4*A**2", "I_sat": "A"},
}

__all__ = ["RLCGamma61Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
