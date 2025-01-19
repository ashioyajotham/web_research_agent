import asyncio
import aiohttp
from typing import Dict, List
import json
from ratelimit import limits, sleep_and_retry

class WebSearchTool:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
    
    @sleep_and_retry
    @limits(calls=10, period=60)  # Rate limit: 10 calls per minute
    async def search(self, query: str, num_results: int = 5) -> Dict:
        """
        Perform web search using Serper API
        """
        if isinstance(query, str) and query.startswith('"') and query.endswith('"'):
            query = query[1:-1]  # Remove surrounding quotes

        try:
            print(f"Searching for: {query}")  # Debug print
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json={"q": query, "num": num_results}
                ) as response:
                    
                    data = await response.json()
                    print(f"Search response: {json.dumps(data, indent=2)}")  # Debug
                    
                    return {
                        "success": True,
                        "results": data.get("organic", [])
                    }
                    
        except Exception as e:
            print(f"Search error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def _parse_results(self, data: Dict) -> Dict:
        results = []
        
        if 'organic' in data:
            for item in data['organic']:
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'position': item.get('position', 0)
                })
        
        return {
            'success': True,
            'results': results,
            'total_results': len(results)
        }

    async def retry_with_backoff(self, query: str, max_retries: int = 3) -> Dict:
        for attempt in range(max_retries):
            try:
                return await self.search(query)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff