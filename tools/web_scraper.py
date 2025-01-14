import requests
from bs4 import BeautifulSoup
from .base import BaseTool
from typing import Dict, Any

class WebScraperTool(BaseTool):
    def execute(self, url: str, **kwargs) -> Dict[str, Any]:
        try:
            # Ignore max_length param if provided but use it for truncation if specified
            max_length = kwargs.get('max_length', 500000)
            
            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            response.raise_for_status()
            text = self._extract_main_content(response.text)
            
            # Truncate to max_length if needed
            if len(text) > max_length:
                text = text[:max_length]
                
            return {
                'success': True,
                'output': text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
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