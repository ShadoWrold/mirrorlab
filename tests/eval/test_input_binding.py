"""Regression tests for LLM-submission input binding (task #7).

Sprint 4's first sweep returned 0.0 across all 60 cells because the scoring
pipeline failed to bind LLM submissions whose predictor signature listed
scenario constants (q1, q2, k_e, …) as kwargs the test grid never supplied.
These tests pin the binding contract:

  * declared input names that match grid keys → predictor receives them;
  * extra kwargs the grid packer injects (scenario constants) are filtered
    against the predictor signature, not blindly forwarded;
  * an entry's ``inputs`` list aliases grid keys positionally when the LLM
    used different variable names;
  * SI named units (``N``, ``W``, ``C`` …) survive the stage-1 dim filter.

The golden test loads the real gpt-5.4 + coulomb γ-5-1 submission from
``docs/sprint4-sweep-data.json`` and asserts the rescore now exceeds 0.5
— the artefact captures Sprint 4's regression in one assertion.
"""

from __future__ import annotations

import json
import os

import pytest

from mirrorlab.eval.dimensional import match_dim, parse_dim
from mirrorlab.eval.numeric import evaluate_entry
from mirrorlab.eval.scoring import score_submission
from mirrorlab.runners.sprint3_pilot import (
    pack_grids,
    score_against_scenario,
    _scenario_constants,
)
from mirrorlab.scenarios.loader import load as load_scenario


# ---- Stage-1 dim filter: SI named units --------------------------------

def test_newton_unit_parses_as_kg_m_per_s2():
    assert parse_dim("N") == parse_dim("kg*m*s**-2")


def test_watt_per_meter_squared_matches_thermal_target():
    # thermal heat flux output (W m^-2) matches the equivalent base form.
    assert parse_dim("W*m**-2") == parse_dim("kg*s**-3")
    assert parse_dim("W/m^2") == parse_dim("W*m**-2")


def test_dimensionless_strings_normalise_to_zero():
    assert parse_dim("dimensionless") == parse_dim("1")


def test_abstract_form_still_uses_amount_symbols():
    # Bracketed abstract form keeps the original N=amount mapping so
    # symbolic dim usage isn't shadowed by SI-named-unit overrides.
    from mirrorlab.eval.dimensional import _UNIT_TO_INDEX  # noqa: SLF001
    assert _UNIT_TO_INDEX["N"] == 5  # amount-of-substance index unchanged
    # Bracketed form preserves M·L/T² → (1,1,-2,…) without invoking newton.
    assert parse_dim("[M·L/T²]") == (1, 1, -2, 0, 0, 0, 0)


# ---- Stage-2 numerical binding -----------------------------------------

DIM_FORCE = "kg*m*s**-2"
GRIDS = {
    "a": [({"r": 0.5}, 8987551787.368176 * 1e-9 * 1e-9 / 0.5 ** 2),
          ({"r": 1.0}, 8987551787.368176 * 1e-9 * 1e-9 / 1.0 ** 2)],
    "b": [({"r": 2.0}, 8987551787.368176 * 1e-9 * 1e-9 / 2.0 ** 2)],
    "c": [({"r": 0.7}, 8987551787.368176 * 1e-9 * 1e-9 / 0.7 ** 2)],
}


def _enriched(grids, consts):
    return {k: [({**consts, **ins}, gt) for ins, gt in pts] for k, pts in grids.items()}


def test_kwarg_predictor_with_matching_grid_keys_scores_high():
    """LLM-style entry whose predictor takes q1, q2, r — q1/q2 supplied via constants."""
    entry = {
        "law_id": "L1",
        "formula": "F = k q1 q2 / r^2",
        "predictor": {
            "lang": "python",
            "code": "def f(r, q1, q2, k):\n    return k * q1 * q2 / (r ** 2)\n",
        },
        "inputs": [{"name": "r", "units": "m"},
                   {"name": "q1", "units": "C"},
                   {"name": "q2", "units": "C"}],
        "outputs": [{"name": "F", "units": "N"}],
        "params": [{"name": "k", "units": "N m^2 C^-2", "value": 8987551787.368176}],
    }
    consts = {"q1": 1.0e-9, "q2": 1.0e-9}
    s = score_submission(
        [entry], target_dim=DIM_FORCE,
        test_grids=_enriched(GRIDS, consts),
        canonical_inputs=["r"],
    )
    assert s > 0.95


def test_predictor_signature_filters_unused_constants():
    """Extra constants in the grid dict must not poison a strict signature."""
    entry = {
        "law_id": "L1",
        "predictor": {"lang": "python", "code": "def f(x, k):\n    return -k*x\n"},
        "inputs": [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "N"}],
        "params": [{"name": "k", "units": "kg*s**-2", "value": 2.0}],
    }
    grids = {"a": [({"x": 0.1, "extra1": 99.0, "noise": 1.0}, -0.2)]}
    s = evaluate_entry(entry, grids)
    assert s > 0.95


def test_inputs_list_aliases_grid_keys_positionally():
    """LLM used 'displacement' for what the grid calls 'x' → still scored."""
    entry = {
        "law_id": "L1",
        "predictor": {
            "lang": "python",
            "code": "def f(displacement, k):\n    return -k * displacement\n",
        },
        "inputs": [{"name": "displacement", "units": "m"}],
        "outputs": [{"name": "F", "units": "N"}],
        "params": [{"name": "k", "units": "kg*s**-2", "value": 3.0}],
    }
    grids = {"a": [({"x": 0.0}, 0.0), ({"x": 0.5}, -1.5), ({"x": -0.2}, 0.6)]}
    s = score_submission(
        [entry], target_dim=DIM_FORCE,
        test_grids=grids,
        canonical_inputs=["x"],
    )
    assert s > 0.95


def test_match_dim_accepts_newton_against_kg_m_s_target():
    entry = {"outputs": [{"name": "F", "units": "N"}]}
    assert match_dim(entry, DIM_FORCE)


# ---- Golden regression: gpt-5.4 + coulomb γ-5-1 ------------------------

SWEEP_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "sprint4-sweep-data.json"
)


def _gpt54_coulomb_entry():
    with open(SWEEP_JSON, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    for e in blob["entries"]:
        if (
            e["model"] == "gpt-5.4-20260305"
            and e["domain_id"] == "coulomb"
            and e["shift_id"] == "gamma_5_1"
        ):
            return e
    return None


@pytest.mark.skipif(
    not os.path.exists(SWEEP_JSON) or _gpt54_coulomb_entry() is None,
    reason="sprint4 sweep artefact not present",
)
def test_sprint4_gpt54_coulomb_gamma_5_1_now_scores():
    entry = _gpt54_coulomb_entry()
    assert entry is not None
    scenario = load_scenario("coulomb", "gamma_5_1", seed=0)
    s = score_against_scenario(scenario, entry["submission"])
    # Was 0.0 before the fix; the correct Coulomb predictor against a
    # γ-shifted scenario must clear 0.5 once binding is repaired.
    assert s > 0.5, f"expected >0.5 after binding fix, got {s}"


def test_pack_grids_enriches_with_canonical_constants():
    scenario = load_scenario("coulomb", "gamma_5_1", seed=0)
    consts = _scenario_constants(scenario)
    # canonical names from dim_signature.params must be present even when
    # the underlying sim uses aliased attributes (q_src/q_test).
    for canon in ("q1", "q2", "k_e", "m"):
        assert canon in consts, f"missing canonical const {canon}"
    packed = pack_grids(scenario)
    a0 = packed["a"][0][0]
    for canon in ("q1", "q2", "k_e", "r"):
        assert canon in a0
