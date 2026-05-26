"""δ-5-1 — Coulomb field-coupled charge leakage (Q-conservation break).

Catalog: dq_i/dt = −α · (|E_loc,i|/E_ref)^n · q_i; force law itself unchanged.
Broken: Q conservation (T-rev bundled). Retained: T-trans, S-trans, ROT, PAR.

Sim setup: N=2 charges with fixed positions; integrate charge values only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

K_E_DEFAULT = 8.9875517873681764e9
ALPHA_MIN, ALPHA_MAX = 1e-4, 1e-1
N_MIN, N_MAX = 0.5, 2.0


@dataclass(frozen=True)
class CoulombDelta51Params:
    k_e: float
    alpha: float
    n_exp: float
    E_ref: float
    q1_0: float
    q2_0: float
    # positions fixed
    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    T_sim: float


def _E_loc_mag(q_other: float, dx: float, dy: float, dz: float,
               p: CoulombDelta51Params) -> float:
    r2 = dx * dx + dy * dy + dz * dz
    r = math.sqrt(r2)
    if r == 0.0:
        return 0.0
    return abs(p.k_e * q_other / r2)


def shifted_law(q1: float, q2: float, p: CoulombDelta51Params):
    """dq/dt vector."""
    dx, dy, dz = p.x1 - p.x2, p.y1 - p.y2, p.z1 - p.z2
    E1 = _E_loc_mag(q2, dx, dy, dz, p)
    E2 = _E_loc_mag(q1, dx, dy, dz, p)
    dq1 = -p.alpha * (E1 / p.E_ref) ** p.n_exp * q1
    dq2 = -p.alpha * (E2 / p.E_ref) ** p.n_exp * q2
    return (dq1, dq2)


def sampler(seed: int) -> CoulombDelta51Params:
    rng = np.random.default_rng(seed)
    k_e = K_E_DEFAULT * loguniform(rng, 0.5, 2.0)
    alpha = loguniform(rng, ALPHA_MIN, ALPHA_MAX)
    n_exp = float(rng.uniform(N_MIN, N_MAX))
    q1 = 1.0e-6
    q2 = -1.0e-6
    r = 1.0
    E_typ = k_e * abs(q2) / (r * r)
    E_ref = E_typ * loguniform(rng, 0.1, 10.0)
    T_sim = 1.0 / alpha
    return CoulombDelta51Params(
        k_e=k_e, alpha=alpha, n_exp=n_exp, E_ref=E_ref,
        q1_0=q1, q2_0=q2,
        x1=0.0, y1=0.0, z1=0.0, x2=r, y2=0.0, z2=0.0,
        T_sim=T_sim,
    )


def validator(p) -> bool:
    if not isinstance(p, CoulombDelta51Params):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if not (N_MIN <= p.n_exp <= N_MAX):
        return False
    if p.k_e <= 0 or p.E_ref <= 0:
        return False
    if p.alpha * p.T_sim > 1.0 + 1e-9:
        return False
    return True


class _Sim:
    def __init__(self, p: CoulombDelta51Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            q1, q2 = y
            return shifted_law(q1, q2, p)

        sol = solve_ivp(rhs, (0.0, t_max), [p.q1_0, p.q2_0],
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
        q1, q2 = float(y[0]), float(y[1])
        return {"t": float(t), "q1": q1, "q2": q2,
                "Q_total": float(q1 + q2)}


def build(*, params: CoulombDelta51Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"δ-5-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"q1": "A*s", "q2": "A*s"},
    "outputs": {"dq1_dt": "A", "dq2_dt": "A"},
    "params": {"k_e": "kg*m**3*s**-4*A**-2", "alpha": "s**-1",
               "n_exp": "1", "E_ref": "kg*m*s**-3*A**-1"},
}

__all__ = ["CoulombDelta51Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
