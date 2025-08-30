from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from .tool_registry import BaseTool
from utils.logger import get_logger
from config.config import get_config
import re
import requests
from urllib.parse import urlparse
import html2text

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
        """Execute browser tool with enhanced URL handling."""
        url = parameters.get("url")
        extract_type = parameters.get("extract_type", "main_content")
        selector = parameters.get("selector", "")

        # Handle fallback to search snippets
        if parameters.get("use_search_snippets") or not url:
            snippet_out = self._extract_from_search_snippets(memory)
            return {
                "status": "success" if snippet_out.get("extracted_text") else "error",
                "output": snippet_out
            }
        
        # Validate URL before attempting to browse
        if not url or not self._is_valid_url(url):
            logger.info("Invalid or missing URL for browser; falling back to search snippets")
            snippet_out = self._extract_from_search_snippets(memory)
            return {
                "status": "success" if snippet_out.get("extracted_text") else "error",
                "output": snippet_out
            }
        
        # Check if we have cached content
        cached_content = memory.get_cached_content(url)
        if (cached_content):
            logger.info(f"Using cached content for {url}")
            title = self._extract_title(cached_content) or ""
            text = cached_content
            if extract_type == "summary":
                text = "\n".join(text.splitlines()[:80])
            return {
                "status": "success",
                "output": {
                    "url": url,
                    "title": title,
                    "content": text,
                    "extracted_text": text
                }
            }
        else:
            logger.info(f"Fetching URL: {url}")
        
        try:
            resp = self._fetch_url(url)
            if resp is None or resp.status_code >= 400:
                logger.warning(f"Fetch failed for {url} with status {getattr(resp, 'status_code', 'n/a')}")
                snippet_out = self._extract_from_search_snippets(memory)
                return {
                    "status": "success" if snippet_out.get("extracted_text") else "error",
                    "output": snippet_out
                }
            html = resp.text or ""
            soup = BeautifulSoup(html, "html.parser")
            title = self._extract_title(html) or (soup.title.string.strip() if soup.title and soup.title.string else "")
            # Extract main content or full page
            if extract_type == "full":
                text_md = self._process_full_page(html)
            else:
                main_html = self._extract_main_content(soup, selector)
                text_md = self.html_converter.handle(str(main_html)) if main_html else self._process_full_page(html)
            # Cache if available
            if hasattr(memory, "cache_content"):
                try:
                    memory.cache_content(url, text_md)
                except Exception:
                    pass
            return {
                "status": "success",
                "output": {
                    "url": url,
                    "title": title,
                    "content": text_md,
                    "extracted_text": text_md
                }
            }
        except Exception as e:
            logger.error(f"Browser error for {url}: {e}")
            return {"status": "error", "error": str(e), "output": {}}
    
    def _extract_from_search_snippets(self, memory):
        """Extract information from search snippets when URL browsing fails."""
        # Try multiple ways to get search results
        search_results = getattr(memory, 'search_results', [])
        
        # If no search_results attribute, try to find them in recent results
        if not search_results:
            recent = getattr(memory, 'recent_results', []) or []
            for r in recent:
                out = r.get("output", {})
                if isinstance(out, dict) and isinstance(out.get("results"), list):
                    search_results = out["results"]
                    break
        
        if not search_results:
            logger.info("No search results available for snippet extraction")
            return {"title": "Combined Search Results", "extracted_text": "", "urls": []}
        
        logger.info(f"Extracting from {len(search_results)} search result snippets")
        
        # Combine snippets from search results
        combined_content = []
        urls = []
        
        for i, result in enumerate(search_results[:5]):            
            snippet = (result.get("snippet") or "").strip()
            link = result.get("link") or result.get("url") or ""
            title = result.get("title") or ""
            if snippet:
                combined_content.append(f"{title}\n{snippet}".strip())
            if link:
                urls.append(link)
        
        if not combined_content:
            return {"title": "Combined Search Results", "extracted_text": "", "urls": urls}
        
        extracted_text = "\n\n".join(combined_content)
        
        logger.info(f"Successfully extracted {len(extracted_text)} characters from search snippets")
        return {"title": "Combined Search Results", "extracted_text": extracted_text, "urls": urls}

    def _is_valid_url(self, url):
        try:
            u = urlparse(url)
            return bool(u.scheme in ("http", "https") and u.netloc)
        except Exception:
            return False

    def _fetch_url(self, url):
        try:
            return requests.get(url, headers=self.headers, timeout=15)
        except Exception:
            return None

    def _extract_title(self, content):
        try:
            soup = BeautifulSoup(content, "html.parser")
            return soup.title.string.strip() if soup.title and soup.title.string else ""
        except Exception:
            return ""

    def _extract_main_content(self, content, selector=""):
        # content can be BeautifulSoup or HTML string
        soup = content if isinstance(content, BeautifulSoup) else BeautifulSoup(str(content), "html.parser")
        if selector:
            sel = soup.select_one(selector)
            if sel:
                return sel
        # Heuristics: article, role=main, main, content containers
        for cand in [
            "article", "[role=main]", "main",
            "div#content", "div.article", "section.article", "div.post", "div#main"
        ]:
            el = soup.select_one(cand)
            if el:
                return el
        return soup.body or soup

    def _process_full_page(self, content):
        try:
            return self.html_converter.handle(content)
        except Exception:
            return BeautifulSoup(content, "html.parser").get_text(" ", strip=True)

    def _determine_relevant_entity_types(self, title, content):
        # Placeholder; kept for compatibility
        return []

    def _enrich_entity_relationships(self, entities, query, title):
        # Placeholder; kept for compatibility
        return entities
