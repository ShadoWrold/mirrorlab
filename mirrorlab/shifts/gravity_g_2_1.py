"""γ-2-1 — Gravity quadrupolar anisotropic (ROT break).

Catalog (ROUND-2 FINAL): V = −G₀ m₁ m₂ [1 + ξ(μ²−⅓)] / r, μ = r̂·n̂.
F = −∇V ⇒
  F_r  = −G₀ m₁ m₂ [1 + ξ(μ²−⅓)] / r²
  F_⊥  = +(2 G₀ m₁ m₂ ξ μ / r²) · (n̂ − μ r̂)
Broken: ROT. Conservative ⇒ E preserved.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

G_DEFAULT = 6.67430e-11
XI_MIN, XI_MAX = 0.05, 0.4


@dataclass(frozen=True)
class GravityGamma21Params:
    G0: float
    M: float
    m: float
    xi: float
    nx: float
    ny: float
    nz: float
    # IC in 3D (xyz):
    x0: float
    y0: float
    z0: float
    vx0: float
    vy0: float
    vz0: float


def shifted_force(pos: Tuple[float, float, float],
                  p: GravityGamma21Params) -> Tuple[float, float, float]:
    x, y, z = pos
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    if r == 0.0:
        return (0.0, 0.0, 0.0)
    rhat = (x / r, y / r, z / r)
    nhat = (p.nx, p.ny, p.nz)
    mu = rhat[0] * nhat[0] + rhat[1] * nhat[1] + rhat[2] * nhat[2]
    Amp = p.G0 * p.M * p.m
    rad_coef = -Amp * (1.0 + p.xi * (mu * mu - 1.0 / 3.0)) / r2
    perp_coef = 2.0 * Amp * p.xi * mu / r2
    # n̂ − μ r̂
    nx_perp = nhat[0] - mu * rhat[0]
    ny_perp = nhat[1] - mu * rhat[1]
    nz_perp = nhat[2] - mu * rhat[2]
    Fx = rad_coef * rhat[0] + perp_coef * nx_perp
    Fy = rad_coef * rhat[1] + perp_coef * ny_perp
    Fz = rad_coef * rhat[2] + perp_coef * nz_perp
    return (Fx, Fy, Fz)


def sampler(seed: int) -> GravityGamma21Params:
    rng = np.random.default_rng(seed)
    G0 = G_DEFAULT * loguniform(rng, 0.5, 2.0)
    M = float(10 ** rng.uniform(20.0, 24.0))
    xi = float(rng.uniform(XI_MIN, XI_MAX))
    # n̂ uniform on S²
    u = rng.uniform(-1.0, 1.0)
    phi = rng.uniform(0.0, 2.0 * math.pi)
    s = math.sqrt(1.0 - u * u)
    nx, ny, nz = s * math.cos(phi), s * math.sin(phi), u
    r0 = 1.0e7
    # Choose circular-ish IC in xy plane
    v_circ = math.sqrt(G_DEFAULT * M / r0)
    return GravityGamma21Params(
        G0=G0, M=M, m=1.0, xi=xi, nx=nx, ny=ny, nz=nz,
        x0=r0, y0=0.0, z0=0.0,
        vx0=0.0, vy0=v_circ, vz0=0.0,
    )


def validator(p) -> bool:
    if not isinstance(p, GravityGamma21Params):
        return False
    if not (XI_MIN <= p.xi <= XI_MAX):
        return False
    if p.xi >= 0.5:  # safe: bracket positive
        return False
    if p.G0 <= 0 or p.M <= 0 or p.m <= 0:
        return False
    norm = math.sqrt(p.nx * p.nx + p.ny * p.ny + p.nz * p.nz)
    if abs(norm - 1.0) > 1e-6:
        return False
    if math.sqrt(p.x0 ** 2 + p.y0 ** 2 + p.z0 ** 2) <= 0:
        return False
    return True


class _Sim:
    def __init__(self, p: GravityGamma21Params) -> None:
        self._p = p
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self):
        return self._p

    def _integrate(self, t_max: float) -> None:
        p = self._p

        def rhs(t, y):
            x, yc, z, vx, vy, vz = y
            Fx, Fy, Fz = shifted_force((x, yc, z), p)
            return (vx, vy, vz, Fx / p.m, Fy / p.m, Fz / p.m)

        sol = solve_ivp(rhs, (0.0, t_max),
                        [p.x0, p.y0, p.z0, p.vx0, p.vy0, p.vz0],
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
        x, yc, z, vx, vy, vz = (float(v) for v in y)
        Lz = self._p.m * (x * vy - yc * vx)
        return {"t": float(t), "x": x, "y": yc, "z": z,
                "vx": vx, "vy": vy, "vz": vz, "Lz": float(Lz)}


def build(*, params: GravityGamma21Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-2-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "y": "m", "z": "m"},
    "outputs": {"Fx": "kg*m*s**-2", "Fy": "kg*m*s**-2", "Fz": "kg*m*s**-2"},
    "params": {"G0": "m**3*kg**-1*s**-2", "M": "kg", "m": "kg", "xi": "1"},
}

__all__ = ["GravityGamma21Params", "shifted_force", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
