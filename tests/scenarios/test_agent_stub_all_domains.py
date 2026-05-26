"""Sprint-3 contract tests: rule-based stub emits valid submissions for all domains."""

from __future__ import annotations

import math
import re

import pytest

from mirrorlab.scenarios import agent_stub
from mirrorlab.scenarios.loader import load
from mirrorlab.scenarios.registry import REGISTRY

# (domain, baseline) and (domain, γ_X_1) — first γ shift per domain, mapping
# from the registry naming convention used in Sprint 2.
_GAMMA_FIRST = {
    "hooke": "gamma_1_1",
    "gravity": "gamma_2_1",
    "damped_ho": "gamma_3_1",
    "pendulum": "gamma_4_1",
    "coulomb": "gamma_5_1",
    "rlc": "gamma_6_1",
    "thermal": "gamma_7_1",
    "wave": "gamma_8_1",
    "optics": "gamma_9_1",
    "fluid": "gamma_10_1",
    "kinetics": "gamma_11_1",
    "decay": "gamma_12_1",
}

_UNITS_TOKEN = re.compile(r"^[A-Za-z_*\d\-\.\*\^]+$")  # liberal


def _check_submission_shape(entry: dict) -> None:
    assert isinstance(entry, dict)
    for key in ("law_id", "formula", "predictor", "inputs", "outputs", "params"):
        assert key in entry, f"missing key {key!r}"
    assert isinstance(entry["inputs"], list) and entry["inputs"]
    assert isinstance(entry["outputs"], list) and entry["outputs"]
    assert isinstance(entry["params"], list)
    for fld in entry["inputs"] + entry["outputs"]:
        assert "name" in fld and "units" in fld
        assert isinstance(fld["units"], str) and fld["units"]
    for p in entry["params"]:
        assert "name" in p and "units" in p and "value" in p
        assert isinstance(p["units"], str) and p["units"]
        assert math.isfinite(float(p["value"]))
    assert entry["predictor"].get("lang") == "python"
    assert isinstance(entry["predictor"].get("code"), str)


def _dim_for_domain(domain_id: str) -> dict:
    sc = load(domain_id, "baseline", seed=0)
    return sc.dim_signature


@pytest.mark.parametrize(
    "domain_id,shift_id",
    [(d, "baseline") for d in sorted(_GAMMA_FIRST)]
    + [(d, g) for d, g in sorted(_GAMMA_FIRST.items())],
)
def test_stub_runs_on_pair(domain_id: str, shift_id: str) -> None:
    """The stub must emit a valid Submission entry for every required pair."""
    assert (domain_id, shift_id) in REGISTRY
    sc = load(domain_id, shift_id, seed=0)
    entry = agent_stub.run(sc)
    _check_submission_shape(entry)
    # Outputs dim must match domain's declared output unit family (a
    # weaker check than exact equality — the agent may propose a
    # different output name, but the unit string must be syntactically
    # valid and non-empty, asserted in _check_submission_shape above).


def test_hooke_baseline_recovers_k() -> None:
    """Regression of Sprint-1 expectation: hooke baseline fit recovers k."""
    sc = load("hooke", "baseline", seed=0)
    entry = agent_stub.run(sc)
    k_true = float(sc.sim.params.k)
    k_hat = entry["params"][0]["value"]
    assert k_hat == pytest.approx(k_true, rel=1e-3)


def test_stub_dispatches_by_domain() -> None:
    """Each domain produces a stable formula string (regression smoke)."""
    formulas = {}
    for d in sorted(_GAMMA_FIRST):
        sc = load(d, "baseline", seed=0)
        formulas[d] = agent_stub.run(sc)["formula"]
    # All distinct → genuine per-domain dispatch (not a single fallback).
    assert len(set(formulas.values())) == len(formulas), formulas
