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
import threading
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

# Transient network/infrastructure errors that warrant trying the next provider
# rather than surfacing as a hard failure.  Timeouts commonly occur when a
# free-tier provider (Groq, OpenRouter) is slow under a large accumulated prompt.
_TRANSIENT_SIGNALS = (
    "timed out",
    "timeout",
    "connection",
    "read timeout",
    "connect timeout",
    "service unavailable",
    "502",
    "503",
    "504",
)


def _is_quota_error(exc: Exception) -> bool:
    low = str(exc).lower()
    return any(signal in low for signal in _QUOTA_SIGNALS)


def _is_transient_error(exc: Exception) -> bool:
    low = str(exc).lower()
    return any(signal in low for signal in _TRANSIENT_SIGNALS)


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
        self._lock = threading.Lock()   # guards _current_index across threads
        # One semaphore per provider index — limits concurrent calls to 1 per
        # provider so parallel sub-agents don't simultaneously hammer the same
        # rate-limited free-tier endpoint.
        self._provider_semaphores = [threading.Semaphore(1) for _ in interfaces]

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
        Thread-safe: concurrent callers serialise per provider via semaphores,
        and _current_index mutations are protected by a lock.
        Raises the last exception if all providers are exhausted.
        """
        with self._lock:
            start_index = self._current_index

        for i in range(start_index, len(self.interfaces)):
            llm = self.interfaces[i]
            name = getattr(llm, "provider_name", None) or getattr(llm, "model_name", "unknown")

            if i > start_index:
                prev_name = (
                    getattr(self.interfaces[i - 1], "provider_name", None)
                    or getattr(self.interfaces[i - 1], "model_name", "unknown")
                )
                with self._lock:
                    if self._current_index < i:   # only advance once across threads
                        logger.warning(f"Falling back from {prev_name} to {name}")
                        if self.switch_callback:
                            self.switch_callback(prev_name, name)
                        self._current_index = i

            # Serialise concurrent calls to this provider — free-tier APIs
            # (Groq, OpenRouter) have per-minute limits that parallel threads
            # blow through instantly when sharing one endpoint.
            with self._provider_semaphores[i]:
                try:
                    return llm.generate(prompt)
                except Exception as e:
                    is_fallback = _is_quota_error(e) or _is_transient_error(e)
                    if is_fallback and i < len(self.interfaces) - 1:
                        reason = "quota error" if _is_quota_error(e) else "transient error"
                        logger.warning(f"[{name}] {reason}, trying next provider: {str(e)[:100]}")
                        continue
                    raise

        raise RuntimeError("ModelFallbackChain exhausted all providers.")

    def reset(self) -> None:
        """Reset to the primary provider (call between independent queries if desired)."""
        self._current_index = 0
