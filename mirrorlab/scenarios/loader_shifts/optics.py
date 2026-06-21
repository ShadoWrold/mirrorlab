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
    """θ_i kept below the total-internal-reflection critical angle so the
    refraction angle θ_t = asin((n1/n2)·sinθ_i) is always defined (no nan,
    no asin domain error on honest Snell submissions).

    Worst-case critical angles over the n1,n2 ∈ [1.0,1.6] sampler:
      - (a)/(c): sub-grid (c) reuses (a)'s θ points but perturbs n1,n2 by
        1±0.30 (CAL-3), pushing n1/n2 up to ~2.97 → θ_c ≈ 0.343 rad. Cap
        the in-domain range at 0.30 to stay clear.
      - (b) OOD: uses the unperturbed sim params (n1/n2 ≤ 1.6 → θ_c ≈
        0.675 rad), so it can extrapolate to 0.65 and still never saturate.
    """
    if mode == "b":
        return np.linspace(0.35, 0.65, _GRID_SIZE)
    return np.linspace(0.05, 0.30, _GRID_SIZE)


def _snell_sin(n1: float, n2: float, theta_i: float) -> float:
    if n2 == 0.0:
        return 0.0
    return (n1 / n2) * math.sin(theta_i)


def _angle(sin_val: float) -> float:
    # The scored observable is the refraction ANGLE θ_t (rad), matching the
    # domain dim_signature (output theta2:"1") and the catalog step()'s asin
    # form. Clamp at total internal reflection so GT never goes nan.
    return math.asin(max(-1.0, min(1.0, sin_val)))


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    def gt(inputs):
        th = inputs["theta1"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2",), 1.5)
            return _angle(_snell_sin(n1, n2, th))

        return fn

    def build(rng, mode):
        ths = _theta_grid(mode)
        return [({"theta1": float(th)}, gt({"theta1": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


# ---- γ-9-1 (anisotropic n) -------------------------------------------------

def gamma_9_1_grids(sim, seed: int, magnitude: float):
    def gt(inputs):
        th_i = inputs["theta1"]
        th_pol = inputs["theta_pol"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n0 = _attr(p, ("n0",), 1.5)
            dn = _attr(p, ("dn",), 0.0)
            phi = _attr(p, ("phi",), 0.0)
            n_eff = n0 + dn * math.sin(2.0 * th_pol - phi) ** 2
            return _angle(_snell_sin(n1, n_eff, th_i))

        return fn

    def build(rng: np.random.Generator, mode: str):
        ths = _theta_grid(mode)
        # Bias θ_pol away from the dn-cancellation node so the
        # anisotropy is observable. Cover both quadrants.
        pols = rng.uniform(0.0, math.pi, size=_GRID_SIZE)
        return [({"theta1": float(th), "theta_pol": float(tp)},
                 gt({"theta1": float(th), "theta_pol": float(tp)}))
                for th, tp in zip(ths, pols)]

    return _pack(seed, magnitude, sim, build)


# ---- γ-9-2 (intensity-dependent n, cubic correction) -----------------------

def gamma_9_2_grids(sim, seed: int, magnitude: float):
    # Spatial-dispersion non-reciprocal break:
    #   sin θ_t = (n1/n2) sinθ + κ·anti·sinθ·sin(β·ν·sinθ)
    # ν is a second visible axis (normalized optical frequency). The
    # oscillatory term non-separably couples θ and ν, so no low-order 2-D
    # polynomial / separable power law absorbs it; ν-OOD makes overfits
    # diverge. β is a fixed structural constant (not perturbed by cf).
    from mirrorlab.shifts.optics_g_9_2 import BETA as _BETA

    def gt(inputs):
        th = inputs["theta1"]
        nu = inputs["nu"]

        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2",), 1.5)
            kappa = _attr(p, ("kappa",), 0.0)
            s = math.sin(th)
            anti = (n1 - n2) / (n1 + n2) if (n1 + n2) != 0 else 0.0
            return _angle((n1 / n2) * s + kappa * anti * s * math.sin(_BETA * nu * s))

        return fn

    def build(rng, mode):
        # ν carries the aggressive OOD (not TIR-limited); θ stays small to
        # avoid total internal reflection.
        if mode == "b":
            ths = np.linspace(0.33, 0.55, _GRID_SIZE)
            nus = rng.uniform(2.5, 5.0, size=_GRID_SIZE)
        else:
            ths = np.linspace(0.05, 0.30, _GRID_SIZE)
            nus = rng.uniform(0.5, 2.0, size=_GRID_SIZE)
        return [({"theta1": float(th), "nu": float(nu)},
                 gt({"theta1": float(th), "nu": float(nu)}))
                for th, nu in zip(ths, nus)]

    return _pack(seed, magnitude, sim, build)


# ---- δ-9-1 (absorbing-film energy non-conservation; scored channel = T) ----

def delta_9_1_grids(sim, seed: int, magnitude: float):
    # Beer-Lambert transmittance T(θ_i) = (1−R0)·exp(−β/cosθ_i). The grazing
    # cliff (cosθ→0) is the refit-resistant feature, so this cell uses its OWN
    # θ grid (the energy channel has no asin TIR limit): in-domain modest
    # angles, OOD pushed into the grazing-cliff region. Scored output is the
    # transmittance T (not the angle), exposing the R+T≠1 energy break.
    def gt(inputs):
        th = inputs["theta1"]

        def fn(p):
            R0 = _attr(p, ("R0",), 0.1)
            beta = _attr(p, ("beta",), 0.5)
            return (1.0 - R0) * math.exp(-beta / math.cos(th))

        return fn

    def build(rng, mode):
        if mode == "b":
            ths = np.linspace(0.75, 1.45, _GRID_SIZE)   # grazing-cliff OOD
        else:
            ths = np.linspace(0.05, 0.55, _GRID_SIZE)
        return [({"theta1": float(th)}, gt({"theta1": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


_shifts.register("optics", "baseline", baseline_grids)
_shifts.register("optics", "gamma_9_1", gamma_9_1_grids)
_shifts.register("optics", "gamma_9_2", gamma_9_2_grids)
_shifts.register("optics", "delta_9_1", delta_9_1_grids)


__all__ = [
    "baseline_grids", "gamma_9_1_grids", "gamma_9_2_grids", "delta_9_1_grids",
]
