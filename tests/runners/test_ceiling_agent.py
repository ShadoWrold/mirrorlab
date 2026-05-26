"""Tests for the oracle ceiling agent (Sprint 4 #2)."""

from __future__ import annotations

import pytest

from mirrorlab.eval.dimensional import parse_dim
from mirrorlab.runners.ceiling_agent import (
    CeilingAgent,
    broken_symmetry_for,
    build_submission,
)
from mirrorlab.runners.ceiling_sweep import all_pairs
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.loader import load as load_scenario


def test_submission_shape_hooke_baseline():
    scenario = load_scenario("hooke", "baseline", seed=0)
    sub = build_submission(scenario)
    assert isinstance(sub, list) and len(sub) == 1
    e = sub[0]
    for key in ("law_id", "formula", "predictor", "inputs", "outputs", "params"):
        assert key in e, f"missing {key}"
    assert callable(e["_predictor"])
    assert e["claim_broken_symmetry"] == "none"


def test_dim_signature_matches_scenario():
    scenario = load_scenario("gravity", "gamma_2_2", seed=0)
    sub = build_submission(scenario)
    target_units = next(iter(scenario.dim_signature["outputs"].values()))
    got_units = sub[0]["outputs"][0]["units"]
    assert parse_dim(got_units) == parse_dim(target_units)


def test_hooke_baseline_ceiling_score_high():
    scenario = load_scenario("hooke", "baseline", seed=0)
    sub = CeilingAgent().run(scenario)
    s = score_against_scenario(scenario, sub, gt_symmetry="none")
    assert s > 0.8, f"hooke baseline ceiling too low: {s}"


def test_hooke_gamma_1_1_ceiling_score_high():
    scenario = load_scenario("hooke", "gamma_1_1", seed=0)
    sub = CeilingAgent().run(scenario)
    s = score_against_scenario(scenario, sub, gt_symmetry="PAR")
    # Oracle wraps the actual shifted_force → must beat the baseline-form
    # stub easily on (a)+(b).
    assert s > 0.8, f"hooke γ-1-1 ceiling too low: {s}"


def test_all_pairs_produce_valid_submission():
    for domain_id, shift_id in all_pairs():
        scenario = load_scenario(domain_id, shift_id, seed=0)
        sub = build_submission(scenario)
        assert sub and "outputs" in sub[0]
        # Predictor must be callable on each grid's input dict without raising.
        pred = sub[0]["_predictor"]
        for grid in scenario.test_grids.values():
            for point in grid:
                if isinstance(point, tuple):
                    inputs, _ = point
                else:
                    # Hooke ndarray case: predictor takes x.
                    inputs = {"x": float(point)}
                pred(**inputs)  # must not raise


def test_broken_symmetry_baseline_is_none():
    assert broken_symmetry_for("hooke", "baseline") == "none"
    assert broken_symmetry_for("hooke", "gamma_1_1") == "PAR"
    assert broken_symmetry_for("gravity", "delta_2_1") == "T_TRANS"
