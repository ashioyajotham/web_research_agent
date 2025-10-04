"""
Web search tool using Serper.dev API.
Allows the agent to search Google for information.
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from .base import Tool

logger = logging.getLogger(__name__)


class SearchTool(Tool):
    """Tool for searching the web using Serper.dev API."""

    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize the search tool.

        Args:
            api_key: Serper.dev API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://google.serper.dev/search"
        super().__init__()

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return """Search Google for information on the web.

Parameters:
- query (str, required): The search query string

Returns:
A formatted string containing search results with titles, links, and snippets.
Each result includes:
- Position number
- Title
- URL
- Snippet (brief description)

Use this tool when you need to:
- Find current information on the web
- Locate specific websites or documents
- Research topics, people, companies, or events
- Find sources for statements or facts

Example usage:
query: "Joe Biden statements on US-China relations 2023"
query: "Volkswagen greenhouse gas emissions 2023"
query: "Epoch AI dataset large-scale models"
"""

    def execute(self, query: str) -> str:
        """
        Execute a web search.

        Args:
            query: The search query string

        Returns:
            Formatted string with search results

        Raises:
            Exception: If the search fails
        """
        if not query or not query.strip():
            return "Error: Search query cannot be empty"

        try:
            logger.info(f"Searching for: {query}")

            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }

            payload = {
                "q": query,
                "num": 10,  # Number of results to return
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            data = response.json()

            return self._format_results(data, query)

        except requests.exceptions.Timeout:
            logger.error(f"Search request timed out for query: {query}")
            return f"Error: Search request timed out after {self.timeout} seconds"
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {str(e)}")
            return f"Error: Search request failed: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search response: {str(e)}")
            return f"Error: Failed to parse search response: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during search: {str(e)}")
            return f"Error: Unexpected error during search: {str(e)}"

    def _format_results(self, data: Dict[str, Any], query: str) -> str:
        """
        Format search results into a readable string.

        Args:
            data: The response data from Serper API
            query: The original search query

        Returns:
            Formatted string with search results
        """
        results = []
        results.append(f"Search results for: {query}\n")
        results.append("=" * 80 + "\n")

        # Extract organic results
        organic_results = data.get("organic", [])

        if not organic_results:
            return f"No search results found for: {query}"

        for idx, result in enumerate(organic_results, 1):
            title = result.get("title", "No title")
            link = result.get("link", "No link")
            snippet = result.get("snippet", "No description available")

            results.append(f"\n[{idx}] {title}")
            results.append(f"URL: {link}")
            results.append(f"Snippet: {snippet}")
            results.append("-" * 80)

        # Add knowledge graph if available
        knowledge_graph = data.get("knowledgeGraph")
        if knowledge_graph:
            results.append("\n\nKNOWLEDGE GRAPH:")
            results.append("=" * 80)
            if "title" in knowledge_graph:
                results.append(f"Title: {knowledge_graph['title']}")
            if "description" in knowledge_graph:
                results.append(f"Description: {knowledge_graph['description']}")
            if "attributes" in knowledge_graph:
                results.append("Attributes:")
                for key, value in knowledge_graph["attributes"].items():
                    results.append(f"  - {key}: {value}")

        # Add answer box if available
        answer_box = data.get("answerBox")
        if answer_box:
            results.append("\n\nANSWER BOX:")
            results.append("=" * 80)
            if "answer" in answer_box:
                results.append(f"Answer: {answer_box['answer']}")
            if "snippet" in answer_box:
                results.append(f"Snippet: {answer_box['snippet']}")

        return "\n".join(results)
