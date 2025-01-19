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
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'q': query,
                    'num': num_results
                }
                
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Search failed: {response.status}")
                    
                    data = await response.json()
                    return self._parse_results(data)
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': []
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