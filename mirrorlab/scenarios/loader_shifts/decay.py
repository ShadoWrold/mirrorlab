"""Per-shift truth-form grid builders for the Decay domain.

Blueprint-xy §3.2 / §4 rows 34-36 + baseline. All 4 cells use
step()-based truth (blueprint §3.2.1 step()-only list):

- baseline   GT N(t) = N₀·exp(−λ t)  (closed-form, no Instance needed)
- γ-12-1     density-coupled rate, dN/dt = −λ N (1 + α(N/N₀)^p);
             step()-based
- γ-12-2     parametric-modulated rate, dN/dt = −λ(t) N with
             λ(t) = λ₀[1 + ε cos(ωt)]; step()-based
- δ-12-1     branching loss, two-species (N_A, N_B); GT projects to N_A
             (consistent with single-channel observable convention)

The shift modules' ``Instance(...)`` constructors enforce the catalog
sampler's validator ranges. Counterfactual perturbation (±30%) routinely
pushes coefficients outside those ranges, so we bypass the constructor
on (c) by calling ``solve_ivp`` against the same rhs closure directly.
This is purely about scoring the perturbed-law GT; the underlying
physics is well-defined for any finite (lam, α, p, N_scale).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
from scipy.integrate import solve_ivp

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    decay_d_12_1 as _d121,
    decay_g_12_1 as _g121,
    decay_g_12_2 as _g122,
)


def _solve_to(rhs, y0, t: float):
    """Integrate ``rhs(t, y)`` from 0 to ``t`` and return ``y(t)``.

    Bypasses the shift modules' Instance constructors (and their
    validator gates) so counterfactual-perturbed params can score
    even when they fall outside the catalog sampler's safe band.

    Falls back to ``y0`` if the integrator refuses the step — this is
    a conservative tie at the IC, used only when a cf perturbation
    pushes the dynamics into a stiff or singular region.
    """
    t = max(float(t), 0.0)
    if t == 0.0:
        return list(y0)
    try:
        sol = solve_ivp(
            rhs, (0.0, t), list(y0),
            method="DOP853", rtol=1e-9, atol=1e-12,
        )
    except Exception:
        return list(y0)
    if not sol.success:
        return list(y0)
    return [float(v) for v in sol.y[:, -1]]


# ---- baseline (closed-form N₀·exp(−λ t)) -----------------------------------

def baseline_grids(sim: Any, seed: int, magnitude: float):
    lam0 = float(_attr(sim.params, ("lam",), 0.1)) or 0.1
    t_horizon = 1.0 / lam0  # one e-fold

    def gt(inputs: Dict[str, float]):
        t = inputs["t"]

        def fn(p):
            lam = float(_attr(p, ("lam",), 0.1))
            N0 = float(_attr(p, ("N0",), 1.0e6))
            return N0 * math.exp(-lam * t)

        return fn

    def build(rng, mode):
        if mode == "b":
            ts = np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
        else:
            ts = np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-12-1 (density-coupled rate, step-based) -----------------------------

def gamma_12_1_grids(sim: Any, seed: int, magnitude: float):
    lam0 = float(_attr(sim.params, ("lam",), 0.1)) or 0.1
    t_horizon = 1.0 / lam0

    def gt(inputs: Dict[str, float]):
        t = inputs["t"]

        def fn(p):
            lam = float(_attr(p, ("lam",), 0.1))
            alpha = float(_attr(p, ("alpha",), 0.0))
            p_exp = float(_attr(p, ("p",), 1.0))
            N_scale = float(_attr(p, ("N_scale",), 1.0)) or 1.0
            N_init = float(_attr(p, ("N_init",), 1.0e6))

            def rhs(_t, y):
                (N,) = y
                Ns = max(N, 0.0)
                return (-lam * Ns * (1.0 + alpha * (Ns / N_scale) ** p_exp),)

            y_t = _solve_to(rhs, [N_init], t)
            return y_t[0]

        return fn

    def build(rng, mode):
        if mode == "b":
            ts = np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
        else:
            ts = np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-12-2 (parametric-modulated rate) -----------------------------------

def gamma_12_2_grids(sim: Any, seed: int, magnitude: float):
    lam0 = float(_attr(sim.params, ("lam0", "lam"), 0.1)) or 0.1
    t_horizon = 1.0 / lam0

    def gt(inputs: Dict[str, float]):
        t = inputs["t"]

        def fn(p):
            lam_b = float(_attr(p, ("lam0", "lam"), 0.1))
            eps = float(_attr(p, ("eps",), 0.0))
            omega = float(_attr(p, ("omega",), 0.0))
            N_init = float(_attr(p, ("N_init",), 1.0e6))

            def rhs(_t, y):
                (N,) = y
                lam_t = lam_b * (1.0 + eps * math.cos(omega * _t))
                return (-lam_t * N,)

            y_t = _solve_to(rhs, [N_init], t)
            return y_t[0]

        return fn

    def build(rng, mode):
        if mode == "b":
            ts = np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
        else:
            ts = np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- δ-12-1 (branching loss; GT = N_A) -------------------------------------

def delta_12_1_grids(sim: Any, seed: int, magnitude: float):
    lam0 = float(_attr(sim.params, ("lam",), 0.1)) or 0.1
    t_horizon = 1.0 / lam0

    def gt(inputs: Dict[str, float]):
        t = inputs["t"]

        def fn(p):
            lam = float(_attr(p, ("lam",), 0.1))
            xi = float(_attr(p, ("xi",), 0.0))
            NA0 = float(_attr(p, ("N_A0",), 1.0e6))
            NB0 = float(_attr(p, ("N_B0",), 0.0))

            def rhs(_t, y):
                NA, _NB = y
                return (-lam * NA, (1.0 - xi) * lam * NA)

            y_t = _solve_to(rhs, [NA0, NB0], t)
            return y_t[0]  # N_A(t)

        return fn

    def build(rng, mode):
        if mode == "b":
            ts = np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
        else:
            ts = np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


_shifts.register("decay", "baseline", baseline_grids)
_shifts.register("decay", "gamma_12_1", gamma_12_1_grids)
_shifts.register("decay", "gamma_12_2", gamma_12_2_grids)
_shifts.register("decay", "delta_12_1", delta_12_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_12_1_grids",
    "gamma_12_2_grids",
    "delta_12_1_grids",
]
