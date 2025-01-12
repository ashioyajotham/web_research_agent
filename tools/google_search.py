import os
import aiohttp
from typing import Dict, Any
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
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json={"q": query}
            ) as response:
                return await response.json()
