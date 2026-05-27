"""Per-shift truth-form grid builders for the pendulum domain.

Blueprint-xy §3.2 / §4 rows 10-12 + baseline. Output is angular
acceleration ẗheta.

- baseline   inputs {theta}, GT −(g/L)·sin(θ)
- γ-4-1      inputs {theta}, GT −(g/L)·sin(θ) − (g/L)·α·(1 − cos(θ))
- γ-4-2      inputs {theta}, GT −g_eff(θ)·sin(θ) with g_eff dependent
             on height L(1 − cos θ)
- δ-4-1      inputs {theta, t}, GT −g₀(1 + ε·cos(Ω·t))·sin(θ)
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
    _pack,
)
from mirrorlab.shifts import (
    pendulum_d_4_1 as _d41,
    pendulum_g_4_1 as _g41,
    pendulum_g_4_2 as _g42,
)


def _theta_grid(amp: float, mode: str) -> np.ndarray:
    """Sample θ in [−amp, amp] (in-domain) or 1.5·amp..π (OOD)."""
    if mode == "b":
        amp_ood = min(math.pi - 1e-3, _OOD_FACTOR * amp)
        return np.concatenate([
            np.linspace(-amp_ood, -1.5 * amp, _GRID_SIZE // 2),
            np.linspace(1.5 * amp, amp_ood, _GRID_SIZE - _GRID_SIZE // 2),
        ])
    return np.linspace(-amp, amp, _GRID_SIZE)


def baseline_grids(sim: Any, seed: int, magnitude: float):
    theta0 = abs(_attr(sim.params, ("theta0",), 0.3)) or 0.3

    def gt(inputs):
        th = inputs["theta"]

        def fn(p):
            gol = _attr(p, ("g_over_L", "g0_over_L"),
                        _attr(p, ("g",), 9.81) / max(_attr(p, ("L",), 1.0), 1e-9))
            return -gol * math.sin(th)

        return fn

    def build(rng, mode):
        ths = _theta_grid(theta0, mode)
        return [({"theta": float(th)}, gt({"theta": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


def gamma_4_1_grids(sim: Any, seed: int, magnitude: float):
    theta0 = abs(_attr(sim.params, ("theta0",), 0.3)) or 0.3

    def gt(inputs):
        th = inputs["theta"]

        def fn(p):
            return float(_g41.shifted_law(th, p))

        return fn

    def build(rng, mode):
        ths = _theta_grid(theta0, mode)
        return [({"theta": float(th)}, gt({"theta": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


def gamma_4_2_grids(sim: Any, seed: int, magnitude: float):
    theta0 = abs(_attr(sim.params, ("theta0",), 0.3)) or 0.3

    def gt(inputs):
        th = inputs["theta"]

        def fn(p):
            return float(_g42.shifted_law(th, p))

        return fn

    def build(rng, mode):
        ths = _theta_grid(theta0, mode)
        return [({"theta": float(th)}, gt({"theta": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


def delta_4_1_grids(sim: Any, seed: int, magnitude: float):
    theta0 = abs(_attr(sim.params, ("theta0",), 0.3)) or 0.3
    Omega = float(_attr(sim.params, ("Omega",), 1.0)) or 1.0
    period = 2.0 * math.pi / Omega

    def gt(inputs):
        th, t = inputs["theta"], inputs["t"]

        def fn(p):
            return float(_d41.shifted_law(th, t, p))

        return fn

    def build(rng, mode):
        ths = _theta_grid(theta0, mode)
        if mode == "b":
            ts = np.linspace(2.0 * period, 5.0 * period, _GRID_SIZE)
        else:
            ts = np.linspace(0.0, 2.0 * period, _GRID_SIZE)
        return [({"theta": float(th), "t": float(t)},
                 gt({"theta": float(th), "t": float(t)}))
                for th, t in zip(ths, ts)]

    return _pack(seed, magnitude, sim, build)


_shifts.register("pendulum", "baseline", baseline_grids)
_shifts.register("pendulum", "gamma_4_1", gamma_4_1_grids)
_shifts.register("pendulum", "gamma_4_2", gamma_4_2_grids)
_shifts.register("pendulum", "delta_4_1", delta_4_1_grids)


__all__ = [
    "baseline_grids", "gamma_4_1_grids", "gamma_4_2_grids", "delta_4_1_grids",
]
