"""Per-shift truth-form grid builders for the Coulomb domain.

Blueprint-xy §3.2, §4 rows 13-15 + baseline.

- baseline   inputs ``{r}``, GT ``k_e·q1·q2/r²``
- γ-5-1 ROT  inputs ``{x,y,z}``, GT signed-|F|·r̂ from shifted_force
- γ-5-2 sat  inputs ``{x,y,z}`` (test charge position); GT signed-|F|·r̂
             from 2-source saturating shifted_force (sources are
             closure constants from sim.params, not grid keys —
             they are boundary conditions, not law-coefficient
             perturbation targets)
- δ-5-1      inputs ``{q1, q2}``, GT ``‖dq/dt‖`` from shifted_law.
             Note: charge positions stay fixed (BC, not grid axis).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import (
    _GRID_SIZE,
    _OOD_FACTOR,
    _attr,
    _linspace_signed,
    _ood_signed,
    _pack,
)
from mirrorlab.shifts import (
    coulomb_d_5_1 as _d51,
    coulomb_g_5_1 as _g51,
    coulomb_g_5_2 as _g52,
)


# Shared with gravity.py — biased μ schedule so anisotropic ξ·(μ²−1/3)
# term does not average to zero. Reuses gravity's <μ²> ≈ 0.67 layout.
_MU_SCHEDULE = np.concatenate([
    np.linspace(-1.0, -0.7, 5),
    np.array([0.0]),
    np.linspace(0.7, 1.0, 5),
])


def _signed_radial_magnitude_3d(F: Tuple[float, float, float],
                                 rhat: Tuple[float, float, float]) -> float:
    dot = F[0] * rhat[0] + F[1] * rhat[1] + F[2] * rhat[2]
    mag = math.sqrt(F[0] ** 2 + F[1] ** 2 + F[2] ** 2)
    return math.copysign(mag, dot) if dot != 0.0 else mag


def _xyz_at(r: float, mu: float, nhat: Tuple[float, float, float],
            rng: np.random.Generator) -> Tuple[float, float, float]:
    """Sample a position at radius ``r`` and polar angle ``cos⁻¹ μ`` from ``n̂``.

    Identical construction to gravity.py: build an orthonormal frame
    aligned with ``n̂`` and draw a random azimuth.
    """
    sin_theta = math.sqrt(max(0.0, 1.0 - mu * mu))
    nx, ny, nz = nhat
    helper = (0.0, 0.0, 1.0) if abs(nz) < 0.9 else (1.0, 0.0, 0.0)
    e1x = ny * helper[2] - nz * helper[1]
    e1y = nz * helper[0] - nx * helper[2]
    e1z = nx * helper[1] - ny * helper[0]
    e1n = math.sqrt(e1x * e1x + e1y * e1y + e1z * e1z) or 1.0
    e1 = (e1x / e1n, e1y / e1n, e1z / e1n)
    e2 = (
        ny * e1[2] - nz * e1[1],
        nz * e1[0] - nx * e1[2],
        nx * e1[1] - ny * e1[0],
    )
    phi = float(rng.uniform(0.0, 2.0 * math.pi))
    rhat = (
        mu * nx + sin_theta * (math.cos(phi) * e1[0] + math.sin(phi) * e2[0]),
        mu * ny + sin_theta * (math.cos(phi) * e1[1] + math.sin(phi) * e2[1]),
        mu * nz + sin_theta * (math.cos(phi) * e1[2] + math.sin(phi) * e2[2]),
    )
    return (r * rhat[0], r * rhat[1], r * rhat[2])


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim: Any, seed: int, magnitude: float):
    r0 = abs(_attr(sim.params, ("r0",), 1.0)) or 1.0

    def gt(inputs: Dict[str, float]):
        r = inputs["r"]

        def fn(p):
            k_e = _attr(p, ("k_e",), 8.9875517873681764e9)
            q1 = _attr(p, ("q1", "q_src"), 1.0e-9)
            q2 = _attr(p, ("q2", "q_test"), 1.0e-9)
            return k_e * q1 * q2 / (r * r)

        return fn

    def build(rng, mode):
        if mode == "b":
            rs = np.linspace(1.5 * r0, _OOD_FACTOR * r0, _GRID_SIZE)
        else:
            rs = np.linspace(0.5 * r0, 1.5 * r0, _GRID_SIZE)
        return [({"r": float(r)}, gt({"r": float(r)})) for r in rs]

    return _pack(seed, magnitude, sim, build)


# ---- γ-5-1 (ROT 3D anisotropic) --------------------------------------------

def gamma_5_1_grids(sim: Any, seed: int, magnitude: float):
    r0 = abs(_attr(sim.params, ("x0",), 1.0)) or 1.0
    mhat = (
        float(_attr(sim.params, ("mx",), 0.0)),
        float(_attr(sim.params, ("my",), 0.0)),
        float(_attr(sim.params, ("mz",), 1.0)),
    )

    def gt(inputs: Dict[str, float]):
        x, y, z = inputs["x"], inputs["y"], inputs["z"]
        r = math.sqrt(x * x + y * y + z * z)
        if r == 0.0:
            return lambda _p: 0.0
        rhat = (x / r, y / r, z / r)

        def fn(p):
            F = _g51.shifted_force((x, y, z), p)
            return _signed_radial_magnitude_3d(F, rhat)

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            radii = np.linspace(1.5 * r0, _OOD_FACTOR * r0, _GRID_SIZE)
        else:
            radii = np.linspace(0.5 * r0, 1.5 * r0, _GRID_SIZE)
        pts: List[Tuple[Dict[str, float], Any]] = []
        for r, mu in zip(radii, _MU_SCHEDULE):
            pos = _xyz_at(float(r), float(mu), mhat, rng)
            ins = {"x": pos[0], "y": pos[1], "z": pos[2]}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-5-2 (saturating, 2 fixed sources + 1 mobile test charge) ------------

def gamma_5_2_grids(sim: Any, seed: int, magnitude: float):
    # The test charge moves in 3D; source positions are fixed BC. Sample
    # test positions around the midpoint of the two sources where the
    # saturating term dominates (potential is large near a source).
    src1 = (
        float(_attr(sim.params, ("src1_x",), -0.5)),
        float(_attr(sim.params, ("src1_y",), 0.0)),
        float(_attr(sim.params, ("src1_z",), 0.0)),
    )
    src2 = (
        float(_attr(sim.params, ("src2_x",), 0.5)),
        float(_attr(sim.params, ("src2_y",), 0.0)),
        float(_attr(sim.params, ("src2_z",), 0.0)),
    )
    mid = ((src1[0] + src2[0]) / 2, (src1[1] + src2[1]) / 2, (src1[2] + src2[2]) / 2)
    sep = math.sqrt(
        (src1[0] - src2[0]) ** 2
        + (src1[1] - src2[1]) ** 2
        + (src1[2] - src2[2]) ** 2
    ) or 1.0
    # Sample at radii from 0.5·sep to 1.5·sep around the midpoint, with
    # random direction. The saturating nonlinearity bites at large φ_lin,
    # which is largest near a source — so the tighter radii expose the
    # γ shift more.
    r_amp = 0.5 * sep

    def gt(inputs: Dict[str, float]):
        x, y, z = inputs["x"], inputs["y"], inputs["z"]
        r = math.sqrt(
            (x - mid[0]) ** 2 + (y - mid[1]) ** 2 + (z - mid[2]) ** 2
        )
        if r == 0.0:
            return lambda _p: 0.0
        rhat = ((x - mid[0]) / r, (y - mid[1]) / r, (z - mid[2]) / r)

        def fn(p):
            F = _g52.shifted_force((x, y, z), p)
            return _signed_radial_magnitude_3d(F, rhat)

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            radii = np.linspace(1.5 * r_amp, _OOD_FACTOR * r_amp, _GRID_SIZE)
        else:
            radii = np.linspace(0.3 * r_amp, 1.3 * r_amp, _GRID_SIZE)
        pts = []
        for r in radii:
            # Random direction from the midpoint.
            u = float(rng.uniform(-1.0, 1.0))
            ph = float(rng.uniform(0.0, 2.0 * math.pi))
            s = math.sqrt(1.0 - u * u)
            dx, dy, dz = s * math.cos(ph), s * math.sin(ph), u
            x = mid[0] + float(r) * dx
            y = mid[1] + float(r) * dy
            z = mid[2] + float(r) * dz
            ins = {"x": x, "y": y, "z": z}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-5-1 (charge leakage dynamics) ---------------------------------------

def delta_5_1_grids(sim: Any, seed: int, magnitude: float):
    """GT is ``‖dq/dt‖`` (Euclidean norm of the charge-rate vector).

    Inputs are the two instantaneous charges (q1, q2). Charge positions
    are fixed BC (carried by sim.params), so the E-field-coupling rate
    depends only on the charges. Sample charges in a band around the
    initial values so dq/dt is non-trivially shift-dependent on every
    point.
    """
    q1_amp = abs(_attr(sim.params, ("q1_0",), 1.0e-6)) or 1.0e-6
    q2_amp = abs(_attr(sim.params, ("q2_0",), 1.0e-6)) or 1.0e-6

    def gt(inputs: Dict[str, float]):
        q1, q2 = inputs["q1"], inputs["q2"]

        def fn(p):
            dq1, dq2 = _d51.shifted_law(q1, q2, p)
            return math.sqrt(dq1 * dq1 + dq2 * dq2)

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            q1s = _ood_signed(q1_amp, _GRID_SIZE)
            q2s = _ood_signed(q2_amp, _GRID_SIZE)
        else:
            q1s = _linspace_signed(q1_amp, _GRID_SIZE)
            q2s = _linspace_signed(q2_amp, _GRID_SIZE)
        # Shuffle q2 so each grid point pairs a non-trivial (q1, q2).
        q2s_shuffled = rng.permutation(q2s)
        pts = []
        for q1, q2 in zip(q1s, q2s_shuffled):
            ins = {"q1": float(q1), "q2": float(q2)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# Register all four. setdefault in loader_shifts.register_legacy_dispatch
# preserves these.
_shifts.register("coulomb", "baseline", baseline_grids)
_shifts.register("coulomb", "gamma_5_1", gamma_5_1_grids)
_shifts.register("coulomb", "gamma_5_2", gamma_5_2_grids)
_shifts.register("coulomb", "delta_5_1", delta_5_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_5_1_grids",
    "gamma_5_2_grids",
    "delta_5_1_grids",
]
