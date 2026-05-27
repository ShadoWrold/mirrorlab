"""Per-shift truth-form grid builders for the Hooke domain.

Blueprint-xy §3.2, §4 rows 1-3 + baseline. Replaces the Sprint-1
``_hooke_test_grids`` ndarray path with the post-XY tuple-list contract:

- baseline   inputs ``{x}``, GT ``-k·x``
- γ-1-1      inputs ``{x}``, GT ``-k·x·[1 + η·tanh(x/x₀)]``
- γ-1-2 (ROT) inputs ``{x, y}``, GT ``signed-|F|·r̂`` projection
- δ-1-1      inputs ``{x, v}``, GT ``-k·x − c·(x²/L²)·v``

γ-1-2 reuses the gravity ROT projection convention (blueprint §2.5):
the scalar truth is the radial-projected force magnitude with the sign
of the radial component. The grid samples ``θ`` away from the
anisotropy nodes so the ξ correction is observable in the scalar
projection.
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
    hooke_d_1_1 as _d11,
    hooke_g_1_1 as _g11,
    hooke_g_1_2 as _g12,
)


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim: Any, seed: int, magnitude: float):
    x_amp = abs(_attr(sim.params, ("x0",), 1.0)) or 1.0

    def gt(inputs: Dict[str, float]):
        x = inputs["x"]

        def fn(p):
            k = _attr(p, ("k",), 1.0)
            return -k * x

        return fn

    def build(rng, mode):
        xs = _ood_signed(x_amp, _GRID_SIZE) if mode == "b" else _linspace_signed(x_amp, _GRID_SIZE)
        return [({"x": float(x)}, gt({"x": float(x)})) for x in xs]

    return _pack(seed, magnitude, sim, build)


# ---- γ-1-1 (saturating asymmetric, 1D) -------------------------------------

def gamma_1_1_grids(sim: Any, seed: int, magnitude: float):
    x_amp = abs(_attr(sim.params, ("x_scale", "x0"), 1.0)) or 1.0

    def gt(inputs: Dict[str, float]):
        x = inputs["x"]

        def fn(p):
            return float(_g11.shifted_force(x, p))

        return fn

    def build(rng, mode):
        xs = _ood_signed(x_amp, _GRID_SIZE) if mode == "b" else _linspace_signed(x_amp, _GRID_SIZE)
        return [({"x": float(x)}, gt({"x": float(x)})) for x in xs]

    return _pack(seed, magnitude, sim, build)


# ---- γ-1-2 (2D ROT anisotropic stiffness) ----------------------------------

# θ schedule biased toward where ξ·cos(2(θ−φ)) is large in magnitude
# (i.e. avoid θ ≈ φ ± π/4 zero crossings). For φ unknown at grid-build
# time, sample a spread of θ values across [0, π); the average over
# this schedule guarantees ⟨cos(2(θ−φ))²⟩ > 0 for any φ.
_THETA_SCHEDULE_A = np.linspace(0.0, math.pi, _GRID_SIZE, endpoint=False)


def _signed_radial_magnitude_2d(Fx: float, Fy: float,
                                 rhat_x: float, rhat_y: float) -> float:
    dot = Fx * rhat_x + Fy * rhat_y
    mag = math.sqrt(Fx * Fx + Fy * Fy)
    return math.copysign(mag, dot) if dot != 0.0 else mag


def gamma_1_2_grids(sim: Any, seed: int, magnitude: float):
    r_amp = abs(_attr(sim.params, ("x0",), 1.0)) or 1.0

    def gt(inputs: Dict[str, float]):
        x, y = inputs["x"], inputs["y"]
        r = math.sqrt(x * x + y * y)
        if r == 0.0:
            return lambda _p: 0.0
        rhat = (x / r, y / r)

        def fn(p):
            Fx, Fy = _g12.shifted_force((x, y), p)
            return _signed_radial_magnitude_2d(Fx, Fy, rhat[0], rhat[1])

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            radii = np.linspace(1.5 * r_amp, _OOD_FACTOR * r_amp, _GRID_SIZE)
        else:
            radii = np.linspace(0.5 * r_amp, 1.5 * r_amp, _GRID_SIZE)
        pts: List[Tuple[Dict[str, float], Any]] = []
        for r, th in zip(radii, _THETA_SCHEDULE_A):
            x = float(r) * math.cos(float(th))
            y = float(r) * math.sin(float(th))
            ins = {"x": x, "y": y}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-1-1 (amplitude-conditioned drag, 1D with v) -------------------------

def delta_1_1_grids(sim: Any, seed: int, magnitude: float):
    # The drag term ``-c·(x²/L²)·v`` is quadratic in x and linear in v
    # but the catalog default sampler gives c ~ 1e-3 and L ~ 0.5, so at
    # x ~ x0 ~ 0.1 the drag is ~1e-4 of the spring force. To make the
    # truth predictor measurably outscore the baseline ``-k·x``, sample
    # both x and v near the catalog's safety bound rather than near
    # the IC amplitude. ``L`` is the natural amplitude scale for the
    # drag-onset term, so reuse it for both axes.
    L_amp = abs(_attr(sim.params, ("L",), 1.0)) or 1.0

    def gt(inputs: Dict[str, float]):
        x, v = inputs["x"], inputs["v"]

        def fn(p):
            return float(_d11.shifted_force(x, v, p))

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            xs = _ood_signed(L_amp, _GRID_SIZE)
        else:
            xs = _linspace_signed(L_amp, _GRID_SIZE)
        # Drag scales as x² so the inner half of xs has weak drag; pair
        # those points with v near the upper bound so every grid point
        # carries a measurable truth-vs-baseline gap.
        vs = rng.uniform(-2.0 * L_amp, 2.0 * L_amp, size=len(xs))
        pts = []
        for x, v in zip(xs, vs):
            ins = {"x": float(x), "v": float(v)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# Register all four at import. loader_shifts.register_legacy_dispatch
# uses setdefault and will not overwrite these.
_shifts.register("hooke", "baseline", baseline_grids)
_shifts.register("hooke", "gamma_1_1", gamma_1_1_grids)
_shifts.register("hooke", "gamma_1_2", gamma_1_2_grids)
_shifts.register("hooke", "delta_1_1", delta_1_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_1_1_grids",
    "gamma_1_2_grids",
    "delta_1_1_grids",
]
