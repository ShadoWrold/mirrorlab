"""γ-2-2 — Gravity log-periodic modulation (discrete-scale-invariance break).

Catalog (ROUND-2 redesign): F(r) = −G M m /r² · [1 + α·cos(ω·ln(r/r₀))].
Broken: SCALE (continuous scale invariance → discrete scale invariance, DSI).
Retained: ROT (central), T-trans, T-rev.

The earlier Lorentzian bump α·u/(1+u²) looked like a power-law distortion on
log-r and was absorbed exactly by a free-exponent refit F=−c/rⁿ (stub/refit
~0.6, unhardenable). The log-periodic modulation cos(ω·ln(r/r₀)) oscillates in
ln(r) with NO finite power-law / polynomial closed form, so a free F=−c/rⁿ (or a
finite log-polynomial) cannot absorb it. Log-periodicity is real physics —
the signature of discrete scale invariance in DSI systems.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import dataclass, field
from typing import Dict, Mapping

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform
from mirrorlab.spec import ProbeSpec, CellSpec, P, register_cell

G_DEFAULT = 6.67430e-11
ALPHA_MIN, ALPHA_MAX = 0.30, 0.60
OMEGA_MIN, OMEGA_MAX = 4.0, 7.0   # rad per e-fold of r


@dataclass(frozen=True)
class GravityGamma22Params:
    # Field roles (single source of truth for the counterfactual + name map):
    #   law  -> perturbed on sub-grid (c), seen by the predictor as <canonical>
    #   mass -> passive scale, cf-excluded
    #   ic   -> initial condition, cf-excluded
    G: float = field(metadata=P.law("G"))
    M: float = field(metadata=P.law("M"))
    m: float = field(metadata=P.mass())
    alpha: float = field(metadata=P.law("alpha"))
    omega: float = field(metadata=P.law("omega"))       # log-periodic angular freq [1]
    r_scale: float = field(metadata=P.law("r_scale"))   # r₀ (log-periodic phase reference)
    r0: float = field(metadata=P.ic())                  # initial radius
    v0: float = field(metadata=P.ic())


def shifted_force(r: float, p: GravityGamma22Params) -> float:
    mod = 1.0 + p.alpha * math.cos(p.omega * math.log(r / p.r_scale))
    return -p.G * p.M * p.m / (r * r) * mod


def sampler(seed: int) -> GravityGamma22Params:
    rng = np.random.default_rng(seed)
    G = G_DEFAULT * loguniform(rng, 0.5, 2.0)
    M = float(10 ** rng.uniform(20.0, 24.0))
    alpha = float(rng.uniform(ALPHA_MIN, ALPHA_MAX))
    omega = float(rng.uniform(OMEGA_MIN, OMEGA_MAX))
    r0_radius = 1.0e7
    r_scale = r0_radius * loguniform(rng, 0.1, 10.0)
    return GravityGamma22Params(G=G, M=M, m=1.0, alpha=alpha, omega=omega,
                                r_scale=r_scale, r0=r0_radius, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, GravityGamma22Params):
        return False
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX):
        return False
    if not (OMEGA_MIN <= p.omega <= OMEGA_MAX):
        return False
    if p.G <= 0 or p.M <= 0 or p.m <= 0:
        return False
    if p.r_scale <= 0 or p.r0 <= 0:
        return False
    if p.r0 < 1e-3 * p.r_scale:
        return False
    return True


class _Sim:
    def __init__(self, p: GravityGamma22Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            r, v = y
            if r <= 0:
                return (v, 0.0)
            return (v, shifted_force(r, p) / p.m)

        sol = solve_ivp(rhs, (0.0, t_max), [p.r0, p.v0],
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
        r, v = float(y[0]), float(y[1])
        return {"t": float(t), "r": r, "v": v,
                "F": float(shifted_force(r, self._p))}


def build(*, params: GravityGamma22Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-2-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"r": "m"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"G": "m**3*kg**-1*s**-2", "M": "kg", "m": "kg",
               "alpha": "1", "omega": "1", "r_scale": "m"},
}


def law(inputs: Mapping[str, float], p: GravityGamma22Params) -> float:
    """Unified GT/oracle law: law(inputs, params) -> scalar.

    Backs BOTH the grid ground truth and the ceiling oracle, so the break
    formula lives in exactly one place (`shifted_force`).
    """
    return shifted_force(inputs["r"], p)


CELL = CellSpec(
    domain="gravity", shift="gamma_2_2",
    params_type=GravityGamma22Params, law=law,
    sampler=sampler, validator=validator,
    output="F", break_type="SCALE",
    probe_spec=ProbeSpec(kind="scale", axes=('r',)),
)
register_cell(CELL)

__all__ = ["GravityGamma22Params", "shifted_force", "law", "sampler",
           "validator", "build", "shift", "DIM_SIGNATURE", "CELL"]
