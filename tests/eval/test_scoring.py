"""Tests for ``mirrorlab.eval.scoring`` — per-scenario aggregation (spec §7)."""

from __future__ import annotations

import math

import numpy as np

from mirrorlab.eval.scoring import BONUS_DEFAULT, RHO_DEFAULT, SET_CAP, score_submission
from mirrorlab.scenarios.registry import make

DIM_FORCE = "kg*m*s**-2"


def _entry(k, *, claim=None, law_id="L"):
    e = {
        "law_id": law_id,
        "formula": "F = -k*x",
        "_predictor": lambda x, k: -k * x,
        "inputs":  [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": DIM_FORCE}],
        "params":  [{"name": "k", "units": "kg*s**-2", "value": k}],
    }
    if claim is not None:
        e["claim_broken_symmetry"] = claim
    return e


def _grids(sim, x_window=0.5):
    rng = np.random.default_rng(0)
    f, p = sim._force, sim.params  # noqa: SLF001
    xs_a = rng.uniform(-x_window, x_window, 6)
    xs_b = np.concatenate([
        rng.uniform(x_window, 5 * x_window, 3),
        -rng.uniform(x_window, 5 * x_window, 3),
    ])
    xs_c = rng.uniform(-x_window, x_window, 3)
    pack = lambda xs: [({"x": float(x)}, float(f(float(x), p))) for x in xs]
    return {"a": pack(xs_a), "b": pack(xs_b), "c": pack(xs_c)}


def test_cal_defaults_locked_to_spec():
    assert RHO_DEFAULT == 0.05
    assert BONUS_DEFAULT == 0.10
    assert SET_CAP == 5


def test_single_entry_no_shotgun_penalty():
    sim = make("hooke", "baseline", seed=1)
    s = score_submission(
        [_entry(sim.params.k)],
        target_dim=DIM_FORCE,
        test_grids=_grids(sim),
    )
    assert s > 0.95


def test_shotgun_five_entries_penalized():
    sim = make("hooke", "baseline", seed=1)
    grids = _grids(sim)
    one = score_submission([_entry(sim.params.k)], target_dim=DIM_FORCE, test_grids=grids)
    five = score_submission(
        [_entry(sim.params.k, law_id=f"L{i}") for i in range(5)],
        target_dim=DIM_FORCE,
        test_grids=grids,
    )
    # Penalty factor: 1 - 0.05 * (5 - 1) = 0.80
    assert math.isclose(five, one * 0.80, rel_tol=1e-6)


def test_set_capped_at_five():
    sim = make("hooke", "baseline", seed=1)
    grids = _grids(sim)
    submission = [_entry(sim.params.k * 100, law_id=f"bad{i}") for i in range(4)]
    submission += [_entry(sim.params.k, law_id="good")]
    submission += [_entry(sim.params.k, law_id="extra") for _ in range(5)]
    s = score_submission(submission, target_dim=DIM_FORCE, test_grids=grids)
    # Only the first 5 entries count; the good one is at index 4, so it's in.
    # n=5 ⇒ shotgun factor 0.80.
    assert s > 0.7
    assert s < 0.95  # full unpenalized score would be > 0.95


def test_dim_mismatch_zeros_entry():
    sim = make("hooke", "baseline", seed=1)
    bad = _entry(sim.params.k)
    bad["outputs"] = [{"name": "F", "units": "kg*m*s**-1"}]   # wrong dim
    good = _entry(sim.params.k)
    s_only_bad = score_submission([bad], target_dim=DIM_FORCE, test_grids=_grids(sim))
    s_both = score_submission([bad, good], target_dim=DIM_FORCE, test_grids=_grids(sim))
    assert s_only_bad == 0.0
    # Good entry survives, but shotgun-penalized by 1 extra entry.
    assert s_both > 0.9 * 0.95


def test_bonus_only_on_correct_symmetry_claim():
    sim = make("hooke", "gamma_1_1", seed=3)
    grids = _grids(sim, x_window=sim.params.x_scale * 0.5)
    base = score_submission(
        [_entry(sim.params.k)],
        target_dim=DIM_FORCE,
        test_grids=grids,
        gt_symmetry="PAR",
    )
    with_correct = score_submission(
        [_entry(sim.params.k, claim="PAR")],
        target_dim=DIM_FORCE,
        test_grids=grids,
        gt_symmetry="PAR",
    )
    with_wrong = score_submission(
        [_entry(sim.params.k, claim="ROT")],
        target_dim=DIM_FORCE,
        test_grids=grids,
        gt_symmetry="PAR",
    )
    assert math.isclose(with_correct - base, BONUS_DEFAULT, rel_tol=1e-9)
    # Wrong claim ⇒ no bonus, no penalty: identical to no-claim case.
    assert math.isclose(with_wrong, base, rel_tol=1e-9)


def test_bonus_case_insensitive_and_baseline_none():
    sim = make("hooke", "baseline", seed=5)
    grids = _grids(sim)
    s = score_submission(
        [_entry(sim.params.k, claim="none")],
        target_dim=DIM_FORCE,
        test_grids=grids,
        gt_symmetry="none",
    )
    base = score_submission(
        [_entry(sim.params.k)],
        target_dim=DIM_FORCE,
        test_grids=grids,
        gt_symmetry="none",
    )
    assert math.isclose(s - base, BONUS_DEFAULT, rel_tol=1e-9)


def test_empty_submission_scores_zero():
    assert score_submission([], target_dim=DIM_FORCE, test_grids={"a": []}) == 0.0
