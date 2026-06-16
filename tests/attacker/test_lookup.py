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
from mirrorlab.attacker.lookup import build_attacker_system_prompt
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


def test_attacker_confuses_strong_shift_low_score():
    """A canonical baseline-form submission collapses on a STRONG shift.

    Under X+Y, ``k`` (and every law coefficient) is a free parameter the
    evaluator overrides per-point on sub-grid (c), so a "wrong-k" canonical
    Hooke no longer scores differently from a right-k one — the old
    ``test_attacker_confuses_gamma_shift_low_score`` premise ("wrong
    parameters → low score") is void.

    What DOES collapse is a baseline-form predictor on a shift whose broken
    symmetry the canonical law structurally cannot express. Gravity γ-2-1
    (ROT break, 3-D anisotropic) is such a cell: T23 shows the textbook
    inverse-square radial form scores ~0 there. We assert the attacker's
    canonical submission lands well under the CAL-9 gate on this cell.

    NOTE: this is a *per-cell* property only for STRONG cells. Weak shifts
    (hooke γ-1-1/δ-1-1, several T-modulated δ cells) score high by physics —
    see ``test_run_attack_sweep_gate_is_macro_mean`` for the aggregate gate.
    """
    scenario = load_scenario("gravity", "gamma_2_1", seed=0)
    sub = [{
        "law_id": "newton_gravity",
        "formula": "F = -G*M*m/r**2",
        "predictor": {"lang": "python",
                      "code": "def f(r, G, M, m):\n    return -G*M*m/(r*r)\n"},
        "inputs":  [{"name": "r", "units": "m"}],
        "outputs": [{"name": "F", "units": DIM_FORCE}],
        "params":  [{"name": "G", "units": "m**3*kg**-1*s**-2", "value": 6.674e-11},
                    {"name": "M", "units": "kg", "value": 1.0e21},
                    {"name": "m", "units": "kg", "value": 1.0}],
        "claim_broken_symmetry": "none",
    }]
    responses = [FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": sub})])]
    attacker = LookupAttacker(llm_call=_scripted(responses))
    result = attacker.run(scenario)

    score = _score_attack(scenario, result)
    assert score < 0.50, (
        f"a canonical inverse-square submission should collapse on the "
        f"ROT-broken gravity γ-2-1 cell, got {score:.3f}"
    )


def test_attacker_budget_is_k20_per_cal8():
    """Defaults must not drift away from CAL-8."""
    attacker = LookupAttacker(llm_call=lambda m, t: FakeMsg())
    assert attacker.max_tool_calls == 20


# ---- Prompt-vs-runtime budget invariant ---------------------------------

def test_attacker_prompt_default_advertises_cal8_budget():
    p = build_attacker_system_prompt()
    assert "20 tool calls" in p
    assert "60 s" in p
    assert "#17" in p  # 20 - 3


def test_attacker_prompt_renders_runtime_budget():
    """Sprint-3 incident: prompt said 20, runner allowed 6 → confused attacker."""
    p = build_attacker_system_prompt(max_tool_calls=6, max_wall_seconds=45)
    assert "6 tool calls" in p
    assert "45 s" in p
    assert "20 tool calls" not in p
    assert "#3" in p  # 6 - 3


def test_attacker_system_message_uses_runtime_budget():
    """The system message LookupAttacker sends must reflect runner K."""
    scenario = load_scenario("hooke", "baseline", seed=0)
    captured: dict = {}

    def llm_call(messages, tools):
        captured.setdefault("sys", messages[0]["content"])
        return FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL,
                                       {"submission": CANONICAL_HOOKE})])

    attacker = LookupAttacker(
        llm_call=llm_call, max_tool_calls=6, max_wall_seconds=45,
    )
    attacker.run(scenario)
    assert "6 tool calls" in captured["sys"]
    assert "45 s" in captured["sys"]
    assert "#3" in captured["sys"]


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

def test_run_attack_sweep_gate_is_macro_mean_on_strong_cells():
    """The CAL-9 gate is the 24-cell *macro-mean*, not a per-cell property.

    A locked attacker submitting the canonical inverse-square law collapses
    on STRONG cells (gravity γ-2-1, coulomb γ-5-1 — both ROT-broken, ~0 in
    T23). Restricting the slice to those, the aggregate must sit under the
    gate. We deliberately do NOT use hooke γ-1-1/δ-1-1 here: under X+Y those
    are weak shifts where a textbook 1-D linear form scores ~0.65–0.86 by
    physics, so a 2-cell hooke slice does NOT pass the gate — that is real
    benchmark physics, not a runner bug. The honest aggregate gate over the
    full γ∪δ slice is validated by the real T24 LLM sweep, not this unit test.
    """
    def llm_call(messages, tools):
        # Canonical Newtonian gravity (also dimensionally valid as a generic
        # inverse-square force on coulomb's force channel). On a ROT-broken
        # cell its radial form cannot track the 3-D anisotropy → score ~0.
        sub = [{
            "law_id": "inverse_square",
            "formula": "F = -G*M*m/r**2",
            "predictor": {"lang": "python",
                          "code": "def f(r, G, M, m):\n    return -G*M*m/(r*r)\n"},
            "inputs":  [{"name": "r", "units": "m"}],
            "outputs": [{"name": "F", "units": DIM_FORCE}],
            "params":  [{"name": "G", "units": "m**3*kg**-1*s**-2", "value": 6.674e-11},
                        {"name": "M", "units": "kg", "value": 1.0e21},
                        {"name": "m", "units": "kg", "value": 1.0}],
            "claim_broken_symmetry": "none",
        }]
        return FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": sub})])

    attacker = LookupAttacker(llm_call=llm_call)
    report = run_attack_sweep(
        attacker,
        slice_pairs=(("gravity", "gamma_2_1"), ("coulomb", "gamma_5_1")),
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
