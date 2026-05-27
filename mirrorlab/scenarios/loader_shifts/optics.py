"""Per-shift truth-form grid builders for the optics domain.

Blueprint-xy §3.2 / §4 rows 25-27 + baseline.

The catalog's optics shifts fix θ_i in params; their step() emits a
scalar refraction outcome. For a meaningful sweep we promote θ_i to a
grid input and compute the truth via each shift's law:

- baseline   inputs {theta_i},          GT sin(θ_t) = (n1/n2)·sin(θ_i)
- γ-9-1 ROT  inputs {theta_i, theta_pol}, GT (n1/n_eff)·sin(θ_i)
             with n_eff = n0 + dn·sin²(2·θ_pol − φ)
- γ-9-2      inputs {theta_i},          GT (n1/n2)·sin(θ_i) + κ·anti·sin³(θ_i)
- δ-9-1      inputs {theta_i, t},       GT baseline Snell (the catalog
             step() is identical to baseline — the leakage ξ is unused
             in the shift module's step today; recorded for v2 follow-up)

Output is sin(θ_t) — dimensionless and finite even when nan-tripped at
total internal reflection.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    optics_d_9_1 as _d91,
    optics_g_9_1 as _g91,
    optics_g_9_2 as _g92,
)


def _theta_grid(mode: str) -> np.ndarray:
    """θ_i in [0, π/2 − ε]; sample upper range for OOD."""
    if mode == "b":
        return np.linspace(0.7, math.pi / 2.0 - 0.05, _GRID_SIZE)
    return np.linspace(0.05, 0.7, _GRID_SIZE)


def _snell_sin(n1: float, n2: float, theta_i: float) -> float:
    if n2 == 0.0:
        return 0.0
    return (n1 / n2) * math.sin(theta_i)


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    def gt(inputs):
        th = inputs["theta_i"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2",), 1.5)
            return _snell_sin(n1, n2, th)

        return fn

    def build(rng, mode):
        ths = _theta_grid(mode)
        return [({"theta_i": float(th)}, gt({"theta_i": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


# ---- γ-9-1 (anisotropic n) -------------------------------------------------

def gamma_9_1_grids(sim, seed: int, magnitude: float):
    def gt(inputs):
        th_i = inputs["theta_i"]
        th_pol = inputs["theta_pol"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n0 = _attr(p, ("n0",), 1.5)
            dn = _attr(p, ("dn",), 0.0)
            phi = _attr(p, ("phi",), 0.0)
            n_eff = n0 + dn * math.sin(2.0 * th_pol - phi) ** 2
            return _snell_sin(n1, n_eff, th_i)

        return fn

    def build(rng: np.random.Generator, mode: str):
        ths = _theta_grid(mode)
        # Bias θ_pol away from the dn-cancellation node so the
        # anisotropy is observable. Cover both quadrants.
        pols = rng.uniform(0.0, math.pi, size=_GRID_SIZE)
        return [({"theta_i": float(th), "theta_pol": float(tp)},
                 gt({"theta_i": float(th), "theta_pol": float(tp)}))
                for th, tp in zip(ths, pols)]

    return _pack(seed, magnitude, sim, build)


# ---- γ-9-2 (intensity-dependent n, cubic correction) -----------------------

def gamma_9_2_grids(sim, seed: int, magnitude: float):
    def gt(inputs):
        th = inputs["theta_i"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2",), 1.5)
            kappa = _attr(p, ("kappa",), 0.0)
            s = math.sin(th)
            anti = (n1 - n2) / (n1 + n2) if (n1 + n2) != 0 else 0.0
            return (n1 / n2) * s + kappa * anti * s ** 3

        return fn

    def build(rng, mode):
        ths = _theta_grid(mode)
        return [({"theta_i": float(th)}, gt({"theta_i": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


# ---- δ-9-1 (time-modulated n; catalog step() is currently baseline) --------

def delta_9_1_grids(sim, seed: int, magnitude: float):
    # The catalog's δ-9-1 step() does not actually use ξ/p — its current
    # form is identical to baseline Snell. We still expose t as a grid
    # input so a future patch that lights up the ξ-dependence has a
    # canonical axis ready. GT matches the current step() == baseline.
    def gt(inputs):
        th = inputs["theta_i"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2",), 1.5)
            return _snell_sin(n1, n2, th)

        return fn

    def build(rng, mode):
        ths = _theta_grid(mode)
        ts = rng.uniform(0.0, 1.0, size=_GRID_SIZE)  # placeholder axis
        return [({"theta_i": float(th), "t": float(t)},
                 gt({"theta_i": float(th), "t": float(t)}))
                for th, t in zip(ths, ts)]

    return _pack(seed, magnitude, sim, build)


_shifts.register("optics", "baseline", baseline_grids)
_shifts.register("optics", "gamma_9_1", gamma_9_1_grids)
_shifts.register("optics", "gamma_9_2", gamma_9_2_grids)
_shifts.register("optics", "delta_9_1", delta_9_1_grids)


__all__ = [
    "baseline_grids", "gamma_9_1_grids", "gamma_9_2_grids", "delta_9_1_grids",
]
