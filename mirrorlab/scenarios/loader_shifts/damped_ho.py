"""Per-shift truth-form grid builders for the damped harmonic oscillator domain.

Blueprint-xy §3.2 / §4 rows 7-9 + baseline.

- baseline   inputs {x, v}, GT ẍ = −(k/m)·x − (c/m)·v
- γ-3-1      inputs {x, v}, GT ẍ = −2γv − ω₀²(1 + κ·x_ref⁻²·⟨x²⟩)·x.
             ⟨x²⟩ is a running average; for a static grid we approximate
             ⟨x²⟩ ≈ x² at the current point (single-point proxy; the
             true rolling-window value is only available during sim
             trajectories — blueprint §9 Q4 left this as a P2 trade-off).
- γ-3-2      inputs {x, v, t}, GT ẍ = −2γv − ω₀²[1 + ε·cos(Ω_p·t)]·x
- δ-3-1      inputs {x, v}, GT ẍ = −2γ·(|x|/L − 1)·v − ω₀²·x
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

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
    damped_ho_d_3_1 as _d31,
    damped_ho_g_3_1 as _g31,
    damped_ho_g_3_2 as _g32,
)


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim: Any, seed: int, magnitude: float):
    x_amp = abs(_attr(sim.params, ("x0",), 1.0)) or 1.0
    v_amp = abs(_attr(sim.params, ("v0",), 1.0)) or 1.0

    def gt(inputs):
        x, v = inputs["x"], inputs["v"]

        def fn(p):
            k = _attr(p, ("k",), 1.0)
            c = _attr(p, ("c",), 0.0)
            m = _attr(p, ("m",), 1.0)
            return -(k / m) * x - (c / m) * v

        return fn

    def build(rng, mode):
        xs = _ood_signed(x_amp, _GRID_SIZE) if mode == "b" else _linspace_signed(x_amp, _GRID_SIZE)
        vs = rng.uniform(-v_amp, v_amp, size=_GRID_SIZE)
        return [({"x": float(x), "v": float(v)}, gt({"x": float(x), "v": float(v)}))
                for x, v in zip(xs, vs)]

    return _pack(seed, magnitude, sim, build)


# ---- γ-3-1 (saturating amplitude-dependent stiffness) ----------------------

def gamma_3_1_grids(sim: Any, seed: int, magnitude: float):
    # Reference amplitude for the running x²_mean proxy: use the catalog's
    # x_ref so the proxy lands in the regime where κ·x²/x_ref² is O(1).
    x_amp = abs(_attr(sim.params, ("x_ref", "x0"), 1.0)) or 1.0
    v_amp = x_amp  # natural velocity scale at ω~1

    def gt(inputs):
        x, v = inputs["x"], inputs["v"]
        x2_mean = x * x  # single-point proxy for ⟨x²⟩

        def fn(p):
            return float(_g31.shifted_law(x, v, x2_mean, p))

        return fn

    def build(rng, mode):
        xs = _ood_signed(x_amp, _GRID_SIZE) if mode == "b" else _linspace_signed(x_amp, _GRID_SIZE)
        vs = rng.uniform(-v_amp, v_amp, size=_GRID_SIZE)
        return [({"x": float(x), "v": float(v)}, gt({"x": float(x), "v": float(v)}))
                for x, v in zip(xs, vs)]

    return _pack(seed, magnitude, sim, build)


# ---- γ-3-2 (parametric drive, +t) ------------------------------------------

def gamma_3_2_grids(sim: Any, seed: int, magnitude: float):
    x_amp = abs(_attr(sim.params, ("x0",), 1.0)) or 1.0
    v_amp = abs(_attr(sim.params, ("v0",), x_amp)) or x_amp
    Omega_p = float(_attr(sim.params, ("Omega_p",), 1.0)) or 1.0
    period = 2.0 * math.pi / Omega_p

    def gt(inputs):
        x, v, t = inputs["x"], inputs["v"], inputs["t"]

        def fn(p):
            return float(_g32.shifted_law(x, v, t, p))

        return fn

    def build(rng, mode):
        xs = _ood_signed(x_amp, _GRID_SIZE) if mode == "b" else _linspace_signed(x_amp, _GRID_SIZE)
        vs = rng.uniform(-v_amp, v_amp, size=_GRID_SIZE)
        if mode == "b":
            ts = np.linspace(2.0 * period, 5.0 * period, _GRID_SIZE)
        else:
            ts = np.linspace(0.0, 2.0 * period, _GRID_SIZE)
        pts = []
        for x, v, t in zip(xs, vs, ts):
            ins = {"x": float(x), "v": float(v), "t": float(t)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-3-1 (gated drag) ----------------------------------------------------

def delta_3_1_grids(sim: Any, seed: int, magnitude: float):
    # Drag activates when |x| > L; sample beyond L on both sides so the
    # gate flips sign.
    L_amp = abs(_attr(sim.params, ("L",), 1.0)) or 1.0
    v_amp = L_amp

    def gt(inputs):
        x, v = inputs["x"], inputs["v"]

        def fn(p):
            return float(_d31.shifted_law(x, v, p))

        return fn

    def build(rng, mode):
        if mode == "b":
            xs = _ood_signed(L_amp, _GRID_SIZE)
        else:
            xs = _linspace_signed(2.0 * L_amp, _GRID_SIZE)
        vs = rng.uniform(-v_amp, v_amp, size=_GRID_SIZE)
        return [({"x": float(x), "v": float(v)}, gt({"x": float(x), "v": float(v)}))
                for x, v in zip(xs, vs)]

    return _pack(seed, magnitude, sim, build)


_shifts.register("damped_ho", "baseline", baseline_grids)
_shifts.register("damped_ho", "gamma_3_1", gamma_3_1_grids)
_shifts.register("damped_ho", "gamma_3_2", gamma_3_2_grids)
_shifts.register("damped_ho", "delta_3_1", delta_3_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_3_1_grids",
    "gamma_3_2_grids",
    "delta_3_1_grids",
]
