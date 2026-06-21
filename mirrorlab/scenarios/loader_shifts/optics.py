"""Per-shift truth-form grid builders for the optics domain.

Blueprint-xy §3.2 / §4 rows 25-27 + baseline.

The catalog's optics shifts fix θ_i in params; their step() emits a
scalar refraction outcome. For a meaningful sweep we promote θ_i to a
grid input and compute the truth via each cell's registered ``spec.law``
(the same callable the oracle uses — single source of truth):

- baseline   inputs {theta_i},          GT θ_t = asin((n1/n2)·sin θ_i)
- γ-9-1 ROT  inputs {theta_i, theta_pol}, GT dichroic transmittance T
- γ-9-2      inputs {theta_i, nu},       GT spatial-dispersion angle θ_t
- δ-9-1      inputs {theta_i},           GT absorbing-film transmittance T

Each builder keeps its OWN θ/ν grid design (TIR-safe ranges, grazing-cliff
OOD, ν-OOD) — only the GT *value* is delegated to ``spec.law``, never the
sampling. See tests/runners for the loader↔law bit-parity guard.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _pack
from mirrorlab.spec import get_cell as _get_cell


def _law_gt(domain: str, shift: str):
    """Return a ``gt(inputs) -> fn(p)`` closure that evaluates the cell's
    registered ``spec.law`` — the same law the oracle wraps, so the grid GT
    and the oracle predictor can never drift apart."""
    spec = _get_cell(domain, shift)

    def gt(inputs: Dict[str, float]):
        def fn(p):
            return spec.law(inputs, p)
        return fn

    return gt


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


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim, seed: int, magnitude: float):
    gt = _law_gt("optics", "baseline")

    def build(rng, mode):
        ths = _theta_grid(mode)
        return [({"theta1": float(th)}, gt({"theta1": float(th)})) for th in ths]

    return _pack(seed, magnitude, sim, build)


# ---- γ-9-1 (polarization-dependent absorption / dichroism) -----------------

def gamma_9_1_grids(sim, seed: int, magnitude: float):
    # Polarization-selective Beer-Lambert transmittance:
    #   T(θ_i, θ_pol) = (1−R0)·exp(−β(θ_pol)/cosθ_i),
    #   β(θ_pol) = β0·(1 + χ·sin²(2θ_pol − φ)).
    # The grazing-angle cliff (cosθ_i→0) is the refit-resistant feature, so
    # this cell uses its OWN θ grid (energy channel has no asin TIR limit):
    # in-domain modest angles, OOD pushed into the grazing-cliff region.
    # θ_pol carries the polarization-U(1) break via the dichroic depth.
    gt = _law_gt("optics", "gamma_9_1")

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            ths = np.linspace(0.75, 1.45, _GRID_SIZE)   # grazing-cliff OOD
        else:
            ths = np.linspace(0.05, 0.55, _GRID_SIZE)
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
    gt = _law_gt("optics", "gamma_9_2")

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
    gt = _law_gt("optics", "delta_9_1")

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
