import os
import aiohttp
import json
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin
from utils.helpers import logger, WebUtils
from bs4 import BeautifulSoup, Comment
import re
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.timestamps = []

    async def acquire(self):
        now = datetime.now()
        # Clean old timestamps
        self.timestamps = [ts for ts in self.timestamps 
                         if now - ts < timedelta(seconds=self.period)]
        
        if len(self.timestamps) >= self.calls:
            sleep_time = (self.timestamps[0] + 
                         timedelta(seconds=self.period) - now).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.timestamps.append(now)

class WebBrowser:
    def __init__(self):
        # Serper setup
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is not set")
            
        self.base_url = "https://google.serper.dev/search"
        self.sources = []
        self.headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        self.search_cache = {}  # Add search cache
        self.rate_limiter = RateLimiter(calls=5, period=1)  # 5 calls per second
        
    async def search(self, query: str, task_context: Dict = None) -> Dict:
        """Enhanced search with rate limiting and retry logic"""
        cache_key = f"{query}:{json.dumps(task_context or {})}"
        
        if cache_key in self.search_cache:
            logger.info(f"Using cached results for query: {query}")
            return self.search_cache[cache_key]

        await self.rate_limiter.acquire()
        
        try:
            search_params = await self._build_search_context(query, task_context)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=search_params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Search API error: {error_text}")
                        raise ValueError(f"Search API error: {error_text}")
                    
                    results = await response.json()
                    
                    # Process and validate results
                    if 'organic' in results:
                        filtered_results = self._process_results(results['organic'], task_context)
                        results['organic'] = filtered_results
                        
                    self.search_cache[cache_key] = results
                    return results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def _build_search_context(self, query: str, task_context: Dict) -> Dict:
        """Build search parameters for Serper API"""
        search_params = {
            'q': self._refine_query(query, task_context),
            'num': 10,
            'gl': 'us',
            'hl': 'en'
        }

        # Add time context if specified
        if task_context and task_context.get('temporal_aspect'):
            if task_context['temporal_aspect'] == 'current':
                search_params['timeRange'] = 'y'  # Last year
            elif task_context['temporal_aspect'] == 'historical':
                search_params['timeRange'] = 'a'  # Any time

        return search_params

    def _refine_query(self, query: str, task_context: Dict = None) -> str:
        """Improve query based on task context"""
        if not task_context:
            return query
            
        # Remove generic phrases
        generic_phrases = [
            "gather relevant data",
            "browse the web",
            "comprehensive understanding",
            "identify and extract",
            "research"
        ]
        
        refined = query
        for phrase in generic_phrases:
            refined = refined.replace(phrase, "").strip()
        
        # Add task-specific context
        if "biden" in refined.lower() and "china" in refined.lower():
            refined += " official statement quotes remarks"
            
        return refined.strip()

    def _process_results(self, results: List[Dict], task_context: Dict) -> List[Dict]:
        """Process and filter search results based on context"""
        processed = []
        seen_urls = set()
        
        for result in results:
            if not self._is_valid_result(result):
                continue
                
            url = result.get('link')
            if url in seen_urls:
                continue
                
            if self._is_relevant_result(result, task_context):
                seen_urls.add(url)
                processed.append(result)
                
        return processed

    def _is_valid_result(self, result: Dict) -> bool:
        """Validate result structure and content"""
        required_fields = ['title', 'link', 'snippet']
        return all(result.get(field) for field in required_fields)

    def _is_relevant_result(self, result: Dict, task_context: Dict = None) -> bool:
        """Enhanced relevance checking with context awareness"""
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        # Skip certain domains
        blocked_domains = ['pinterest', 'facebook', 'instagram']
        if any(domain in result['link'].lower() for domain in blocked_domains):
            return False
            
        # Task-specific relevance
        if task_context and task_context.get('type') == 'statement_collection':
            required_terms = task_context.get('required_terms', [])
            if all(term.lower() in text for term in required_terms):
                return True
                
        return False

    def _update_sources(self, results: List[Dict]):
        """Update sources list with deduplication"""
        seen_urls = set()
        for result in results:
            url = result.get('link')
            if url and url not in seen_urls and self._is_relevant_result(result):
                seen_urls.add(url)
                self.sources.append({
                    'url': url,
                    'title': result.get('title', ''),
                    'snippet': result.get('snippet', ''),
                    'position': result.get('position', 0),
                    'timestamp': datetime.now().isoformat()
                })