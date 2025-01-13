from typing import Dict, Any, Optional, List
import aiohttp
import json
import os
import logging
import asyncio
from aiohttp import ClientTimeout
from .base import BaseTool

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GoogleSearchTool(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key (SERPER_API_KEY) not found in environment variables")
        logger.debug(f"Serper API Key configured: {self.api_key[:5]}...")
        self.base_url = "https://google.serper.dev/search"
        self.timeout = ClientTimeout(total=30)  # 30 second timeout
        self.max_retries = 3

    def get_description(self) -> str:
        """Implement abstract method from BaseTool"""
        return "Performs web searches using Serper API and returns structured results"

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search with retries"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                return await self._make_request(query, **kwargs)
            except Exception as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(f"Search failed, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Search failed after {self.max_retries} retries: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Search failed: {str(e)}",
                        "results": []
                    }

    async def _make_request(self, query: str, **kwargs) -> Dict[str, Any]:
        """Make API request with basic error handling"""
        if not query or not isinstance(query, str):
            return {"success": False, "error": "Invalid query", "results": []}

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        params = {
            "q": query,
            "num": min(kwargs.get('num', 3), 5)
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API error: {error_text}",
                        "results": []
                    }

                data = await response.json()
                results = []
                for i, item in enumerate(data.get('organic', [])):
                    result = {
                        "title": self._clean_title(item.get('title', '')),
                        "link": item.get('link', ''),
                        "snippet": self._clean_snippet(item.get('snippet', '')),
                        "position": i + 1
                    }
                    results.append(result)

                return {
                    "success": True,
                    "results": results,
                    "knowledge_graph": self._process_knowledge_graph(data.get('knowledgeGraph', {})),
                    "related_searches": data.get('relatedSearches', [])
                }

    def _clean_title(self, title: str) -> str:
        """Clean up title text"""
        prefixes = ["Richest People", "The Richest", "The Person", "Person"]
        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        return title

    def _clean_snippet(self, snippet: str) -> str:
        """Clean up snippet text"""
        prefixes = [
            "According to", "From", "Source:",
            "Wikipedia:", "Reuters:", "Richest People",
            "The Richest", "The Person", "Person"
        ]
        for prefix in prefixes:
            if snippet.startswith(prefix):
                snippet = snippet[len(prefix):].strip()
        return snippet

    def _process_knowledge_graph(self, kg_data: Dict) -> Dict:
        """Process knowledge graph data"""
        if not kg_data:
            return {}
        return {
            "title": self._clean_title(kg_data.get("title", "")),
            "type": kg_data.get("type", ""),
            "description": kg_data.get("description", ""),
            "attributes": kg_data.get("attributes", {})
        }
