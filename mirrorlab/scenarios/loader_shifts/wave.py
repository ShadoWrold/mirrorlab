"""Per-shift truth-form grid builders for the wave domain.

Blueprint-xy §3.2 / §4 rows 19-21 + baseline. Output is wave amplitude
u at the probe location. The shift modules' Instance.step(t) gives u(t)
directly; we use step()-based truth uniformly.

- baseline   inputs {t}, GT u(t) = A·sin(k·x_probe − c·k·t)
- γ-8-1      inputs {t}, GT via shifted_omega_squared (closed-form sin)
- γ-8-2      inputs {t}, GT via shifted_omega_squared (closed-form sin)
- δ-8-1      inputs {t}, GT via Instance.step() — wavepacket decay ODE
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    wave_d_8_1 as _d81,
    wave_g_8_1 as _g81,
    wave_g_8_2 as _g82,
)


def _t_grid(period: float, mode: str) -> np.ndarray:
    if mode == "b":
        return np.linspace(2.0 * period, 5.0 * period, _GRID_SIZE)
    return np.linspace(0.0, 2.0 * period, _GRID_SIZE)


# ---- baseline (sin(kx − ωt) with ω = c·k) ----------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    k0 = abs(_attr(p_sim, ("k",), 1.0)) or 1.0
    c0 = abs(_attr(p_sim, ("c",), 1.0)) or 1.0
    x_probe = float(_attr(p_sim, ("x_probe",), 0.0))
    omega0 = c0 * k0
    period = 2.0 * math.pi / max(omega0, 1e-12)

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            A = _attr(p, ("A",), 1.0)
            k = _attr(p, ("k",), 1.0)
            c = _attr(p, ("c",), 1.0)
            phi = _attr(p, ("phi",), 0.0)
            arg = k * x_probe - c * k * t + phi
            return A * math.sin(arg)

        return fn

    def build(rng, mode):
        ts = _t_grid(period, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-8-1 (dispersion modification) ---------------------------------------

def gamma_8_1_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    k0 = abs(_attr(p_sim, ("k",), 1.0)) or 1.0
    c0 = abs(_attr(p_sim, ("c",), 1.0)) or 1.0
    period = 2.0 * math.pi / max(c0 * k0, 1e-12)

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            w2 = _g81.shifted_omega_squared(p)
            omega = math.sqrt(max(w2, 0.0))
            arg = p.k * p.x_probe - omega * t
            return p.A * math.sin(arg)

        return fn

    def build(rng, mode):
        ts = _t_grid(period, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-8-2 (angle-dependent dispersion) ------------------------------------

def gamma_8_2_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    k0 = abs(_attr(p_sim, ("k",), 1.0)) or 1.0
    c0 = abs(_attr(p_sim, ("c",), 1.0)) or 1.0
    period = 2.0 * math.pi / max(c0 * k0, 1e-12)

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            w2 = _g82.shifted_omega_squared(p)
            omega = math.sqrt(max(w2, 0.0))
            arg = p.k * p.x_probe - omega * t
            return p.A * math.sin(arg)

        return fn

    def build(rng, mode):
        ts = _t_grid(period, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- δ-8-1 (wavepacket decay, step-based) ----------------------------------

def delta_8_1_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    k0 = abs(_attr(p_sim, ("k",), 1.0)) or 1.0
    c0 = abs(_attr(p_sim, ("c",), 1.0)) or 1.0
    period = 2.0 * math.pi / max(c0 * k0, 1e-12)

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            # The catalog Instance validates its params; cf perturbation
            # routinely steps outside the sampler band, so fall back to
            # the baseline sin if the Instance refuses to build.
            try:
                inst = _d81.WaveDelta81Instance(p)
            except (ValueError, TypeError):
                A = _attr(p, ("A",), 1.0)
                k = _attr(p, ("k",), 1.0)
                c = _attr(p, ("c",), 1.0)
                return A * math.sin(k * float(_attr(p_sim, ("x_probe",), 0.0)) - c * k * t)
            return inst.step(t)["u"]

        return fn

    def build(rng, mode):
        ts = _t_grid(period, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


_shifts.register("wave", "baseline", baseline_grids)
_shifts.register("wave", "gamma_8_1", gamma_8_1_grids)
_shifts.register("wave", "gamma_8_2", gamma_8_2_grids)
_shifts.register("wave", "delta_8_1", delta_8_1_grids)


__all__ = [
    "baseline_grids", "gamma_8_1_grids", "gamma_8_2_grids", "delta_8_1_grids",
]
