"""LookupAttacker — locked-prompt adversarial agent (spec §8).

The attacker is given the *same* tool pool, scenario prompt, and
submission protocol as the honest LLMAgent, but its system prompt is
**locked** to instruct "identify the closest matching textbook law from
your training data and submit it; do not propose novel modifications."

This module deliberately re-implements a small tool loop instead of
sub-classing :class:`mirrorlab.runners.llm_agent.LLMAgent`, so that the
attacker prompt cannot be silently mutated by future edits to the honest
agent's system prompt. CAL-8 budget defaults: ``K = 20`` tool calls,
60 s wall-clock.

The "claimed textbook law" is extracted post-hoc from the first
submission entry's ``law_id`` and ``formula`` fields, so a malformed
submission still scores 0 without crashing.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from mirrorlab.runners.llm_agent import (
    Submission,
    _assistant_message_payload,
    _dispatch_tool,
    _extract_tool_calls,
    _msg_content,
    _safe_jsonify,
    _tool_call_args_raw,
    _tool_call_id,
    _tool_call_name,
    _try_parse_submission,
    _truncate,
)
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
from mirrorlab.tools.sandbox import SandboxContext

log = logging.getLogger(__name__)


# ---- LOCKED attacker prompt --------------------------------------------
#
# This string is part of the benchmark contract — see
# ``docs/sprint3-attacker-spec.md``. Do NOT modify it without bumping the
# attacker version and re-running the closed-loop gate (CAL-9). The
# prompt deliberately:
#   1. names the strategy ("identify textbook law from training data");
#   2. forbids novel modifications;
#   3. preserves the §5 submission schema verbatim so a fair comparison
#      against the honest agent's submission rules is possible.
#
# Token-equivalent length is logged at every release; keep edits minimal.

ATTACKER_SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert physicist with deep textbook knowledge. You will "
    "observe a physical system through tool calls. Your STRATEGY IS "
    "LOCKED: identify the closest matching known law from your training "
    "data — any well-known textbook law in classical mechanics, "
    "electromagnetism, thermodynamics, optics, fluids, kinetics, or "
    "nuclear physics — and submit that canonical textbook form. Prefer "
    "canonical textbook forms. Do not propose novel modifications, "
    "higher-order corrections, or speculative parameter additions "
    "beyond the canonical law.\n"
    "\n"
    "Budget: at most {max_tool_calls} tool calls and {max_wall_seconds} s "
    "wall-clock. Use the first few measurements to confirm which textbook "
    "law applies, then call `submit_answer` exactly once. Plan to submit "
    "by tool call #{submit_by} (budget minus 3) so you keep a safety "
    "margin before the runner cuts you off.\n"
    "\n"
    "Submission schema (each entry, list length ≤ 5):\n"
    "  - law_id: a textbook law label (e.g. 'hooke', 'coulomb')\n"
    "  - formula: the canonical textbook formula string\n"
    "  - predictor.lang: 'python'\n"
    "  - predictor.code: a `def f(...):` returning a float\n"
    "  - inputs: list of {{name, units}} (SI)\n"
    "  - outputs: list of {{name, units}} (SI)\n"
    "  - params: list of {{name, units, value}}\n"
    "  - claim_broken_symmetry (optional): 'none' if you believe the "
    "    canonical law applies unmodified.\n"
)


def build_attacker_system_prompt(
    max_tool_calls: int = 20, max_wall_seconds: int = 60,
) -> str:
    """Render the locked attacker prompt against the active runtime budget.

    The runtime ``K`` enforced by :class:`LookupAttacker` MUST match the
    ``K`` advertised in-prompt to the model.
    """
    submit_by = max(1, int(max_tool_calls) - 3)
    return ATTACKER_SYSTEM_PROMPT_TEMPLATE.format(
        max_tool_calls=int(max_tool_calls),
        max_wall_seconds=int(max_wall_seconds),
        submit_by=submit_by,
    )


# Backwards-compatible default-budget rendering (CAL-8 K=20 / 60 s).
ATTACKER_SYSTEM_PROMPT = build_attacker_system_prompt()


# ---- Attack result -----------------------------------------------------

@dataclass
class AttackResult:
    """Per-scenario attacker output."""

    domain_id: str
    shift_id: str
    seed: int
    submission: Submission
    claimed_law: Optional[str]
    claimed_formula: Optional[str]
    tool_calls: int
    llm_turns: int
    elapsed_s: float
    terminated_by: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "shift_id": self.shift_id,
            "seed": self.seed,
            "submission": self.submission,
            "claimed_law": self.claimed_law,
            "claimed_formula": self.claimed_formula,
            "tool_calls": self.tool_calls,
            "llm_turns": self.llm_turns,
            "elapsed_s": round(self.elapsed_s, 4),
            "terminated_by": self.terminated_by,
        }


def _extract_claim(submission: Submission) -> tuple[Optional[str], Optional[str]]:
    """Pull (law_id, formula) from the first submission entry."""
    if not submission:
        return None, None
    first = submission[0]
    law = first.get("law_id") if isinstance(first, Mapping) else None
    formula = first.get("formula") if isinstance(first, Mapping) else None
    return (
        str(law) if law is not None else None,
        str(formula) if formula is not None else None,
    )


# ---- LookupAttacker ----------------------------------------------------

@dataclass
class LookupAttacker:
    """Locked-prompt LLM attacker.

    Parameters
    ----------
    model, base_url, api_key
        Forwarded to :class:`OpenAIClient` when ``llm_call`` is not given.
    max_tool_calls
        CAL-8 budget — default 20.
    max_wall_seconds
        Soft wall-clock cap; matches honest agent default 60 s.
    llm_call
        Optional dependency-injected callable for tests. Same signature
        as :class:`LLMAgent`: ``(messages, tools) -> assistant_message``.
    """

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    max_tool_calls: int = 20  # CAL-8
    max_wall_seconds: int = 60
    llm_call: Optional[LLMCallable] = None

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

    def run(self, scenario: ScenarioInstance) -> AttackResult:
        caller = self._resolve_caller()
        tools = build_tool_schemas()
        ctx = SandboxContext(
            sim=scenario.sim,
            scenario_id=f"attacker/{scenario.domain_id}/{scenario.shift_id}/{scenario.seed}",
        )
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": build_attacker_system_prompt(
                self.max_tool_calls, self.max_wall_seconds,
            )},
            {"role": "user", "content": scenario.prompt},
        ]
        deadline = time.monotonic() + float(self.max_wall_seconds)
        start = time.monotonic()

        tool_calls = 0
        llm_turns = 0
        parse_errors = 0
        submission: Submission = []
        terminated_by = "unknown"

        while True:
            if time.monotonic() >= deadline:
                terminated_by = "wall"
                break
            if tool_calls >= self.max_tool_calls:
                terminated_by = "budget"
                break

            try:
                msg = caller(messages, tools)
            except Exception as exc:  # noqa: BLE001 — network failures
                log.error("attacker LLM call failed: %s", exc)
                terminated_by = "llm_error"
                break
            llm_turns += 1

            calls = _extract_tool_calls(msg)

            if not calls:
                # Bare-text terminal: try to parse a JSON array out.
                text = _msg_content(msg)
                parsed = _try_parse_submission(text)
                if parsed is not None:
                    submission = _truncate(parsed)
                    terminated_by = "submit"
                    break
                if parse_errors == 0:
                    parse_errors += 1
                    messages.append(_assistant_message_payload(msg))
                    messages.append({
                        "role": "user",
                        "content": (
                            "Could not parse a submission. Call "
                            "`submit_answer` with a JSON array."
                        ),
                    })
                    continue
                terminated_by = "parse_error"
                break

            messages.append(_assistant_message_payload(msg))

            should_break = False
            for tc in calls:
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
                        submission = _truncate(list(sub))
                        terminated_by = "submit"
                        should_break = True
                        break
                    messages.append({
                        "role": "tool",
                        "tool_call_id": _tool_call_id(tc),
                        "content": json.dumps(
                            {"error": "submission must be a JSON array"}
                        ),
                    })
                    parse_errors += 1
                    if parse_errors >= 2:
                        terminated_by = "parse_error"
                        should_break = True
                        break
                    continue

                canonical = unmangle_name(name)
                tool_calls += 1
                result = _dispatch_tool(ctx, canonical, kwargs)
                messages.append({
                    "role": "tool",
                    "tool_call_id": _tool_call_id(tc),
                    "content": _safe_jsonify(result),
                })

                if tool_calls >= self.max_tool_calls:
                    terminated_by = "budget"
                    should_break = True
                    break

            if should_break:
                break

        elapsed = time.monotonic() - start
        claimed_law, claimed_formula = _extract_claim(submission)
        return AttackResult(
            domain_id=scenario.domain_id,
            shift_id=scenario.shift_id,
            seed=scenario.seed,
            submission=submission,
            claimed_law=claimed_law,
            claimed_formula=claimed_formula,
            tool_calls=tool_calls,
            llm_turns=llm_turns,
            elapsed_s=elapsed,
            terminated_by=terminated_by,
        )


__all__ = [
    "ATTACKER_SYSTEM_PROMPT",
    "ATTACKER_SYSTEM_PROMPT_TEMPLATE",
    "build_attacker_system_prompt",
    "AttackResult",
    "LookupAttacker",
]
