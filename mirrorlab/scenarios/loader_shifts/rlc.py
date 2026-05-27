"""Per-shift truth-form grid builders for the RLC domain.

Blueprint-xy §3.2 / §4 rows 16-18 + baseline.

Output is di/dt (or (di1/dt, di2/dt) projected to scalar for γ-6-2).

- baseline   inputs {q, i}, GT di/dt = −(R·i + q/C) / L
- γ-6-1      inputs {q, i}, GT shifted_law with L_eff(i) saturation
- γ-6-2      inputs {q_1, i_1, q_2, i_2}, GT first-circuit di1/dt
             (project the 2-coupled-LC vector to its primary component)
- δ-6-1      inputs {q, i, t}, GT shifted_law with L(t) modulation
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    rlc_d_6_1 as _d61,
    rlc_g_6_1 as _g61,
    rlc_g_6_2 as _g62,
)


def _qi_amp(sim: Any):
    q0 = abs(_attr(sim.params, ("q0", "q1_0"), 1.0)) or 1.0
    i0 = abs(_attr(sim.params, ("i0", "i1_0"), 1.0)) or 1.0
    return q0, i0


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    q_a, i_a = _qi_amp(sim)

    def gt(inputs):
        q, i = inputs["q"], inputs["i"]

        def fn(p):
            L = _attr(p, ("L", "L0", "L1"), 1.0)
            R = _attr(p, ("R", "R1"), 0.0)
            C = _attr(p, ("C", "C1"), 1.0)
            return -(R * i + q / C) / max(L, 1e-12)

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            q = q_a * float(rng.uniform(-scale, scale))
            i = i_a * float(rng.uniform(-scale, scale))
            ins = {"q": q, "i": i}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-6-1 (L_eff(i) saturating inductor) ----------------------------------

def gamma_6_1_grids(sim, seed: int, magnitude: float):
    q_a, i_a = _qi_amp(sim)

    def gt(inputs):
        q, i = inputs["q"], inputs["i"]

        def fn(p):
            return float(_g61.shifted_law(q, i, p))

        return fn

    def build(rng: np.random.Generator, mode: str):
        # Bias i near I_sat so the saturation is observable.
        scale = 5.0 if mode == "b" else 2.0
        pts = []
        for _ in range(_GRID_SIZE):
            q = q_a * float(rng.uniform(-scale, scale))
            i = i_a * float(rng.uniform(-scale, scale))
            ins = {"q": q, "i": i}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-6-2 (2-coupled LC, project to di1/dt) -------------------------------

def gamma_6_2_grids(sim, seed: int, magnitude: float):
    q1_a = abs(_attr(sim.params, ("q1_0",), 1.0)) or 1.0
    i1_a = abs(_attr(sim.params, ("i1_0",), 1.0)) or 1.0
    q2_a = abs(_attr(sim.params, ("q2_0",), 1.0)) or 1.0
    i2_a = abs(_attr(sim.params, ("i2_0",), 1.0)) or 1.0

    def gt(inputs):
        q1, i1, q2, i2 = inputs["q_1"], inputs["i_1"], inputs["q_2"], inputs["i_2"]

        def fn(p):
            di1, _di2 = _g62.shifted_law(q1, i1, q2, i2, p)
            return float(di1)

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            ins = {
                "q_1": q1_a * float(rng.uniform(-scale, scale)),
                "i_1": i1_a * float(rng.uniform(-scale, scale)),
                "q_2": q2_a * float(rng.uniform(-scale, scale)),
                "i_2": i2_a * float(rng.uniform(-scale, scale)),
            }
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-6-1 (L(t) parametric modulation) ------------------------------------

def delta_6_1_grids(sim, seed: int, magnitude: float):
    q_a, i_a = _qi_amp(sim)
    Omega = float(_attr(sim.params, ("Omega_p",), 1.0)) or 1.0
    period = 2.0 * math.pi / Omega

    def gt(inputs):
        q, i, t = inputs["q"], inputs["i"], inputs["t"]

        def fn(p):
            return float(_d61.shifted_law(q, i, t, p))

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        if mode == "b":
            ts = np.linspace(2.0 * period, 5.0 * period, _GRID_SIZE)
        else:
            ts = np.linspace(0.0, 2.0 * period, _GRID_SIZE)
        pts = []
        for t in ts:
            ins = {
                "q": q_a * float(rng.uniform(-scale, scale)),
                "i": i_a * float(rng.uniform(-scale, scale)),
                "t": float(t),
            }
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


_shifts.register("rlc", "baseline", baseline_grids)
_shifts.register("rlc", "gamma_6_1", gamma_6_1_grids)
_shifts.register("rlc", "gamma_6_2", gamma_6_2_grids)
_shifts.register("rlc", "delta_6_1", delta_6_1_grids)


__all__ = [
    "baseline_grids", "gamma_6_1_grids", "gamma_6_2_grids", "delta_6_1_grids",
]
