"""
Base tool class for the agent's tool system.
This provides a simple, extensible interface for adding new tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools follow a simple interface:
    - name: unique identifier for the tool
    - description: what the tool does (used by the LLM to decide when to use it)
    - execute: the actual tool logic
    """

    def __init__(self):
        """Initialize the tool."""
        self._validate()

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a description of what the tool does.
        This is used by the LLM to decide when to use the tool.
        Should include information about parameters and what the tool returns.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            str: The result of the tool execution as a string

        Raises:
            Exception: If the tool execution fails
        """
        pass

    def _validate(self) -> None:
        """Validate that the tool is properly configured."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")

    def __str__(self) -> str:
        """Return string representation of the tool."""
        return f"Tool({self.name})"

    def __repr__(self) -> str:
        """Return detailed string representation of the tool."""
        return f"Tool(name={self.name}, description={self.description[:50]}...)"

    def get_info(self) -> Dict[str, str]:
        """
        Return tool information as a dictionary.
        Useful for generating tool documentation for the LLM.
        """
        return {
            "name": self.name,
            "description": self.description,
        }
