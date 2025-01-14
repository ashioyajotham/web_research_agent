from typing import Dict, Any, Optional, List, Tuple
import aiohttp
import json
import os
import logging
import asyncio
from aiohttp import ClientTimeout
from .base import BaseTool
from collections import defaultdict
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DynamicSearchContext:
    """Enhanced search context management"""
    def __init__(self):
        self.recent_queries = []
        self.success_patterns = defaultdict(float)
        self.temporal_data = defaultdict(list)
        self.adaptive_timeouts = defaultdict(float)
        self.pattern_weights = defaultdict(float)
        
    def update(self, query: str, success: bool, results: List[Dict], execution_time: float):
        """Update context with search results and execution metrics"""
        pattern = self._extract_pattern(query)
        
        # Update success patterns
        if success:
            self.success_patterns[pattern] += 0.1
            self.adaptive_timeouts[pattern] = max(
                execution_time * 1.5,
                self.adaptive_timeouts[pattern]
            )
        else:
            self.success_patterns[pattern] = max(0, self.success_patterns[pattern] - 0.05)
        
        # Update temporal data
        self.temporal_data[pattern].append({
            'timestamp': datetime.now(),
            'success': success,
            'results': len(results)
        })
        
        # Keep only recent history
        self._prune_old_data()

    def get_search_params(self, query: str) -> Dict[str, Any]:
        """Get optimized search parameters based on history"""
        pattern = self._extract_pattern(query)
        base_params = self._get_base_params()
        
        # Adapt parameters based on success patterns
        if pattern in self.success_patterns:
            confidence = self.success_patterns[pattern]
            base_params.update(self._adapt_params(confidence))
            
        # Add temporal awareness
        if temporal_data := self.temporal_data.get(pattern):
            base_params['timerange'] = self._optimize_timerange(temporal_data)
            
        return base_params

    def _extract_pattern(self, query: str) -> str:
        """Extract search pattern from query"""
        # Basic pattern extraction
        words = query.lower().split()
        return ' '.join(word for word in words if len(word) > 3)[:50]

    def _adapt_params(self, confidence: float) -> Dict[str, Any]:
        """Adapt search parameters based on confidence"""
        return {
            'num': int(10 + (1 - confidence) * 20),
            'detailed': confidence < 0.7,
            'safe': confidence > 0.8
        }

class AdaptiveSearchTool(BaseTool):
    """Enhanced search tool with dynamic adaptation"""
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key not found")
            
        self.base_url = "https://google.serper.dev/search"
        self.timeout = ClientTimeout(total=30)
        self.max_retries = 3
        self.context = DynamicSearchContext()
        
        # Flexible result processors
        self.result_processors = {
            'standard': self._process_standard_results,
            'temporal': self._process_temporal_results,
            'semantic': self._process_semantic_results,
            'metric': self._process_metric_results
        }
        
        # Dynamic search strategies
        self.search_strategies = {
            'broad': self._broad_strategy,
            'focused': self._focused_strategy,
            'deep': self._deep_strategy,
            'temporal': self._temporal_strategy
        }
        
        # Pattern matching system
        self.pattern_matcher = DynamicPattern()

        # Add dynamic result handlers
        self.result_handlers = {
            'semantic': self._handle_semantic_results,
            'temporal': self._handle_temporal_results,
            'metrics': self._handle_metric_results,
            'generic': self._handle_generic_results
        }
        
        # Dynamic search modifiers
        self.search_modifiers = {
            'precision': lambda q: f'"{q}"',
            'broad': lambda q: f'{q} OR similar',
            'recent': lambda q: f'{q} after:2023',
            'comprehensive': lambda q: f'allintitle: {q}'
        }

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search with dynamic adaptation"""
        start_time = time.time()
        try:
            # Determine optimal search approach
            search_type = self._analyze_query_intent(query)
            modifier = self.search_modifiers.get(search_type, lambda x: x)
            modified_query = modifier(query)

            # Get search parameters from context
            params = self.context.get_search_params(query)
            params.update(kwargs)
            
            # Determine search strategy
            strategy = self._determine_strategy(query, params)
            strategy_fn = self.search_strategies.get(strategy, self._broad_strategy)
            
            # Execute search with adaptive retry
            raw_results = await self._execute_with_backoff(modified_query, **params)
            
            # Process results using appropriate handler
            handler = self.result_handlers.get(search_type, self.result_handlers['generic'])
            processed_results = await handler(raw_results)

            # Update context
            execution_time = time.time() - start_time
            self.context.update(query, bool(processed_results), raw_results, execution_time)
            
            return {
                'success': True,
                'results': processed_results,
                'metadata': {
                    'strategy': strategy,
                    'execution_time': execution_time,
                    'result_count': len(processed_results),
                    'search_type': search_type,
                    'modified_query': modified_query
                }
            }
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }

    def _determine_strategy(self, query: str, params: Dict) -> str:
        """Determine optimal search strategy"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['when', 'date', 'year', 'time']):
            return 'temporal'
        elif params.get('detailed', False):
            return 'deep'
        elif any(word in query_lower for word in ['latest', 'recent', 'new']):
            return 'focused'
        return 'broad'

    async def _execute_with_retries(self, query: str, params: Dict) -> List[Dict]:
        """Execute search with adaptive retries"""
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                return await self._make_request(query, **params)
            except Exception as e:
                retry_count += 1
                last_error = e
                
                # Adaptive backoff
                wait_time = min(2 ** retry_count, 10)
                await asyncio.sleep(wait_time)
                
                # Adapt parameters for retry
                params = self._adapt_params_for_retry(params, retry_count)
                
        raise last_error

    async def _execute_with_backoff(self, query: str, **kwargs) -> List[Dict]:
        """Execute search with adaptive backoff"""
        retries = kwargs.get('retries', self.max_retries)
        base_delay = kwargs.get('base_delay', 1)
        
        for attempt in range(retries):
            try:
                return await self._make_request(query, **kwargs)
            except Exception as e:
                if attempt == retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Retry {attempt + 1}/{retries} after {delay}s")
                await asyncio.sleep(delay)

    def _get_result_processor(self, query: str, results: List[Dict]) -> Callable:
        """Get appropriate result processor based on query and results"""
        if self._is_temporal_query(query):
            return self.result_processors['temporal']
        elif self._has_metrics(results):
            return self.result_processors['metric']
        elif len(results) > 10:
            return self.result_processors['semantic']
        return self.result_processors['standard']

    async def _process_standard_results(self, results: List[Dict], params: Dict) -> List[Dict]:
        """Process results with basic filtering and ranking"""
        processed = []
        for result in results:
            if self._is_valid_result(result):
                result['relevance'] = self._calculate_relevance(result, params)
                processed.append(result)
        
        return sorted(processed, key=lambda x: x['relevance'], reverse=True)

    async def _process_temporal_results(self, results: List[Dict], params: Dict) -> List[Dict]:
        """Process results with temporal awareness"""
        temporal_results = []
        for result in results:
            if timestamp := self._extract_timestamp(result):
                result['timestamp'] = timestamp
                temporal_results.append(result)
        
        return sorted(temporal_results, key=lambda x: x['timestamp'], reverse=True)

    async def _handle_semantic_results(self, results: List[Dict]) -> List[Dict]:
        """Handle results requiring semantic understanding"""
        processed = []
        for result in results:
            relevance = self._calculate_semantic_relevance(result)
            if relevance > 0.5:
                result['relevance'] = relevance
                processed.append(result)
        return sorted(processed, key=lambda x: x['relevance'], reverse=True)

    async def _handle_temporal_results(self, results: List[Dict]) -> List[Dict]:
        """Handle results with temporal awareness"""
        temporal_results = []
        for result in results:
            if timestamp := self._extract_timestamp(result):
                result['timestamp'] = timestamp
                temporal_results.append(result)
        
        return sorted(temporal_results, key=lambda x: x['timestamp'], reverse=True)

    async def _handle_metric_results(self, results: List[Dict]) -> List[Dict]:
        """Handle results with metric awareness"""
        metric_results = []
        for result in results:
            if metrics := self._extract_metrics(result):
                result['metrics'] = metrics
                metric_results.append(result)
        
        return sorted(metric_results, key=lambda x: x['metrics'], reverse=True)

    async def _handle_generic_results(self, results: List[Dict]) -> List[Dict]:
        """Handle generic results"""
        return results

    def _calculate_relevance(self, result: Dict, params: Dict) -> float:
        """Calculate result relevance score"""
        score = 0.0
        
        # Title relevance
        if 'title' in result:
            score += len(set(params.get('keywords', [])) & set(result['title'].lower().split()))
            
        # Source quality
        if 'domain' in result:
            score += self._get_domain_score(result['domain'])
            
        # Freshness
        if 'date' in result:
            score += self._calculate_freshness(result['date'])
            
        return min(score / 10, 1.0)

    def _calculate_semantic_relevance(self, result: Dict) -> float:
        """Calculate semantic relevance score dynamically"""
        score = 0.0
        if 'title' in result:
            score += 0.4 * self._text_quality_score(result['title'])
        if 'snippet' in result:
            score += 0.6 * self._text_quality_score(result['snippet'])
        return min(score, 1.0)

    def _text_quality_score(self, text: str) -> float:
        """Calculate text quality score"""
        if not text:
            return 0.0
        
        # Consider multiple factors
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(word_count, 1)
        
        # Normalize scores
        length_score = min(word_count / 20, 1.0)
        complexity_score = min(avg_word_length / 5, 1.0)
        
        return (length_score + complexity_score) / 2

    def _adapt_params_for_retry(self, params: Dict, retry_count: int) -> Dict:
        """Adapt parameters for retry attempts"""
        adapted = params.copy()
        
        # Increase result count
        adapted['num'] = min(params.get('num', 10) + 5 * retry_count, 30)
        
        # Adjust timeouts
        adapted['timeout'] = params.get('timeout', 30) * (1 + 0.5 * retry_count)
        
        return adapted

    def _analyze_query_intent(self, query: str) -> str:
        """Dynamically determine search intent"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['statistics', 'numbers', 'metrics']):
            return 'metrics'
        elif any(term in query_lower for term in ['when', 'date', 'year', 'time']):
            return 'temporal'
        elif len(query.split()) > 4:
            return 'semantic'
        return 'generic'

    # ... Rest of the implementation ...
