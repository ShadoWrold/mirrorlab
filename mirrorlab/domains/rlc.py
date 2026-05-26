"""Series RLC circuit baseline.

Baseline law: L q̈ + R q̇ + q/C = 0 (free oscillation; charge q on capacitor).
Source-free for v1; driving terms live in the shift layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class RLCParams:
    L: float        # inductance [H]
    R: float        # resistance [Ω]
    C: float        # capacitance [F]
    q0: float       # initial charge [C]
    i0: float       # initial current [A]


class RLCBaseline:
    def __init__(self, params: RLCParams, *, rtol: float = 1e-9, atol: float = 1e-12) -> None:
        if params.L <= 0 or params.C <= 0:
            raise ValueError("L, C must be positive")
        self._params = params
        self._rtol, self._atol = rtol, atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> RLCParams:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params

        def rhs(t, y):
            q, i = y
            return (i, -(p.R * i + q / p.C) / p.L)

        sol = solve_ivp(rhs, (0.0, t_max), [p.q0, p.i0], method="DOP853",
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
        q, i = float(y[0]), float(y[1])
        p = self._params
        V = q / p.C + p.R * i
        return {"t": float(t), "q": q, "i": i, "V": float(V)}


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"q": "A*s", "i": "A", "V": "kg*m**2*s**-3*A**-1"},
    "params": {"L": "kg*m**2*s**-2*A**-2", "R": "kg*m**2*s**-3*A**-2", "C": "kg**-1*m**-2*s**4*A**2"},
}
