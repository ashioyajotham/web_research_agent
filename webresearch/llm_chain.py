"""
Model fallback chain.

Wraps an ordered list of LLM interfaces (Gemini, Groq, OpenRouter, Ollama, …)
and tries each in turn when the active provider hits a quota or rate-limit error.

Usage::

    from webresearch.llm_chain import ModelFallbackChain
    from webresearch.llm import LLMInterface
    from webresearch.llm_compat import OpenAICompatibleLLMInterface

    chain = ModelFallbackChain(
        interfaces=[gemini_llm, groq_llm, openrouter_llm],
        switch_callback=lambda from_name, to_name: print(f"Switching {from_name} -> {to_name}"),
    )
    answer = chain.generate(prompt)

The chain exposes the same .generate() signature as the individual interfaces,
so it can be passed directly to ReActAgent or ParallelResearchAgent.
"""

import logging
from typing import Callable, List, Optional, Union

from .llm import LLMInterface
from .llm_compat import OpenAICompatibleLLMInterface

logger = logging.getLogger(__name__)

AnyLLM = Union[LLMInterface, OpenAICompatibleLLMInterface]

# Substrings that indicate the error is a quota/rate-limit rather than a
# genuine model or network failure.  On these errors we try the next provider.
_QUOTA_SIGNALS = (
    "quota",
    "rate limit",
    "rate-limit",
    "ratelimit",
    "429",
    "too many requests",
    "daily request quota",
    "per-minute rate limit",
)


def _is_quota_error(exc: Exception) -> bool:
    low = str(exc).lower()
    return any(signal in low for signal in _QUOTA_SIGNALS)


class ModelFallbackChain:
    """
    Ordered chain of LLM interfaces with automatic fallback on quota errors.

    Args:
        interfaces: Ordered list of LLM interfaces to try.  The first entry
                    is the primary provider; subsequent entries are fallbacks.
        switch_callback: Optional callable(from_name: str, to_name: str) invoked
                         whenever the chain switches to a new provider.  Use this
                         to surface a notification in the CLI.
    """

    def __init__(
        self,
        interfaces: List[AnyLLM],
        switch_callback: Optional[Callable[[str, str], None]] = None,
    ):
        if not interfaces:
            raise ValueError("ModelFallbackChain requires at least one interface.")
        self.interfaces = interfaces
        self.switch_callback = switch_callback
        self._current_index = 0

    @property
    def current(self) -> AnyLLM:
        return self.interfaces[self._current_index]

    @property
    def current_name(self) -> str:
        llm = self.current
        return getattr(llm, "provider_name", None) or getattr(llm, "model_name", str(llm))

    def generate(self, prompt: str) -> str:
        """
        Generate a response, falling back through the chain on quota errors.
        Raises the last exception if all providers are exhausted.
        """
        start_index = self._current_index

        for i in range(start_index, len(self.interfaces)):
            llm = self.interfaces[i]
            name = getattr(llm, "provider_name", None) or getattr(llm, "model_name", "unknown")

            if i > start_index:
                # We advanced — notify
                prev_name = getattr(self.interfaces[i - 1], "provider_name", None) or \
                            getattr(self.interfaces[i - 1], "model_name", "unknown")
                logger.warning(f"Falling back from {prev_name} to {name}")
                if self.switch_callback:
                    self.switch_callback(prev_name, name)
                self._current_index = i

            try:
                return llm.generate(prompt)
            except Exception as e:
                if _is_quota_error(e) and i < len(self.interfaces) - 1:
                    logger.warning(f"[{name}] quota error, trying next provider: {str(e)[:100]}")
                    continue
                # Either not a quota error, or no more providers — re-raise
                raise

        # Should not reach here
        raise RuntimeError("ModelFallbackChain exhausted all providers.")

    def reset(self) -> None:
        """Reset to the primary provider (call between independent queries if desired)."""
        self._current_index = 0
