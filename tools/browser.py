from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import html2text
import re
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
        url = parameters.get("url", "")
        if not url:
            return {"error": "No URL provided for browsing"}
        
        # Enhanced URL validation and normalization
        if not isinstance(url, str) or len(url) < 3:
            return {"error": f"Invalid URL format: {url}"}
        
        # Check for obvious placeholder patterns and try to resolve them
        placeholder_patterns = [
            r"\[.*\]",  # Anything in square brackets
            r"placeholder",
            r"URL_from",
            r"FILL_IN",
            r"<URL>",
            r"{.*}"  # Anything in curly braces
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                # This is clearly a placeholder that wasn't resolved, try to get a URL from memory
                if hasattr(memory, 'search_results') and memory.search_results:
                    first_url = memory.search_results[0].get("link", "")
                    if first_url:
                        logger.warning(f"URL '{url}' appears to be an unresolved placeholder. Using first search result URL: {first_url}")
                        url = first_url
                        break
                else:
                    return {"error": f"Could not resolve placeholder URL: {url}"}
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.info(f"Added https:// prefix to URL: {url}")
        
        # URL validation - check basic URL structure
        if not re.match(r"https?://[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:[0-9]+)?(/.*)?$", url):
            return {"error": f"URL format appears invalid: {url}"}
        
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
            
            # Enhanced entity extraction - now always extracts entities even if not explicitly requested
            try:
                from agent.comprehension import Comprehension
                comprehension = Comprehension()
                
                # Determine relevant entity types based on title and content
                entity_types = self._determine_relevant_entity_types(result["title"], processed_content)
                
                # Extract entities with focused types
                entities = comprehension.extract_entities(processed_content, entity_types)
                
                # Try to extract relationships between entities
                enriched_entities = self._enrich_entity_relationships(entities, parameters.get("query", ""), result["title"])
                
                # Add extracted entities to memory
                memory.add_entities(enriched_entities)
                
                # Include entities in result if requested
                if parameters.get("extract_entities", True):  # Default to True for better info extraction
                    result["entities"] = enriched_entities
            
            except Exception as e:
                logger.error(f"Error during entity extraction: {str(e)}")
            
            return result
            
        except Exception as e:
            error_message = f"Error processing content from {url}: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
    
    def _process_url_parameter(self, url: str, memory: Any) -> str:
        """
        Process URL parameter to handle various placeholder formats.
        
        Args:
            url (str): URL or placeholder
            memory (Memory): Agent's memory
            
        Returns:
            str: Processed URL or error message
        """
        # Handle variable substitution for search result URLs in various formats
        if url.startswith("{search_result_") and "url}" in url:
            # Format: {search_result_0_url}
            try:
                idx_str = re.search(r"search_result_(\d+)", url).group(1)
                idx = int(idx_str)
                
                if hasattr(memory, 'search_results') and memory.search_results:
                    if idx < len(memory.search_results):
                        return memory.search_results[idx].get("link", "")
                    else:
                        return f"Error: Search result index {idx} out of range"
                else:
                    return f"Error: No search results available in memory"
            except Exception as e:
                return f"Error: Failed to process URL placeholder: {str(e)}"
        
        elif re.match(r"\[.*URL.*\]", url, re.IGNORECASE) or re.match(r"\[Insert.*\]", url, re.IGNORECASE):
            # Format: [Insert URL from search results] or similar
            logger.warning(f"Found placeholder URL: {url}")
            
            # Try to use the first search result as fallback
            if hasattr(memory, 'search_results') and memory.search_results:
                first_url = memory.search_results[0].get("link", "")
                logger.info(f"Substituting placeholder with first search result: {first_url}")
                return first_url
            else:
                return f"Error: Cannot resolve placeholder URL: {url}"
        
        # If it seems like a valid URL, return it
        return url
    
    def _fetch_url(self, url: str) -> str:
        """
        Fetch content from a URL.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str: Raw HTML content
        """
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.info(f"Added https:// prefix to URL: {url}")
        
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
    
    def _determine_relevant_entity_types(self, title, content):
        """Determine which entity types are most relevant to extract based on content."""
        title_lower = title.lower() if title else ""
        content_sample = content[:2000].lower() if content else ""
        
        # Start with a base set of entity types
        entity_types = ["person", "organization", "role"]
        
        # Check for keywords suggesting date relevance
        date_keywords = ["when", "date", "time", "year", "month", "history", "founded", "established", "launched"]
        if any(keyword in title_lower or keyword in content_sample for keyword in date_keywords):
            entity_types.append("date")
        
        # Check for keywords suggesting location relevance
        location_keywords = ["where", "location", "country", "city", "region", "headquartered", "based in"]
        if any(keyword in title_lower or keyword in content_sample for keyword in location_keywords):
            entity_types.append("location")
        
        # Check for other specialized entities based on content
        if "%" in content_sample or any(term in content_sample for term in ["percent", "rate", "growth", "decline"]):
            entity_types.append("percentage")
        
        if "$" in content_sample or any(term in content_sample for term in ["dollar", "price", "cost", "value", "worth"]):
            entity_types.append("monetary_value")
        
        return entity_types

    def _enrich_entity_relationships(self, entities, query, title):
        """
        Enrich entity extraction by establishing relationships between entities.
        
        Args:
            entities (dict): Extracted entities
            query (str): The original query that led to this extraction
            title (str): Title of the webpage
            
        Returns:
            dict: Enriched entity dictionary with relationships
        """
        if not entities or len(entities) < 2:
            return entities
        
        # Create a new dictionary to avoid modifying the original
        enriched = {k: v.copy() if isinstance(v, list) else v for k, v in entities.items()}
        
        # Try to establish role-person-organization relationships
        if "person" in enriched and "organization" in enriched and "role" not in enriched:
            # Check if title or query contains role keywords
            role_keywords = ["ceo", "chief executive", "president", "founder", "director", "chairman"]
            title_and_query = (title + " " + query).lower()
            
            for role in role_keywords:
                if role in title_and_query:
                    # We found a role keyword, try to associate person and organization
                    if len(enriched["person"]) > 0 and len(enriched["organization"]) > 0:
                        # Create a role entry with person and organization
                        person = enriched["person"][0]  # Most important person
                        org = enriched["organization"][0]  # Most important organization
                        role_entry = f"{role.upper()}: {person} @ {org}"
                        
                        if "role" not in enriched:
                            enriched["role"] = []
                        enriched["role"].append(role_entry)
                        break
        
        # Enhanced relationship extraction for existing roles
        if "role" in enriched and "person" in enriched and "organization" in enriched:
            # Check for incomplete role entries (those without person or organization)
            updated_roles = []
            for role_entry in enriched["role"]:
                if ":" not in role_entry or "@" not in role_entry:
                    # Try to enhance this role
                    role_parts = role_entry.lower().split()
                    if len(role_parts) > 0:
                        role_type = role_parts[0]  # e.g., "ceo", "founder"
                        
                        # Find most relevant person and organization
                        person = enriched["person"][0] if enriched["person"] else "Unknown"
                        org = enriched["organization"][0] if enriched["organization"] else "Unknown"
                        
                        # Create proper formatted role
                        updated_role = f"{role_type.upper()}: {person} @ {org}"
                        updated_roles.append(updated_role)
                    else:
                        updated_roles.append(role_entry)
                else:
                    updated_roles.append(role_entry)
            
            enriched["role"] = updated_roles
        
        return enriched
