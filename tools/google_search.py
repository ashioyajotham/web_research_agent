from typing import Dict, Any, Optional
import aiohttp
import json
import os
from .base import BaseTool

class GoogleSearchTool(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key (SERPER_API_KEY) not found in environment variables")
        self.base_url = "https://google.serper.dev/search"

    def get_description(self) -> str:
        """Implement abstract method from BaseTool"""
        return "Performs web searches using Serper API and returns structured results"

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search using Serper API"""
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Prepare search parameters
            search_params = {
                "q": query,
                "num": kwargs.get('num', 10)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=search_params
                ) as response:
                    data = await response.json()
                    
                    if 'error' in data:
                        return {
                            "success": False,
                            "error": data.get('error', 'Unknown error'),
                            "results": []
                        }
                    
                    # Format results
                    results = []
                    organic = data.get('organic', [])
                    for i, item in enumerate(organic):
                        results.append({
                            "title": item.get('title', ''),
                            "link": item.get('link', ''),
                            "snippet": item.get('snippet', ''),
                            "date": item.get('date', ''),
                            "position": i + 1
                        })
                    
                    return {
                        "success": True,
                        "results": results,
                        "knowledge_graph": data.get('knowledgeGraph', {}),
                        "related_searches": data.get('relatedSearches', [])
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
