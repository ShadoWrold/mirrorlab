"""Per-shift truth-form grid builders for the kinetics domain.

Blueprint-xy §3.2 / §4 rows 31-33 + baseline. Output is reactant
concentration C (or C_A for δ-11-1's branching).

All 4 cells use step()-based truth (blueprint §3.2.1 step()-only list).
The cf-validator-skip pattern (try/except around Instance(...)) handles
out-of-band perturbations on (c) by falling back to baseline C₀·exp(−k·t).
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    kinetics_d_11_1 as _d111,
    kinetics_g_11_1 as _g111,
    kinetics_g_11_2 as _g112,
)
from mirrorlab.domains.kinetics import KineticsBaseline, KineticsParams


def _t_grid(t_horizon: float, mode: str) -> np.ndarray:
    if mode == "b":
        return np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
    return np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)


def _baseline_C(t: float, p: Any) -> float:
    """Closed-form fallback when an Instance refuses cf-perturbed params."""
    k = float(_attr(p, ("k",), 1.0))
    n = float(_attr(p, ("n",), 1.0))
    C0 = float(_attr(p, ("C0", "C_A0"), 1.0)) or 1.0
    if n == 1.0:
        return C0 * math.exp(-k * t)
    # n-th order analytic.
    base = C0 ** (1.0 - n) + (n - 1.0) * k * t
    if base <= 0:
        return 0.0
    return base ** (1.0 / (1.0 - n))


# ---- baseline (n-th order, step-based) -------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    k0 = float(_attr(sim.params, ("k",), 1.0)) or 1.0
    t_horizon = 1.0 / k0

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            try:
                inst = KineticsBaseline(p)
                return inst.step(t)["C"]
            except (ValueError, TypeError):
                return _baseline_C(t, p)

        return fn

    def build(rng, mode):
        ts = _t_grid(t_horizon, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-11-1 (fractional-order kinetics) ------------------------------------

def gamma_11_1_grids(sim, seed: int, magnitude: float):
    """Fractional Adams-Moulton is O(n_steps²); cap the step count by
    enlarging dt for short-horizon test points so a per-call solve
    stays sub-second even on cf-perturbed params."""
    k0 = float(_attr(sim.params, ("k",), 1.0)) or 1.0
    t_horizon = 1.0 / k0
    _MAX_STEPS = 200

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            try:
                # Replace dt with one that yields ≤ _MAX_STEPS for the
                # requested t. Preserves the catalog's beta/k/n/C0 so
                # the perturbed-params semantics are intact.
                dt_eff = max(float(getattr(p, "dt", 0.05)), abs(t) / _MAX_STEPS)
                p_eff = _g111.KineticsGamma111Params(
                    k=float(p.k), n=float(p.n), beta=float(p.beta),
                    C0=float(p.C0), tau_min=float(p.tau_min), dt=dt_eff,
                )
                inst = _g111.KineticsGamma111Instance(p_eff)
                return inst.step(t)["C"]
            except (ValueError, TypeError):
                return _baseline_C(t, p)

        return fn

    def build(rng, mode):
        ts = _t_grid(t_horizon, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- γ-11-2 (saturating kinetics) ------------------------------------------

def gamma_11_2_grids(sim, seed: int, magnitude: float):
    k0 = float(_attr(sim.params, ("k",), 1.0)) or 1.0
    t_horizon = 1.0 / k0

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            try:
                inst = _g112.KineticsGamma112Instance(p)
                return inst.step(t)["C"]
            except (ValueError, TypeError):
                return _baseline_C(t, p)

        return fn

    def build(rng, mode):
        ts = _t_grid(t_horizon, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# ---- δ-11-1 (branching to dark product B; GT = C_A) ------------------------

def delta_11_1_grids(sim, seed: int, magnitude: float):
    k0 = float(_attr(sim.params, ("k",), 1.0)) or 1.0
    t_horizon = 1.0 / k0

    def gt(inputs):
        t = inputs["t"]

        def fn(p):
            try:
                inst = _d111.KineticsDelta111Instance(p)
                return inst.step(t)["C_A"]
            except (ValueError, TypeError):
                return _baseline_C(t, p)

        return fn

    def build(rng, mode):
        ts = _t_grid(t_horizon, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


_shifts.register("kinetics", "baseline", baseline_grids)
_shifts.register("kinetics", "gamma_11_1", gamma_11_1_grids)
_shifts.register("kinetics", "gamma_11_2", gamma_11_2_grids)
_shifts.register("kinetics", "delta_11_1", delta_11_1_grids)


__all__ = [
    "baseline_grids", "gamma_11_1_grids", "gamma_11_2_grids", "delta_11_1_grids",
]
