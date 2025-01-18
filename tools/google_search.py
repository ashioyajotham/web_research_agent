from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from aiohttp import ClientTimeout
from collections import defaultdict
from .base import BaseTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicSearchContext:
    """Enhanced search context management"""
    def __init__(self):
        self.success_patterns = {}  # pattern -> confidence score
        self.temporal_data = defaultdict(list)  # pattern -> [(timestamp, success)]
        self.execution_times = defaultdict(list)  # pattern -> [times]
        self.max_history = 100
        self.min_confidence = 0.3

    def update(self, query: str, success: bool, results: List[Dict], execution_time: float):
        """Update context with search results"""
        pattern = self._extract_pattern(query)
        
        # Update success patterns
        if pattern in self.success_patterns:
            current = self.success_patterns[pattern]
            self.success_patterns[pattern] = (current * 0.8 + float(success) * 0.2)
        else:
            self.success_patterns[pattern] = float(success)

        # Update temporal data
        self.temporal_data[pattern].append((datetime.now(), success))
        self.execution_times[pattern].append(execution_time)
        
        # Prune old data
        self._prune_old_data()

    def get_search_params(self, query: str) -> Dict[str, Any]:
        """Get optimized search parameters"""
        pattern = self._extract_pattern(query)
        base_params = self._get_base_params()
        
        if pattern in self.success_patterns:
            confidence = self.success_patterns[pattern]
            base_params.update(self._adapt_params(confidence))
            
        if temporal_data := self.temporal_data.get(pattern):
            base_params['timerange'] = self._optimize_timerange(temporal_data)
            
        return base_params

    def _extract_pattern(self, query: str) -> str:
        """Extract search pattern from query"""
        words = query.lower().split()
        return " ".join(word for word in words if len(word) > 3)

    def _get_base_params(self) -> Dict[str, Any]:
        """Get base search parameters"""
        return {
            'num': 10,
            'page': 1,
            'safe': True,
            'type': 'search'
        }

    def _adapt_params(self, confidence: float) -> Dict[str, Any]:
        """Adapt parameters based on confidence"""
        if confidence > 0.8:
            return {'num': 5}
        elif confidence < 0.4:
            return {'num': 15}
        return {}

    def _optimize_timerange(self, temporal_data: List[Tuple[datetime, bool]]) -> str:
        """Optimize time range based on historical success"""
        recent = [s for t, s in temporal_data if t > datetime.now() - timedelta(days=7)]
        if len(recent) >= 3 and sum(recent) / len(recent) > 0.7:
            return 'last_week'
        return 'all'

    def _prune_old_data(self):
        """Remove old data to maintain performance"""
        for pattern in list(self.temporal_data.keys()):
            self.temporal_data[pattern] = self.temporal_data[pattern][-self.max_history:]
            self.execution_times[pattern] = self.execution_times[pattern][-self.max_history:]

class AdaptiveSearchTool(BaseTool):
    """Adaptive Google Search tool with learning capabilities"""
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key not found")
            
        # Add missing attributes
        self.base_url = "https://google.serper.dev/search"
        self.max_retries = 3
        self.timeout = ClientTimeout(total=30)
        self.logger = logging.getLogger(__name__)
        self.context = DynamicSearchContext()

    @staticmethod
    def get_description() -> str:
        """Implement abstract method - tool description"""
        return "Performs adaptive web searches using Google Search API with learning capabilities"

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """Implement abstract method - tool metadata"""
        return {
            "name": "google_search",
            "type": "search",
            "description": "Adaptive Google Search Tool",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "Search query to execute",
                    "required": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                }
            },
            "output": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "results": {"type": "array"},
                    "execution_time": {"type": "number"}
                }
            }
        }

    async def execute(self, query: str = None, **kwargs) -> Dict[str, Any]:
        """Execute search with proper parameter handling"""
        if not query:
            return {
                'success': False,
                'error': 'Query parameter is required',
                'output': {'results': []}
            }

        start_time = time.time()
        try:
            results = await self._execute_with_backoff(query, **kwargs)
            execution_time = time.time() - start_time
            
            # Only return success if we have actual results
            if not results:
                return {
                    'success': False,
                    'error': 'No search results found',
                    'output': {'results': []},
                    'execution_time': execution_time
                }
            
            # Return results in standardized format
            return {
                'success': True,
                'output': {
                    'results': results,
                    'metadata': {
                        'execution_time': execution_time,
                        'result_count': len(results)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': {'results': []}
            }

    async def _execute_search(self, query: str, **kwargs) -> List[Dict]:
        """Execute search with retries"""
        params = self.context.get_search_params(query)
        params.update(kwargs)
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        self.base_url,
                        json={'q': query, **params},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._process_results(data)
                        else:
                            error = await response.text()
                            self.logger.warning(f"Search attempt {attempt + 1} failed: {error}")
                            
            except asyncio.TimeoutError:
                self.logger.warning(f"Search attempt {attempt + 1} timed out")
                continue
                
            except Exception as e:
                self.logger.error(f"Search attempt {attempt + 1} failed: {str(e)}")
                continue
                
            await asyncio.sleep(1 * (attempt + 1))

        raise Exception(f"Search failed after {self.max_retries} attempts")

    async def _execute_with_backoff(self, query: str, **kwargs) -> List[Dict]:
        """Execute search with exponential backoff"""
        max_attempts = kwargs.get('retries', self.max_retries)
        base_delay = kwargs.get('base_delay', 1)
        
        for attempt in range(max_attempts):
            try:
                # Prepare search parameters
                params = self.context.get_search_params(query)
                params.update(kwargs)
                
                headers = {
                    'X-API-KEY': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                # Execute search with proper error handling
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        self.base_url,
                        json={'q': query, **params},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = self._process_results(data)
                            if results:  # Only return if we have actual results
                                return results
                        else:
                            error = await response.text()
                            self.logger.warning(f"Search attempt {attempt + 1}/{max_attempts} failed: {error}")
                            
            except asyncio.TimeoutError:
                self.logger.warning(f"Search attempt {attempt + 1}/{max_attempts} timed out")
            except Exception as e:
                self.logger.error(f"Search attempt {attempt + 1}/{max_attempts} failed: {str(e)}")
            
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                self.logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        return []  # Return empty list if all attempts fail

    def _process_results(self, data: Dict) -> List[Dict]:
        """Process and clean search results"""
        if not data or 'organic' not in data:
            return []
            
        results = []
        for item in data.get('organic', []):
            if 'title' in item and 'link' in item:
                results.append({
                    'title': item['title'],
                    'url': item['link'],
                    'snippet': item.get('snippet', ''),
                    'position': item.get('position', 0)
                })
                
        return results[:10]  # Limit to top 10 results