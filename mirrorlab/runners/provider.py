"""Provider dispatch for MirrorLab LLM clients.

Sprint 3.5 only had one provider (OpenAI-compat proxy at :4142). Sprint 4
adds Claude + Gemini via the Anthropic-format proxy at :4141. Higher-level
runners use :func:`make_client` instead of instantiating client classes
directly, so adding new providers stays local.
"""

from __future__ import annotations

from typing import Optional, Protocol, Sequence, Mapping, Any

from mirrorlab.runners.openai_client import (
    DEFAULT_BASE_URL as OPENAI_DEFAULT_BASE_URL,
    OpenAIClient,
)
from mirrorlab.runners.anthropic_client import (
    DEFAULT_BASE_URL as ANTHROPIC_DEFAULT_BASE_URL,
    DEFAULT_API_KEY as ANTHROPIC_DEFAULT_API_KEY,
    AnthropicClient,
)


PROVIDER_DEFAULT_BASE_URL = {
    "openai": OPENAI_DEFAULT_BASE_URL,
    "anthropic": ANTHROPIC_DEFAULT_BASE_URL,
    "gemini": ANTHROPIC_DEFAULT_BASE_URL,
}


class ClientProtocol(Protocol):
    """Minimum surface :class:`LLMAgent` requires from a client."""

    model: str
    base_url: str

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        model: Optional[str] = ...,
        tool_choice: str = ...,
    ) -> Any: ...


def detect_provider(model: str) -> str:
    """Auto-pick the provider from the model id prefix.

    Conventions (Sprint 4):
      * ``gpt-*``     → openai     (4142)
      * ``claude-*``  → anthropic  (4141)
      * ``gemini-*``  → anthropic  (4141; Gemini is mirrored under
        Anthropic format on this proxy per ``/v1/models``)
    """
    m = (model or "").lower()
    if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if m.startswith("claude-"):
        return "anthropic"
    if m.startswith("gemini-"):
        return "gemini"
    raise ValueError(
        f"cannot detect provider for model {model!r}; pass provider= explicitly "
        "(supported: openai, anthropic, gemini)"
    )


def make_client(
    provider: Optional[str] = None,
    *,
    model: str,
    base_url: Optional[str] = None,
    api_key: str = "",
    timeout: float = 60.0,
) -> ClientProtocol:
    """Construct the right client for ``model``.

    If ``provider`` is omitted it is inferred from ``model``. If
    ``base_url`` is omitted the provider default is used.
    """
    if provider is None:
        provider = detect_provider(model)
    provider = provider.lower()
    if provider not in PROVIDER_DEFAULT_BASE_URL:
        raise ValueError(
            f"unknown provider {provider!r}; supported: "
            f"{sorted(PROVIDER_DEFAULT_BASE_URL)}"
        )
    resolved_base = base_url or PROVIDER_DEFAULT_BASE_URL[provider]
    if provider == "openai":
        return OpenAIClient(
            model=model,
            base_url=resolved_base,
            api_key=api_key,
            timeout=timeout,
        )
    # anthropic + gemini share the 4141 proxy
    return AnthropicClient(
        model=model,
        base_url=resolved_base,
        api_key=api_key or ANTHROPIC_DEFAULT_API_KEY,
        timeout=timeout,
    )


__all__ = [
    "ClientProtocol",
    "PROVIDER_DEFAULT_BASE_URL",
    "detect_provider",
    "make_client",
]
