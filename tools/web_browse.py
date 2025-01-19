import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import asyncio
from urllib.parse import urlparse
import re

class WebBrowserTool:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def browse(self, url: str, selectors: Optional[List[str]] = None) -> Dict:
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}',
                            'content': None
                        }

                    html = await response.text()
                    return self._extract_content(html, selectors, url)

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': None
            }

    def _extract_content(self, html: str, selectors: Optional[List[str]], url: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for elem in soup.find_all(['script', 'style', 'noscript']):
            elem.decompose()

        content = {}
        
        if selectors:
            # Extract specific elements
            for selector in selectors:
                elements = soup.select(selector)
                content[selector] = [self._clean_text(elem.get_text()) for elem in elements]
        else:
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            content['main'] = self._clean_text(main_content.get_text()) if main_content else ""
            
            # Extract title
            title = soup.find('title')
            content['title'] = self._clean_text(title.get_text()) if title else ""

        return {
            'success': True,
            'url': url,
            'content': content,
            'metadata': self._get_metadata(soup)
        }

    def _clean_text(self, text: str) -> str:
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        return text

    def _get_metadata(self, soup: BeautifulSoup) -> Dict:
        metadata = {}
        
        # Get meta description
        desc = soup.find('meta', attrs={'name': 'description'})
        if desc:
            metadata['description'] = desc.get('content', '')

        # Get meta keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords:
            metadata['keywords'] = keywords.get('content', '').split(',')

        return metadata