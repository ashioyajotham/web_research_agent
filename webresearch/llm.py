"""
LLM interface for interacting with Google Gemini models.
Handles all communication with the Gemini API.
"""

import google.generativeai as genai
from typing import List, Dict, Any, Optional
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

        # Set safety settings to be permissive for research tasks
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
        )

        logger.info(f"Initialized LLM interface with model: {model_name}")

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
                logger.warning(f"Attempt {attempt + 1}/{retry_count} failed: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    raise Exception(
                        f"Failed to generate response after {retry_count} attempts: {str(e)}"
                    )

    def generate_with_history(
        self, messages: List[Dict[str, str]], retry_count: int = 3
    ) -> str:
        """
        Generate a response with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            retry_count: Number of times to retry on failure

        Returns:
            The generated text response
        """
        # Convert messages to Gemini format
        chat = self.model.start_chat(history=[])

        # Build the conversation history
        for msg in messages[:-1]:  # All except the last message
            if msg["role"] == "user":
                chat.send_message(msg["content"])

        # Send the final message and get response
        last_message = messages[-1]["content"]

        for attempt in range(retry_count):
            try:
                response = chat.send_message(last_message)

                if not response.text:
                    if hasattr(response, "prompt_feedback"):
                        logger.warning(f"Response blocked: {response.prompt_feedback}")
                    raise ValueError("Empty response from model")

                return response.text

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{retry_count} failed: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2**attempt)
                else:
                    raise Exception(
                        f"Failed to generate response after {retry_count} attempts: {str(e)}"
                    )
