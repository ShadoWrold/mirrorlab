"""γ-5-1 — Coulomb anisotropic pair potential (ROT break).

Catalog (ROUND-2 FINAL): V_pair = (k q_i q_j / r) · [1 + χ((r̂·m̂)² − ⅓)], F = −∇_x V.
Explicit (ν ≡ r̂·m̂, r̂ from j to i so positive q_i q_j gives repulsion):
  F_r  = (k q_i q_j / r²) · [1 + χ(ν² − ⅓)]
  F_⊥  = −(2 k q_i q_j χ ν / r²) · (m̂ − ν r̂)
Broken: ROT. Conservative ⇒ E preserved.

Sim setup: source charge at origin (held fixed), test charge moves in 3D under
the modified pair force.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

K_E_DEFAULT = 8.9875517873681764e9
CHI_MIN, CHI_MAX = 0.05, 0.4


@dataclass(frozen=True)
class CoulombGamma51Params:
    k_e: float
    q_src: float
    q_test: float
    chi: float
    mx: float
    my: float
    mz: float
    m: float
    x0: float
    y0: float
    z0: float
    vx0: float
    vy0: float
    vz0: float


def shifted_force(pos: Tuple[float, float, float],
                  p: CoulombGamma51Params) -> Tuple[float, float, float]:
    x, y, z = pos
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    if r == 0.0:
        return (0.0, 0.0, 0.0)
    rhat = (x / r, y / r, z / r)
    mhat = (p.mx, p.my, p.mz)
    nu = rhat[0] * mhat[0] + rhat[1] * mhat[1] + rhat[2] * mhat[2]
    A = p.k_e * p.q_src * p.q_test
    rad = A * (1.0 + p.chi * (nu * nu - 1.0 / 3.0)) / r2
    perp_coef = -2.0 * A * p.chi * nu / r2
    mx_perp = mhat[0] - nu * rhat[0]
    my_perp = mhat[1] - nu * rhat[1]
    mz_perp = mhat[2] - nu * rhat[2]
    Fx = rad * rhat[0] + perp_coef * mx_perp
    Fy = rad * rhat[1] + perp_coef * my_perp
    Fz = rad * rhat[2] + perp_coef * mz_perp
    return (Fx, Fy, Fz)


def sampler(seed: int) -> CoulombGamma51Params:
    rng = np.random.default_rng(seed)
    k_e = K_E_DEFAULT * loguniform(rng, 0.5, 2.0)
    chi = float(rng.uniform(CHI_MIN, CHI_MAX))
    u = rng.uniform(-1.0, 1.0)
    phi = rng.uniform(0.0, 2.0 * math.pi)
    s = math.sqrt(1.0 - u * u)
    mx, my, mz = s * math.cos(phi), s * math.sin(phi), u
    q_src = -1.0e-6
    q_test = 1.0e-6
    return CoulombGamma51Params(
        k_e=k_e, q_src=q_src, q_test=q_test, chi=chi,
        mx=mx, my=my, mz=mz, m=1.0e-3,
        x0=1.0, y0=0.0, z0=0.0,
        vx0=0.0, vy0=0.1, vz0=0.0,
    )


def validator(p) -> bool:
    if not isinstance(p, CoulombGamma51Params):
        return False
    if not (CHI_MIN <= p.chi <= CHI_MAX):
        return False
    if p.chi >= 0.5:
        return False
    if p.m <= 0 or p.k_e <= 0:
        return False
    norm = math.sqrt(p.mx ** 2 + p.my ** 2 + p.mz ** 2)
    if abs(norm - 1.0) > 1e-6:
        return False
    if math.sqrt(p.x0 ** 2 + p.y0 ** 2 + p.z0 ** 2) <= 0:
        return False
    return True


class _Sim:
    def __init__(self, p: CoulombGamma51Params) -> None:
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
        return {"t": float(t), "x": x, "y": yc, "z": z,
                "vx": vx, "vy": vy, "vz": vz}


def build(*, params: CoulombGamma51Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-5-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "y": "m", "z": "m"},
    "outputs": {"Fx": "kg*m*s**-2", "Fy": "kg*m*s**-2", "Fz": "kg*m*s**-2"},
    "params": {"k_e": "kg*m**3*s**-4*A**-2", "q_src": "A*s",
               "q_test": "A*s", "chi": "1", "m": "kg"},
}

__all__ = ["CoulombGamma51Params", "shifted_force", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
