"""Per-shift truth-form grid builders for the fluid domain.

Blueprint-xy §3.2 / §4 rows 28-30 + baseline. Output is downstream
pressure p2.

- baseline   inputs {p1, v1, v2, h1, h2}, GT Bernoulli
             p2 = p1 + ½ρ(v1²−v2²) + ρg(h1−h2)
- γ-10-1     inputs {p1, h1, h2}, GT shifted_pressure(p) with v1/v2
             3-vectors held in closure (sim.params provides them; the
             grid varies the scalar BC instead). The α-anisotropic
             kinetic term is encoded in M(α,n̂); cf perturbation of α
             still moves GT per (c) point through Y plumbing.
- γ-10-2     inputs {p1, v1, v2, h1, h2}, GT exponential atmosphere
             gh potential
- δ-10-1     inputs {p1, v1, v2, h1, h2}, GT Bernoulli minus zeta·loss
             (loss integral closed over closure params: m, L_path, v_inf)
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.shifts import (
    fluid_d_10_1 as _d101,
    fluid_g_10_1 as _g101,
    fluid_g_10_2 as _g102,
)


# ---- baseline (classical Bernoulli) ----------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    p10 = float(_attr(sim.params, ("p1",), 1.0e5)) or 1.0e5
    v10 = abs(_attr(sim.params, ("v1",), 1.0)) or 1.0
    h10 = abs(_attr(sim.params, ("h1",), 1.0)) or 1.0

    def gt(inputs):
        p1, v1, v2, h1, h2 = (inputs[k] for k in ("p1", "v1", "v2", "h1", "h2"))

        def fn(p):
            rho = _attr(p, ("rho",), 1000.0)
            g = _attr(p, ("g",), 9.81)
            return p1 + 0.5 * rho * (v1 * v1 - v2 * v2) + rho * g * (h1 - h2)

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            p1 = p10 * float(rng.uniform(0.5, scale))
            v1 = v10 * float(rng.uniform(0.2, scale))
            v2 = v10 * float(rng.uniform(0.2, scale))
            h1 = h10 * float(rng.uniform(0.5, scale))
            h2 = h10 * float(rng.uniform(0.5, scale))
            ins = {"p1": p1, "v1": v1, "v2": v2, "h1": h1, "h2": h2}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-10-1 (anisotropic KE tensor M(α,n̂)) --------------------------------

def gamma_10_1_grids(sim, seed: int, magnitude: float):
    """v1/v2 are 3-vectors in params; treat them as BC (closure). Grid
    varies the scalar Bernoulli BCs (p1, h1, h2) so the spread is
    driven by α (cf-perturbed) on (c)."""
    p_sim = sim.params
    p10 = float(_attr(p_sim, ("p1",), 1.0e5)) or 1.0e5
    h10 = abs(_attr(p_sim, ("h1",), 1.0)) or 1.0

    def gt(inputs):
        p1, h1, h2 = inputs["p1"], inputs["h1"], inputs["h2"]

        def fn(p):
            # Build a temporary Params with the grid-driven scalar BCs
            # so we can reuse the shift module's pressure formula
            # (which handles M(α,n̂) for us).
            p_eff = _g101.FluidGamma101Params(
                rho=p.rho, alpha=p.alpha, n=getattr(p, "n", (1.0, 0.0, 0.0)),
                g=p.g, h1=h1, p1=p1, v1=p_sim.v1, h2=h2, v2=p_sim.v2,
            )
            return float(_g101.shifted_pressure(p_eff))

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            p1 = p10 * float(rng.uniform(0.5, scale))
            h1 = h10 * float(rng.uniform(0.5, scale))
            h2 = h10 * float(rng.uniform(0.5, scale))
            ins = {"p1": p1, "h1": h1, "h2": h2}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-10-2 (exponential atmosphere) ---------------------------------------

def gamma_10_2_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    p10 = float(_attr(p_sim, ("p1",), 1.0e5)) or 1.0e5
    v10 = abs(_attr(p_sim, ("v1",), 1.0)) or 1.0
    h10 = abs(_attr(p_sim, ("h1",), 1.0)) or 1.0

    def gt(inputs):
        p1, v1, v2, h1, h2 = (inputs[k] for k in ("p1", "v1", "v2", "h1", "h2"))

        def fn(p):
            p_eff = _g102.FluidGamma102Params(
                rho=p.rho, g=p.g, h0=p.h0, lam=p.lam, q=p.q,
                h1=h1, v1=v1, p1=p1, h2=h2, v2=v2,
            )
            return float(_g102.shifted_pressure(p_eff))

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            p1 = p10 * float(rng.uniform(0.5, scale))
            v1 = v10 * float(rng.uniform(0.2, scale))
            v2 = v10 * float(rng.uniform(0.2, scale))
            h1 = h10 * float(rng.uniform(0.5, scale))
            h2 = h10 * float(rng.uniform(0.5, scale))
            ins = {"p1": p1, "v1": v1, "v2": v2, "h1": h1, "h2": h2}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-10-1 (Bernoulli with friction loss) ---------------------------------

def delta_10_1_grids(sim, seed: int, magnitude: float):
    p_sim = sim.params
    p10 = float(_attr(p_sim, ("p1",), 1.0e5)) or 1.0e5
    v10 = abs(_attr(p_sim, ("v1",), 1.0)) or 1.0
    h10 = abs(_attr(p_sim, ("h1",), 1.0)) or 1.0

    def gt(inputs):
        p1, v1, v2, h1, h2 = (inputs[k] for k in ("p1", "v1", "v2", "h1", "h2"))

        def fn(p):
            p_eff = _d101.FluidDelta101Params(
                rho=p.rho, g=p.g,
                h1=h1, v1=v1, p1=p1, h2=h2, v2=v2,
                zeta=p.zeta,
                m=p_sim.m, v_inf=p_sim.v_inf, L_path=p_sim.L_path,
            )
            return float(_d101.shifted_pressure(p_eff))

        return fn

    def build(rng: np.random.Generator, mode: str):
        scale = 5.0 if mode == "b" else 1.5
        pts = []
        for _ in range(_GRID_SIZE):
            p1 = p10 * float(rng.uniform(0.5, scale))
            v1 = v10 * float(rng.uniform(0.2, scale))
            v2 = v10 * float(rng.uniform(0.2, scale))
            h1 = h10 * float(rng.uniform(0.5, scale))
            h2 = h10 * float(rng.uniform(0.5, scale))
            ins = {"p1": p1, "v1": v1, "v2": v2, "h1": h1, "h2": h2}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


_shifts.register("fluid", "baseline", baseline_grids)
_shifts.register("fluid", "gamma_10_1", gamma_10_1_grids)
_shifts.register("fluid", "gamma_10_2", gamma_10_2_grids)
_shifts.register("fluid", "delta_10_1", delta_10_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_10_1_grids",
    "gamma_10_2_grids",
    "delta_10_1_grids",
]
