import os
import aiohttp
from typing import Dict, Any, Optional
from .base import BaseTool

class GoogleSearchTool(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable not set")
        self.base_url = "https://google.serper.dev/search"

    def get_description(self) -> str:
        return "Performs web searches using Google Search API"

    async def execute(self, query: str) -> Dict[str, Any]:
        """Execute search query"""
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json={"q": query}
                ) as response:
                    if response.status == 403:
                        raise ValueError(f"API Key unauthorized. Please check your SERPER_API_KEY")
                    elif response.status != 200:
                        raise ValueError(f"API request failed with status {response.status}")
                    
                    result = await response.json()
                    return {
                        "success": True,
                        "results": result.get("organic", []),
                        "knowledge_graph": result.get("knowledgeGraph", {}),
                        "related_searches": result.get("relatedSearches", [])
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
