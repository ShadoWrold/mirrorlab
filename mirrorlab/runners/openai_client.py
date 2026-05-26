"""Thin OpenAI-compatible client wrapper for MirrorLab.

Points the official ``openai`` SDK at a local proxy (e.g.
``http://127.0.0.1:4142/v1``) and converts ``mirrorlab.tools.registry``
entries to OpenAI function-call tool schemas.

Design notes
------------
- The SDK is imported lazily so unit tests that only exercise the schema
  builder do not require ``openai`` to be installed.
- Canonical MirrorLab tool names use dots (``measure.position``). OpenAI
  function names must match ``^[a-zA-Z0-9_-]{1,64}$``, so we mangle dots
  to a double underscore (``measure__position``) and provide round-trip
  helpers ``mangle_name`` / ``unmangle_name``.
- The wrapper exposes a single ``chat`` method that returns the raw
  OpenAI ``ChatCompletion`` message object; higher-level loop logic lives
  in ``llm_agent.py``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from mirrorlab.tools.registry import REGISTRY, ToolSpec

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://127.0.0.1:4142/v1"
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_API_KEY_ENV = "MIRRORLAB_LLM_API_KEY"

# Synthetic terminal tool the agent calls to submit its final answer.
SUBMIT_TOOL = "submit_answer"


# ---- Name mangling -----------------------------------------------------

def mangle_name(canonical: str) -> str:
    return canonical.replace(".", "__")


def unmangle_name(mangled: str) -> str:
    return mangled.replace("__", ".")


# ---- Tool schema builder ----------------------------------------------

_CATEGORY_HINT = {
    "measure": "Probe the live simulation for an observable. Read-only.",
    "manipulate": "Mutate simulation state (initial conditions, parameters, "
                  "external fields). Use sparingly.",
    "analyze": "Pure numeric/symbolic analysis on data the agent supplies. "
               "Does not touch the simulation.",
    "knowledge": "Look up reference constants, formulas, or unit conversions.",
}


def _tool_schema(spec: ToolSpec) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": mangle_name(spec.name),
            "description": (
                f"[{spec.category}] {_CATEGORY_HINT.get(spec.category, '')} "
                f"Canonical tool id: {spec.name}."
            ).strip(),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            },
        },
    }


def _submit_tool_schema() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": SUBMIT_TOOL,
            "description": (
                "Submit the final candidate-law set and end the scenario. "
                "Argument ``submission`` is a JSON array of entries matching "
                "the §5 schema (law_id, formula, predictor.code, inputs, "
                "outputs, params); optional ``claim_broken_symmetry``."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "submission": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": True},
                        "description": "List of candidate-law entries (cap 5).",
                    },
                },
                "required": ["submission"],
                "additionalProperties": True,
            },
        },
    }


def build_tool_schemas(
    registry: Mapping[str, ToolSpec] = REGISTRY,
    *,
    include_submit: bool = True,
) -> List[Dict[str, Any]]:
    """OpenAI tool-list payload for the entire MVS plus the submit terminator."""
    schemas = [_tool_schema(spec) for spec in registry.values()]
    if include_submit:
        schemas.append(_submit_tool_schema())
    return schemas


# ---- Client wrapper ----------------------------------------------------

@dataclass
class OpenAIClient:
    """Lazy-import wrapper around the ``openai`` SDK.

    Attributes
    ----------
    model
        Default model id (overridable per-call).
    base_url
        Proxy endpoint base; passed to the SDK as-is.
    api_key
        Bearer token. Resolve from env via ``OpenAIClient.from_env``.
    timeout
        Per-request wall-clock cap (seconds).
    """

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    timeout: float = 60.0
    max_tokens: int = 4096

    @classmethod
    def from_env(
        cls,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        env_var: str = DEFAULT_API_KEY_ENV,
        timeout: float = 60.0,
    ) -> "OpenAIClient":
        api_key = os.environ.get(env_var, "").strip()
        if not api_key:
            raise RuntimeError(
                f"environment variable {env_var!r} is empty; "
                "set it before running the LLM agent."
            )
        return cls(model=model, base_url=base_url, api_key=api_key, timeout=timeout)

    def _sdk(self):  # pragma: no cover — exercised only on real runs
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai SDK not installed; pip install openai>=1.0 to run the "
                "LLM agent against the local proxy."
            ) from exc
        return OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        model: Optional[str] = None,
        tool_choice: str = "auto",
    ) -> Any:
        """Single chat-completion request.

        Returns the raw ``choices[0].message`` object. Callers handle
        ``.content`` and ``.tool_calls`` themselves.
        """
        client = self._sdk()
        model_id = model or self.model
        log.debug("openai chat: model=%s tools=%d msgs=%d",
                  model_id, len(tools), len(messages))
        # gpt-5.x family on this proxy rejects `tool_choice` and `max_tokens`
        # (litellm UnsupportedParamsError). Drop them for those models.
        params: Dict[str, Any] = {
            "model": model_id,
            "messages": list(messages),
            "tools": list(tools),
        }
        if not model_id.startswith("gpt-5"):
            params["tool_choice"] = tool_choice
            params["max_tokens"] = self.max_tokens
        resp = client.chat.completions.create(**params)
        return resp.choices[0].message


# ---- Public alias type for dependency-injected callers ----------------

LLMCallable = Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]], Any]


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_API_KEY_ENV",
    "SUBMIT_TOOL",
    "OpenAIClient",
    "LLMCallable",
    "build_tool_schemas",
    "mangle_name",
    "unmangle_name",
]
