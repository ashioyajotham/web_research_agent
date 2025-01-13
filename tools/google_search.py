from typing import Dict, Any, Optional, List
import aiohttp
import json
import os
import logging
import asyncio
from aiohttp import TCPConnector, ClientTimeout
from .base import BaseTool

import time
import ssl

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GoogleSearchTool(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key (SERPER_API_KEY) not found in environment variables")
        logger.debug(f"Serper API Key configured: {self.api_key[:5]}...")
        self.base_url = "https://google.serper.dev/search"
        self.timeout = ClientTimeout(
            total=60,  # Increase total timeout
            connect=30,
            sock_connect=30,
            sock_read=30
        )
        self.max_retries = 2  # Reduced retries
        self._session = None
        self._connector = None  # Initialize connector later
        self._cleanup_event = None
        self._cleanup_lock = asyncio.Lock()
        self._initialized = False
        self.ssl_context = None
        self._init_ssl_context()

    def _init_ssl_context(self):
        """Initialize SSL context with proper verification"""
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

    async def _ensure_session(self):
        """Ensure session and connector are initialized with SSL handling"""
        if not self._initialized:
            async with self._cleanup_lock:
                if not self._initialized:  # Double check under lock
                    if not self._connector:
                        self._connector = TCPConnector(
                            limit=5,
                            force_close=True,
                            ssl=self.ssl_context,
                            enable_cleanup_closed=True
                        )
                    
                    if not self._session:
                        self._session = aiohttp.ClientSession(
                            connector=self._connector,
                            timeout=self.timeout,
                            raise_for_status=True,
                            headers={
                                "Connection": "close"  # Prevent keep-alive issues
                            }
                        )
                    self._initialized = True
        return self._session

    async def _cleanup(self):
        """Enhanced cleanup with proper error handling"""
        async with self._cleanup_lock:
            try:
                if self._session and not self._session.closed:
                    await self._session.close()
                    await asyncio.sleep(0.2)  # Give more time for cleanup
                self._session = None

                if self._connector and not self._connector.closed:
                    await self._connector.close()
                    await asyncio.sleep(0.2)
                self._connector = None
                
                self._initialized = False
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

    async def __aenter__(self):
        """Initialize shared session"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup session"""
        await self._cleanup()

    def get_description(self) -> str:
        """Implement abstract method from BaseTool"""
        return "Performs web searches using Serper API and returns structured results"

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search with proper resource management"""
        try:
            return await self._execute_with_retries(query, **kwargs)
        finally:
            # Ensure cleanup happens after execution
            await self._cleanup()

    async def _execute_with_retries(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle retries with proper resource management"""
        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                session = await self._ensure_session()
                return await self._make_request(query, session, **kwargs)
            except asyncio.TimeoutError as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(f"Request timed out, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.exception("Search error")
                return {
                    "success": False,
                    "error": f"Search error: {str(e)}",
                    "results": []
                }

        logger.error(f"Failed after {self.max_retries} retries: {str(last_error)}")
        return {
            "success": False,
            "error": f"Request failed after {self.max_retries} retries",
            "results": []
        }

    async def _process_knowledge_graph(self, kg_data: Dict) -> Dict[str, Any]:
        """Process and structure knowledge graph data"""
        if not kg_data:
            return {}
            
        try:
            structured_data = {
                "title": kg_data.get("title", ""),
                "type": kg_data.get("type", ""),
                "description": kg_data.get("description", ""),
                "attributes": {},
                "links": []
            }

            # Process attributes
            if "attributes" in kg_data:
                structured_data["attributes"] = {
                    k.lower().replace(" ", "_"): v 
                    for k, v in kg_data["attributes"].items()
                }

            # Extract URLs and references
            if "links" in kg_data:
                structured_data["links"] = [
                    {"title": link.get("title", ""),
                     "url": link.get("url", "")}
                    for link in kg_data["links"]
                ]

            # Clean up person names in title
            if kg_data.get('title'):
                title = kg_data['title']
                # Remove common prefixes
                prefixes_to_remove = [
                    "Richest People",
                    "The Richest",
                    "The Person",
                    "Person",
                    "People",
                    "Individual"
                ]
                for prefix in prefixes_to_remove:
                    if title.startswith(prefix):
                        title = title[len(prefix):].strip()
                kg_data['title'] = title

            return structured_data
        except Exception as e:
            logger.error(f"Knowledge graph processing error: {str(e)}")
            return {}

    async def _make_request(self, query: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        """Optimized request method with better error handling"""
        if not query or not isinstance(query, str):
            logger.error(f"Invalid query: {query}")
            return {
                "success": False,
                "error": "Invalid query",
                "results": []
            }

        search_params = {
            "q": query,
            "num": min(kwargs.get('num', 3), 5)  # Limit results more strictly
        }
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Connection": "close"  # Ensure connection closes properly
        }

        try:
            async with session.post(
                self.base_url,
                headers=headers,
                json=search_params,
                ssl=self.ssl_context,
                timeout=self.timeout
            ) as response:
                logger.debug(f"Serper API response status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API error: {error_text}")
                    return {
                        "success": False,
                        "error": f"API returned status {response.status}",
                        "results": []
                    }

                try:
                    data = await response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return {
                        "success": False,
                        "error": "Invalid JSON response",
                        "results": []
                    }

                # Process results with knowledge graph
                results = []
                organic = data.get('organic', [])
                knowledge_graph = await self._process_knowledge_graph(data.get('knowledgeGraph', {}))
                
                for i, item in enumerate(organic):
                    title = item.get('title', '')
                    # Clean up person titles
                    prefixes_to_remove = ["Richest People", "The Richest", "The Person", "Person"]
                    for prefix in prefixes_to_remove:
                        if title.startswith(prefix):
                            title = title[len(prefix):].strip()

                    result = {
                        "title": title,
                        "link": item.get('link', ''),
                        "snippet": self._clean_snippet(item.get('snippet', '')),
                        "date": item.get('date', ''),
                        "position": i + 1,
                        "domain": self._extract_domain(item.get('link', '')),
                        "highlighted_terms": self._extract_highlighted_terms(item.get('snippet', ''))
                    }
                    results.append(result)
                
                logger.debug(f"Successfully processed {len(results)} results")
                return {
                    "success": True,
                    "results": results,
                    "knowledge_graph": knowledge_graph,
                    "related_searches": data.get('relatedSearches', []),
                    "meta": {
                        "total_results": len(results),
                        "has_knowledge_graph": bool(knowledge_graph),
                        "query_time": time.time() - kwargs.get('start_time', time.time())
                    }
                }

        except asyncio.TimeoutError as e:
            logger.error(f"Request timed out: {str(e)}")
            return {
                "success": False,
                "error": "Request timed out",
                "results": []
            }
        except (aiohttp.ClientError, ssl.SSLError) as e:
            logger.error(f"Connection error: {str(e)}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "results": []
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": f"Error: {str(e)}",
                "results": []
            }

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""

    def _extract_highlighted_terms(self, text: str) -> List[str]:
        """Extract highlighted or important terms from text"""
        import re
        # Look for terms in bold tags or with special formatting
        terms = re.findall(r'<b>(.*?)</b>|"([^"]+)"|\*\*(.*?)\*\*', text)
        # Flatten and clean the results
        return list(set(term for match in terms for term in match if term))

    def _clean_snippet(self, snippet: str) -> str:
        """Clean up snippet text"""
        prefixes_to_remove = [
            "Richest People",
            "The Richest",
            "The Person",
            "Person",
            "According to",
            "From",
            "Source:",
            "Wikipedia:",
            "Reuters:"
        ]
        cleaned = snippet
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        return cleaned.strip()

    def __del__(self):
        """Ensure cleanup runs on deletion"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._cleanup())
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._cleanup())
                loop.close()
        except Exception:
            pass
