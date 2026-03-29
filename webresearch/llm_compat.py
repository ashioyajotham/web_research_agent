"""
OpenAI-compatible LLM interface.

Covers any provider that exposes the OpenAI chat-completions API shape:
  - Groq          (https://api.groq.com/openai/v1)
  - OpenRouter    (https://openrouter.ai/api/v1)
  - DeepSeek      (https://api.deepseek.com/v1)
  - Ollama local  (http://localhost:11434/v1)

Requires the `openai` package:  pip install openai
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI, RateLimitError, APIStatusError
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


def openai_available() -> bool:
    return _OPENAI_AVAILABLE


# Well-known provider presets: (base_url, display_name, recommended_model)
PROVIDERS = {
    "groq": (
        "https://api.groq.com/openai/v1",
        "Groq",
        "llama-3.3-70b-versatile",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OpenRouter",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
    "deepseek": (
        "https://api.deepseek.com/v1",
        "DeepSeek",
        "deepseek-chat",
    ),
    "ollama": (
        "http://localhost:11434/v1",
        "Ollama (local)",
        "llama3.3",
    ),
}


class OpenAICompatibleLLMInterface:
    """
    Thin wrapper around any OpenAI-compatible chat-completions endpoint.
    Exposes the same .generate() interface as LLMInterface so it can be
    used interchangeably inside ModelFallbackChain.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str,
        provider_name: str = "",
        temperature: float = 0.1,
    ):
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "The 'openai' package is required for non-Gemini providers. "
                "Install it with:  pip install openai"
            )
        self.model_name = model_name
        self.provider_name = provider_name or base_url
        self.temperature = temperature
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialised {self.provider_name} interface ({model_name})")

    @staticmethod
    def _parse_retry_after(err_str: str) -> Optional[float]:
        """Extract retry-after seconds from a 429 error string if present."""
        import re
        # Groq embeds: "Please try again in 6.25s"
        m = re.search(r"try again in\s+([\d.]+)s", err_str, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.0
        # Generic "retry after N seconds"
        m = re.search(r"retry.{0,10}after\s+([\d.]+)\s*s", err_str, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.0
        return None

    def generate(self, prompt: str, retry_count: int = 3) -> str:
        for attempt in range(retry_count):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=4096,  # 2048 truncated complex ReAct reasoning on fallback providers
                )
                return response.choices[0].message.content or ""

            except Exception as e:
                err = str(e)
                is_quota = "quota" in err.lower() or "rate" in err.lower() or "429" in err

                if not is_quota:
                    raise

                logger.warning(f"[{self.provider_name}] attempt {attempt + 1}/{retry_count} failed: {err[:120]}")

                if attempt < retry_count - 1:
                    # Honour the server's retry-after hint; fall back to
                    # exponential backoff but floor at 10s for per-minute limits.
                    hint = self._parse_retry_after(err)
                    delay = hint if hint else max(10.0, 2 ** (attempt + 2))
                    logger.warning(f"[{self.provider_name}] rate-limited — waiting {delay:.0f}s (attempt {attempt+1}/{retry_count})")
                    time.sleep(delay)
                else:
                    raise Exception(
                        f"[{self.provider_name}] rate-limited after {retry_count} attempts."
                    )
