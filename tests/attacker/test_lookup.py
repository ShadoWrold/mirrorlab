"""Mock-based unit tests for the lookup-attacker (spec §8 / CAL-8 / CAL-9).

No test in this module touches a real LLM endpoint. The attacker's
``llm_call`` is replaced with a scripted callable that emits a fixed
sequence of assistant messages, exactly as in
``tests/runners/test_llm_agent.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Sequence

import pytest

from mirrorlab.attacker import (
    ATTACKER_SYSTEM_PROMPT,
    ATTACK_SLICE,
    LookupAttacker,
    PASS_THRESHOLD,
    run_attack_sweep,
)
from mirrorlab.attacker.runner import _aggregate, _score_attack
from mirrorlab.runners.openai_client import SUBMIT_TOOL, mangle_name
from mirrorlab.scenarios.loader import load as load_scenario


# ---- Fake OpenAI message objects (mirrors tests/runners) ---------------

@dataclass
class FakeFn:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFn
    type: str = "function"


@dataclass
class FakeMsg:
    content: str = ""
    tool_calls: List[FakeToolCall] = field(default_factory=list)


def _tc(call_id: str, name: str, args: Mapping[str, Any]) -> FakeToolCall:
    return FakeToolCall(id=call_id,
                        function=FakeFn(name=name, arguments=json.dumps(args)))


def _scripted(responses: Sequence[FakeMsg]) -> Callable:
    it = iter(responses)
    def _call(messages, tools):
        return next(it)
    return _call


# ---- Canonical / non-canonical submissions ------------------------------

DIM_FORCE = "kg*m*s**-2"

CANONICAL_HOOKE = [{
    "law_id": "hooke",
    "formula": "F = -k*x",
    "predictor": {"lang": "python", "code": "def f(x, k):\n    return -k*x\n"},
    "inputs":  [{"name": "x", "units": "m"}],
    "outputs": [{"name": "F", "units": DIM_FORCE}],
    "params":  [{"name": "k", "units": "kg*s**-2", "value": 1.5}],
    "claim_broken_symmetry": "none",
}]


def _hooke_canonical_for(sim) -> List[dict]:
    """Canonical Hooke submission using the scenario's true ``k``."""
    return [{
        "law_id": "hooke",
        "formula": "F = -k*x",
        "predictor": {"lang": "python",
                      "code": "def f(x, k):\n    return -k*x\n"},
        "inputs":  [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": DIM_FORCE}],
        "params":  [{"name": "k", "units": "kg*s**-2",
                     "value": float(sim.params.k)}],
        "claim_broken_symmetry": "none",
    }]


# ---- Prompt lock --------------------------------------------------------

def test_attacker_prompt_is_locked_and_documents_strategy():
    """Spec §8.2 — the prompt is part of the contract."""
    p = ATTACKER_SYSTEM_PROMPT
    assert "STRATEGY IS LOCKED" in p
    assert "textbook" in p.lower()
    assert "do not propose novel" in p.lower()
    assert "20 tool calls" in p
    assert "submit_answer" in p


def test_slice_is_24_pairs_one_gamma_one_delta_per_domain():
    """Spec §8.1 — 12 domains × (1 γ + 1 δ) = 24 cells."""
    assert len(ATTACK_SLICE) == 24
    domains = {d for d, _ in ATTACK_SLICE}
    assert len(domains) == 12
    gammas = [s for _, s in ATTACK_SLICE if "gamma_" in s]
    deltas = [s for _, s in ATTACK_SLICE if "delta_" in s]
    assert len(gammas) == 12
    assert len(deltas) == 12


def test_pass_threshold_is_half():
    """CAL-9 pinned at < 0.50."""
    assert PASS_THRESHOLD == 0.50


# ---- Single-scenario attacks --------------------------------------------

def test_attacker_identifies_baseline_high_score():
    """Attacker called on Hooke baseline submits the canonical law → high S."""
    scenario = load_scenario("hooke", "baseline", seed=0)
    sub = _hooke_canonical_for(scenario.sim)
    responses = [FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": sub})])]
    attacker = LookupAttacker(llm_call=_scripted(responses))
    result = attacker.run(scenario)

    assert result.terminated_by == "submit"
    assert result.claimed_law == "hooke"
    assert result.claimed_formula == "F = -k*x"
    assert result.submission == sub

    score = _score_attack(scenario, result)
    assert score > 0.9, f"expected high score on baseline, got {score}"


def test_attacker_confuses_gamma_shift_low_score():
    """A canonical Hooke submission with the WRONG k → low S on a shifted scenario.

    This exercises the runner's score-collection path against a deliberately
    non-matching predictor (analogue of a lookup-attacker who picks the right
    law family but wrong parameters on a counterfactual shift). The RMSLE-
    based scorer must collapse the score well below 0.50.

    NOTE: we use a *deliberately* mis-fit predictor rather than relying on the
    γ-1-1 shift's deviation from canonical Hooke, because the existing Hooke
    test grid only varies ``x`` (velocity-dependent and high-η-tanh terms
    don't manifest in a 1-D x-only grid). End-to-end attack-vs-shift behavior
    is the integrator's real-sweep concern, not a unit-test property.
    """
    scenario = load_scenario("hooke", "gamma_1_1", seed=0)
    # Submit canonical Hooke shape with a wildly wrong stiffness — predictor
    # value diverges from ground truth → low score.
    sub = [{
        "law_id": "hooke",
        "formula": "F = -k*x",
        "predictor": {"lang": "python",
                      "code": "def f(x, k):\n    return -k*x\n"},
        "inputs":  [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": DIM_FORCE}],
        "params":  [{"name": "k", "units": "kg*s**-2",
                     "value": 100.0 * float(scenario.sim.params.k) + 50.0}],
        "claim_broken_symmetry": "none",
    }]
    responses = [FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": sub})])]
    attacker = LookupAttacker(llm_call=_scripted(responses))
    result = attacker.run(scenario)

    score = _score_attack(scenario, result)
    assert score < 0.50, (
        f"a wildly wrong canonical Hooke submission should score under "
        f"the gate, got {score:.3f}"
    )


def test_attacker_budget_is_k20_per_cal8():
    """Defaults must not drift away from CAL-8."""
    attacker = LookupAttacker(llm_call=lambda m, t: FakeMsg())
    assert attacker.max_tool_calls == 20


def test_attacker_records_tool_calls_then_submits():
    scenario = load_scenario("hooke", "baseline", seed=0)
    sub = _hooke_canonical_for(scenario.sim)

    def llm_call(messages, tools):
        seen_tool_result = any(m.get("role") == "tool" for m in messages)
        if not seen_tool_result:
            return FakeMsg(tool_calls=[
                _tc("c1", mangle_name("measure.observable"),
                    {"name": "x", "t": 0.0}),
            ])
        return FakeMsg(tool_calls=[_tc("c2", SUBMIT_TOOL, {"submission": sub})])

    attacker = LookupAttacker(llm_call=llm_call)
    result = attacker.run(scenario)
    assert result.tool_calls == 1
    assert result.llm_turns == 2
    assert result.terminated_by == "submit"


def test_attacker_budget_exhaustion_returns_empty_submission():
    scenario = load_scenario("hooke", "baseline", seed=0)
    # Always emit a measure call, never submit → budget exhausted.
    looper = lambda m, t: FakeMsg(tool_calls=[
        _tc(f"c{len(m)}", mangle_name("measure.observable"),
            {"name": "x", "t": 0.0}),
    ])
    attacker = LookupAttacker(llm_call=looper, max_tool_calls=3)
    result = attacker.run(scenario)
    assert result.terminated_by == "budget"
    assert result.tool_calls == 3
    assert result.submission == []
    assert result.claimed_law is None


def test_malformed_submit_retries_once():
    scenario = load_scenario("hooke", "baseline", seed=0)
    sub = _hooke_canonical_for(scenario.sim)
    responses = [
        FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": "not-a-list"})]),
        FakeMsg(tool_calls=[_tc("c2", SUBMIT_TOOL, {"submission": sub})]),
    ]
    attacker = LookupAttacker(llm_call=_scripted(responses))
    result = attacker.run(scenario)
    assert result.submission == sub
    assert result.terminated_by == "submit"


# ---- Aggregate scoring math --------------------------------------------

from mirrorlab.attacker.lookup import AttackResult


def _fake_result(domain: str, shift: str, seed: int) -> AttackResult:
    return AttackResult(
        domain_id=domain, shift_id=shift, seed=seed,
        submission=[], claimed_law=None, claimed_formula=None,
        tool_calls=0, llm_turns=0, elapsed_s=0.0, terminated_by="submit",
    )


def test_aggregate_macro_mean_then_equal_weight():
    """Spec §7: cell mean over seeds, then equal-weight average over cells."""
    results = [
        _fake_result("hooke", "gamma_1_1", 0),
        _fake_result("hooke", "gamma_1_1", 1),
        _fake_result("hooke", "gamma_1_1", 2),
        _fake_result("hooke", "delta_1_1", 0),
        _fake_result("hooke", "delta_1_1", 1),
        _fake_result("hooke", "delta_1_1", 2),
    ]
    scores = [0.9, 0.9, 0.9,  0.1, 0.1, 0.1]
    cells, s_bench = _aggregate(results, scores)
    assert cells[("hooke", "gamma_1_1")] == pytest.approx(0.9)
    assert cells[("hooke", "delta_1_1")] == pytest.approx(0.1)
    # Equal-weight average of the two cells.
    assert s_bench == pytest.approx(0.5)


def test_aggregate_handles_empty():
    cells, s_bench = _aggregate([], [])
    assert cells == {}
    assert s_bench == 0.0


# ---- Sweep driver -------------------------------------------------------

def test_run_attack_sweep_passes_threshold_on_confused_attacker():
    """Locked attacker that always submits canonical Hooke is confused by γ-1-1
    and δ-1-1 → S_bench^lookup < 0.50.

    We restrict the slice to the Hooke pair only so the partial test-grid
    wiring (only Hooke has (a)/(b)/(c) grids today) doesn't bias the
    aggregate to 0 from missing grids.
    """
    def llm_call(messages, tools):
        # Scenario is identified by the user prompt; pick the right baseline
        # k by reading the SystemContext-attached scenario id is not visible,
        # so we just emit a fixed-k canonical Hooke. RMSLE-based scoring will
        # naturally collapse it on the shifted scenario regardless of k.
        sub = [{
            "law_id": "hooke",
            "formula": "F = -k*x",
            "predictor": {"lang": "python",
                          "code": "def f(x, k):\n    return -k*x\n"},
            "inputs":  [{"name": "x", "units": "m"}],
            "outputs": [{"name": "F", "units": DIM_FORCE}],
            "params":  [{"name": "k", "units": "kg*s**-2", "value": 10.0}],
            "claim_broken_symmetry": "none",
        }]
        return FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": sub})])

    attacker = LookupAttacker(llm_call=llm_call)
    report = run_attack_sweep(
        attacker,
        slice_pairs=(("hooke", "gamma_1_1"), ("hooke", "delta_1_1")),
        seeds=(0, 1, 2),
    )
    assert report.n_scenarios == 6  # 2 cells × 3 seeds
    assert len(report.cell_scores) == 2
    assert report.s_bench_lookup < PASS_THRESHOLD
    assert report.passed is True


def test_attack_report_serialises_to_json():
    """The CLI prints ``report.as_dict()`` as JSON — schema check."""
    def llm_call(messages, tools):
        return FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL,
                                       {"submission": CANONICAL_HOOKE})])
    attacker = LookupAttacker(llm_call=llm_call)
    report = run_attack_sweep(
        attacker,
        slice_pairs=(("hooke", "gamma_1_1"),),
        seeds=(0,),
    )
    payload = report.as_dict()
    assert "s_bench_lookup" in payload
    assert "threshold" in payload
    assert "passed" in payload
    assert "scenarios" in payload
    assert payload["scenarios"][0]["domain_id"] == "hooke"
    # Round-trip JSON.
    text = json.dumps(payload)
    assert json.loads(text) == payload


# ---- No-network guard --------------------------------------------------

def test_attacker_never_calls_openai_sdk_in_tests():
    from unittest.mock import patch
    scenario = load_scenario("hooke", "baseline", seed=0)
    responses = [FakeMsg(tool_calls=[
        _tc("c1", SUBMIT_TOOL, {"submission": CANONICAL_HOOKE})
    ])]
    with patch("mirrorlab.runners.openai_client.OpenAIClient._sdk",
               side_effect=AssertionError("must not call SDK in tests")):
        attacker = LookupAttacker(llm_call=_scripted(responses))
        attacker.run(scenario)
