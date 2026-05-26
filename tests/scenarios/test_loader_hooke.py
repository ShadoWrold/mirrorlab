"""Sprint-1 contract tests for the Hooke scenario loader + rule-based stub."""

from __future__ import annotations

import re

import numpy as np
import pytest

from mirrorlab.scenarios import agent_stub
from mirrorlab.scenarios.loader import ScenarioInstance, load


# Tokens the agent-visible prompt MUST NOT contain: shift labels and any hint
# of the underlying formula family.
_PROMPT_FORBIDDEN = (
    "gamma_1_1",
    "γ-1-1",
    "g_1_1",
    "tanh",
    "η",
    "eta",
    "x_scale",
    "Hooke",
    "hooke",
    "spring",
    "PAR",
    "parity",
    "broken",
    "linear",
    "F = -k",
    "-k*x",
    "-k x",
    "shift",
)


@pytest.mark.parametrize("shift_id", ["baseline", "gamma_1_1"])
def test_load_returns_scenario_instance(shift_id: str) -> None:
    sc = load("hooke", shift_id, seed=0)
    assert isinstance(sc, ScenarioInstance)
    assert sc.domain_id == "hooke"
    assert sc.shift_id == shift_id
    assert sc.seed == 0
    # sim is wired
    obs = sc.sim.step(0.0)
    for key in ("t", "x", "v", "F"):
        assert key in obs
    # observables + dim sig are present
    assert "x" in sc.observables and "F" in sc.observables
    assert sc.dim_signature["outputs"]["F"] == "kg*m*s**-2"
    # test grids: a / b / c populated
    for key in ("a", "b", "c"):
        assert key in sc.test_grids
        assert isinstance(sc.test_grids[key], np.ndarray)
        assert sc.test_grids[key].size > 0


@pytest.mark.parametrize("shift_id", ["baseline", "gamma_1_1"])
def test_prompt_does_not_leak_shift_or_formula(shift_id: str) -> None:
    sc = load("hooke", shift_id, seed=0)
    prompt = sc.prompt
    assert isinstance(prompt, str) and prompt.strip()
    lowered = prompt.lower()
    for token in _PROMPT_FORBIDDEN:
        assert token.lower() not in lowered, (
            f"prompt for ({sc.domain_id}, {sc.shift_id}) leaked forbidden "
            f"token {token!r}"
        )
    # prompt is identical across shifts of the same domain (no per-shift leak)
    sc_other = load(
        "hooke", "gamma_1_1" if shift_id == "baseline" else "baseline", seed=0
    )
    assert sc.prompt == sc_other.prompt


def test_stub_submits_linear_law_on_baseline() -> None:
    sc = load("hooke", "baseline", seed=0)
    entry = agent_stub.run(sc)
    _assert_linear_submission_shape(entry)
    # On baseline (true F = -k x), the fitted k should recover the GT k closely.
    k_true = float(sc.sim.params.k)
    k_hat = entry["params"][0]["value"]
    assert k_hat == pytest.approx(k_true, rel=1e-3)


def test_stub_submits_linear_law_on_gamma_1_1() -> None:
    sc = load("hooke", "gamma_1_1", seed=0)
    entry = agent_stub.run(sc)
    # Same linear law shape — stub does NOT adapt to nonlinearity (by design).
    _assert_linear_submission_shape(entry)
    # We don't assert accuracy here; the demo's whole point is that this
    # mis-extrapolates on γ-1-1 and the evaluator will score it down.
    assert np.isfinite(entry["params"][0]["value"])


def _assert_linear_submission_shape(entry: dict) -> None:
    assert entry["formula"] == "F = -k*x"
    assert entry["inputs"] == [{"name": "x", "units": "m"}]
    assert entry["outputs"] == [{"name": "F", "units": "kg*m*s**-2"}]
    assert len(entry["params"]) == 1
    assert entry["params"][0]["name"] == "k"
    assert entry["params"][0]["units"] == "kg*s**-2"
    assert entry["predictor"]["lang"] == "python"
    # predictor body actually implements the declared formula
    code = entry["predictor"]["code"]
    assert re.search(r"-\s*k\s*\*\s*x", code)
