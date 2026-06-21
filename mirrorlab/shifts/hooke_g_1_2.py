"""γ-1-2 — Hooke 2D anisotropic stiffness (ROT break).

Catalog (ROUND-2 FINAL): V(r,θ) = ½ K(θ) r²,  K(θ) = k₀ [1 + ξ cos(2(θ−φ))].
F = −∇V ⇒ F_r = −K(θ) r,  F_θ = k₀ ξ r · sin(2(θ−φ)).
Broken: ROT (L_z Noether). Retained: T-trans/E, T-rev, PAR.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

K_MIN, K_MAX = 1.0, 100.0
XI_MIN, XI_MAX = 0.1, 0.7
PHI_MIN, PHI_MAX = 0.0, math.pi


@dataclass(frozen=True)
class HookeGamma12Params:
    k0: float = field(metadata=P.law("k"))
    xi: float = field(metadata=P.law("xi"))
    phi: float = field(metadata=P.law("phi"))
    m: float = field(metadata=P.mass())
    x0: float = field(metadata=P.ic())
    y0: float = field(metadata=P.ic())
    vx0: float = field(metadata=P.ic())
    vy0: float = field(metadata=P.ic())


def shifted_force(xy: Tuple[float, float], p: HookeGamma12Params) -> Tuple[float, float]:
    x, y = xy
    r2 = x * x + y * y
    if r2 == 0.0:
        return (0.0, 0.0)
    r = math.sqrt(r2)
    theta = math.atan2(y, x)
    c = math.cos(2.0 * (theta - p.phi))
    s = math.sin(2.0 * (theta - p.phi))
    K = p.k0 * (1.0 + p.xi * c)
    F_r = -K * r
    F_theta = p.k0 * p.xi * r * s
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    Fx = F_r * cos_t - F_theta * sin_t
    Fy = F_r * sin_t + F_theta * cos_t
    return (Fx, Fy)


def potential(xy: Tuple[float, float], p: HookeGamma12Params) -> float:
    x, y = xy
    r2 = x * x + y * y
    if r2 == 0.0:
        return 0.0
    theta = math.atan2(y, x)
    K = p.k0 * (1.0 + p.xi * math.cos(2.0 * (theta - p.phi)))
    return 0.5 * K * r2


def sampler(seed: int) -> HookeGamma12Params:
    rng = np.random.default_rng(seed)
    k0 = loguniform(rng, K_MIN, K_MAX)
    xi = float(rng.uniform(XI_MIN, XI_MAX))
    phi = float(rng.uniform(PHI_MIN, PHI_MAX))
    return HookeGamma12Params(k0=k0, xi=xi, phi=phi, m=1.0,
                              x0=0.1, y0=0.05, vx0=0.0, vy0=0.0)


def validator(p) -> bool:
    if not isinstance(p, HookeGamma12Params):
        return False
    if not (K_MIN <= p.k0 <= K_MAX):
        return False
    if not (XI_MIN <= p.xi <= XI_MAX):
        return False
    if not (PHI_MIN <= p.phi <= PHI_MAX):
        return False
    if p.m <= 0.0:
        return False
    if p.xi >= 1.0:
        return False
    return True


class _Sim:
    def __init__(self, p: HookeGamma12Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            x, yc, vx, vy = y
            Fx, Fy = shifted_force((x, yc), p)
            return (vx, vy, Fx / p.m, Fy / p.m)

        sol = solve_ivp(rhs, (0.0, t_max), [p.x0, p.y0, p.vx0, p.vy0],
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
        x, yc, vx, vy = (float(v) for v in y)
        Fx, Fy = shifted_force((x, yc), self._p)
        return {"t": float(t), "x": x, "y": yc, "vx": vx, "vy": vy,
                "Fx": float(Fx), "Fy": float(Fy)}


def build(*, params: HookeGamma12Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-1-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)


def law(inputs, p: HookeGamma12Params) -> float:
    """Unified GT/oracle law: the 2-D anisotropic force projected onto the
    signed radial magnitude (blueprint §2.5), so the scored scalar matches the
    grid GT exactly. F = (Fx, Fy) = shifted_force((x, y)); return
    sign(F·r̂)·|F|.
    """
    x, y = inputs["x"], inputs["y"]
    r = math.sqrt(x * x + y * y)
    if r == 0.0:
        return 0.0
    Fx, Fy = shifted_force((x, y), p)
    rhat_x, rhat_y = x / r, y / r
    dot = Fx * rhat_x + Fy * rhat_y
    mag = math.sqrt(Fx * Fx + Fy * Fy)
    return math.copysign(mag, dot) if dot != 0.0 else mag


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "y": "m"},
    "outputs": {"Fx": "kg*m*s**-2", "Fy": "kg*m*s**-2"},
    "params": {"k0": "kg*s**-2", "xi": "1", "phi": "rad", "m": "kg"},
}

CELL = CellSpec(
    domain="hooke", shift="gamma_1_2",
    params_type=HookeGamma12Params, law=law,
    sampler=sampler, validator=validator,
    output="F", broken_symmetry="ROT",
)
register_cell(CELL)

__all__ = ["HookeGamma12Params", "shifted_force", "law", "potential", "sampler",
           "validator", "build", "shift", "DIM_SIGNATURE", "CELL"]
