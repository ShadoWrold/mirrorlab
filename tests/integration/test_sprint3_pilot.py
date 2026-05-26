"""Sprint 3 pilot integration tests (mocked LLM).

These tests exercise the *plumbing* of ``sprint3_pilot.run_pilot``: that
both the honest scenario sweep and the attacker sweep run end-to-end
without exceptions on the locked 5-scenario pilot set + the 24-cell
γ∪δ slice, and that the aggregation math matches the spec.

No network is contacted; both LLM callers are dependency-injected mocks.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence

import pytest

from mirrorlab.attacker.runner import ATTACK_SLICE, _aggregate
from mirrorlab.runners.sprint3_pilot import (
    PILOT_SCENARIOS,
    PilotReport,
    pack_grids,
    run_attacker_pilot,
    run_honest_pilot,
    run_pilot,
    score_against_scenario,
)
from mirrorlab.runners.openai_client import SUBMIT_TOOL
from mirrorlab.scenarios.loader import load as load_scenario


# ---- Mock-message scaffolding ------------------------------------------


class _MockToolCall:
    """Minimal duck-type of the OpenAI tool-call object the agent expects."""

    def __init__(self, name: str, arguments: str, tc_id: str = "tc_0"):
        self.id = tc_id
        self.type = "function"

        class _Fn:
            pass

        self.function = _Fn()
        self.function.name = name
        self.function.arguments = arguments


class _MockMessage:
    def __init__(self, *, content: str = "", tool_calls=None):
        self.content = content
        self.tool_calls = list(tool_calls or [])


def _submit_message(submission: List[Dict[str, Any]]) -> _MockMessage:
    args = json.dumps({"submission": submission})
    return _MockMessage(tool_calls=[_MockToolCall(SUBMIT_TOOL, args)])


def _measure_then_submit(submission: List[Dict[str, Any]]):
    """Returns a stateful LLMCallable that: turn 1 → call a measure tool;
    turn 2 → submit the supplied entry list."""
    state = {"turn": 0}

    def caller(messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]]):
        state["turn"] += 1
        if state["turn"] == 1:
            # measure.position is a real MVS tool — exercise one tool-call
            # roundtrip before submitting.
            return _MockMessage(
                tool_calls=[_MockToolCall("measure__position", "{}", tc_id="tc_m")]
            )
        return _submit_message(submission)

    return caller


def _direct_submit(submission: List[Dict[str, Any]]):
    """LLMCallable that submits on the first turn (zero tool calls)."""
    def caller(messages, tools):
        return _submit_message(submission)
    return caller


def _honest_baseline_submission(domain_id: str) -> List[Dict[str, Any]]:
    # Hooke-flavoured submission — entry is dim-compatible for hooke but
    # may dim-fail for other domains, which is acceptable for plumbing.
    return [
        {
            "law_id": "L_pilot_honest",
            "formula": "F = -k * x",
            "predictor": {
                "lang": "python",
                "code": "def f(x):\n    return -1.0 * x\n",
            },
            "inputs": [{"name": "x", "units": "m"}],
            "outputs": [{"name": "F", "units": "kg*m/s**2"}],
            "params": [{"name": "k", "units": "kg/s**2", "value": 1.0}],
            "claim_broken_symmetry": "none",
        }
    ]


def _attacker_textbook_submission(domain_id: str) -> List[Dict[str, Any]]:
    return [
        {
            "law_id": "textbook_lookup",
            "formula": f"canonical textbook ({domain_id})",
            "predictor": {
                "lang": "python",
                "code": "def f(*a, **k):\n    return 0.0\n",
            },
            "inputs": [{"name": "x", "units": "m"}],
            "outputs": [{"name": "F", "units": "kg*m/s**2"}],
            "params": [{"name": "k", "units": "kg/s**2", "value": 1.0}],
            "claim_broken_symmetry": "none",
        }
    ]


# ---- (1) pilot scenarios meet diversity criterion ----------------------

def test_pilot_scenarios_satisfy_spec_diversity():
    # 1 baseline + 2 γ + 2 δ.
    n_base = sum(1 for d, s, _ in PILOT_SCENARIOS if s == "baseline")
    n_gamma = sum(1 for d, s, _ in PILOT_SCENARIOS if s.startswith("gamma_"))
    n_delta = sum(1 for d, s, _ in PILOT_SCENARIOS if s.startswith("delta_"))
    assert n_base == 1, f"want 1 baseline, got {n_base}"
    assert n_gamma == 2, f"want 2 γ, got {n_gamma}"
    assert n_delta == 2, f"want 2 δ, got {n_delta}"
    domains = {d for d, _, _ in PILOT_SCENARIOS}
    assert len(domains) >= 3, f"need ≥3 distinct domains, got {sorted(domains)}"


# ---- (2) pack_grids handles all 12 domains ----------------------------

@pytest.mark.parametrize("domain,shift", [
    ("hooke", "baseline"),
    ("hooke", "gamma_1_1"),
    ("pendulum", "gamma_4_1"),
    ("decay", "gamma_12_1"),
    ("rlc", "delta_6_1"),
    ("kinetics", "delta_11_1"),
    ("coulomb", "delta_5_1"),
    ("thermal", "gamma_7_1"),
])
def test_pack_grids_produces_packable_tuples(domain, shift):
    scenario = load_scenario(domain, shift, seed=0)
    grids = pack_grids(scenario)
    assert grids, f"{domain}/{shift}: no grids packed"
    for key, pts in grids.items():
        assert pts, f"{domain}/{shift} sub-grid {key}: empty"
        ins, gt = pts[0]
        assert isinstance(ins, dict)
        assert isinstance(gt, float)


# ---- (3) honest pilot runs end-to-end through mock LLM ---------------

def test_run_honest_pilot_runs_all_5_scenarios_no_crash():
    submission = _honest_baseline_submission("hooke")
    from mirrorlab.runners.llm_agent import LLMAgent

    def factory() -> LLMAgent:
        return LLMAgent(
            model="mock",
            api_key="mock",
            max_tool_calls=6,
            max_wall_seconds=10,
            llm_call=_measure_then_submit(submission),
            fallback_to_stub=False,
        )

    results = run_honest_pilot(factory, PILOT_SCENARIOS, seed=0)
    assert len(results) == len(PILOT_SCENARIOS)
    for r in results:
        assert r.terminated_by == "submit", (
            f"{r.domain_id}/{r.shift_id} terminated by {r.terminated_by} "
            f"(expected submit; trace dump in stdout above)"
        )
        # Each scenario consumed exactly one tool call (measure.position),
        # confirming the dispatch wiring is live, not silently skipped.
        assert r.n_tool_calls == 1, (
            f"{r.domain_id}/{r.shift_id} tool calls = {r.n_tool_calls}; want 1"
        )
        assert r.submission_len == 1


# ---- (4) attacker pilot iterates 24 cells without crashing -----------

def test_run_attacker_pilot_covers_full_slice():
    from mirrorlab.attacker.lookup import LookupAttacker

    # Per-cell attacker submission keyed by domain so the mock matches.
    def factory() -> LookupAttacker:
        # Use a stateful per-attacker mock so we can claim a domain-shaped law.
        state = {"turn": 0}

        def caller(messages, tools):
            state["turn"] += 1
            sub = _attacker_textbook_submission("any")
            return _submit_message(sub)

        return LookupAttacker(
            model="mock",
            api_key="mock",
            max_tool_calls=2,
            max_wall_seconds=10,
            llm_call=caller,
        )

    report = run_attacker_pilot(factory, seeds=(0,))
    # 24 cells × 1 seed = 24 scenarios.
    assert report.n_scenarios == len(ATTACK_SLICE), (
        f"expected {len(ATTACK_SLICE)} cells, got {report.n_scenarios}"
    )
    # Aggregation math: s_bench_lookup must be the mean across the cell_scores.
    expected = sum(report.cell_scores.values()) / max(len(report.cell_scores), 1)
    assert abs(report.s_bench_lookup - expected) < 1e-9
    # The mock submits a hooke-shaped law; on most non-hooke cells the
    # dim filter or the wrong-formula numeric stage drives the score
    # toward zero. We only require that the aggregation runs and that
    # the pass flag matches the threshold comparison.
    assert report.passed == (report.s_bench_lookup < report.threshold)


# ---- (5) full pilot wrapper end-to-end --------------------------------

def test_run_pilot_full_wrapper_returns_structured_report():
    honest_caller = _measure_then_submit(_honest_baseline_submission("hooke"))
    attacker_caller = _direct_submit(_attacker_textbook_submission("any"))

    report = run_pilot(
        honest_llm_call=honest_caller,
        attacker_llm_call=attacker_caller,
        model="mock",
        api_key="mock",
        honest_max_tool_calls=4,
        honest_max_wall_seconds=10,
        attacker_max_tool_calls=2,
        attacker_max_wall_seconds=10,
        attacker_seeds=(0,),
    )
    assert isinstance(report, PilotReport)
    assert report.pilot_pipeline_ok, (
        "pilot pipeline reported not-ok: " + repr([
            (r.domain_id, r.shift_id, r.terminated_by) for r in report.honest
        ])
    )
    # JSON-serializable.
    payload = json.dumps(report.as_dict(), default=repr)
    assert "attacker" in payload
    assert "honest" in payload
    assert len(report.honest) == 5
    assert report.attacker is not None
    assert report.attacker.n_scenarios == len(ATTACK_SLICE)


# ---- (6) aggregation correctness (pure math) -------------------------

def test_aggregate_macro_mean_matches_spec_formula():
    """``S_bench^lookup`` = equal-weight macro-mean across cells, each
    cell averaged over its seeds (§7)."""
    from mirrorlab.attacker.lookup import AttackResult

    def _stub_result(d: str, s: str, seed: int) -> AttackResult:
        return AttackResult(
            domain_id=d, shift_id=s, seed=seed, submission=[],
            claimed_law=None, claimed_formula=None,
            tool_calls=0, llm_turns=0, elapsed_s=0.0,
            terminated_by="mock",
        )

    results = [
        _stub_result("a", "gamma_1_1", 0),
        _stub_result("a", "gamma_1_1", 1),
        _stub_result("b", "delta_1_1", 0),
    ]
    scores = [0.4, 0.6, 0.8]   # cell ("a",γ) mean = 0.5; cell ("b",δ) mean = 0.8
    cell_scores, s_bench = _aggregate(results, scores)
    assert cell_scores[("a", "gamma_1_1")] == pytest.approx(0.5)
    assert cell_scores[("b", "delta_1_1")] == pytest.approx(0.8)
    assert s_bench == pytest.approx((0.5 + 0.8) / 2)


# ---- (7) score_against_scenario hooke baseline = 1.0 ------------------

def test_score_against_scenario_hooke_baseline_perfect():
    scenario = load_scenario("hooke", "baseline", seed=0)
    sim = scenario.sim
    k = float(sim.params.k)
    # Submit the exact baseline law with the live k.
    submission = [
        {
            "law_id": "F=-kx",
            "formula": "F = -k * x",
            "predictor": {
                "lang": "python",
                "code": "def f(x, k):\n    return -k * x\n",
            },
            "inputs": [{"name": "x", "units": "m"}],
            "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
            "params": [{"name": "k", "units": "kg*s**-2", "value": k}],
            "claim_broken_symmetry": "none",
        }
    ]
    s = score_against_scenario(scenario, submission, gt_symmetry="none")
    # Bonus fires for matching symmetry claim; pilot relies on this being > 0.95.
    assert s > 0.95, f"hooke baseline ideal-law score too low: {s:.4f}"
