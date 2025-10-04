"""
Tool management module.
Provides a registry and manager for all available tools.
"""

from typing import Dict, List, Optional
from .base import Tool
from .search import SearchTool
from .scrape import ScrapeTool
from .code_executor import CodeExecutorTool
from .file_ops import FileOpsTool

import logging

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages registration and access to tools."""

    def __init__(self):
        """Initialize the tool manager with an empty registry."""
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool with the manager.

        Args:
            tool: The tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self.tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered")

        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.

        Args:
            name: The name of the tool

        Returns:
            The tool instance, or None if not found
        """
        return self.tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """
        Get all registered tools.

        Returns:
            List of all tool instances
        """
        return list(self.tools.values())

    def get_tool_descriptions(self) -> str:
        """
        Get formatted descriptions of all tools for the LLM.

        Returns:
            Formatted string with all tool descriptions
        """
        if not self.tools:
            return "No tools available."

        descriptions = ["Available tools:\n"]
        for tool in self.tools.values():
            descriptions.append(f"\n{'-' * 80}")
            descriptions.append(f"Tool: {tool.name}")
            descriptions.append(f"{'-' * 80}")
            descriptions.append(tool.description)

        return "\n".join(descriptions)

    def execute_tool(self, name: str, **kwargs) -> str:
        """
        Execute a tool by name with the given parameters.

        Args:
            name: The name of the tool to execute
            **kwargs: Tool-specific parameters

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(name)
        if not tool:
            available_tools = ", ".join(self.tools.keys())
            return f"Error: Tool '{name}' not found. Available tools: {available_tools}"

        try:
            logger.info(f"Executing tool: {name} with params: {list(kwargs.keys())}")
            result = tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            return f"Error executing tool '{name}': {str(e)}"


__all__ = [
    "Tool",
    "ToolManager",
    "SearchTool",
    "ScrapeTool",
    "CodeExecutorTool",
    "FileOpsTool",
]
