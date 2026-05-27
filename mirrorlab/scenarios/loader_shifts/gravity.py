"""Per-shift truth-form grid builders for the Gravity domain.

Blueprint-xy §3.2, §4 row 4 (γ-2-1). Each builder constructs (a)/(b)/(c)
sub-grids whose ground-truth values invoke the shift's actual
``shifted_force`` from ``mirrorlab.shifts.gravity_*`` rather than the
baseline ``-G·M·m/r²`` closure that the pre-XY loader used. Inputs are
expanded to the shift's discriminating axes — γ-2-1 needs 3D positions
because the anisotropic correction lives in ``μ = r̂ · n̂``, a scalar that
is identically zero-mean over a uniform-direction sample.

Convention (§2.5): the scalar ground truth is the **signed magnitude of
the force projected onto the unit radial direction**, i.e.
``GT = sign(F · r̂) · |F|``. This reduces to ``−G·M·m/r²`` on baseline
(no transverse component, μ undefined / irrelevant) and exposes the γ-2-1
quadrupole correction by varying with ``μ²``.
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
    _pack,
)
from mirrorlab.shifts import gravity_g_2_1 as _g221


# Direction-biased μ values that DELIBERATELY avoid the ⟨μ²⟩ = 1/3 mean
# of a uniform spherical sample (blueprint §4 row 4 sampling concern).
# Sample preferentially near the poles (|μ| → 1) where the anisotropic
# term ξ·(μ²−1/3) is largest in magnitude, so the γ-2-1 quadrupole
# correction dominates the scalar projection. Reused on (a) and (c);
# (b) shifts to OOD radii but keeps the same μ schedule so direction
# bias does not confound radius OOD. Empirical ⟨μ²⟩ ≈ 0.66 with this
# schedule (verified by tests/scenarios/test_loader_xy.py).
_MU_SCHEDULE_A = np.concatenate([
    np.linspace(-1.0, -0.7, 5),
    np.array([0.0]),  # pin one equator point so all-pole sampling is not assumed
    np.linspace(0.7, 1.0, 5),
])


def _signed_radial_magnitude(F: Tuple[float, float, float],
                              rhat: Tuple[float, float, float]) -> float:
    """Return ``sign(F·r̂) · |F|`` per blueprint §2.5 projection convention."""
    dot = F[0] * rhat[0] + F[1] * rhat[1] + F[2] * rhat[2]
    mag = math.sqrt(F[0] ** 2 + F[1] ** 2 + F[2] ** 2)
    return math.copysign(mag, dot) if dot != 0.0 else mag


def _xyz_at(r: float, mu: float, nhat: Tuple[float, float, float],
            rng: np.random.Generator) -> Tuple[float, float, float]:
    """Sample a position at radius ``r`` and angle ``cos⁻¹(μ)`` from ``n̂``.

    ``μ = r̂·n̂`` only fixes the polar angle relative to ``n̂``; the azimuth
    around ``n̂`` is irrelevant for γ-2-1's quadrupole (it depends only on
    ``μ²``), but the truth law is still vector-valued so we draw an
    azimuth uniformly to break tie cases. The sampled ``r̂`` is
    constructed by rotating ``n̂`` by the polar angle and then by a random
    azimuth around ``n̂``.
    """
    # Polar angle θ such that cos θ = μ.
    sin_theta = math.sqrt(max(0.0, 1.0 - mu * mu))
    # Build an orthonormal frame {n̂, ê1, ê2} so we can rotate.
    nx, ny, nz = nhat
    # Pick a helper vector not parallel to n̂.
    if abs(nz) < 0.9:
        helper = (0.0, 0.0, 1.0)
    else:
        helper = (1.0, 0.0, 0.0)
    # ê1 = (n̂ × helper)/|...|
    e1x = ny * helper[2] - nz * helper[1]
    e1y = nz * helper[0] - nx * helper[2]
    e1z = nx * helper[1] - ny * helper[0]
    e1n = math.sqrt(e1x * e1x + e1y * e1y + e1z * e1z) or 1.0
    e1 = (e1x / e1n, e1y / e1n, e1z / e1n)
    # ê2 = n̂ × ê1
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


def gamma_2_1_grids(sim: Any, seed: int, magnitude: float):
    """Truth-form (a)/(b)/(c) grids for gravity γ-2-1.

    The grid points are 3-D ``{x, y, z}`` tuples. GT at each point is
    ``signed-|F|·r̂`` from ``shifted_force(pos, params)``. Direction
    sampling is deliberately biased away from ``⟨μ²⟩ = 1/3`` so the γ-2-1
    quadrupole correction is observable in the scalar projection
    (blueprint §4 row 4 sampling concern).
    """
    r0 = abs(_attr(sim.params, ("x0",), 1.0e7)) or 1.0e7
    nhat = (
        float(_attr(sim.params, ("nx",), 0.0)),
        float(_attr(sim.params, ("ny",), 0.0)),
        float(_attr(sim.params, ("nz",), 1.0)),
    )

    def gt(inputs: Dict[str, float]):
        x, y, z = inputs["x"], inputs["y"], inputs["z"]
        r = math.sqrt(x * x + y * y + z * z)
        if r == 0.0:
            return lambda _p: 0.0
        rhat = (x / r, y / r, z / r)

        def fn(p):
            F = _g221.shifted_force((x, y, z), p)
            return _signed_radial_magnitude(F, rhat)

        return fn

    def build(rng: np.random.Generator, mode: str) -> List[Tuple[Dict[str, float], Any]]:
        if mode == "b":
            radii = np.linspace(1.5 * r0, _OOD_FACTOR * r0, _GRID_SIZE)
        else:
            radii = np.linspace(0.5 * r0, 1.5 * r0, _GRID_SIZE)
        pts: List[Tuple[Dict[str, float], Any]] = []
        for r, mu in zip(radii, _MU_SCHEDULE_A):
            pos = _xyz_at(float(r), float(mu), nhat, rng)
            ins = {"x": pos[0], "y": pos[1], "z": pos[2]}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# Register at import — the loader's ``register_legacy_dispatch`` uses
# ``setdefault`` and therefore will NOT overwrite this entry.
_shifts.register("gravity", "gamma_2_1", gamma_2_1_grids)


__all__ = ["gamma_2_1_grids"]
