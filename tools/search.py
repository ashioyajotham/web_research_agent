from typing import Any, Dict, List
import json
import requests
from .tool_registry import BaseTool
from utils.logger import get_logger
from config.config import get_config

logger = get_logger(__name__)

class SearchResult:
    """Class to hold search result data."""
    
    def __init__(self, title: str, link: str, snippet: str):
        self.title = title
        self.link = link
        self.snippet = snippet
    
    def __str__(self) -> str:
        return f"Title: {self.title}\nURL: {self.link}\nSnippet: {self.snippet}"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet
        }

class SearchTool(BaseTool):
    """Tool for searching the web using serper.dev API."""
    
    def __init__(self):
        """Initialize the search tool."""
        super().__init__(
            name="search",
            description="Searches the web using the serper.dev Google Search API"
        )
        self.config = get_config()
        self.api_key = self.config.get("serper_api_key")
        self.base_url = "https://google.serper.dev/search"
    
    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        query = parameters.get("query")
        if not query:
            return {"status": "error", "error": "No search query provided"}
        
        num_results = int(parameters.get("num_results", self.config.get("max_search_results", 10)))
        logger.info(f"Searching for: {query}")
        
        try:
            raw_results: List[SearchResult] = self._search(query, num_results)
            normalized_results: List[Dict[str, Any]] = [r.to_dict() for r in raw_results]

            if memory is not None:
                try:
                    setattr(memory, "search_results", normalized_results)
                except Exception as e:
                    logger.warning(f"Failed to set search_results in memory: {e}")

            # This is the direct payload the agent loop expects.
            output_payload = {
                "query": query,
                "results": normalized_results
            }
            
            # --- THIS IS THE FIX ---
            # Unpack the payload into the top-level dictionary.
            return {"status": "success", **output_payload}
        
        except Exception as e:
            error_message = f"Error performing search: {str(e)}"
            logger.error(error_message)
            # Return a flat error structure as well for consistency.
            return {"status": "error", "error": error_message}

    def _search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Perform the actual search using serper.dev API.
        
        Args:
            query (str): Search query
            num_results (int): Number of results to return
            
        Returns:
            list: List of SearchResult objects
        """
        if not self.api_key:
            raise ValueError("Serper API key not configured. Please set SERPER_API_KEY.")
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "q": query,
            "num": num_results
        }
        
        timeout = self.config.get("timeout", 30)
        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"Search API returned status code {response.status_code}: {response.text}")
        
        # Wrap response.json() in a try/except
        try:
            search_data = response.json()
        except ValueError:
            raise Exception("Received non-JSON response from search API (possibly HTML error page).")
        
        results = []
        
        # Process organic search results
        organic_results = search_data.get("organic", [])
        for result in organic_results[:num_results]:
            title = result.get("title", "No title")
            link = result.get("link", "")
            snippet = result.get("snippet", "No description available")
            
            results.append(SearchResult(title, link, snippet))
        
        return results

def get_page(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 401:
            logger.error(f"401 Unauthorized: {url}")
            return {"error": f"HTTP 401 accessing {url}"}
        if response.status_code in (403, 429):
            logger.error(f"{response.status_code} blocked: {url}")
            return {"error": f"HTTP {response.status_code} accessing {url}"}
        response.raise_for_status()
        return {"content": response.text}
    except requests.RequestException as e:
        logger.error(f"HTTP error accessing {url}: {str(e)}")
        return {"error": str(e)}
