import aiohttp
import json
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin
from utils.helpers import logger, WebUtils
from bs4 import BeautifulSoup, Comment
import re

class WebBrowser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_serper_api_key()
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.sources = []

    @staticmethod
    def _get_serper_api_key() -> str:
        """Get API key from environment variable"""
        import os
        api_key = os.getenv('SERPER_API_KEY')
        if not api_key:
            raise ValueError("SERPER_API_KEY environment variable not set")
        return api_key

    async def search(self, query: str) -> Dict:
        """Perform a web search using Serper API"""
        try:
            payload = {
                'q': query,
                'num': 5
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise

    async def browse(self, url: str) -> str:
        """Fetch and extract content from a webpage"""
        try:
            # Check if input is actually a URL
            if not url.startswith(('http://', 'https://')):
                if not any(char in url for char in ['/', '.', ':']):
                    # This is probably a search query, not a URL
                    search_results = await self.search(url)
                    if search_results and 'organic' in search_results:
                        url = search_results['organic'][0]['link']
                    else:
                        raise ValueError(f"Could not find valid URL for query: {url}")
                else:
                    # Add https:// if missing
                    url = f'https://{url}'

            # Validate URL
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError(f"Invalid URL format: {url}")

            return await self._fetch_url(url)

        except Exception as e:
            logger.error(f"Failed to browse URL '{url}': {str(e)}")
            raise

    async def _fetch_url(self, url: str) -> str:
        """Fetch URL with proper encoding handling"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers={
                    'User-Agent': self.headers['User-Agent'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.5',
                }) as response:
                    response.raise_for_status()
                    
                    # Try to get encoding from headers
                    content_type = response.headers.get('content-type', '')
                    encoding = None
                    
                    if 'charset=' in content_type:
                        encoding = content_type.split('charset=')[-1]
                    
                    try:
                        if encoding:
                            content = await response.text(encoding=encoding)
                        else:
                            # Try UTF-8 first
                            content = await response.text(encoding='utf-8')
                    except UnicodeDecodeError:
                        # Fallback to latin-1 if UTF-8 fails
                        content = await response.text(encoding='latin-1')
                    
                    return self._extract_main_content(content)
                    
            except aiohttp.ClientError as e:
                logger.error(f"HTTP request failed for URL '{url}': {str(e)}")
                raise
            except UnicodeDecodeError as e:
                logger.error(f"Encoding error for URL '{url}': {str(e)}")
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
        Extract main content from HTML with improved content identification and cleaning
        """
        try:
            from bs4 import BeautifulSoup
            import re

            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'ad', 'noscript']):
                element.decompose()

            # Remove comments
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Find main content area (priority order)
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find(attrs={'role': 'main'}) or 
                soup.find(class_=re.compile(r'(content|article|post)-?(main|body|text)?', re.I)) or 
                soup.find('div', {'class': ['content', 'main', 'article', 'post']}) or 
                soup.body
            )

            if not main_content:
                main_content = soup

            # Clean the content
            text = []
            for paragraph in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                content = paragraph.get_text(strip=True)
                if content and len(content) > 20:  # Filter out short snippets
                    text.append(content)

            # Join paragraphs with proper spacing
            cleaned_text = '\n\n'.join(text)

            # Additional cleaning
            cleaned_text = re.sub(r'\n\s*\n+', '\n\n', cleaned_text)  # Remove extra newlines
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
            cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Remove extra spaces

            # Truncate if too long (preserve complete sentences)
            if len(cleaned_text) > 5000:
                sentences = re.split(r'(?<=[.!?])\s+', cleaned_text[:5000])
                cleaned_text = ' '.join(sentences[:-1]) + '...'

            return cleaned_text.strip()

        except Exception as e:
            logger.error(f"Failed to extract content: {str(e)}")
            return "Content extraction failed"