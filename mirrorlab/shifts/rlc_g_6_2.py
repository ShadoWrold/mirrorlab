"""γ-6-2 — RLC non-reciprocal mutual inductance (Onsager / T-rev break).

Catalog: two coupled loops, M_{12} = M₀ + δM/2, M_{21} = M₀ − δM/2, δM ≠ 0.
  L_i di_i/dt + Σ_{j≠i} M_{ij} di_j/dt + R_i i_i + q_i/C_i = 0.
Broken: Onsager (E-loss Noether-paired). Retained: T-trans, LIN, q↔−q.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

L_MIN, L_MAX = 1e-3, 1.0
R_MIN, R_MAX = 0.1, 100.0
C_MIN, C_MAX = 1e-9, 1e-5


@dataclass(frozen=True)
class RLCGamma62Params:
    L1: float
    L2: float
    R1: float
    R2: float
    C1: float
    C2: float
    M0: float
    dM: float
    q1_0: float
    q2_0: float
    i1_0: float
    i2_0: float


def shifted_law(q1: float, i1: float, q2: float, i2: float,
                p: RLCGamma62Params) -> Tuple[float, float]:
    """Return (di1/dt, di2/dt) by solving 2x2 linear system."""
    M12 = p.M0 + 0.5 * p.dM
    M21 = p.M0 - 0.5 * p.dM
    rhs1 = -(p.R1 * i1 + q1 / p.C1)
    rhs2 = -(p.R2 * i2 + q2 / p.C2)
    det = p.L1 * p.L2 - M12 * M21
    di1 = (p.L2 * rhs1 - M12 * rhs2) / det
    di2 = (-M21 * rhs1 + p.L1 * rhs2) / det
    return (di1, di2)


def sampler(seed: int) -> RLCGamma62Params:
    rng = np.random.default_rng(seed)
    L1 = loguniform(rng, L_MIN, L_MAX)
    L2 = loguniform(rng, L_MIN, L_MAX)
    R1 = loguniform(rng, R_MIN, R_MAX)
    R2 = loguniform(rng, R_MIN, R_MAX)
    C1 = loguniform(rng, C_MIN, C_MAX)
    C2 = loguniform(rng, C_MIN, C_MAX)
    M0 = float(rng.uniform(0.0, 0.5)) * math.sqrt(L1 * L2)
    dM_ratio = float(rng.uniform(0.05, 0.4))
    dM = M0 * dM_ratio
    return RLCGamma62Params(L1=L1, L2=L2, R1=R1, R2=R2, C1=C1, C2=C2,
                            M0=M0, dM=dM,
                            q1_0=1e-7, q2_0=0.0, i1_0=0.0, i2_0=0.0)


def validator(p) -> bool:
    if not isinstance(p, RLCGamma62Params):
        return False
    if not (L_MIN <= p.L1 <= L_MAX):
        return False
    if not (L_MIN <= p.L2 <= L_MAX):
        return False
    if not (R_MIN <= p.R1 <= R_MAX):
        return False
    if not (R_MIN <= p.R2 <= R_MAX):
        return False
    if not (C_MIN <= p.C1 <= C_MAX):
        return False
    if not (C_MIN <= p.C2 <= C_MAX):
        return False
    sqL = math.sqrt(p.L1 * p.L2)
    if abs(p.M0 + 0.5 * p.dM) >= sqL:
        return False
    if abs(p.M0 - 0.5 * p.dM) >= sqL:
        return False
    # require asymmetry: δM ≠ 0
    if abs(p.dM) < 1e-12:
        return False
    return True


class _Sim:
    def __init__(self, p: RLCGamma62Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            q1, i1, q2, i2 = y
            di1, di2 = shifted_law(q1, i1, q2, i2, p)
            return (i1, di1, i2, di2)

        sol = solve_ivp(rhs, (0.0, t_max),
                        [p.q1_0, p.i1_0, p.q2_0, p.i2_0],
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
        q1, i1, q2, i2 = (float(v) for v in y)
        return {"t": float(t), "q1": q1, "i1": i1, "q2": q2, "i2": i2}


def build(*, params: RLCGamma62Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-6-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"q1": "A*s", "i1": "A", "q2": "A*s", "i2": "A"},
    "outputs": {"di1_dt": "A*s**-1", "di2_dt": "A*s**-1"},
    "params": {"L1": "kg*m**2*s**-2*A**-2", "L2": "kg*m**2*s**-2*A**-2",
               "M0": "kg*m**2*s**-2*A**-2", "dM": "kg*m**2*s**-2*A**-2"},
}

__all__ = ["RLCGamma62Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
