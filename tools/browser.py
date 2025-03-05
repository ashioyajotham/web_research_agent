from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import html2text
from .tool_registry import BaseTool
from utils.logger import get_logger
from config.config import get_config

logger = get_logger(__name__)

class BrowserTool(BaseTool):
    """Tool for browsing websites and extracting content."""
    
    def __init__(self):
        """Initialize the browser tool."""
        super().__init__(
            name="browser",
            description="Fetches and processes web content from URLs"
        )
        self.config = get_config()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.bypass_tables = False
        self.html_converter.ignore_images = True
    
    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        """
        Execute the browser tool with the given parameters.
        
        Args:
            parameters (dict): Parameters for the tool
                - url (str): URL to browse
                - extract_type (str, optional): Type of extraction ('full', 'main_content', 'summary')
                - selector (str, optional): CSS selector for targeted extraction
            memory (Memory): Agent's memory
            
        Returns:
            dict: Extracted content and metadata
        """
        url = parameters.get("url")
        if not url:
            return {"error": "No URL provided for browsing"}
        
        # Handle variable substitution for search result URLs
        if url.startswith("{search_result_") and url.endswith("_url}"):
            try:
                # Extract the index from the placeholder
                idx_str = url.replace("{search_result_", "").replace("_url}", "")
                idx = int(idx_str)
                
                # Look for most recent search results in memory
                search_results = memory.task_results.get("Search for information", {}).get("results", [])
                if idx < len(search_results):
                    url = search_results[idx]["link"]
                    logger.info(f"Resolved URL placeholder to: {url}")
                else:
                    return {"error": f"Search result index {idx} out of range"}
            except Exception as e:
                return {"error": f"Failed to resolve URL placeholder: {str(e)}"}
        
        extract_type = parameters.get("extract_type", "main_content")
        selector = parameters.get("selector", "")
        
        # Check if we have cached content
        cached_content = memory.get_cached_content(url)
        if cached_content:
            logger.info(f"Using cached content for URL: {url}")
            content = cached_content["content"]
        else:
            logger.info(f"Browsing URL: {url}")
            try:
                content = self._fetch_url(url)
                # Cache the raw HTML content
                memory.cache_web_content(url, content, {"type": "raw_html"})
            except Exception as e:
                error_message = f"Error accessing URL {url}: {str(e)}"
                logger.error(error_message)
                return {"error": error_message}
        
        try:
            if extract_type == "full":
                processed_content = self._process_full_page(content)
            elif extract_type == "main_content":
                processed_content = self._extract_main_content(content, selector)
            elif extract_type == "summary":
                # Extract main content first, then summarize
                main_content = self._extract_main_content(content, selector)
                # Use comprehension module to summarize
                from agent.comprehension import Comprehension
                comprehension = Comprehension()
                processed_content = comprehension.summarize_content(main_content)
            else:
                return {"error": f"Unknown extraction type: {extract_type}"}
            
            result = {
                "url": url,
                "title": self._extract_title(content),
                "extract_type": extract_type,
                "content": processed_content
            }
            
            return result
        except Exception as e:
            error_message = f"Error processing content from {url}: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
    
    def _fetch_url(self, url: str) -> str:
        """
        Fetch content from a URL.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str: Raw HTML content
        """
        timeout = self.config.get("timeout", 30)
        response = requests.get(url, headers=self.headers, timeout=timeout)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.text
    
    def _extract_title(self, html_content: str) -> str:
        """Extract the page title from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.find('title')
        return title.text.strip() if title else "No title found"
    
    def _process_full_page(self, html_content: str) -> str:
        """Convert the full HTML page to markdown text."""
        return self.html_converter.handle(html_content)
    
    def _extract_main_content(self, html_content: str, selector: str = "") -> str:
        """
        Extract the main content from an HTML page.
        
        Args:
            html_content (str): Raw HTML content
            selector (str, optional): CSS selector for targeted extraction
            
        Returns:
            str: Extracted content as markdown
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove elements that usually contain noise
        for element in soup.select('script, style, nav, footer, iframe, .nav, .menu, .header, .footer, .sidebar, .ad, .comments, .related'):
            element.decompose()
        
        # If a custom selector is provided, use it
        if selector:
            main_element = soup.select_one(selector)
            if main_element:
                return self.html_converter.handle(str(main_element))
        
        # Try common selectors for main content
        for main_selector in ['main', 'article', '.content', '#content', '.post', '.article', '.main']:
            main_element = soup.select_one(main_selector)
            if main_element:
                return self.html_converter.handle(str(main_element))
        
        # Fallback to body if no main content identified
        body = soup.find('body')
        if body:
            return self.html_converter.handle(str(body))
        
        # Last resort: return everything
        return self.html_converter.handle(html_content)
