"""γ-5-2 — Coulomb saturating-potential nonlinearity (LIN/superposition break).

Catalog (ROUND-2 FINAL): φ_lin(x) = Σ_j k q_j / |x − x_j|;
φ_eff = φ_lin + ξ φ_lin³ / (φ_lin² + φ₀²).
E_eff = −∇φ_eff = (dφ_eff/dφ_lin) · (−∇φ_lin).
F = q_test · E_eff.
Broken: LIN (superposition). Conservative.

Sim setup: 2 fixed point sources + 1 mobile test charge in 3D.
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
XI_MIN, XI_MAX = 0.05, 0.5


@dataclass(frozen=True)
class CoulombGamma52Params:
    k_e: float
    xi: float
    phi0: float           # saturation voltage V
    q_test: float
    m: float
    # Two source charges: positions and charges
    src1_q: float
    src1_x: float
    src1_y: float
    src1_z: float
    src2_q: float
    src2_x: float
    src2_y: float
    src2_z: float
    x0: float
    y0: float
    z0: float
    vx0: float
    vy0: float
    vz0: float


def _phi_lin_and_grad(pos: Tuple[float, float, float],
                      p: CoulombGamma52Params) -> Tuple[float, Tuple[float, float, float]]:
    x, y, z = pos
    phi = 0.0
    gx = gy = gz = 0.0
    for q, sx, sy, sz in (
        (p.src1_q, p.src1_x, p.src1_y, p.src1_z),
        (p.src2_q, p.src2_x, p.src2_y, p.src2_z),
    ):
        dx, dy, dz = x - sx, y - sy, z - sz
        r2 = dx * dx + dy * dy + dz * dz
        r = math.sqrt(r2)
        if r == 0.0:
            continue
        phi += p.k_e * q / r
        coef = -p.k_e * q / (r2 * r)  # = ∂/∂x of (k q / r) (with extra sign)
        # ∇(1/r) = -r̂/r² = -(dx,dy,dz)/r³
        gx += coef * dx
        gy += coef * dy
        gz += coef * dz
    return phi, (gx, gy, gz)


def shifted_force(pos: Tuple[float, float, float],
                  p: CoulombGamma52Params) -> Tuple[float, float, float]:
    phi_lin, grad_phi = _phi_lin_and_grad(pos, p)
    phi2 = phi_lin * phi_lin
    denom = phi2 + p.phi0 * p.phi0
    # dφ_eff/dφ_lin = 1 + ξ · φ_lin²(φ_lin² + 3 φ₀²)/(φ_lin² + φ₀²)²
    dphi_eff = 1.0 + p.xi * phi2 * (phi2 + 3.0 * p.phi0 * p.phi0) / (denom * denom)
    # E_eff = -∇φ_eff = -(dφ_eff/dφ_lin) · ∇φ_lin
    Ex = -dphi_eff * grad_phi[0]
    Ey = -dphi_eff * grad_phi[1]
    Ez = -dphi_eff * grad_phi[2]
    return (p.q_test * Ex, p.q_test * Ey, p.q_test * Ez)


def sampler(seed: int) -> CoulombGamma52Params:
    rng = np.random.default_rng(seed)
    k_e = K_E_DEFAULT * loguniform(rng, 0.5, 2.0)
    xi = float(rng.uniform(XI_MIN, XI_MAX))
    # Typical voltage on the order of k_e * q / r_typ
    q_typ = 1.0e-6
    r_typ = 1.0
    phi_typical = k_e * q_typ / r_typ
    phi0 = phi_typical * loguniform(rng, 0.1, 10.0)
    return CoulombGamma52Params(
        k_e=k_e, xi=xi, phi0=phi0, q_test=1.0e-9, m=1.0e-3,
        src1_q=q_typ, src1_x=-0.5, src1_y=0.0, src1_z=0.0,
        src2_q=-q_typ, src2_x=0.5, src2_y=0.0, src2_z=0.0,
        x0=0.0, y0=0.3, z0=0.0,
        vx0=0.0, vy0=0.0, vz0=0.0,
    )


def validator(p) -> bool:
    if not isinstance(p, CoulombGamma52Params):
        return False
    if not (XI_MIN <= p.xi <= XI_MAX):
        return False
    if p.xi >= 1.0:
        return False
    if p.m <= 0 or p.k_e <= 0 or p.phi0 <= 0:
        return False
    return True


class _Sim:
    def __init__(self, p: CoulombGamma52Params) -> None:
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
                        method="DOP853", rtol=1e-8, atol=1e-11, dense_output=True)
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


def build(*, params: CoulombGamma52Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-5-2 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "y": "m", "z": "m"},
    "outputs": {"Fx": "kg*m*s**-2", "Fy": "kg*m*s**-2", "Fz": "kg*m*s**-2"},
    "params": {"k_e": "kg*m**3*s**-4*A**-2", "xi": "1",
               "phi0": "kg*m**2*s**-3*A**-1", "q_test": "A*s", "m": "kg"},
}

__all__ = ["CoulombGamma52Params", "shifted_force", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
