import requests
from bs4 import BeautifulSoup
from .base import BaseTool
from typing import Dict, Any
import aiohttp
import asyncio
from aiohttp import ClientTimeout
import logging

class WebScraperTool(BaseTool):
    def __init__(self):
        self.timeout = ClientTimeout(total=30)
        self.max_retries = 3
        self.logger = logging.getLogger(__name__)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute with flexible parameter handling"""
        url = kwargs.get('url')
        if not url:
            # Handle the case when URL comes from query parameter
            query = kwargs.get('query')
            if query and query.startswith('http'):
                url = query

        if not url:
            return {
                'success': False,
                'error': 'URL parameter required',
                'output': None
            }

        try:
            content = await self._scrape_url(url)
            return {
                'success': True,
                'output': content
            }
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': None
            }

    async def _scrape_url(self, url: str) -> str:
        """Scrape content from URL with retries"""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            raise Exception(f"HTTP {response.status}")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))

    def _extract_main_content(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'meta', 'link', 'header', 'footer', 'nav']):
            element.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:500000]  # Limit content length
    
    def get_description(self) -> str:
        """Return tool description"""
        return "A web scraping tool that extracts content from web pages with support for various content types and structures."

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata"""
        return {
            "name": "web_scraper",
            "type": "content_extraction",
            "version": "1.0",
            "capabilities": [
                "html_extraction",
                "text_extraction",
                "structured_data",
                "dynamic_content"
            ]
        }