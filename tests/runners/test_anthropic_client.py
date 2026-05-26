"""Mock-based tests for AnthropicClient.

Never hits the real proxy; :meth:`AnthropicClient._post` is monkeypatched
to return a canned Anthropic Messages-API response.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from mirrorlab.runners import anthropic_client as ac
from mirrorlab.runners.anthropic_client import (
    AnthropicClient,
    anthropic_response_to_openai_message,
    openai_messages_to_anthropic,
    openai_tools_to_anthropic,
)
from mirrorlab.runners.openai_client import (
    SUBMIT_TOOL,
    build_tool_schemas,
    mangle_name,
)


# ---- Schema conversion -------------------------------------------------

def test_tool_schema_conversion_shape():
    openai_tools = build_tool_schemas()
    anth = openai_tools_to_anthropic(openai_tools)
    assert len(anth) == len(openai_tools)
    for entry in anth:
        assert "name" in entry
        assert "description" in entry
        assert "input_schema" in entry
        assert entry["input_schema"]["type"] == "object"
        # Anthropic forbids the OpenAI-style "function" envelope
        assert "function" not in entry
        assert "parameters" not in entry
    names = {e["name"] for e in anth}
    assert SUBMIT_TOOL in names
    assert "measure__position" in names


def test_message_conversion_extracts_system():
    msgs = [
        {"role": "system", "content": "you are a physicist"},
        {"role": "user", "content": "find the law"},
    ]
    system, out = openai_messages_to_anthropic(msgs)
    assert system == "you are a physicist"
    assert out == [{"role": "user", "content": "find the law"}]


def test_message_conversion_assistant_tool_calls_to_blocks():
    msgs = [
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": "let me measure",
            "tool_calls": [{
                "id": "tc_1",
                "type": "function",
                "function": {"name": "measure__observable",
                             "arguments": json.dumps({"name": "x", "t": 0.1})},
            }],
        },
        {"role": "tool", "tool_call_id": "tc_1", "content": json.dumps({"value": 1.23})},
        {"role": "assistant", "content": "ok done"},
    ]
    system, out = openai_messages_to_anthropic(msgs)
    assert system is None
    # user, assistant(text+tool_use), user(tool_result), assistant(text)
    assert [m["role"] for m in out] == ["user", "assistant", "user", "assistant"]
    asst = out[1]["content"]
    assert any(b["type"] == "text" and b["text"] == "let me measure" for b in asst)
    use_block = next(b for b in asst if b["type"] == "tool_use")
    assert use_block["id"] == "tc_1"
    assert use_block["name"] == "measure__observable"
    assert use_block["input"] == {"name": "x", "t": 0.1}
    # tool result lives inside a user message
    tr_user = out[2]
    assert isinstance(tr_user["content"], list)
    assert tr_user["content"][0]["type"] == "tool_result"
    assert tr_user["content"][0]["tool_use_id"] == "tc_1"


def test_response_conversion_with_tool_use():
    payload = {
        "id": "msg_x",
        "model": "claude-sonnet-4-6",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "calling measure"},
            {"type": "tool_use", "id": "tu_1", "name": "measure__observable",
             "input": {"name": "x", "t": 0.0}},
        ],
        "stop_reason": "tool_use",
    }
    msg = anthropic_response_to_openai_message(payload)
    assert msg.content == "calling measure"
    assert len(msg.tool_calls) == 1
    tc = msg.tool_calls[0]
    assert tc.id == "tu_1"
    assert tc.type == "function"
    assert tc.function.name == "measure__observable"
    assert json.loads(tc.function.arguments) == {"name": "x", "t": 0.0}


def test_response_conversion_text_only():
    payload = {"content": [{"type": "text", "text": "hello"}]}
    msg = anthropic_response_to_openai_message(payload)
    assert msg.content == "hello"
    assert msg.tool_calls == []


def test_response_conversion_ignores_thinking_blocks():
    payload = {"content": [
        {"type": "thinking", "thinking": "internal monologue"},
        {"type": "text", "text": "the answer"},
    ]}
    msg = anthropic_response_to_openai_message(payload)
    assert msg.content == "the answer"


# ---- Client.chat round-trip with patched _post -------------------------

def test_chat_sends_anthropic_shaped_body_and_parses_tool_use():
    captured: Dict[str, Any] = {}

    def fake_post(self, body):
        captured["body"] = body
        return {
            "content": [
                {"type": "text", "text": "calling tool"},
                {"type": "tool_use", "id": "tu_42",
                 "name": "measure__observable", "input": {"name": "x", "t": 0.0}},
            ],
        }

    client = AnthropicClient(model="claude-sonnet-4-6", api_key="dummy")
    with patch.object(AnthropicClient, "_post", fake_post):
        msg = client.chat(
            [{"role": "system", "content": "be terse"},
             {"role": "user", "content": "go"}],
            build_tool_schemas(),
        )
    body = captured["body"]
    assert body["model"] == "claude-sonnet-4-6"
    assert body["max_tokens"] >= 1
    assert body["system"] == "be terse"
    # System message stripped from messages list
    assert body["messages"] == [{"role": "user", "content": "go"}]
    # Tools converted to Anthropic shape
    assert body["tools"] and "input_schema" in body["tools"][0]
    assert body["tool_choice"] == {"type": "auto"}
    # Response: OpenAI-shaped
    assert msg.content == "calling tool"
    assert msg.tool_calls[0].function.name == "measure__observable"


def test_chat_drops_tools_when_tool_choice_none():
    captured: Dict[str, Any] = {}

    def fake_post(self, body):
        captured["body"] = body
        return {"content": [{"type": "text", "text": "ok"}]}

    client = AnthropicClient(model="claude-sonnet-4-6", api_key="dummy")
    with patch.object(AnthropicClient, "_post", fake_post):
        client.chat([{"role": "user", "content": "go"}],
                    build_tool_schemas(), tool_choice="none")
    body = captured["body"]
    assert "tools" not in body
    assert "tool_choice" not in body


def test_endpoint_handles_v1_suffix():
    c = AnthropicClient(base_url="http://127.0.0.1:4141")
    assert c._endpoint() == "http://127.0.0.1:4141/v1/messages"
    c = AnthropicClient(base_url="http://127.0.0.1:4141/v1")
    assert c._endpoint() == "http://127.0.0.1:4141/v1/messages"
    c = AnthropicClient(base_url="http://127.0.0.1:4141/")
    assert c._endpoint() == "http://127.0.0.1:4141/v1/messages"


def test_from_env_defaults_to_dummy_when_no_env(monkeypatch):
    monkeypatch.delenv("MIRRORLAB_LLM_API_KEY", raising=False)
    c = AnthropicClient.from_env(model="claude-opus-4-7")
    assert c.api_key == "dummy"
    assert c.model == "claude-opus-4-7"


# ---- Integration with LLMAgent -----------------------------------------

def test_anthropic_client_drops_into_llm_agent():
    """End-to-end: AnthropicClient round-trips with the agent's tool loop."""
    from mirrorlab.runners.llm_agent import LLMAgent
    from mirrorlab.scenarios.loader import load as load_scenario

    valid_submission = [{
        "law_id": "L1", "formula": "F=-k*x",
        "predictor": {"lang": "python", "code": "def f(x,k): return -k*x"},
        "inputs": [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
        "params": [{"name": "k", "units": "kg*s**-2", "value": 1.5}],
    }]

    state = {"step": 0}

    def fake_post(self, body):
        state["step"] += 1
        if state["step"] == 1:
            return {"content": [{"type": "tool_use", "id": "tu_1",
                                 "name": SUBMIT_TOOL,
                                 "input": {"submission": valid_submission}}]}
        raise AssertionError("agent should have terminated after step 1")

    scenario = load_scenario("hooke", "baseline", seed=0)
    client = AnthropicClient(model="claude-sonnet-4-6", api_key="dummy")
    with patch.object(AnthropicClient, "_post", fake_post):
        agent = LLMAgent(
            llm_call=lambda m, t: client.chat(m, t),
            fallback_to_stub=False,
        )
        sub, trace = agent.run_with_trace(scenario)
    assert trace.terminated_by == "submit"
    assert sub == valid_submission
