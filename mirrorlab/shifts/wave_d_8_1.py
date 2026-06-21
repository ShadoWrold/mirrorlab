"""δ-8-1 — Scalar wave: amplitude-gated viscous damping.

Catalog (Domain 8, Tier-2):
    ∂_t² u = c² ∂_x² u - α₀ (|u|/u_ref) ∂_t u

Broken : energy (dissipation, T-rev bundled).
Retained: T-trans, S-trans, parity x→-x; u → -u also invariant.

Lumped ODE reduction: for plane wave at probe, modal amplitude obeys
    ü + α₀ (|u|/u_ref) u̇ + ω² u = 0,  ω = c k.
Integrate that to get u(t).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

ALPHA_MIN, ALPHA_MAX = 1e-3, 0.3
U_REF_MIN, U_REF_MAX = 1e-3, 2.0
C_MIN, C_MAX = 50.0, 5000.0


@dataclass(frozen=True)
class WaveDelta81Params:
    A: float = field(metadata=P.law("A"))        # initial amplitude [m]
    k: float = field(metadata=P.law("k"))        # wavenumber [1/m]
    c: float = field(metadata=P.law("c"))        # base phase speed [m/s]
    alpha0: float = field(metadata=P.law("alpha"))   # damping rate [1/s]
    u_ref: float = field(metadata=P.law("u_ref"))    # amplitude reference [m]


class WaveDelta81Instance:
    def __init__(self, params: WaveDelta81Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-8-1 params failed validator: {params!r}")
        self._params = params
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> WaveDelta81Params:
        return self._params

    def _integrate(self, t_max: float) -> None:
        p = self._params
        omega = p.c * p.k

        def rhs(t, y):
            u, v = y
            return (v, -p.alpha0 * (abs(u) / p.u_ref) * v - omega * omega * u)

        sol = solve_ivp(
            rhs, (0.0, t_max), [p.A, 0.0], method="DOP853",
            rtol=1e-9, atol=1e-12, dense_output=True,
        )
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
        return {"t": float(t), "u": float(y[0]), "du_dt": float(y[1])}


def sampler(seed: int) -> WaveDelta81Params:
    rng = np.random.default_rng(seed)
    # Linear-uniform alpha0 (was loguniform, median ~0.017 — far too weak).
    # A raised 0.1→1.0 with u_ref scaled ×10 to [0.5,1.5]: this is a pure
    # rescaling of the wave amplitude so |u| leaves the slog(log1p) near-linear
    # toe (where the amplitude-gated damping break was invisible and the stub
    # scored high), while keeping the gate ratio |u|/u_ref at the same O(1)
    # operating point so the break physics is unchanged. The oracle runs the
    # same ODE so the ceiling stays exact.
    alpha0 = float(rng.uniform(0.1, 0.3))
    u_ref = float(rng.uniform(0.5, 1.5))
    c = float(np.exp(rng.uniform(np.log(C_MIN), np.log(C_MAX))))
    return WaveDelta81Params(A=1.0, k=2.0, c=c, alpha0=alpha0, u_ref=u_ref)


def validator(params: WaveDelta81Params) -> bool:
    if not isinstance(params, WaveDelta81Params):
        return False
    if not (ALPHA_MIN <= params.alpha0 <= ALPHA_MAX):
        return False
    if not (U_REF_MIN <= params.u_ref <= U_REF_MAX):
        return False
    if not (C_MIN <= params.c <= C_MAX):
        return False
    if params.k <= 0 or params.A <= 0:
        return False
    return True


def build(*, params: WaveDelta81Params | None = None, seed: int = 0) -> WaveDelta81Instance:
    if params is None:
        params = sampler(seed)
    return WaveDelta81Instance(params)


shift = ShiftImpl(law=lambda t, p: 0.0, sampler=sampler, validator=validator)


def law(inputs, p: WaveDelta81Params) -> float:
    """Unified GT/oracle law: damped wavepacket u(t) from the catalog Instance.
    cf perturbation routinely steps outside the sampler band, so fall back to
    the baseline travelling-wave sin if the Instance refuses to build."""
    t = inputs["t"]
    try:
        inst = WaveDelta81Instance(p)
    except (ValueError, TypeError):
        x_probe = getattr(p, "x_probe", 0.0)
        return p.A * math.sin(p.k * x_probe - p.c * p.k * t)
    return inst.step(t)["u"]


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"t": "s"},
    "outputs": {"u": "m"},
    "params": {"A": "m", "k": "m**-1", "c": "m*s**-1", "alpha0": "s**-1", "u_ref": "m"},
}

CELL = CellSpec(
    domain="wave", shift="delta_8_1",
    params_type=WaveDelta81Params, law=law,
    sampler=sampler, validator=validator,
    output="u", broken_symmetry="T_TRANS",
)
register_cell(CELL)

__all__ = [
    "WaveDelta81Params", "WaveDelta81Instance", "law",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "CELL",
]
