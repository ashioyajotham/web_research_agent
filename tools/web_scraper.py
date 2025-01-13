import requests
from bs4 import BeautifulSoup
from .base import BaseTool

class WebScraperTool(BaseTool):
    def execute(self, url: str) -> str:
        try:
            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            response.raise_for_status()
            return self._extract_main_content(response.text)
        except Exception as e:
            return f"Error scraping URL: {str(e)}"
    
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
        return "Scrapes and extracts main content from a given URL. Input should be a valid URL."