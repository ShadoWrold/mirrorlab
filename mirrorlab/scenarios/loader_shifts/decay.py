"""Per-shift truth-form grid builders for the Decay domain.

Blueprint-xy §3.2 / §4 rows 34-36 + baseline. The grid GT is delegated to
each cell's registered ``spec.law`` (the same callable the oracle wraps), so
the integrated decay truth and the oracle predictor can never drift apart:

- baseline   GT N(t) = N₀·exp(−λ t)  (closed-form)
- γ-12-1     density-coupled rate, dN/dt = −λ N (1 + α(N/N₀)^p)
- γ-12-2     parametric-modulated rate, λ(t) = λ₀[1 + ε cos(ωt)]
- δ-12-1     branching loss, GT = total N_A + N_B

``spec.law`` integrates via the shared ``mirrorlab.domains.decay.solve_to``,
which bypasses the shift Instances' validator gates so counterfactual-perturbed
coefficients still score. Each builder keeps its OWN geomspace t-grid (one
e-fold horizon, OOD at 5×); only the GT value is delegated, never the sampling.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import _GRID_SIZE, _attr, _pack
from mirrorlab.spec import get_cell as _get_cell


def _law_gt(domain: str, shift: str):
    """Return a ``gt(inputs) -> fn(p)`` closure evaluating the cell's
    registered ``spec.law`` — the single source of truth shared with the
    oracle predictor."""
    spec = _get_cell(domain, shift)

    def gt(inputs: Dict[str, float]):
        def fn(p):
            return spec.law(inputs, p)
        return fn

    return gt


def _t_grid(t_horizon: float, mode: str) -> np.ndarray:
    if mode == "b":
        return np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
    return np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)


def _decay_grids(sim, seed, magnitude, *, domain, shift, lam_names):
    lam0 = float(_attr(sim.params, lam_names, 0.1)) or 0.1
    t_horizon = 1.0 / lam0  # one e-fold
    gt = _law_gt(domain, shift)

    def build(rng, mode):
        ts = _t_grid(t_horizon, mode)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


def baseline_grids(sim: Any, seed: int, magnitude: float):
    return _decay_grids(sim, seed, magnitude,
                        domain="decay", shift="baseline", lam_names=("lam",))


def gamma_12_1_grids(sim: Any, seed: int, magnitude: float):
    return _decay_grids(sim, seed, magnitude,
                        domain="decay", shift="gamma_12_1", lam_names=("lam",))


def gamma_12_2_grids(sim: Any, seed: int, magnitude: float):
    return _decay_grids(sim, seed, magnitude,
                        domain="decay", shift="gamma_12_2", lam_names=("lam0", "lam"))


def delta_12_1_grids(sim: Any, seed: int, magnitude: float):
    # GT scores the TOTAL N_A + N_B (spec.law returns the sum). The broken
    # symmetry is particle conservation; ξ lives only in N_B's equation, so
    # N_A(t) alone is a pure exponential identical to the textbook law — the
    # total is what drifts when ξ≠0 versus the conserved constant.
    return _decay_grids(sim, seed, magnitude,
                        domain="decay", shift="delta_12_1", lam_names=("lam",))


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
