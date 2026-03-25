"""
Configuration management for the web research agent.
Loads API keys and settings from environment variables.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

from .credentials import get_credential


class Config:
    """Configuration class for managing API keys and settings."""

    def __init__(self):
        # Credentials — keyring first, then env var fallback
        self.gemini_api_key: Optional[str] = get_credential("GEMINI_API_KEY")
        self.serper_api_key: Optional[str] = get_credential("SERPER_API_KEY")

        # Agent settings (env var or package default — never persisted to keyring)
        self.max_iterations: int = int(os.getenv("MAX_ITERATIONS", "15"))
        self.max_tool_output_length: int = int(
            os.getenv("MAX_TOOL_OUTPUT_LENGTH", "3000")
        )
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.1"))
        self.model_name: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")

        # Timeout settings
        self.web_request_timeout: int = int(os.getenv("WEB_REQUEST_TIMEOUT", "30"))
        self.code_execution_timeout: int = int(
            os.getenv("CODE_EXECUTION_TIMEOUT", "60")
        )

        # Fallback provider keys (all optional — chain degrades gracefully)
        self.groq_api_key: Optional[str] = get_credential("GROQ_API_KEY")
        self.openrouter_api_key: Optional[str] = get_credential("OPENROUTER_API_KEY")
        self.ollama_base_url: Optional[str] = get_credential("OLLAMA_BASE_URL")

    def validate(self) -> None:
        """Validate that required API keys are present."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        if not self.serper_api_key:
            raise ValueError(
                "SERPER_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )


# Global config instance
config = Config()
