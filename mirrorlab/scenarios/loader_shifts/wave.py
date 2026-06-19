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
from dataclasses import replace
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    wave_d_8_1 as _d81,
    wave_g_8_1 as _g81,
    wave_g_8_2 as _g82,
)


def _t_grid(period: float, mode: str, n_period: float = 2.0) -> np.ndarray:
    # n_period sets the in-domain window length in wave periods. Dispersion
    # (γ-8-1) and amplitude-gated damping (δ-8-1) need many periods for the
    # phase drift / decay to accumulate above the textbook form, so those
    # builders pass a larger n_period; baseline/others keep the default 2.
    if mode == "b":
        return np.linspace(n_period * period, (n_period + 3.0) * period, _GRID_SIZE)
    return np.linspace(0.0, n_period * period, _GRID_SIZE)


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
    # Dispersion ω²=c²k²(1+γk) is a FUNCTION OF k. The old grid fixed k and
    # only swept t, so the wave collapsed to a single frequency that a
    # textbook ω=c·k fit absorbs into an effective speed. To expose
    # dispersion we sweep k across a decade at a FIXED clock time t_ref:
    # then the truth ω(k)=ck√(1+γk) and the textbook ω=ck diverge in the
    # observed phase, so u(k) cannot be matched by any constant speed.
    t_ref = 3.0 * (2.0 * math.pi / max(c0 * k0, 1e-12))

    def gt(inputs):
        k = inputs["k"]
        t = inputs["t"]

        def fn(p):
            # Force the grid's k (an observation axis), never p.k (which the
            # counterfactual sub-grid would perturb). gamma/c come from p so
            # cf perturbation on (c) still flows through.
            p_eff = replace(p, k=k)
            w2 = _g81.shifted_omega_squared(p_eff)
            omega = math.sqrt(max(w2, 0.0))
            arg = k * p.x_probe - omega * t
            return p.A * math.sin(arg)

        return fn

    def build(rng, mode):
        if mode == "b":
            ks = np.geomspace(5.0 * k0, 20.0 * k0, _GRID_SIZE)
        else:
            ks = np.geomspace(0.5 * k0, 5.0 * k0, _GRID_SIZE)
        return [({"k": float(k), "t": float(t_ref)},
                 gt({"k": float(k), "t": float(t_ref)})) for k in ks]

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
        ts = _t_grid(period, mode, n_period=20.0)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


_shifts.register("wave", "baseline", baseline_grids)
_shifts.register("wave", "gamma_8_1", gamma_8_1_grids)
_shifts.register("wave", "gamma_8_2", gamma_8_2_grids)
_shifts.register("wave", "delta_8_1", delta_8_1_grids)


__all__ = [
    "baseline_grids", "gamma_8_1_grids", "gamma_8_2_grids", "delta_8_1_grids",
]
