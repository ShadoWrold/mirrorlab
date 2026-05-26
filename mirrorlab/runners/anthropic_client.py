"""Anthropic-format client wrapper for MirrorLab (proxy at :4141).

Mirrors the surface of :class:`mirrorlab.runners.openai_client.OpenAIClient`
so :class:`mirrorlab.runners.llm_agent.LLMAgent` can drop it in without
branching internally:

  * ``chat(messages, tools, *, model=None, tool_choice="auto") -> Message``
  * Returns an object exposing ``.content`` (str) and ``.tool_calls``
    (list of items with ``.id``, ``.type == "function"`` and
    ``.function.name`` / ``.function.arguments`` (JSON str)).

Notes
-----
- The local proxy at ``http://127.0.0.1:4141`` speaks the Anthropic
  Messages API (``POST /v1/messages``, header ``x-api-key``) and hosts
  Claude (4.5/4.6/4.7) and Gemini (2.5/3.1) — the latter mirrored under
  Anthropic format per the proxy's ``/v1/models`` listing.
- The wrapper hand-rolls HTTP via ``urllib.request`` so the ``anthropic``
  SDK is not required. Tests patch :meth:`AnthropicClient._post`.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib import request as _urlrequest
from urllib import error as _urlerror

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://127.0.0.1:4141"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_API_KEY = "dummy"
ANTHROPIC_VERSION = "2023-06-01"


# ---- OpenAI-shaped response objects -----------------------------------

@dataclass
class _Fn:
    name: str
    arguments: str


@dataclass
class _TC:
    id: str
    function: _Fn
    type: str = "function"


@dataclass
class _Msg:
    content: str = ""
    tool_calls: List[_TC] = field(default_factory=list)


# ---- Schema / message conversion --------------------------------------

def openai_tools_to_anthropic(tools: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Convert OpenAI ``[{"type":"function","function":{...}}]`` to Anthropic
    ``[{"name","description","input_schema"}]`` form."""
    out: List[Dict[str, Any]] = []
    for t in tools:
        fn = t.get("function") if isinstance(t, Mapping) else None
        if not isinstance(fn, Mapping):
            continue
        out.append({
            "name": fn.get("name"),
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {
                "type": "object", "properties": {}, "additionalProperties": True,
            },
        })
    return out


def openai_messages_to_anthropic(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[Optional[str], List[Dict[str, Any]]]:
    """Split a flat OpenAI message list into ``(system_text, anthropic_messages)``.

    - ``system`` messages collapse into a single ``system`` parameter.
    - ``assistant`` messages with ``tool_calls`` become content arrays of
      ``{"type":"text"}`` + ``{"type":"tool_use"}`` blocks.
    - ``tool`` messages (OpenAI tool-results) merge into a single
      ``user`` message containing ``{"type":"tool_result"}`` blocks.
    """
    system_parts: List[str] = []
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            text = str(m.get("content") or "")
            if text:
                system_parts.append(text)
        elif role == "user":
            out.append({"role": "user", "content": str(m.get("content") or "")})
        elif role == "assistant":
            blocks: List[Dict[str, Any]] = []
            text = str(m.get("content") or "")
            if text:
                blocks.append({"type": "text", "text": text})
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") if isinstance(tc, Mapping) else {}
                raw = (fn or {}).get("arguments") or "{}"
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else dict(raw)
                except (TypeError, ValueError, json.JSONDecodeError):
                    parsed = {}
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or "",
                    "name": (fn or {}).get("name") or "",
                    "input": parsed if isinstance(parsed, Mapping) else {},
                })
            if not blocks:
                blocks = [{"type": "text", "text": ""}]
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            tr = {
                "type": "tool_result",
                "tool_use_id": str(m.get("tool_call_id") or ""),
                "content": str(m.get("content") or ""),
            }
            if out and out[-1]["role"] == "user" and isinstance(out[-1].get("content"), list):
                out[-1]["content"].append(tr)
            else:
                out.append({"role": "user", "content": [tr]})
        # silently drop unknown roles
    system_text = "\n\n".join(system_parts) if system_parts else None
    return system_text, out


def anthropic_response_to_openai_message(payload: Mapping[str, Any]) -> _Msg:
    """Convert Anthropic ``/v1/messages`` JSON to an OpenAI-shaped message."""
    text_chunks: List[str] = []
    tool_calls: List[_TC] = []
    for block in payload.get("content") or []:
        if not isinstance(block, Mapping):
            continue
        btype = block.get("type")
        if btype == "text":
            t = block.get("text")
            if t:
                text_chunks.append(str(t))
        elif btype == "tool_use":
            tool_calls.append(_TC(
                id=str(block.get("id") or ""),
                function=_Fn(
                    name=str(block.get("name") or ""),
                    arguments=json.dumps(block.get("input") or {}),
                ),
            ))
        # thinking / redacted_thinking blocks: ignore for now
    return _Msg(content="".join(text_chunks), tool_calls=tool_calls)


# ---- Client wrapper ----------------------------------------------------

@dataclass
class AnthropicClient:
    """Hand-rolled Anthropic Messages-API client (proxy at :4141)."""

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    timeout: float = 60.0
    max_tokens: int = 4096
    anthropic_version: str = ANTHROPIC_VERSION

    @classmethod
    def from_env(
        cls,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        env_var: str = "MIRRORLAB_LLM_API_KEY",
        timeout: float = 60.0,
    ) -> "AnthropicClient":
        api_key = (os.environ.get(env_var) or DEFAULT_API_KEY).strip() or DEFAULT_API_KEY
        return cls(model=model, base_url=base_url, api_key=api_key, timeout=timeout)

    def _endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            return base + "/messages"
        return base + "/v1/messages"

    def _post(self, body: Mapping[str, Any]) -> Dict[str, Any]:  # pragma: no cover — patched in tests
        data = json.dumps(body).encode("utf-8")
        req = _urlrequest.Request(
            self._endpoint(),
            data=data,
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.anthropic_version,
            },
        )
        try:
            with _urlrequest.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except _urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"anthropic proxy HTTP {exc.code}: {detail}") from exc
        return json.loads(raw.decode("utf-8"))

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        model: Optional[str] = None,
        tool_choice: str = "auto",
    ) -> _Msg:
        """Single Messages-API request. Returns OpenAI-shaped message."""
        system_text, anth_messages = openai_messages_to_anthropic(messages)
        anth_tools = openai_tools_to_anthropic(tools)
        body: Dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": self.max_tokens,
            "messages": anth_messages,
        }
        if system_text:
            body["system"] = system_text
        if anth_tools:
            body["tools"] = anth_tools
            # Anthropic tool_choice shape differs from OpenAI's plain string.
            if tool_choice == "auto":
                body["tool_choice"] = {"type": "auto"}
            elif tool_choice == "any":
                body["tool_choice"] = {"type": "any"}
            elif tool_choice == "none":
                # Easiest portable equivalent: just drop tools.
                body.pop("tools", None)
                body.pop("tool_choice", None)
        log.debug("anthropic chat: model=%s tools=%d msgs=%d",
                  body["model"], len(anth_tools), len(anth_messages))
        raw = self._post(body)
        return anthropic_response_to_openai_message(raw)


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_API_KEY",
    "ANTHROPIC_VERSION",
    "AnthropicClient",
    "openai_tools_to_anthropic",
    "openai_messages_to_anthropic",
    "anthropic_response_to_openai_message",
]
