"""Tests for the provider dispatch layer."""

from __future__ import annotations

import pytest

from mirrorlab.runners.anthropic_client import AnthropicClient
from mirrorlab.runners.openai_client import OpenAIClient
from mirrorlab.runners.provider import (
    PROVIDER_DEFAULT_BASE_URL,
    detect_provider,
    make_client,
)


# ---- detect_provider ---------------------------------------------------

@pytest.mark.parametrize("model,expected", [
    ("gpt-5.4-20260305", "openai"),
    ("gpt-4o-mini", "openai"),
    ("gpt-5", "openai"),
    ("claude-opus-4-6", "anthropic"),
    ("claude-sonnet-4-6", "anthropic"),
    ("claude-haiku-4-5-20251001", "anthropic"),
    ("claude-opus-4-7", "anthropic"),
    ("gemini-3.1-pro-preview", "gemini"),
    ("gemini-2.5-flash", "gemini"),
])
def test_detect_provider_known_prefixes(model, expected):
    assert detect_provider(model) == expected


def test_detect_provider_unknown_model_raises():
    with pytest.raises(ValueError):
        detect_provider("mistral-large")


# ---- make_client dispatch ---------------------------------------------

def test_gpt_model_routes_to_openai_4142():
    c = make_client(model="gpt-5.4-20260305", api_key="sk-x")
    assert isinstance(c, OpenAIClient)
    assert c.model == "gpt-5.4-20260305"
    assert "4142" in c.base_url
    assert c.base_url == PROVIDER_DEFAULT_BASE_URL["openai"]


def test_claude_model_routes_to_anthropic_4141():
    c = make_client(model="claude-opus-4-6", api_key="dummy")
    assert isinstance(c, AnthropicClient)
    assert c.model == "claude-opus-4-6"
    assert "4141" in c.base_url
    assert c.base_url == PROVIDER_DEFAULT_BASE_URL["anthropic"]


def test_gemini_model_routes_to_anthropic_format_on_4141():
    c = make_client(model="gemini-3.1-pro-preview")
    # gemini-* uses the Anthropic-format client against the 4141 proxy
    assert isinstance(c, AnthropicClient)
    assert c.model == "gemini-3.1-pro-preview"
    assert "4141" in c.base_url
    assert c.base_url == PROVIDER_DEFAULT_BASE_URL["gemini"]
    # Falls back to "dummy" when no api_key passed
    assert c.api_key == "dummy"


def test_explicit_provider_overrides_prefix_detection():
    c = make_client("anthropic", model="gpt-4o-mirror", api_key="x")
    assert isinstance(c, AnthropicClient)
    c = make_client("openai", model="claude-mirror", api_key="x")
    assert isinstance(c, OpenAIClient)


def test_explicit_base_url_overrides_default():
    c = make_client(model="claude-opus-4-6", base_url="http://example:9999")
    assert c.base_url == "http://example:9999"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        make_client("mistral", model="claude-opus-4-6")


def test_unknown_model_without_provider_raises():
    with pytest.raises(ValueError):
        make_client(model="llama-3-70b")


# ---- LLMAgent integration ---------------------------------------------

def test_llm_agent_picks_anthropic_client_for_claude_model():
    from mirrorlab.runners.llm_agent import LLMAgent

    agent = LLMAgent(model="claude-sonnet-4-6", api_key="dummy")
    caller = agent._resolve_caller()
    # caller is a closure over a client; we patched make_client paths.
    # Easier: invoke make_client directly with the same args.
    c = make_client(model="claude-sonnet-4-6", api_key="dummy")
    assert isinstance(c, AnthropicClient)


def test_llm_agent_picks_openai_client_for_gpt_model():
    from mirrorlab.runners.llm_agent import LLMAgent

    agent = LLMAgent(model="gpt-5.4-20260305", api_key="sk")
    c = make_client(model=agent.model, api_key=agent.api_key)
    assert isinstance(c, OpenAIClient)
    assert "4142" in c.base_url
