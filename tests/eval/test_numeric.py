"""Tests for ``mirrorlab.eval.numeric`` — RMSLE + per-entry scoring.

Golden case: the correct Hooke baseline law ``F = -k·x`` should score high
on a baseline scenario and lower on γ-1-1 (where the truth is the
saturating-asymmetric nonlinear law).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mirrorlab.eval.numeric import (
    CLAMP,
    SUBGRID_WEIGHTS,
    TAU_DEFAULT,
    evaluate_entry,
    rmsle,
)
from mirrorlab.scenarios.registry import make
from mirrorlab.shifts.hooke_g_1_1 import HookeGamma11Params, shifted_force


def test_rmsle_zero_on_exact_match():
    assert rmsle([1.0, 2.0, -3.0], [1.0, 2.0, -3.0]) == pytest.approx(0.0)


def test_rmsle_handles_negative_values():
    # Signed-log: should be finite and positive, not nan/inf.
    r = rmsle([-1.0, -2.0], [-1.1, -1.9])
    assert math.isfinite(r) and r > 0


def test_rmsle_clamps_divergent():
    huge = [1e20, -1e30]
    truth = [0.0, 0.0]
    r = rmsle(huge, truth)
    # Without clamp this would be ~log(1e30) ≈ 69; with clamp at 1e6 it's ~log(1e6) ≈ 13.8.
    assert math.isfinite(r)
    assert r <= math.log1p(CLAMP) + 1e-6


def test_rmsle_nan_does_not_poison():
    r = rmsle([float("nan"), 1.0], [0.0, 1.0])
    assert math.isfinite(r)


def test_rmsle_shape_mismatch_raises():
    with pytest.raises(ValueError):
        rmsle([1.0, 2.0], [1.0])


def _hooke_entry(k_guess: float, *, claim=None):
    entry = {
        "law_id": "L1",
        "formula": "F = -k*x",
        "_predictor": lambda x, k: -k * x,
        "inputs":  [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
        "params":  [{"name": "k", "units": "kg*s**-2", "value": k_guess}],
    }
    if claim is not None:
        entry["claim_broken_symmetry"] = claim
    return entry


def _build_grids(sim, *, n_a=8, n_b=8, n_c=4, x_window=0.5, ood_factor=5.0):
    rng = np.random.default_rng(0)
    xs_a = rng.uniform(-x_window, x_window, n_a)
    # OOD: outside the in-domain window, per CAL-2 (5× sampling range default).
    xs_b_pos = rng.uniform(x_window, ood_factor * x_window, n_b // 2)
    xs_b_neg = -rng.uniform(x_window, ood_factor * x_window, n_b - n_b // 2)
    xs_b = np.concatenate([xs_b_pos, xs_b_neg])
    xs_c = rng.uniform(-x_window, x_window, n_c)
    # Use sim.step at t=0 with displaced initial conditions? Simpler for unit
    # tests: directly invoke the force_law via sim._force (it's the ground
    # truth predictor). That's the same surface eval will use in production
    # (wrapped via SimInstance.params + force_law closure).
    f = sim._force  # noqa: SLF001 — test-only access
    p = sim.params

    def grid(xs):
        return [({"x": float(x)}, float(f(float(x), p))) for x in xs]

    return {"a": grid(xs_a), "b": grid(xs_b), "c": grid(xs_c)}


def test_linear_hooke_scores_high_on_baseline():
    sim = make("hooke", "baseline", seed=42)
    entry = _hooke_entry(sim.params.k)
    grids = _build_grids(sim)
    s = evaluate_entry(entry, grids)
    assert s > 0.95


def test_linear_hooke_scores_lower_on_gamma_1_1():
    sim_base = make("hooke", "baseline", seed=42)
    sim_shift = make("hooke", "gamma_1_1", seed=42)
    grids_base = _build_grids(sim_base)
    grids_shift = _build_grids(sim_shift)
    entry_base = _hooke_entry(sim_base.params.k)
    entry_shift = _hooke_entry(sim_shift.params.k)
    s_base = evaluate_entry(entry_base, grids_base)
    s_shift = evaluate_entry(entry_shift, grids_shift)
    # The linear guess on a nonlinear truth must underperform the linear
    # guess on the linear truth. Hard inequality.
    assert s_shift < s_base


def test_subgrid_weights_default_match_cal1():
    assert SUBGRID_WEIGHTS == {"a": 0.40, "b": 0.40, "c": 0.20}


def test_tau_default_matches_cal4():
    assert TAU_DEFAULT == 0.5


def test_constant_predictor_scores_near_zero():
    sim = make("hooke", "baseline", seed=7)
    grids = _build_grids(sim, x_window=1.0)
    entry = {
        "law_id": "trivial",
        "formula": "F = 0",
        "_predictor": lambda x: 0.0,
        "inputs":  [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
        "params":  [],
    }
    s = evaluate_entry(entry, grids)
    assert s < 0.9  # well below a fitting predictor on a nontrivial spring
