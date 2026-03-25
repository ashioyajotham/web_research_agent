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

__version__ = "2.4.2"
__author__ = "Victor Jotham Ashioya"
__license__ = "MIT"

# Import main components for easy access
from .agent import ReActAgent, Step
from .config import config, Config
from .llm import LLMInterface
from .llm_compat import OpenAICompatibleLLMInterface, openai_available, PROVIDERS
from .llm_chain import ModelFallbackChain
from .memory import ConversationMemory
from .credentials import get_credential, set_credential, keyring_available
from .parallel import ParallelResearchAgent
from .tools import (
    Tool,
    ToolManager,
    SearchTool,
    ScrapeTool,
    BrowserScrapeTool,
    CodeExecutorTool,
    FileOpsTool,
    PDFExtractTool,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "ReActAgent",
    "ParallelResearchAgent",
    "Step",
    "Config",
    "config",
    "LLMInterface",
    "OpenAICompatibleLLMInterface",
    "ModelFallbackChain",
    "openai_available",
    "PROVIDERS",
    "ConversationMemory",
    "get_credential",
    "set_credential",
    "keyring_available",
    "Tool",
    "ToolManager",
    "SearchTool",
    "ScrapeTool",
    "BrowserScrapeTool",
    "CodeExecutorTool",
    "FileOpsTool",
    "PDFExtractTool",
]
