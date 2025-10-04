"""
Web Research Agent - An AI agent using ReAct methodology for autonomous web research.

This package provides a sophisticated AI agent that can:
- Search the web for information
- Scrape and parse web pages
- Execute Python code for data analysis
- Process complex research tasks autonomously

Usage:
    From command line:
        $ webresearch

    From Python:
        from web_research_agent import ReActAgent, initialize_agent

        agent = initialize_agent()
        result = agent.run("Your research question")

For more information, see: https://github.com/victorashioya/web_research_agent
"""

__version__ = "1.2.0"
__author__ = "Victor Jotham Ashioya"
__license__ = "MIT"

# Import main components for easy access
from .agent import ReActAgent, Step
from .config import config, Config
from .llm import LLMInterface
from .tools import (
    Tool,
    ToolManager,
    SearchTool,
    ScrapeTool,
    CodeExecutorTool,
    FileOpsTool,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core components
    "ReActAgent",
    "Step",
    "Config",
    "config",
    "LLMInterface",
    # Tools
    "Tool",
    "ToolManager",
    "SearchTool",
    "ScrapeTool",
    "CodeExecutorTool",
    "FileOpsTool",
]
