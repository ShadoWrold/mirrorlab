"""γ-4-2 — Pendulum height-graded gravity (vertical S-trans break).

Catalog: θ̈ + (g₀/L)·[1 − α·(L(1−cos θ))/H]·sin θ = 0.
Broken: vertical S-trans. Retained: T-trans, PAR.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.spec import ProbeSpec, P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

GL_MIN, GL_MAX = 1.0, 100.0
ALPHA_MIN, ALPHA_MAX = 0.15, 0.3


@dataclass(frozen=True)
class PendulumGamma42Params:
    g0_over_L: float = field(metadata=P.law("g_over_L"))
    alpha: float = field(metadata=P.law("alpha"))
    L: float = field(metadata=P.law("L"))
    H: float = field(metadata=P.law("H"))
    theta0: float = field(metadata=P.ic())
    omega0: float = field(metadata=P.ic())


def shifted_law(theta: float, p: PendulumGamma42Params) -> float:
    height = p.L * (1.0 - math.cos(theta))
    g_eff = p.g0_over_L * (1.0 - p.alpha * height / p.H)
    return -g_eff * math.sin(theta)


def sampler(seed: int) -> PendulumGamma42Params:
    rng = np.random.default_rng(seed)
    g0_over_L = loguniform(rng, GL_MIN, GL_MAX)
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    L = loguniform(rng, 0.1, 2.0)
    # Sample the break strength r = α·L/H directly and back-solve H. The old
    # H = H_min_safe·loguniform(1,50) let H grow up to 50× the safe minimum,
    # so r collapsed toward ~0.006 for many seeds and the height-grading
    # correction α·L(1−cosθ)/H vanished — both the textbook stub AND a smart
    # constant-g_eff re-fit then scored high (cell was soft). Pinning
    # r ∈ [0.40, 0.47] keeps the correction a visible, non-absorbable fraction
    # while staying under the g_eff>0 safety bound r<0.5.
    r = float(rng.uniform(0.40, 0.47))
    H = alpha * L / r
    return PendulumGamma42Params(g0_over_L=g0_over_L, alpha=alpha, L=L, H=H,
                                 theta0=0.3, omega0=0.0)


def validator(p) -> bool:
    if not isinstance(p, PendulumGamma42Params):
        return False
    if not (GL_MIN <= p.g0_over_L <= GL_MAX):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if p.L <= 0 or p.H <= 0:
        return False
    # Break strength r = α·L/H must stay in the visible, non-absorbable band
    # the sampler targets (lower bound) and below the g_eff>0 safety bound
    # (upper bound). The lower bound also stops an externally-constructed
    # weak-break param (r≈0.006) from re-creating the old soft cell.
    if not (0.385 <= p.alpha * p.L / p.H < 0.5):
        return False
    if abs(p.theta0) > math.pi / 2:
        return False
    return True


class _Sim:
    def __init__(self, p: PendulumGamma42Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            th, om = y
            return (om, shifted_law(th, p))

        sol = solve_ivp(rhs, (0.0, t_max), [p.theta0, p.omega0],
                        method="DOP853", rtol=1e-9, atol=1e-12, dense_output=True)
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
        theta, omega = float(y[0]), float(y[1])
        return {"t": float(t), "theta": theta, "omega": omega}


def build(*, params: PendulumGamma42Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-4-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)


def law(inputs, p: PendulumGamma42Params) -> float:
    """Unified GT/oracle law (height-dependent g)."""
    return shifted_law(inputs["theta"], p)


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta": "rad"},
    "outputs": {"theta_ddot": "rad*s**-2"},
    "params": {"g0_over_L": "s**-2", "alpha": "1", "L": "m", "H": "m"},
}

CELL = CellSpec(
    domain="pendulum", shift="gamma_4_2",
    params_type=PendulumGamma42Params, law=law,
    sampler=sampler, validator=validator,
    output="theta_ddot", break_type="S_TRANS",
    probe_spec=ProbeSpec(kind="scale", axes=('theta',)),
)
register_cell(CELL)

__all__ = ["PendulumGamma42Params", "shifted_law", "law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE", "CELL"]
