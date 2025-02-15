import aiohttp
import json
from typing import List, Dict, Optional
from utils.helpers import logger, WebUtils

class WebBrowser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_serper_api_key()
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

    @staticmethod
    def _get_serper_api_key() -> str:
        """Get API key from environment variable"""
        import os
        api_key = os.getenv('SERPER_API_KEY')
        if not api_key:
            raise ValueError("SERPER_API_KEY environment variable not set")
        return api_key

    async def search(self, query: str) -> Dict:
        """
        Perform a web search using Serper API
        """
        try:
            payload = {
                'q': query,
                'num': 5  # Number of results to return
            }
            
            response = await WebUtils.make_http_request(
                url=self.base_url,
                method="POST",
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            return self._parse_search_results(response)

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise

    async def browse(self, url: str) -> str:
        """
        Fetch and extract content from a webpage
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
                    return self._extract_main_content(html)

        except Exception as e:
            logger.error(f"Failed to browse URL '{url}': {str(e)}")
            raise

    def _parse_search_results(self, response: Dict) -> Dict:
        """
        Parse and structure search results
        """
        parsed_results = {
            'organic': [],
            'knowledge_graph': None,
            'related_searches': []
        }

        if 'organic' in response:
            parsed_results['organic'] = [
                {
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': result.get('snippet', ''),
                    'position': result.get('position', 0)
                }
                for result in response['organic']
            ]

        if 'knowledgeGraph' in response:
            parsed_results['knowledge_graph'] = response['knowledgeGraph']

        if 'relatedSearches' in response:
            parsed_results['related_searches'] = response['relatedSearches']

        return parsed_results

    def _extract_main_content(self, html: str) -> str:
        """
        Extract main content from HTML
        TODO: Implement more sophisticated content extraction
        """
        # Basic implementation - should be enhanced with proper HTML parsing
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:5000]  # Limit length of returned content