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

import inspect
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
    "analyze": "Pure numeric/symbolic analysis on data you supply. "
               "Does not touch the simulation.",
    "knowledge": "Look up reference constants, formulas, glossaries, or "
                 "unit conversions.",
}

# Map a (stringified) Python annotation to a JSON-Schema property. Annotations
# arrive as strings because the tool modules use ``from __future__ import
# annotations``, so we pattern-match on the source text rather than the type
# object. Unknown shapes fall back to an untyped property (no ``type`` key),
# which is valid JSON-Schema and lets the model pass anything.
def _annotation_to_property(ann: Any) -> Dict[str, Any]:
    text = ann if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    text = text.strip()
    # Unwrap Optional[X] / typing.Optional → schema for X (nullability is
    # conveyed by the field simply being omittable, not by a union type).
    if text.startswith("Optional[") and text.endswith("]"):
        return _annotation_to_property(text[len("Optional["):-1])
    if text in ("str",):
        return {"type": "string"}
    if text in ("float",):
        return {"type": "number"}
    if text in ("int",):
        return {"type": "integer"}
    if text in ("bool",):
        return {"type": "boolean"}
    # Sequence[float] / List[float] / List[...] → array of numbers (default
    # number items; bare lists stay loosely typed).
    if text.startswith(("Sequence[", "List[")):
        inner = text[text.index("[") + 1:-1].strip()
        items = _annotation_to_property(inner) if inner else {}
        return {"type": "array", "items": items or {"type": "number"}}
    # Dict[...] → object with free-form values.
    if text.startswith("Dict["):
        return {"type": "object", "additionalProperties": True}
    # Any / unknown → untyped (accept anything).
    return {}


def _parameters_schema(spec: ToolSpec) -> Dict[str, Any]:
    """Build a JSON-Schema ``parameters`` object from the tool's signature.

    The harness injects ``sim`` for ``needs_sim`` tools, so it is excluded
    from the model-facing schema. The variadic ``**kwargs`` catch-all (only
    ``knowledge.unit_convert``) is dropped from ``properties`` but keeps the
    object open via ``additionalProperties``. A trailing ``_`` on a name
    (Python keyword workaround, e.g. ``from_``) is preserved as-is — the
    dispatcher forwards kwargs verbatim.
    """
    sig = inspect.signature(spec.fn)
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for name, p in sig.parameters.items():
        if name == "sim":
            continue  # injected by the harness, never supplied by the model
        if p.kind in (inspect.Parameter.VAR_POSITIONAL,
                      inspect.Parameter.VAR_KEYWORD):
            continue  # *args / **kwargs: keep object open below, not a field
        properties[name] = _annotation_to_property(p.annotation)
        if p.default is inspect.Parameter.empty:
            required.append(name)
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": True,
    }
    if required:
        schema["required"] = required
    return schema


def _tool_description(spec: ToolSpec) -> str:
    """Human/LLM-facing tool description: first paragraph of the tool's own
    docstring (the authoritative per-tool signal the model can always act on),
    prefixed with the category hint for context."""
    doc = inspect.getdoc(spec.fn) or ""
    first_para = doc.split("\n\n", 1)[0].strip().replace("\n", " ")
    hint = _CATEGORY_HINT.get(spec.category, "")
    body = f"{first_para} " if first_para else ""
    return f"[{spec.category}] {body}{hint} Canonical tool id: {spec.name}.".strip()


def _tool_schema(spec: ToolSpec) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": mangle_name(spec.name),
            "description": _tool_description(spec),
            "parameters": _parameters_schema(spec),
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
