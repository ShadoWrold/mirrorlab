"""LLM agent loop — CAL-7 budgeted, tool-calling, JSON-submission.

Wires a real LLM (via :mod:`mirrorlab.runners.openai_client`) into the
MirrorLab scenario harness. Replaces — but does not delete —
``scenarios.agent_stub`` as a real-discovery baseline.

Contract
--------

``LLMAgent.run(scenario)`` returns a ``Submission`` (a list of §5 entries)
suitable for ``mirrorlab.eval.scoring.score_submission``. The loop:

  1. Send system prompt + scenario prompt + tool manifest.
  2. Receive an assistant message with either
        - ``tool_calls`` → dispatch each through
          ``mirrorlab.tools.registry.call`` (logged via ``SandboxContext``)
          and feed results back, or
        - a ``submit_answer`` tool call → terminate, return the submission.
  3. Budgets per CAL-7: ``max_tool_calls`` (default 30) and
     ``max_wall_seconds`` (default 60). Either exhaustion terminates the
     loop and we submit the best partial answer we can extract from
     ``scratchpad['draft_submission']`` (the agent is asked to keep this
     fresh), or fall back to ``agent_stub`` for the scenario's domain.
  4. JSON parse errors retry once; second failure ⇒ empty submission.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from mirrorlab.runners.openai_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMCallable,
    SUBMIT_TOOL,
    OpenAIClient,
    build_tool_schemas,
    unmangle_name,
)
from mirrorlab.scenarios.loader import ScenarioInstance
from mirrorlab.tools.registry import call as tool_call
from mirrorlab.tools.sandbox import SandboxContext

log = logging.getLogger(__name__)

Submission = List[Dict[str, Any]]

SYSTEM_PROMPT = (
    "You are a physics-discovery agent. Given a scenario description and a "
    "toolbox of measurement / manipulation / analysis / knowledge tools, "
    "you must propose one or more candidate laws describing the system "
    "and submit them via the `submit_answer` tool.\n"
    "\n"
    "Submission schema (each entry):\n"
    "  - law_id: short label (e.g. 'L1')\n"
    "  - formula: human-readable formula string\n"
    "  - predictor.lang: 'python'\n"
    "  - predictor.code: a `def f(...):` returning a float\n"
    "  - inputs: list of {name, units} (SI)\n"
    "  - outputs: list of {name, units} (SI)\n"
    "  - params: list of {name, units, value}\n"
    "  - claim_broken_symmetry (optional): e.g. 'PAR', 'TR', 'none'\n"
    "\n"
    "Budgets: at most 30 tool calls and 60s wall-clock. Be efficient. "
    "When you have a candidate law, call `submit_answer` exactly once. "
    "Submission set is capped at 5 entries (declaration order)."
)


# ---- Helpers -----------------------------------------------------------

def _extract_tool_calls(msg: Any) -> List[Any]:
    """Pull ``.tool_calls`` from either a dict or an SDK Message object."""
    if msg is None:
        return []
    if isinstance(msg, Mapping):
        return list(msg.get("tool_calls") or [])
    return list(getattr(msg, "tool_calls", None) or [])


def _msg_content(msg: Any) -> str:
    if isinstance(msg, Mapping):
        return str(msg.get("content") or "")
    return str(getattr(msg, "content", "") or "")


def _tool_call_name(tc: Any) -> str:
    fn = tc["function"] if isinstance(tc, Mapping) else getattr(tc, "function", tc)
    return fn["name"] if isinstance(fn, Mapping) else getattr(fn, "name", "")


def _tool_call_args_raw(tc: Any) -> str:
    fn = tc["function"] if isinstance(tc, Mapping) else getattr(tc, "function", tc)
    return fn["arguments"] if isinstance(fn, Mapping) else getattr(fn, "arguments", "")


def _tool_call_id(tc: Any) -> str:
    if isinstance(tc, Mapping):
        return str(tc.get("id") or "")
    return str(getattr(tc, "id", "") or "")


def _assistant_message_payload(msg: Any) -> Dict[str, Any]:
    """Normalize a model message to the dict shape OpenAI expects on echo-back."""
    content = _msg_content(msg)
    tool_calls = _extract_tool_calls(msg)
    payload: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        payload["tool_calls"] = [
            {
                "id": _tool_call_id(tc),
                "type": "function",
                "function": {
                    "name": _tool_call_name(tc),
                    "arguments": _tool_call_args_raw(tc),
                },
            }
            for tc in tool_calls
        ]
    return payload


def _safe_jsonify(value: Any) -> str:
    try:
        return json.dumps(value, default=repr)
    except (TypeError, ValueError):
        return json.dumps(repr(value))


def _empty_submission() -> Submission:
    return []


def _stub_fallback(scenario: ScenarioInstance) -> Submission:
    """Best-effort fallback when the LLM never submits."""
    try:
        from mirrorlab.scenarios.agent_stub import run as stub_run
        return [stub_run(scenario)]
    except Exception as exc:  # noqa: BLE001 — fallback must never raise
        log.warning("stub fallback failed for %s: %s", scenario.domain_id, exc)
        return _empty_submission()


# ---- Agent -------------------------------------------------------------

@dataclass
class AgentTrace:
    """Per-run diagnostic record (post-hoc only, never fed to the LLM)."""

    tool_calls: int = 0
    llm_turns: int = 0
    elapsed_s: float = 0.0
    terminated_by: str = "unknown"  # submit / budget / wall / parse_error
    parse_errors: int = 0
    raw_submission_text: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMAgent:
    """Real-LLM agent that runs one scenario.

    Parameters
    ----------
    model, base_url, api_key
        Forwarded to :class:`OpenAIClient` when ``llm_call`` is not given.
    max_tool_calls, max_wall_seconds
        CAL-7 budgets (defaults 30 calls / 60s wall clock).
    llm_call
        Optional dependency-injected callable for tests. Signature:
        ``(messages, tools) -> assistant_message``. If ``None`` we
        construct an :class:`OpenAIClient` from the credentials.
    """

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    max_tool_calls: int = 30
    max_wall_seconds: int = 60
    llm_call: Optional[LLMCallable] = None
    fallback_to_stub: bool = True

    def _resolve_caller(self) -> LLMCallable:
        if self.llm_call is not None:
            return self.llm_call
        client = OpenAIClient(
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=float(self.max_wall_seconds),
        )
        return lambda messages, tools: client.chat(messages, tools)

    def run(self, scenario: ScenarioInstance) -> Submission:
        submission, _ = self.run_with_trace(scenario)
        return submission

    def run_with_trace(self, scenario: ScenarioInstance) -> tuple[Submission, AgentTrace]:
        caller = self._resolve_caller()
        tools = build_tool_schemas()
        ctx = SandboxContext(
            sim=scenario.sim,
            scenario_id=f"{scenario.domain_id}/{scenario.shift_id}/{scenario.seed}",
        )
        trace = AgentTrace()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario.prompt},
        ]
        deadline = time.monotonic() + float(self.max_wall_seconds)
        parse_retries = 0

        while True:
            # Wall-clock budget check.
            if time.monotonic() >= deadline:
                trace.terminated_by = "wall"
                trace.elapsed_s = float(self.max_wall_seconds)
                return self._finalize(scenario, trace, partial_text=None), trace
            # Tool-call budget check (counted at dispatch time below as well).
            if trace.tool_calls >= self.max_tool_calls:
                trace.terminated_by = "budget"
                trace.elapsed_s = self._elapsed(deadline)
                return self._finalize(scenario, trace, partial_text=None), trace

            try:
                msg = caller(messages, tools)
            except Exception as exc:  # noqa: BLE001 — network/proxy failures
                log.error("LLM call failed (turn %d): %s", trace.llm_turns, exc)
                trace.terminated_by = "llm_error"
                trace.elapsed_s = self._elapsed(deadline)
                return self._finalize(scenario, trace, partial_text=None), trace
            trace.llm_turns += 1
            trace.messages.append(_assistant_message_payload(msg))

            tool_calls = _extract_tool_calls(msg)

            # No tool call at all → terminal message; try to parse a
            # bare-JSON submission out of the content as a courtesy.
            if not tool_calls:
                text = _msg_content(msg)
                parsed = _try_parse_submission(text)
                if parsed is not None:
                    trace.terminated_by = "submit"
                    trace.raw_submission_text = text
                    trace.elapsed_s = self._elapsed(deadline)
                    return _truncate(parsed), trace
                if parse_retries == 0:
                    parse_retries += 1
                    trace.parse_errors += 1
                    messages.append(_assistant_message_payload(msg))
                    messages.append({
                        "role": "user",
                        "content": (
                            "I could not parse a submission from your last "
                            "message. Please call the `submit_answer` tool "
                            "with the JSON array argument."
                        ),
                    })
                    continue
                trace.parse_errors += 1
                trace.terminated_by = "parse_error"
                trace.elapsed_s = self._elapsed(deadline)
                return self._finalize(scenario, trace, partial_text=text), trace

            # Echo assistant message into history before tool results.
            messages.append(_assistant_message_payload(msg))

            terminated = False
            for tc in tool_calls:
                name = _tool_call_name(tc)
                raw_args = _tool_call_args_raw(tc) or "{}"
                try:
                    kwargs = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                    if not isinstance(kwargs, Mapping):
                        kwargs = {}
                except (TypeError, ValueError, json.JSONDecodeError):
                    kwargs = {}

                if name == SUBMIT_TOOL:
                    sub = kwargs.get("submission") if isinstance(kwargs, Mapping) else None
                    if isinstance(sub, list):
                        trace.terminated_by = "submit"
                        trace.raw_submission_text = raw_args if isinstance(raw_args, str) else _safe_jsonify(sub)
                        trace.elapsed_s = self._elapsed(deadline)
                        return _truncate(list(sub)), trace
                    # Malformed submit → retry once via tool-result message.
                    messages.append({
                        "role": "tool",
                        "tool_call_id": _tool_call_id(tc),
                        "content": json.dumps({
                            "error": "submission must be a JSON array of entries",
                        }),
                    })
                    trace.parse_errors += 1
                    if trace.parse_errors >= 2:
                        terminated = True
                        trace.terminated_by = "parse_error"
                        break
                    continue

                # Regular MVS tool.
                canonical = unmangle_name(name)
                trace.tool_calls += 1
                result = _dispatch_tool(ctx, canonical, kwargs)
                messages.append({
                    "role": "tool",
                    "tool_call_id": _tool_call_id(tc),
                    "content": _safe_jsonify(result),
                })

                if trace.tool_calls >= self.max_tool_calls:
                    terminated = True
                    trace.terminated_by = "budget"
                    break

            if terminated:
                trace.elapsed_s = self._elapsed(deadline)
                return self._finalize(scenario, trace, partial_text=None), trace

    def _elapsed(self, deadline: float) -> float:
        return float(self.max_wall_seconds) - max(0.0, deadline - time.monotonic())

    def _finalize(
        self,
        scenario: ScenarioInstance,
        trace: AgentTrace,
        *,
        partial_text: Optional[str],
    ) -> Submission:
        """Best-guess submission after budget exhaustion or unparseable end."""
        if partial_text:
            parsed = _try_parse_submission(partial_text)
            if parsed is not None:
                return _truncate(parsed)
        if self.fallback_to_stub:
            return _stub_fallback(scenario)
        return _empty_submission()


# ---- Dispatch helpers --------------------------------------------------

def _dispatch_tool(ctx: SandboxContext, canonical: str, kwargs: Mapping[str, Any]) -> Any:
    try:
        result = tool_call(ctx, canonical, **dict(kwargs))
    except Exception as exc:  # noqa: BLE001 — tool errors are LLM-visible
        return {"error": f"{type(exc).__name__}: {exc}", "tool": canonical}
    # Make sure result is JSON-serialisable before we hand it back.
    try:
        json.dumps(result, default=repr)
        return result
    except (TypeError, ValueError):
        return repr(result)


def _try_parse_submission(text: str) -> Optional[Submission]:
    """Best-effort JSON-array extraction from arbitrary assistant text."""
    if not text:
        return None
    text = text.strip()
    # Strip ```json fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip("\n").lstrip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        # Try to locate the first JSON array in the text.
        start = text.find("[")
        end = text.rfind("]")
        if 0 <= start < end:
            try:
                obj = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
        else:
            return None
    if isinstance(obj, list):
        return [e for e in obj if isinstance(e, Mapping)] or None
    if isinstance(obj, Mapping) and "submission" in obj and isinstance(obj["submission"], list):
        return [e for e in obj["submission"] if isinstance(e, Mapping)] or None
    return None


def _truncate(submission: Submission) -> Submission:
    """Cap at 5 entries per §5.2."""
    return [dict(e) for e in submission[:5]]


__all__ = [
    "AgentTrace",
    "LLMAgent",
    "Submission",
    "SYSTEM_PROMPT",
]
