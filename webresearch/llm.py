"""
LLM interface for interacting with Google Gemini models.
Handles all communication with the Gemini API.
"""

import re
import google.generativeai as genai
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface for interacting with Google Gemini models."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.1,
    ):
        """
        Initialize the LLM interface.

        Args:
            api_key: Google Gemini API key
            model_name: Name of the Gemini model to use
            temperature: Temperature for response generation (0.0-1.0)
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature

        # Configure the model with safety settings
        self.generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        # BLOCK_ONLY_HIGH allows legitimate research content (geopolitical, news about
        # violence) while still blocking obvious misuse vectors.  BLOCK_NONE on
        # SEXUALLY_EXPLICIT and HARASSMENT has no research justification.
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
        ]

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
        )

        logger.info(f"Initialized LLM interface with model: {model_name}")

    @staticmethod
    def _parse_retry_delay(error: Exception) -> Optional[float]:
        """Extract retry_delay seconds from a Gemini 429 error message, if present."""
        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", str(error))
        if match:
            return float(match.group(1))
        match = re.search(r"retry in\s+([\d.]+)s", str(error), re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _is_daily_quota(error: Exception) -> bool:
        """Return True if the 429 error is a daily (not per-minute) quota exhaustion."""
        return "PerDay" in str(error)

    def _friendly_quota_message(self, error: Exception) -> str:
        """Return a human-readable quota error message."""
        err = str(error)
        limit_match = re.search(r"quota_value:\s*(\d+)", err)
        limit = limit_match.group(1) if limit_match else "unknown"
        if "PerDay" in err:
            return (
                f"Daily request quota exhausted for {self.model_name} "
                f"(free tier limit: {limit} requests/day). "
                "Try again tomorrow, or enable billing at https://ai.dev/rate-limit to increase your quota."
            )
        delay_match = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", err)
        wait = delay_match.group(1) if delay_match else "~60"
        return (
            f"Per-minute rate limit hit for {self.model_name} (free tier: {limit} RPM). "
            f"Waiting {wait}s as requested by API before retry..."
        )

    def generate(self, prompt: str, retry_count: int = 3) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The input prompt
            retry_count: Number of times to retry on failure

        Returns:
            The generated text response

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)

                # Check if response was blocked
                if not response.text:
                    if hasattr(response, "prompt_feedback"):
                        logger.warning(f"Response blocked: {response.prompt_feedback}")
                    raise ValueError("Empty response from model")

                return response.text

            except Exception as e:
                if self._is_daily_quota(e):
                    # Daily quota cannot be resolved by waiting — fail immediately
                    raise Exception(self._friendly_quota_message(e))

                logger.warning(f"Attempt {attempt + 1}/{retry_count} failed: {str(e)}")
                if attempt < retry_count - 1:
                    delay = self._parse_retry_delay(e)
                    if delay is None:
                        delay = 2 ** (attempt + 1)
                    logger.info(self._friendly_quota_message(e))
                    time.sleep(delay)
                else:
                    raise Exception(
                        f"Failed to generate response after {retry_count} attempts: {str(e)}"
                    )

