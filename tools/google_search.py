from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import asyncio
import aiohttp
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
            
        self.base_url = "https://google.serper.dev/search"
        self.timeout = ClientTimeout(total=30)
        self.max_retries = 3
        self.context = DynamicSearchContext()
        self.logger = logger

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
        """Execute search with automatic retries and optimization"""
        if not query:
            return {'success': False, 'error': 'Query required', 'results': []}

        start_time = datetime.now()
        try:
            results = await self._execute_search(query, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            success = bool(results)
            self.context.update(query, success, results, execution_time)
            
            return {
                'success': True,
                'results': results,
                'execution_time': execution_time
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
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

    def _process_results(self, data: Dict) -> List[Dict]:
        """Process and clean search results"""
        if not data or 'organic' not in data:
            return []
            
        results = []
        for item in data['organic']:
            if 'title' in item and 'link' in item:
                results.append({
                    'title': item['title'],
                    'url': item['link'],
                    'snippet': item.get('snippet', ''),
                    'position': item.get('position', 0)
                })
                
        return results[:10]  # Limit to top 10 results