"""Mock-based unit tests for the LLM agent runner.

These tests NEVER hit the real LLM endpoint; the agent's ``llm_call``
dependency is replaced with a scripted callable that emits a fixed
sequence of assistant messages.

Coverage:

  * Tool schema builder shape (32 MVS tools + 1 submit tool, mangled names).
  * Tool dispatch: assistant emits a ``measure__observable`` call → runner
    invokes ``tools.registry.call`` → result fed back as a tool message.
  * Submission parse: a valid ``submit_answer`` call → produces the right
    Submission list (truncated at 5).
  * Budget exhaustion: 30 tool calls without submission → fallback path
    fires (rule-based stub or empty if disabled).
  * Wall-clock budget: synthetic time mock terminates the loop.
  * Bare-text JSON submission fallback (no tool call → parse JSON array).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Sequence
from unittest.mock import patch

import pytest

from mirrorlab.runners import llm_agent as agent_mod
from mirrorlab.runners.llm_agent import LLMAgent
from mirrorlab.runners.openai_client import (
    SUBMIT_TOOL,
    build_tool_schemas,
    mangle_name,
    unmangle_name,
)
from mirrorlab.scenarios.loader import load as load_scenario


# ---- Lightweight fake OpenAI message objects ---------------------------

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
    return FakeToolCall(id=call_id, function=FakeFn(name=name, arguments=json.dumps(args)))


def _scripted(responses: Sequence[FakeMsg]) -> Callable:
    """Build an ``llm_call`` that returns ``responses`` in order."""
    it = iter(responses)

    def _call(messages, tools):
        try:
            return next(it)
        except StopIteration:  # pragma: no cover — test should not exhaust
            raise AssertionError("scripted LLM exhausted")

    return _call


# ---- Tool schema -------------------------------------------------------

def test_tool_schemas_shape():
    schemas = build_tool_schemas()
    # 32 MVS tools + 1 synthetic submit tool.
    assert len(schemas) == 33
    names = {s["function"]["name"] for s in schemas}
    assert SUBMIT_TOOL in names
    # No dots in OpenAI tool names; dotted canonical → double-underscore.
    assert "measure__position" in names
    assert "measure.position" not in names
    # All function entries are typed and have a parameters object.
    for s in schemas:
        assert s["type"] == "function"
        assert s["function"]["parameters"]["type"] == "object"


def test_name_mangling_roundtrip():
    for canonical in ("measure.position", "manipulate.set_initial",
                      "analyze.dimensional_analysis", "knowledge.lookup_constant"):
        assert unmangle_name(mangle_name(canonical)) == canonical


# ---- Submission via submit_answer --------------------------------------

VALID_SUBMISSION = [
    {
        "law_id": "L1",
        "formula": "F = -k*x",
        "predictor": {"lang": "python", "code": "def f(x, k):\n    return -k*x\n"},
        "inputs": [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
        "params": [{"name": "k", "units": "kg*s**-2", "value": 1.5}],
    },
]


def test_submit_answer_round_trip():
    scenario = load_scenario("hooke", "baseline", seed=0)
    responses = [
        FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": VALID_SUBMISSION})]),
    ]
    agent = LLMAgent(llm_call=_scripted(responses), fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert trace.terminated_by == "submit"
    assert sub == VALID_SUBMISSION
    assert trace.tool_calls == 0
    assert trace.llm_turns == 1


def test_submission_truncated_at_five():
    scenario = load_scenario("hooke", "baseline", seed=0)
    big = [dict(VALID_SUBMISSION[0], law_id=f"L{i}") for i in range(7)]
    responses = [
        FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": big})]),
    ]
    agent = LLMAgent(llm_call=_scripted(responses), fallback_to_stub=False)
    sub, _ = agent.run_with_trace(scenario)
    assert len(sub) == 5


# ---- Tool dispatch -----------------------------------------------------

def test_measure_tool_dispatch_round_trip():
    """Assistant calls measure.observable → registry executes → submit."""
    scenario = load_scenario("hooke", "baseline", seed=0)

    captured: Dict[str, Any] = {}

    def llm_call(messages, tools):
        # Detect whether we've already seen a tool-result message; if so, submit.
        seen_tool_result = any(m.get("role") == "tool" for m in messages)
        if not seen_tool_result:
            return FakeMsg(tool_calls=[
                _tc("c1", mangle_name("measure.observable"),
                    {"name": "x", "t": 0.1}),
            ])
        # Capture the tool message for assertion.
        for m in messages:
            if m.get("role") == "tool":
                captured["tool_content"] = m["content"]
                break
        return FakeMsg(tool_calls=[_tc("c2", SUBMIT_TOOL, {"submission": VALID_SUBMISSION})])

    agent = LLMAgent(llm_call=llm_call, fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert sub == VALID_SUBMISSION
    assert trace.tool_calls == 1
    assert trace.terminated_by == "submit"
    # Tool-result JSON should be present and non-empty.
    assert "tool_content" in captured
    payload = json.loads(captured["tool_content"])
    # measure.observable returns a numeric or dict; either way it must be
    # JSON-serialisable and not an error.
    assert not (isinstance(payload, Mapping) and "error" in payload)


def test_unknown_tool_returns_error_to_llm():
    """A bogus tool call should not crash; the LLM gets an error payload."""
    scenario = load_scenario("hooke", "baseline", seed=0)

    def llm_call(messages, tools):
        seen_tool_result = any(m.get("role") == "tool" for m in messages)
        if not seen_tool_result:
            return FakeMsg(tool_calls=[_tc("c1", "not__a__tool", {})])
        # Check the error reached us.
        for m in messages:
            if m.get("role") == "tool":
                payload = json.loads(m["content"])
                assert "error" in payload
                break
        return FakeMsg(tool_calls=[_tc("c2", SUBMIT_TOOL, {"submission": VALID_SUBMISSION})])

    agent = LLMAgent(llm_call=llm_call, fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert sub == VALID_SUBMISSION
    assert trace.tool_calls == 1


# ---- Budget exhaustion -------------------------------------------------

def test_tool_call_budget_triggers_fallback():
    scenario = load_scenario("hooke", "baseline", seed=0)
    # Always emit a single measure tool call, never submit.
    looper = lambda messages, tools: FakeMsg(tool_calls=[
        _tc(f"c{len(messages)}", mangle_name("measure.observable"),
            {"name": "x", "t": 0.1}),
    ])
    agent = LLMAgent(
        llm_call=looper,
        max_tool_calls=5,
        max_wall_seconds=60,
        fallback_to_stub=True,
    )
    sub, trace = agent.run_with_trace(scenario)
    assert trace.tool_calls == 5
    assert trace.terminated_by == "budget"
    # Fallback to stub → exactly one entry from agent_stub.
    assert len(sub) == 1
    assert sub[0]["law_id"] == "L1"


def test_tool_call_budget_no_fallback_returns_empty():
    scenario = load_scenario("hooke", "baseline", seed=0)
    looper = lambda messages, tools: FakeMsg(tool_calls=[
        _tc(f"c{len(messages)}", mangle_name("measure.observable"),
            {"name": "x", "t": 0.1}),
    ])
    agent = LLMAgent(
        llm_call=looper,
        max_tool_calls=3,
        max_wall_seconds=60,
        fallback_to_stub=False,
    )
    sub, trace = agent.run_with_trace(scenario)
    assert trace.terminated_by == "budget"
    assert sub == []


def test_default_budgets_match_cal7():
    """CAL-7 says 30 calls + 60s. Defaults must not drift silently."""
    agent = LLMAgent(llm_call=lambda m, t: FakeMsg())
    assert agent.max_tool_calls == 30
    assert agent.max_wall_seconds == 60


# ---- Wall-clock -------------------------------------------------------

def test_wall_clock_budget_terminates(monkeypatch):
    scenario = load_scenario("hooke", "baseline", seed=0)
    t = {"now": 1000.0}

    def fake_monotonic():
        return t["now"]

    monkeypatch.setattr(agent_mod.time, "monotonic", fake_monotonic)

    def llm_call(messages, tools):
        # Each turn burns 30s of synthetic wall time.
        t["now"] += 30.0
        return FakeMsg(tool_calls=[
            _tc("cx", mangle_name("measure.observable"), {"name": "x", "t": 0.0}),
        ])

    agent = LLMAgent(
        llm_call=llm_call,
        max_tool_calls=1000,
        max_wall_seconds=60,
        fallback_to_stub=False,
    )
    sub, trace = agent.run_with_trace(scenario)
    assert trace.terminated_by == "wall"
    assert sub == []


# ---- Bare-JSON submission fallback -------------------------------------

def test_bare_json_submission_in_content():
    scenario = load_scenario("hooke", "baseline", seed=0)
    text = "Here is my answer:\n```json\n" + json.dumps(VALID_SUBMISSION) + "\n```"
    responses = [FakeMsg(content=text)]
    agent = LLMAgent(llm_call=_scripted(responses), fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert trace.terminated_by == "submit"
    assert len(sub) == 1
    assert sub[0]["law_id"] == "L1"


def test_unparseable_content_retries_then_fails(monkeypatch):
    scenario = load_scenario("hooke", "baseline", seed=0)
    responses = [
        FakeMsg(content="I think the answer is roughly something."),
        FakeMsg(content="Still cannot produce JSON."),
    ]
    agent = LLMAgent(llm_call=_scripted(responses), fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert trace.parse_errors >= 2
    assert trace.terminated_by == "parse_error"
    assert sub == []


def test_malformed_submit_tool_args_retries():
    scenario = load_scenario("hooke", "baseline", seed=0)
    responses = [
        FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": "not-a-list"})]),
        FakeMsg(tool_calls=[_tc("c2", SUBMIT_TOOL, {"submission": VALID_SUBMISSION})]),
    ]
    agent = LLMAgent(llm_call=_scripted(responses), fallback_to_stub=False)
    sub, trace = agent.run_with_trace(scenario)
    assert sub == VALID_SUBMISSION
    assert trace.parse_errors == 1


# ---- No real network --------------------------------------------------

def test_agent_never_calls_openai_sdk_in_tests():
    """Sanity: the openai SDK is never imported on this test path."""
    import sys
    # If a previous test pulled in openai, we can't assert non-import; but
    # we can assert that LLMAgent runs without touching ``openai.OpenAI``.
    scenario = load_scenario("hooke", "baseline", seed=0)
    responses = [FakeMsg(tool_calls=[_tc("c1", SUBMIT_TOOL, {"submission": VALID_SUBMISSION})])]
    with patch("mirrorlab.runners.openai_client.OpenAIClient._sdk",
               side_effect=AssertionError("must not call SDK in tests")):
        agent = LLMAgent(llm_call=_scripted(responses))
        agent.run(scenario)
