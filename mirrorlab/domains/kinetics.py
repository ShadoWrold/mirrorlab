"""Reaction-kinetics baseline (single n-th-order irreversible reaction).

Baseline law: dC/dt = -k Cⁿ.  Returned via numeric integration so non-integer
orders are supported without analytical case-splits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class KineticsParams:
    k: float        # rate constant (units depend on n)
    n: float        # reaction order [1]
    C0: float       # initial concentration [mol/m³]


class KineticsBaseline:
    def __init__(self, params: KineticsParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.C0 < 0 or params.k < 0:
            raise ValueError("C0, k must be non-negative")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> KineticsParams:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            (C,) = y
            C_safe = max(C, 0.0)
            return (-p.k * (C_safe ** p.n),)

        sol = solve_ivp(rhs, (0.0, t_max), [p.C0], method="DOP853",
                        rtol=self._rtol, atol=self._atol, dense_output=True)
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
        C = float(y[0])
        rate = -self._params.k * (max(C, 0.0) ** self._params.n)
        return {"t": float(t), "C": C, "rate": float(rate)}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"C": "mol*m**-3", "rate": "mol*m**-3*s**-1"},
    "params": {"n": "1"},
}
