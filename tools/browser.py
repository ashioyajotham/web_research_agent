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
        """Execute browser tool with enhanced URL handling."""
        url = parameters.get("url")
        
        # Handle fallback to search snippets
        if parameters.get("use_search_snippets") or not url:
            logger.info("Using search snippets instead of web browsing")
            snippet_result = self._extract_from_search_snippets(memory)
            
            # Process snippet content for entities if it has substantial content
            if snippet_result.get("extracted_text") and len(snippet_result["extracted_text"]) > 100:
                try:
                    from agent.comprehension import Comprehension
                    comprehension = Comprehension()
                    
                    entity_types = ["PERSON", "ORG", "DATE", "GPE"]
                    entities = comprehension.extract_entities(snippet_result["extracted_text"], entity_types)
                    
                    # Handle different entity formats
                    if isinstance(entities, list):
                        entities = {"entities": entities}
                    elif not isinstance(entities, dict):
                        entities = {}
                    
                    if entities:
                        memory.add_entities(entities)
                        snippet_result["entities"] = entities
                        
                except Exception as e:
                    logger.error(f"Error extracting entities from snippets: {str(e)}")
            
            return snippet_result
        
        # Validate URL before attempting to browse
        if not url or not self._is_valid_url(url):
            logger.warning(f"Invalid or placeholder URL detected: {url}")
            return self._extract_from_search_snippets(memory)
        
        # Check if we have cached content
        cached_content = memory.get_cached_content(url)
        if (cached_content):
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
                return self._extract_from_search_snippets(memory)
        
        try:
            extract_type = parameters.get("extract_type", "main_content")
            selector = parameters.get("selector", "")
            
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
                "content": processed_content,
                "extracted_text": processed_content
            }
            
            # Enhanced entity extraction - now always extracts entities even if not explicitly requested
            try:
                from agent.comprehension import Comprehension
                comprehension = Comprehension()
                
                # Determine relevant entity types based on title and content
                entity_types = self._determine_relevant_entity_types(result["title"], processed_content)
                
                # Extract entities with focused types
                entities = comprehension.extract_entities(processed_content, entity_types)
                
                # Ensure entities is a dictionary
                if isinstance(entities, list):
                    # Convert list to dictionary format
                    entities = {"entities": entities}
                elif not isinstance(entities, dict):
                    entities = {}
                
                # Try to extract relationships between entities
                enriched_entities = self._enrich_entity_relationships(entities, parameters.get("query", ""), result["title"])
                
                # Add extracted entities to memory
                if enriched_entities:
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
            return self._extract_from_search_snippets(memory)
    
    def _extract_from_search_snippets(self, memory):
        """Extract information from search snippets when URL browsing fails."""
        # Try multiple ways to get search results
        search_results = getattr(memory, 'search_results', [])
        
        # If no search_results attribute, try to find them in recent results
        if not search_results:
            recent_results = getattr(memory, 'results', [])
            for result in reversed(recent_results):
                if isinstance(result, dict) and "search" in str(result).lower():
                    result_data = result.get("output", {})
                    if isinstance(result_data, dict):
                        search_results = result_data.get("results", []) or result_data.get("search_results", [])
                        if search_results:
                            break
        
        if not search_results:
            logger.warning("No search results available for snippet extraction")
            return {
                "error": "No search results available for snippet extraction",
                "content": "Unable to extract information - no search results found",
                "extracted_text": "No search results available"
            }
        
        logger.info(f"Extracting from {len(search_results)} search result snippets")
        
        # Combine snippets from search results
        combined_content = []
        urls = []
        
        for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
            if isinstance(result, dict) and "snippet" in result:
                title = result.get('title', f'Search Result {i+1}')
                snippet = result['snippet']
                link = result.get('link', '')
                
                combined_content.append(f"**{title}**\n{snippet}")
                if link:
                    urls.append(link)
        
        if not combined_content:
            return {
                "error": "No usable content in search snippets",
                "content": "Search results contained no extractable snippets",
                "extracted_text": "No extractable content found"
            }
        
        extracted_text = "\n\n".join(combined_content)
        
        logger.info(f"Successfully extracted {len(extracted_text)} characters from search snippets")
        
        return {
            "content": extracted_text,
            "extracted_text": extracted_text,
            "source": "search_snippets",
            "title": "Combined Search Results",
            "urls": urls,
            "snippet_count": len(combined_content)
        }

    def _is_valid_url(self, url):
        """Validate URL format."""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check for placeholder patterns
        placeholder_patterns = [
            r'\[.*?\]',
            r'\{.*?\}',
            r'<.*?>',
            r'INSERT',
            r'PLACEHOLDER'
        ]
        
        for pattern in placeholder_patterns:  # FIXED - removed the tuple unpacking
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))

    def _fetch_url(self, url):
        """Fetch content from URL with timeout and error handling."""
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                timeout=self.config.get("request_timeout", 30),
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            raise

    def _extract_title(self, content):
        """Extract title from HTML content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)
            # Fallback to first h1 tag
            h1_tag = soup.find('h1')
            if h1_tag:
                return h1_tag.get_text(strip=True)
            return "Unknown Title"
        except Exception as e:
            logger.warning(f"Error extracting title: {str(e)}")
            return "Unknown Title"

    def _extract_main_content(self, content, selector=""):
        """Extract main content from HTML."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # If selector provided, use it
            if selector:
                main_content = soup.select(selector)
                if main_content:
                    text = ' '.join([element.get_text() for element in main_content])
                else:
                    text = soup.get_text()
            else:
                # Try common main content selectors
                main_selectors = [
                    'main', 'article', '.content', '#content', 
                    '.main-content', '#main-content', '.post-content',
                    '.entry-content', '.article-content'
                ]
                
                text = ""
                for sel in main_selectors:
                    elements = soup.select(sel)
                    if elements:
                        text = ' '.join([element.get_text() for element in elements])
                        break
                
                if not text:
                    text = soup.get_text()
            
            # Clean up the text
            text = re.sub(r'\s+', ' ', text).strip()
            return text
            
        except Exception as e:
            logger.error(f"Error extracting main content: {str(e)}")
            return self.html_converter.handle(content)

    def _process_full_page(self, content):
        """Process the full page content."""
        try:
            return self.html_converter.handle(content)
        except Exception as e:
            logger.error(f"Error processing full page: {str(e)}")
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text()

    def _determine_relevant_entity_types(self, title, content):
        """Determine relevant entity types based on content."""
        entity_types = ["PERSON", "ORG"]  # Default types
        
        title_lower = title.lower()
        content_lower = content.lower()[:1000]  # First 1000 chars for efficiency
        
        # Add location entities if geographical content detected
        if any(word in title_lower or word in content_lower for word in 
               ["country", "city", "location", "geneva", "beijing", "washington"]):
            entity_types.append("GPE")
        
        # Add date entities if temporal content detected
        if any(word in title_lower or word in content_lower for word in 
               ["date", "year", "2023", "2024", "january", "february"]):
            entity_types.append("DATE")
        
        return entity_types

    def _enrich_entity_relationships(self, entities, query, title):
        """Enrich entities with relationship information."""
        # Handle different entity formats
        if isinstance(entities, list):
            entity_list = entities
        elif isinstance(entities, dict):
            entity_list = []
            for entity_type, values in entities.items():
                if isinstance(values, list):
                    entity_list.extend(values)
                else:
                    entity_list.append(str(values))
        else:
            return []
        
        enriched = []
        
        for entity in entity_list:
            entity_str = str(entity)
            # Simple relationship detection based on context
            if "president" in title.lower() or "president" in query.lower():
                if any(name in entity_str.lower() for name in ["biden", "xi", "trump"]):
                    enriched.append(f"{entity_str} @ President")
                else:
                    enriched.append(entity_str)
            elif "coo" in title.lower() or "coo" in query.lower():
                if "organization" in entity_str.lower() or "company" in entity_str.lower():
                    enriched.append(f"{entity_str} @ Mediating Organization")
                else:
                    enriched.append(entity_str)
            else:
                enriched.append(entity_str)
        
        # Convert the enriched list back to a dictionary format that the memory system expects
        # This is what was missing - we need to return a dict, not a list
        return {"entities": enriched} if enriched else {}
