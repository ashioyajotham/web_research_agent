import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import time
import google.generativeai as genai
from datetime import datetime
import re
from collections import Counter
from enum import Enum, auto

from .executor import Executor, ExecutionResult
from .utils.prompts import PromptManager
from tools.base import BaseTool
from utils.logger import AgentLogger
from planning.task_planner import TaskPlanner
from memory.memory_store import MemoryStore
from learning.pattern_learner import PatternLearner
from .strategy import ResearchStrategy
from .utils.temporal_processor import TemporalProcessor
from .config import AgentConfig  # Update to use new config location


class AnswerProcessor:
    def __init__(self, config: AgentConfig):
        self.config = config
        # Generic information extraction patterns
        self.info_patterns = {
            'temporal': [
                r'(?:died|passed\s+away|death)\s+(?:on|in|at)?\s+([^,.]+\d{4})',
                r'(?:on|in|at)\s+([^,.]+\d{4})',
                r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})',
            ],
            'entity': [
                r'(?:is|was|were)\s+([^,.]+)',
                r'(?:called|named|known\s+as)\s+([^,.]+)'
            ],
            'location': [
                r'(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'(?:location|place):\s*([^,.]+)'
            ]
        }

    def extract_direct_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generic information extraction based on query type"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        query_lower = query.lower()
        
        # Determine information type needed
        info_type = self._determine_info_type(query_lower)
        
        # Get relevant patterns
        patterns = self.info_patterns.get(info_type, self.info_patterns['entity'])
        
        # Extract information
        best_match = None
        max_confidence = 0.0
        
        for pattern in patterns:
            if matches := re.findall(pattern, all_text, re.IGNORECASE):
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    best_match = candidate.strip()
                    max_confidence = confidence
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": info_type
        }

    def _determine_info_type(self, query: str) -> str:
        """Determine type of information being requested"""
        if re.match(r'^when\b', query):
            return 'temporal'
        elif re.match(r'^where\b', query):
            return 'location'
        elif re.match(r'^(?:who|what)\b', query):
            return 'entity'
        return 'general'

class TaskType(Enum):
    """Dynamic task type system that can learn and adapt"""
    GENERIC = auto()  # Base type for all tasks
    QUERY = auto()    # Question-based tasks
    RESEARCH = auto() # Research-based tasks
    GENERATION = auto() # Content generation tasks
    ANALYSIS = auto()  # Analysis tasks
    CODE = auto()     # Code-related tasks
    DATA = auto()     # Data-related tasks
    
    @classmethod
    def infer_type(cls, task: str, context: Dict = None) -> 'TaskType':
        """Dynamically infer task type based on context and patterns"""
        task_lower = task.lower()
        
        # Query detection
        if re.match(r'^(?:who|what|when|where|why|how)\b', task_lower):
            return cls.QUERY
            
        # Research detection
        if any(word in task_lower for word in ['research', 'find', 'search', 'look up']):
            return cls.RESEARCH
            
        # Generation detection
        if any(word in task_lower for word in ['create', 'generate', 'write', 'compose']):
            return cls.GENERATION
            
        # Analysis detection
        if any(word in task_lower for word in ['analyze', 'analyse', 'examine', 'study']):
            return cls.ANALYSIS
            
        # Code detection
        if any(word in task_lower for word in ['code', 'program', 'implement', 'function']):
            return cls.CODE
            
        # Data detection
        if any(word in task_lower for word in ['data', 'dataset', 'database']):
            return cls.DATA
            
        return cls.GENERIC

class DynamicPattern:
    """A flexible pattern matching system that can learn and adapt to any type of data"""
    def __init__(self):
        self.patterns = {
            'general': {
                'patterns': [],
                'confidence_weights': {},
                'context_rules': {}
            }
        }
        self.learned_patterns = {}
        self.pattern_history = []

    def add_category(self, category: str, base_patterns: List[str] = None,
                    confidence_rules: Dict[str, float] = None):
        """Dynamically add new pattern categories"""
        self.patterns[category] = {
            'patterns': base_patterns or [],
            'confidence_weights': confidence_rules or {},
            'context_rules': {}
        }

    def learn_pattern(self, text: str, success_data: Dict[str, Any], context: Dict[str, Any] = None):
        """Learn new patterns from successful matches"""
        try:
            signature = self._extract_pattern_signature(text, success_data)
            if signature:
                category = self._infer_pattern_category(signature, context)
                confidence = self._calculate_pattern_confidence(signature, success_data)
                
                if category not in self.patterns:
                    self.add_category(category)
                
                pattern = self._generate_flexible_pattern(signature)
                self.patterns[category]['patterns'].append(pattern)
                self.patterns[category]['confidence_weights'][pattern] = confidence
                
                self._update_pattern_history(category, pattern, confidence)
        except Exception as e:
            pass

    def extract(self, text: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract information using all relevant patterns"""
        results = []
        relevant_categories = self._get_relevant_categories(context)
        
        for category in relevant_categories:
            category_patterns = self.patterns[category]['patterns']
            for pattern in category_patterns:
                confidence = self.patterns[category]['confidence_weights'].get(pattern, 0.5)
                
                if matches := self._apply_pattern(pattern, text, context):
                    for match in matches:
                        results.append({
                            'value': match,
                            'pattern': pattern,
                            'category': category,
                            'confidence': confidence * self._context_multiplier(category, context)
                        })
        
        return sorted(results, key=lambda x: x['confidence'], reverse=True)

    def _extract_pattern_signature(self, text: str, success_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract a signature that can be used to generate new patterns"""
        try:
            # Analyze text structure around successful data points
            context_window = 50
            for key, value in success_data.items():
                if isinstance(value, str) and value in text:
                    idx = text.find(value)
                    before = text[max(0, idx - context_window):idx]
                    after = text[idx + len(value):min(len(text), idx + len(value) + context_window)]
                    
                    return {
                        'prefix': before,
                        'value': value,
                        'suffix': after,
                        'type': self._infer_value_type(value)
                    }
        except:
            return None

    def _generate_flexible_pattern(self, signature: Dict[str, Any]) -> str:
        """Generate a flexible regex pattern from a signature"""
        try:
            # Create pattern based on value type and context
            value_type = signature['type']
            prefix = re.escape(signature['prefix'].strip()).replace(r'\ ', r'\s+')
            suffix = re.escape(signature['suffix'].strip()).replace(r'\ ', r'\s+')
            
            if value_type == 'numeric':
                value_pattern = r'(\d+(?:\.\d+)?)'
            elif value_type == 'date':
                value_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4})'
            else:
                value_pattern = r'([^.,;\s]+(?:\s+[^.,;\s]+)*)'
            
            return f"{prefix}\s*{value_pattern}\s*{suffix}"
        except:
            return r'(.+)'

    def _infer_value_type(self, value: str) -> str:
        """Infer the type of value for pattern generation"""
        if re.match(r'^\d+(?:\.\d+)?$', value):
            return 'numeric'
        elif re.match(r'^(?:\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})$', value):
            return 'date'
        return 'text'

    def _get_relevant_categories(self, context: Dict[str, Any]) -> List[str]:
        """Get relevant pattern categories based on context"""
        if not context:
            return list(self.patterns.keys())
            
        relevant = ['general']  # Always include general patterns
        for category in self.patterns:
            if self._is_category_relevant(category, context):
                relevant.append(category)
        return relevant

    def _context_multiplier(self, category: str, context: Dict[str, Any]) -> float:
        """Calculate context-based confidence multiplier"""
        if not context or category == 'general':
            return 1.0
            
        multiplier = 1.0
        category_rules = self.patterns[category]['context_rules']
        
        for key, value in context.items():
            if key in category_rules:
                multiplier *= category_rules[key].get(str(value), 1.0)
                
        return min(max(multiplier, 0.1), 2.0)

    def _apply_pattern(self, pattern: str, text: str, context: Dict[str, Any]) -> List[str]:
        """Apply a pattern with context awareness"""
        try:
            matches = []
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                if self._validate_match(value, context):
                    matches.append(value)
            return matches
        except:
            return []

    def _validate_match(self, value: str, context: Dict[str, Any]) -> bool:
        """Validate a match based on context"""
        if not context:
            return True
            
        # Add validation logic based on context
        return True

class MetricPattern:
    def __init__(self, pattern: str, unit: str, normalization: float = 1.0):
        self.pattern = pattern
        self.unit = unit
        self.normalization = normalization

class MetricExtractor:
    def __init__(self):
        self.patterns = {
            'emissions': [
                MetricPattern(r'(\d+(?:\.\d+)?)\s*(?:million\s+)?(?:metric\s+)?(?:tons?|t)\s*(?:CO2|CO2e|carbon)', 'tCO2e', 1_000_000),
                MetricPattern(r'(\d+(?:\.\d+)?)\s*(?:MT|Mt)\s*(?:CO2|CO2e)', 'tCO2e', 1_000_000)
            ],
            'percentage': [
                MetricPattern(r'(\d+(?:\.\d+)?)\s*(?:percent|pct|%)', '%', 1.0),
                MetricPattern(r'reduced\s+by\s+(\d+(?:\.\d+)?)\s*(?:percent|pct|%)', '%', 1.0)
            ],
            'currency': [
                MetricPattern(r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)', 'USD', 1_000_000_000),
                MetricPattern(r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:million|mn)', 'USD', 1_000_000)
            ]
        }

    def extract_metrics(self, text: str, metric_type: str = None) -> List[Tuple[float, str]]:
        """Extract metrics of specified type from text"""
        results = []
        patterns = self.patterns.get(metric_type, []) if metric_type else [p for patterns in self.patterns.values() for p in patterns]
        
        for pattern in patterns:
            matches = re.finditer(pattern.pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(1)) * pattern.normalization
                    results.append((value, pattern.unit))
                except (ValueError, IndexError):
                    continue
        return results

    def calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return float('inf') if new_value > 0 else 0
        return ((new_value - old_value) / old_value) * 100

class MetricType:
    """Generic metric type handler"""
    def __init__(self, pattern: str, unit: str = '', scale: float = 1.0):
        self.pattern = pattern
        self.unit = unit
        self.scale = scale
        
    def extract(self, text: str) -> Optional[float]:
        if match := re.search(self.pattern, text, re.IGNORECASE):
            try:
                return float(match.group(1)) * self.scale
            except (ValueError, IndexError):
                return None
        return None

class DynamicMetric:
    """A more flexible metric system that can learn and adapt"""
    def __init__(self, name: str, base_patterns: List[str] = None):
        self.name = name
        self.base_patterns = base_patterns or []
        self.learned_patterns = []
        self.confidence_scores = {}
        self.conversion_rates = {}
        self.context_weights = {}

    def add_pattern(self, pattern: str, confidence: float = 0.5):
        """Dynamically add new patterns with confidence scores"""
        if pattern not in self.base_patterns and pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)
            self.confidence_scores[pattern] = confidence

    def learn_from_example(self, text: str, value: float, unit: str = None):
        """Learn new patterns from examples"""
        # Extract context before and after the value
        context = self._extract_context(text, str(value))
        if context:
            pattern = self._generate_pattern(context, value)
            self.add_pattern(pattern, confidence=0.6)

    def _extract_context(self, text: str, value: str, window: int = 10) -> Optional[Dict[str, str]]:
        """Extract context around a value for pattern learning"""
        try:
            idx = text.find(value)
            if idx >= 0:
                start = max(0, idx - window)
                end = min(len(text), idx + len(value) + window)
                return {
                    'prefix': text[start:idx].strip(),
                    'suffix': text[idx + len(value):end].strip(),
                    'value': value
                }
        except Exception:
            pass
        return None

    def _generate_pattern(self, context: Dict[str, str], value: str) -> str:
        """Generate a new regex pattern from context"""
        prefix = re.escape(context['prefix']).replace(r'\ ', r'\s+')
        suffix = re.escape(context['suffix']).replace(r'\ ', r'\s+')
        return f"{prefix}(\d+(?:\.\d+)?){suffix}"

class AdaptiveMetricSystem:
    """A flexible metric system that can adapt to different domains and contexts"""
    def __init__(self):
        self.metrics = {}
        self.conversions = {}
        self.context_rules = {}
        self.learning_rate = 0.1

    def register_metric(self, name: str, patterns: List[str] = None, 
                       conversions: Dict[str, float] = None,
                       context_rules: Dict[str, float] = None):
        """Register a new metric type with flexible configuration"""
        self.metrics[name] = DynamicMetric(name, patterns)
        if conversions:
            self.conversions[name] = conversions
        if context_rules:
            self.context_rules[name] = context_rules

    def learn_conversion(self, from_unit: str, to_unit: str, rate: float):
        """Learn new unit conversions dynamically"""
        if from_unit not in self.conversions:
            self.conversions[from_unit] = {}
        self.conversions[from_unit][to_unit] = rate

    def add_context_rule(self, metric: str, context: str, weight: float):
        """Add context-based rules for metric interpretation"""
        if metric not in self.context_rules:
            self.context_rules[metric] = {}
        self.context_rules[metric][context] = weight

class DynamicCompletionSystem:
    """A flexible system for handling different types of completions"""
    def __init__(self):
        self.completion_patterns = {
            'definition': {
                'patterns': [r'(?:is|are|means|defined as)\s+', r'refers to\s+', r'can be described as\s+'],
                'weight': 1.0
            },
            'explanation': {
                'patterns': [r'happens when\s+', r'occurs due to\s+', r'works by\s+'],
                'weight': 1.0
            },
            'example': {
                'patterns': [r'for example[,:]?\s+', r'such as\s+', r'like\s+'],
                'weight': 0.8
            }
        }
        self.learned_patterns = {}
        self.context_weights = {}
        
    def add_pattern(self, category: str, pattern: str, weight: float = 1.0):
        """Add new completion pattern dynamically"""
        if category not in self.completion_patterns:
            self.completion_patterns[category] = {'patterns': [], 'weight': weight}
        self.completion_patterns[category]['patterns'].append(pattern)

    def learn_from_completion(self, prompt: str, completion: str, success: bool = True):
        """Learn from successful or unsuccessful completions"""
        try:
            # Extract pattern from successful completion
            if success:
                pattern = self._extract_pattern(prompt, completion)
                if pattern:
                    category = self._categorize_pattern(pattern)
                    self.add_pattern(category, pattern, weight=0.7)
                    
        except Exception as e:
            pass

    def _extract_pattern(self, prompt: str, completion: str) -> Optional[str]:
        """Extract a potential pattern from prompt-completion pair"""
        try:
            # Find common structure
            words_before = prompt.split()[-3:]  # Last 3 words
            words_after = completion.split()[:3]  # First 3 words
            
            if words_before and words_after:
                pattern = r'\s+'.join(map(re.escape, words_before)) + r'\s+(.+)'
                return pattern
        except:
            pass
        return None

    def _categorize_pattern(self, pattern: str) -> str:
        """Categorize a new pattern based on similarity to existing ones"""
        for category, info in self.completion_patterns.items():
            for existing_pattern in info['patterns']:
                if self._pattern_similarity(pattern, existing_pattern) > 0.7:
                    return category
        return 'general'

    def _pattern_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between two patterns"""
        # Simple similarity based on common characters
        chars1 = set(pattern1)
        chars2 = set(pattern2)
        return len(chars1 & chars2) / max(len(chars1), len(chars2))

class Agent:
    def __init__(self, tools: Dict[str, BaseTool], config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.tools = tools
        self.memory = MemoryStore(self.config.memory_path)
        self.planner = TaskPlanner(available_tools=list(tools.keys())) if self.config.planning_enabled else None
        self.pattern_learner = PatternLearner() if self.config.pattern_learning_enabled else None
        self.executor = Executor(tools, parallel=self.config.parallel_execution)
        self.logger = AgentLogger()
        self.answer_processor = AnswerProcessor(self.config)
        self.metric_extractor = MetricExtractor()
        self.temporal_processor = TemporalProcessor()
        self.temporal_context: Optional[datetime] = None
        self.context_history: List[Dict[str, Any]] = []
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Replace specific task patterns with more generic ones
        self.task_patterns = {
            TaskType.QUERY: r'^(?:who|what|when|where|why|how)\s+.+',
            TaskType.RESEARCH: r'(?:find|search|research|analyze|investigate)\s+.+',
            TaskType.GENERATION: r'(?:create|generate|write|compose|implement)\s+.+',
            TaskType.ANALYSIS: r'(?:analyze|compare|evaluate|assess)\s+.+',
            TaskType.GENERIC: r'.*'
        }
        
        # Add completion prompts
        self.completion_system = DynamicCompletionSystem()
        
        # Add some initial domain-specific patterns
        self.completion_system.add_pattern(
            'technical',
            r'in (?:programming|computing|software),?\s+(.+)',
            weight=1.2
        )
        self.completion_system.add_pattern(
            'business',
            r'in business terms?,?\s+(.+)',
            weight=1.1
        )
        self.completion_system.add_pattern(
            'scientific',
            r'scientifically(?:\s+speaking)?,?\s+(.+)',
            weight=1.1
        )

        # Replace rigid metric types with flexible pattern matching
        self.metric_patterns = {
            # Generic numerical patterns
            'number': MetricType(r'(\d+(?:\.\d+)?)\s*(?:units?)?'),
            'percentage': MetricType(r'(\d+(?:\.\d+)?)\s*%'),
            'currency': MetricType(r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:billion|million)?'),
            'measurement': MetricType(r'(\d+(?:\.\d+)?)\s*(?:kg|km|m|ft|lbs)')
        }

        # Replace rigid task patterns with dynamic pattern system
        self.pattern_system = DynamicPattern()
        
        # Dynamic metric system
        self.metric_system = AdaptiveMetricSystem()
        
        # Flexible extraction system
        self.extractors = {
            'general': lambda x: x,  # Default extractor
            'learned': {}  # Learned extractors
        }

        # Add dynamic search configuration
        self.search_config = {
            'adaptive_timeout': True,
            'dynamic_retries': True,
            'semantic_processing': True
        }

        # Initialize with some base metrics
        self.metric_system.register_metric(
            'currency',
            patterns=[
                r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:billion|million|k)?',
                r'(\d+(?:\.\d+)?)\s*(?:dollars|euros|pounds)'
            ],
            conversions={
                'USD': {'EUR': 0.85, 'GBP': 0.73},
                'billion': {'million': 1000, 'k': 1000000}
            }
        )

        self.metric_system.register_metric(
            'percentage',
            patterns=[
                r'(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*percent',
                r'(\d+(?:\.\d+)?)\s*pts?'
            ]
        )

        # Add domain-specific metrics that can be extended
        self.metric_system.register_metric(
            'emissions',
            patterns=[
                r'(\d+(?:\.\d+)?)\s*(?:tons?|t)\s*(?:CO2|CO2e)',
                r'(\d+(?:\.\d+)?)\s*(?:MT|kt)'
            ],
            conversions={
                't': {'kt': 0.001, 'MT': 0.000001}
            }
        )

         # Initialize available tools map with actual available tools including content_tools
        self.available_tools = {
            name: tool for name, tool in tools.items() 
            if name in ['google_search', 'web_scraper', 'content_generator']
        }

    async def process_tasks(self, tasks: List[str]) -> List[Dict[str, Any]]:
        """Process tasks with better criteria handling"""
        # Parse tasks to understand relationships
        parsed_tasks = self.task_parser.parse_tasks('\n'.join(tasks))
        results = []
        
        for parsed_task in parsed_tasks:
            if parsed_task.task_type == "criteria_search":
                # Handle criteria-based search task
                result = await self._handle_criteria_search(parsed_task)
            else:
                # Handle regular task
                result = await self.process_task(parsed_task.main_task)
            results.append(result)
            
        return results

    def _detect_entity_type(self, criteria: Dict) -> str:
        """Detect the type of entity being searched for"""
        # Common entity indicators in criteria
        entity_indicators = {
            'company': ['revenue', 'headquarters', 'employees', 'industry'],
            'person': ['age', 'occupation', 'education', 'nationality'],
            'location': ['population', 'area', 'climate', 'coordinates'],
            'product': ['price', 'features', 'manufacturer', 'specifications'],
            'animal': ['species', 'habitat', 'diet', 'lifespan'],
            'plant': ['height', 'native', 'climate', 'soil']
        }
        
        # Count matches for each entity type
        matches = {
            entity: sum(1 for indicator in indicators 
                       if any(indicator.lower() in str(c).lower() 
                             for c in criteria.values()))
            for entity, indicators in entity_indicators.items()
        }
        
        # Return most likely entity type or default to 'item'
        return max(matches.items(), key=lambda x: x[1])[0] if matches else 'item'

    async def process_task(self, task: str) -> Dict[str, Any]:
        """More flexible task processing"""
        try:
            # Dynamic context building
            context = self._build_task_context(task)
            context['task'] = task  # Ensure task is in context
            
            # Determine processing strategy
            strategy = await self._determine_strategy(task, context)
            
            # Execute with chosen strategy
            result = await self._execute_with_strategy(task, strategy, context)
            
            # Learn from execution if enabled
            if self.config.learning_enabled:
                await self._learn_from_execution(task, result, context)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task processing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _determine_strategy(self, task: str, context: Dict) -> Dict[str, Any]:
        """Dynamically determine processing strategy"""
        strategies = []
        
        # Add strategies based on task properties
        if self._requires_information_gathering(task, context):
            strategies.append(self._create_info_gathering_strategy())
        
        if self._requires_analysis(task, context):
            strategies.append(self._create_analysis_strategy())
        
        if self._requires_generation(task, context):
            strategies.append(self._create_generation_strategy())
        
        # Combine strategies or select best one
        return self._combine_strategies(strategies, context)

    async def _execute_with_strategy(self, task: str, strategy: Dict, context: Dict) -> Dict[str, Any]:
        """Execute task using dynamic strategy"""
        steps = strategy.get('steps', [])
        results = []
        
        for step in steps:
            try:
                # Execute step
                step_result = await self._execute_step(step, context)
                results.append(step_result)
                
                # Update context with step results
                if step_result.get('success'):
                    context.update({
                        'last_result': step_result.get('output', {}),
                        'step_type': step.get('action'),
                        'step_tool': step.get('tool')
                    })
                
                # Adapt strategy based on results
                strategy = self._adapt_strategy(strategy, step_result, context)
                
            except Exception as e:
                self.logger.error(f"Strategy step failed: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'action': step.get('action'),
                    'tool': step.get('tool')
                })
                
        return self._combine_results(results, strategy, context)

    async def _execute_step(self, step: Dict[str, str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step with proper parameter handling"""
        try:
            tool_name = step.get('tool')
            tool = self.tools.get(tool_name)
            
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            
            # Prepare parameters
            params = {
                'query': context.get('task', ''),
                'operation': step.get('action'),
                **self._prepare_tool_params(step.get('action'), context)
            }

            # Execute tool
            result = await tool.execute(**params)
            
            # Validate result structure
            if not isinstance(result, dict):
                return {
                    'success': False,
                    'error': 'Invalid tool response format',
                    'action': step.get('action'),
                    'tool': tool_name
                }
            
            # Validate result content
            if result.get('success') and not result.get('results') and not result.get('output'):
                return {
                    'success': False,
                    'error': 'Tool returned success but no data',
                    'action': step.get('action'),
                    'tool': tool_name
                }
                
            return {
                'success': result.get('success', False),
                'output': result.get('output') or result.get('results', {}),
                'error': result.get('error'),
                'action': step.get('action'),
                'tool': tool_name
            }
            
        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': step.get('action', 'unknown'),
                'tool': step.get('tool', 'unknown')
            }

    def _combine_results(self, results: List[Dict[str, Any]], strategy: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Combine results from multiple steps"""
        if not results:
            return {
                'success': False,
                'error': 'No results to combine',
                'output': {'results': []}
            }

        # Only count truly successful steps with data
        successful_steps = sum(1 for r in results 
                             if r.get('success', False) and 
                             (r.get('output') or r.get('results')))
        total_steps = len(results)
        
        # Success requires actual data
        success = successful_steps > 0
        confidence = (successful_steps / total_steps) if total_steps > 0 else 0.0

        # ...rest of method...

    async def _learn_from_execution(self, task: str, result: Dict, context: Dict):
        """Learn from task execution"""
        if result.get('success'):
            # Learn patterns
            self.pattern_system.learn_pattern(task, result.get('output', {}))
            
            # Learn metrics
            if metrics := result.get('metrics'):
                self._update_metric_system(metrics)
            
            # Learn extraction patterns
            if extractions := result.get('extractions'):
                self._learn_extraction_patterns(extractions)

    def _detect_task_type(self, task: str) -> TaskType:
        """More flexible task type detection"""
        # Use ML/pattern matching to determine task type
        context = self._build_task_context(task)
        return TaskType.infer_type(task, context)

    def _build_task_context(self, task: str) -> Dict[str, Any]:
        """Build rich context for task understanding"""
        return {
            'linguistic': self._analyze_linguistics(task),
            'semantic': self._analyze_semantics(task),
            'temporal': self._extract_temporal_context(task),
            'domain': self._infer_domain(task)
        }

    async def _handle_direct_question(self, task: str) -> Dict[str, Any]:
        """Handle any type of direct question"""
        try:
            search_result = await self.tools["google_search"].execute(task)
            if not search_result.get('success'):
                return {
                    "success": False,
                    "error": "Search failed",
                    "output": {"results": []}
                }
            
            results = search_result.get('output', {}).get('results', [])
            processed_answer = self.answer_processor.extract_direct_answer(task, results)
            
            return {
                "success": True,
                "output": {
                    "direct_answer": processed_answer.get('answer'),
                    "type": processed_answer.get('type'),
                    "results": results
                },
                "confidence": processed_answer.get('confidence', 0.5)
            }
            
        except Exception as e:
            self.logger.error(f"Question handling failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _handle_research(self, task: str) -> Dict[str, Any]:
        """Handle research tasks with chronological organization"""
        try:
            research_strategy = ResearchStrategy()
            result = await research_strategy.execute(task, {"tools": self.tools})
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error,
                    "output": {"results": []}
                }
            
            # Format the output chronologically
            timeline = result.output["timeline"]
            formatted_output = {
                "chronological_summary": {
                    "years": [{
                        "year": year,
                        "quarters": [{
                            "quarter": quarter,
                            "events": events
                        } for quarter, events in quarters.items()]
                    } for year, quarters in timeline.items()]
                },
                "major_milestones": result.output["major_milestones"],
                "latest_developments": result.output["latest_developments"],
                "sources": result.output["sources"]
            }
            
            return {
                "success": True,
                "output": formatted_output,
                "confidence": result.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Research handling failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _handle_code_generation(self, task: str) -> Dict[str, Any]:
        """Enhanced code generation handling"""
        try:
            if "code_generator" not in self.tools:
                return {
                    "success": False,
                    "error": "Code generator not available",
                    "output": {"results": []}
                }

            # Force code generation
            result = await self.tools["code_generator"].execute(
                query=task,
                params={
                    "force_generate": True,  # New flag to force code generation
                    "language": "python",
                    "include_examples": True
                }
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Code generation failed",
                    "output": {"results": []}
                }

            return {
                "success": True,
                "output": {
                    "code": result.get("code"),
                    "explanation": result.get("explanation", ""),
                    "examples": result.get("examples", []),
                    "type": "code_implementation"
                },
                "confidence": result.get("confidence", 0.7)
            }

        except Exception as e:
            self.logger.error(f"Code generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _handle_content_creation(self, task: str) -> Dict[str, Any]:
        """Handle content creation tasks"""
        if "content_generator" not in self.tools:
            return {
                "success": False,
                "error": "Content generation tool not available",
                "output": {"message": "Please use a content generation tool for this task"}
            }
            
        # Generate content using appropriate tool
        content = await self.tools["content_generator"].execute(task)
        
        return {
            "success": True,
            "output": {
                "content": content,
                "type": "article"
            }
        }

    def _extract_entities(self, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract named entities and relationships from results"""
        # Add entity extraction logic here
        # ...existing code...

    async def _execute_with_solution(self, task: str, solution: Dict) -> Dict:
        try:
            task_type = self.planner._analyze_task_type(task) if self.planner else "research"
            
            if task_type == "CODE" and solution.get("code"):
                result = await self.tools["code_generator"].execute(
                    query=task,
                    template=solution.get("code")
                )
            else:
                tool_name = solution.get("tool", "google_search")
                if tool_name in self.tools:
                    result = await self.tools[tool_name].execute(
                        query=task,
                        **solution.get("params", {})
                    )
                else:
                    result = await self._execute_basic_task(task)
            
            return {
                "success": bool(result.get("success", False)),
                "output": result.get("output", {}),
                "confidence": float(result.get("confidence", 0.0)),
                "task": task
            }
            
        except Exception as e:
            self.logger.error(f"Solution adaptation failed: {str(e)}")
            return {
                "success": False,
                "output": {"results": []},
                "error": str(e),
                "task": task
            }

    async def _execute_basic_task(self, task: str) -> Dict[str, Any]:
        try:
            task_lower = task.lower()
            if any(kw in task_lower for kw in ['implement', 'code', 'algorithm', 'program']):
                task_type = "CODE"
            elif any(kw in task_lower for kw in ['dataset', 'data', 'extract', 'analyze']):
                task_type = "DATA"
            else:
                task_type = "RESEARCH"
            
            if task_type == "CODE":
                result = await self.tools["code_generator"].execute(query=task)
                if result.get("success"):
                    return {
                        "success": True,
                        "output": {
                            "code": result.get("code"),
                            "results": [result]
                        },
                        "confidence": 0.8,
                        "execution_time": 0.0,
                        "task": task
                    }
            elif task_type == "DATA":
                result = await self.tools["dataset"].execute(query=task)
                if result.get("success"):
                    return {
                        "success": True,
                        "output": {
                            "data": result.get("data"),
                            "results": [result]
                        },
                        "confidence": 0.7,
                        "execution_time": 0.0,
                        "task": task
                    }
            else:
                search_result = await self.tools["google_search"].execute(query=task)
                if search_result.get("success") and search_result.get("results"):
                    for item in search_result["results"][:3]:
                        try:
                            content = await self.tools["web_scraper"].execute(url=item["link"])
                            if content and isinstance(content, str):
                                item["content"] = content[:1000]
                        except:
                            continue
                    return {
                        "success": True,
                        "output": search_result,
                        "confidence": 0.7,
                        "execution_time": 0.0,
                        "task": task
                    }

            return {
                "success": False,
                "output": {"results": []},
                "confidence": 0.0,
                "error": "Task execution failed",
                "task": task
            }
                
        except Exception as e:
            self.logger.error(f"Basic task execution failed: {str(e)}")
            return {
                "success": False,
                "output": {"results": []},
                "error": str(e),
                "task": task
            }

    def _calculate_effectiveness(self, result: Dict) -> float:
        try:
            effectiveness = 0.0
            
            if result.get("success"):
                effectiveness += 0.5
                
                output = result.get("output", {})
                if isinstance(output, dict):
                    if "results" in output and output["results"]:
                        effectiveness += min(len(output["results"]) * 0.1, 0.3)
                    if "code" in output:
                        effectiveness += 0.2
                    if "data" in output:
                        effectiveness += 0.2
                
                effectiveness *= max(0.1, min(1.0, result.get("confidence", 0.0)))
            
            return min(1.0, effectiveness)
            
        except Exception as e:
            self.logger.error(f"Effectiveness calculation failed: {str(e)}")
            return 0.0

    async def _safe_execute_task(self, task: str) -> Dict[str, Any]:
        max_retries = 3
        retry_count = 0
        
        while (retry_count < max_retries):
            try:
                result = await self._execute_task(task)
                return result
            except asyncio.CancelledError:
                await self._cleanup_cancelled_task()
                raise
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                self.logger.log('WARNING', f"Retry {retry_count}/{max_retries} due to: {str(e)}", "Retry")
                await asyncio.sleep(1 * retry_count)

    async def _cleanup_cancelled_task(self):
        try:
            for task in asyncio.all_tasks():
                if task != asyncio.current_task():
                    task.cancel()
            await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()},
                               return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}", "Cleanup")

    def get_partial_results(self) -> Dict[str, Any]:
        return {}

    async def _execute_task(self, task: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Apply dynamic search configuration for search tasks
            if self._is_search_task(task):
                search_params = self._prepare_search_params(task)
                result = await self.tools["google_search"].execute(
                    query=task,
                    **search_params
                )
                
                if result.get('success'):
                    # Process search results based on task context
                    processed_result = await self._process_search_results(
                        task, 
                        result['results'],
                        result.get('metadata', {})
                    )
                    return self._finalize_result(task, processed_result, time.time() - start_time)

            # Handle other task types
            return await self._execute_basic_task(task)

        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': {'results': []},
                'execution_time': time.time() - start_time
            }

    def _is_search_task(self, task: str) -> bool:
        """Determine if task requires search capabilities"""
        task_lower = task.lower()
        search_indicators = ['find', 'search', 'look up', 'research', 'gather']
        return any(indicator in task_lower for indicator in search_indicators)

    def _prepare_search_params(self, task: str) -> Dict[str, Any]:
        """Prepare dynamic search parameters"""
        params = {
            'timeout': 30,
            'retries': 3,
            'detailed': False
        }
        
        if self.search_config['adaptive_timeout']:
            params['timeout'] = self._calculate_adaptive_timeout(task)
            
        if self.search_config['dynamic_retries']:
            params['retries'] = self._calculate_retry_count(task)
            
        if self.search_config['semantic_processing']:
            params['semantic_analysis'] = True
            
        return params

    def _calculate_adaptive_timeout(self, task: str) -> int:
        """Calculate adaptive timeout based on task complexity"""
        base_timeout = 30
        words = len(task.split())
        return min(base_timeout * (1 + words / 10), 120)

    def _calculate_retry_count(self, task: str) -> int:
        """Calculate retry count based on task importance"""
        base_retries = 3
        if any(term in task.lower() for term in ['important', 'critical', 'urgent']):
            return base_retries + 2
        return base_retries

    async def _process_search_results(self, task: str, results: List[Dict], metadata: Dict) -> Dict[str, Any]:
        """Process search results based on task context"""
        if metadata.get('search_type') == 'semantic':
            return await self._process_semantic_results(task, results)
        elif metadata.get('search_type') == 'temporal':
            return await self._process_temporal_results(task, results)
        return await self._process_generic_results(task, results)

    def _format_execution_result(self, exec_result: ExecutionResult, task: str, start_time: float) -> Dict[str, Any]:
        """Format execution result with proper error handling"""
        try:
            if isinstance(exec_result, ExecutionResult):
                return {
                    'success': bool(exec_result.success),
                    'output': exec_result.output or {'results': []},
                    'confidence': float(exec_result.confidence),
                    'steps_taken': len(exec_result.steps) if exec_result.steps else 0,
                    'execution_time': time.time() - start_time,
                    'task': task,
                    'execution_metrics': exec_result.execution_metrics or {}
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid execution result type',
                    'output': {'results': []},
                    'confidence': 0.0,
                    'execution_time': time.time() - start_time,
                    'task': task
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output': {'results': []},
                'confidence': 0.0,
                'execution_time': time.time() - start_time,
                'task': task
            }

    def _finalize_result(self, task: str, result: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Finalize execution result with proper formatting"""
        if not isinstance(result, dict):
            return {
                'success': False,
                'error': 'Invalid result format',
                'output': {'results': []},
                'confidence': 0.0,
                'execution_time': execution_time,
                'task': task
            }

        # Ensure required fields exist
        output = result.get('output', {'results': []})
        if not isinstance(output, dict):
            output = {'results': [output]}

        return {
            'success': bool(result.get('success', False)),
            'output': output,
            'confidence': float(result.get('confidence', 0.0)),
            'execution_time': execution_time,
            'task': task,
            'error': result.get('error'),
            'metrics': result.get('metrics', {})
        }

    async def _handle_completion(self, task: str) -> Dict[str, Any]:
        """Handle completions more flexibly using dynamic patterns"""
        try:
            # Analyze task context
            context = self._analyze_completion_context(task)
            
            # Get relevant patterns based on context
            patterns = self._get_relevant_completion_patterns(context)
            
            # Generate multiple completion candidates
            candidates = []
            for pattern_info in patterns:
                try:
                    # Prepare contextual prompt
                    prompt = self._prepare_completion_prompt(task, pattern_info['pattern'])
                    
                    # Generate completion
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        prompt
                    )
                    
                    if response and response.text:
                        candidates.append({
                            'completion': response.text.strip(),
                            'confidence': pattern_info['weight'],
                            'pattern': pattern_info['pattern']
                        })
                except:
                    continue

            # Select best completion
            if candidates:
                best_candidate = max(candidates, key=lambda x: x['confidence'])
                
                # Learn from successful completion
                self.completion_system.learn_from_completion(
                    task, 
                    best_candidate['completion']
                )
                
                return {
                    "success": True,
                    "output": {
                        "completion": best_candidate['completion'],
                        "type": "completion",
                        "pattern_used": best_candidate['pattern']
                    },
                    "confidence": best_candidate['confidence']
                }

            return {
                "success": False,
                "error": "Could not generate suitable completion",
                "output": {"results": []}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    def _analyze_completion_context(self, task: str) -> Dict[str, Any]:
        """Analyze the context of a completion task"""
        return {
            'domain': self._detect_domain(task),
            'formality': self._detect_formality(task),
            'complexity': self._detect_complexity(task)
        }

    def _get_relevant_completion_patterns(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get completion patterns relevant to the context"""
        patterns = []
        
        for category, info in self.completion_system.completion_patterns.items():
            # Adjust weight based on context
            weight = info['weight']
            if context['domain'] in category:
                weight *= 1.2
            if context['formality'] == 'formal' and 'technical' in category:
                weight *= 1.1
                
            for pattern in info['patterns']:
                patterns.append({
                    'pattern': pattern,
                    'weight': weight,
                    'category': category
                })
                
        return sorted(patterns, key=lambda x: x['weight'], reverse=True)

    def _prepare_completion_prompt(self, task: str, pattern: str) -> str:
        """Prepare a context-aware completion prompt"""
        # Add relevant context and format the prompt
        return f"Complete this statement naturally and informatively: {task}\n\nProvide a completion that {pattern}"

    async def _handle_numerical_comparison(self, task: str) -> Dict[str, Any]:
        """Handle tasks involving numerical comparisons with flexible metric detection"""
        try:
            # Extract time periods more flexibly
            time_refs = self._extract_time_references(task)
            if len(time_refs) < 2:
                return {"success": False, "error": "Couldn't identify comparison periods"}

            # Detect metric type from context
            metric_info = self._detect_metric_type(task)
            if not metric_info:
                return {"success": False, "error": "Couldn't determine what to measure"}

            # Gather measurements for each time period
            measurements = {}
            for period in time_refs:
                search_query = f"{metric_info['context']} {period}"
                result = await self.tools["google_search"].execute(search_query)
                
                if result.get('success'):
                    for item in result.get('results', []):
                        try:
                            content = await self.tools["web_scraper"].execute(url=item['link'])
                            if content:
                                if value := metric_info['pattern'].extract(content):
                                    measurements[period] = value
                                    break
                        except Exception as e:
                            self.logger.warning(f"Extraction failed for {period}: {e}")
                            continue

            # Compare results
            if len(measurements) == 2:
                return self._format_comparison_result(measurements, metric_info)

            return {
                "success": False,
                "error": "Insufficient data for comparison",
                "output": {"partial_data": measurements}
            }

        except Exception as e:
            self.logger.error(f"Numerical comparison failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    def _detect_metric_type(self, task: str) -> Optional[Dict[str, Any]]:
        """Detect what kind of metric we're looking for based on context"""
        task_lower = task.lower()
        
        # Extract measurement context
        measurement_indicators = {
            'amount': r'(?:amount|quantity|level|value)\s+of\s+([^,.]+)',
            'measure': r'(?:measure|track|monitor)\s+([^,.]+)',
            'compare': r'(?:compare|difference\s+in)\s+([^,.]+)'
        }
        
        for indicator_type, pattern in measurement_indicators.items():
            if match := re.search(pattern, task_lower):
                context = match.group(1).strip()
                # Find most appropriate metric pattern
                metric_pattern = self._find_metric_pattern(context)
                return {
                    'type': indicator_type,
                    'context': context,
                    'pattern': metric_pattern
                }
        
        # Fallback to generic number if context is unclear
        return {
            'type': 'general',
            'context': task_lower,
            'pattern': self.metric_patterns['number']
        }

    def _find_metric_pattern(self, context: str) -> MetricType:
        """Find the most appropriate metric pattern based on context"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['price', 'cost', 'revenue', 'sales', '$', '€', '£']):
            return self.metric_patterns['currency']
        elif any(word in context_lower for word in ['percent', 'ratio', 'rate']):
            return self.metric_patterns['percentage']
        elif any(word in context_lower for word in ['weight', 'height', 'length', 'distance']):
            return self.metric_patterns['measurement']
        
        return self.metric_patterns['number']

    def _extract_time_references(self, task: str) -> List[str]:
        """Extract time references more flexibly"""
        # Look for various time formats
        time_patterns = [
            r'\b\d{4}\b',  # Years
            r'\b(?:Q[1-4]|Quarter\s+[1-4])\s+\d{4}\b',  # Quarters
            r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)|Dec(?:ember)?)\s+\d{4}\b'  # Months
        ]
        
        references = []
        for pattern in time_patterns:
            references.extend(re.findall(pattern, task, re.IGNORECASE))
            
        return sorted(set(references))  # Remove duplicates and sort

    def _format_comparison_result(self, measurements: Dict[str, float], metric_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format comparison results with context"""
        periods = sorted(measurements.keys())
        old_value = measurements[periods[0]]
        new_value = measurements[periods[1]]
        change = ((new_value - old_value) / old_value) * 100 if old_value != 0 else float('inf')
        
        return {
            "success": True,
            "output": {
                "comparison": {
                    "earlier_period": periods[0],
                    "later_period": periods[1],
                    "earlier_value": old_value,
                    "later_value": new_value,
                    "percent_change": round(change, 2),
                    "measure_type": metric_info['type'],
                    "context": metric_info['context']
                }
            },
            "confidence": 0.8
        }

    def update_temporal_context(self, timestamp: datetime) -> None:
        """Update the temporal context with a new timestamp"""
        self.temporal_context = timestamp
        self._update_context_history('temporal_update', {
            'timestamp': timestamp,
            'type': 'temporal'
        })

    def get_temporal_context(self) -> Optional[datetime]:
        """Retrieve current temporal context"""
        return self.temporal_context

    def _update_context_history(self, action: str, data: Dict[str, Any]) -> None:
        """Update the context history with new actions"""
        self.context_history.append({
            'action': action,
            'data': data,
            'timestamp': datetime.now()
        })

    def _analyze_linguistics(self, task: str) -> Dict[str, Any]:
        """Analyze linguistic features of the task"""
        return {
            'length': len(task.split()),
            'question_type': self._detect_question_type(task),
            'tense': self._detect_tense(task),
            'keywords': self._extract_keywords(task)
        }

    def _detect_question_type(self, text: str) -> str:
        """Detect type of question if present"""
        text_lower = text.lower()
        if text_lower.startswith('who'):
            return 'person'
        elif text_lower.startswith('what'):
            return 'definition'
        elif text_lower.startswith('when'):
            return 'temporal'
        elif text_lower.startswith('where'):
            return 'location'
        elif text_lower.startswith('why'):
            return 'reason'
        elif text_lower.startswith('how'):
            return 'method'
        return 'statement'

    def _detect_tense(self, text: str) -> str:
        """Basic tense detection"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['will', 'going to']):
            return 'future'
        elif any(word in text_lower for word in ['did', 'was', 'were']):
            return 'past'
        return 'present'

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to'}
        return [word.lower() for word in text.split() if word.lower() not in stop_words]

    def _analyze_semantics(self, task: str) -> Dict[str, Any]:
        """Analyze semantic features of the task"""
        try:
            # Extract semantic features
            features = {
                'domain': self._infer_domain(task),
                'intent': self._infer_intent(task),
                'entities': self._extract_semantic_entities(task),
                'requirements': self._extract_requirements(task)
            }
            return features
        except Exception as e:
            self.logger.warning(f"Semantic analysis failed: {str(e)}")
            return {
                'domain': 'unknown',
                'intent': 'unknown',
                'entities': [],
                'requirements': []
            }

    def _infer_domain(self, task: str) -> str:
        """Infer the domain of the task"""
        task_lower = task.lower()
        domains = {
            'technical': ['code', 'programming', 'software', 'algorithm', 'data'],
            'business': ['revenue', 'company', 'market', 'sales', 'profit'],
            'scientific': ['research', 'study', 'analysis', 'experiment'],
            'environmental': ['emissions', 'climate', 'sustainability'],
            'general': ['find', 'search', 'list', 'compile', 'identify']
        }
        
        scores = {domain: sum(1 for kw in keywords if kw in task_lower)
                 for domain, keywords in domains.items()}
        return max(scores.items(), key=lambda x: x[1])[0]

    def _infer_intent(self, task: str) -> str:
        """Infer the intent of the task"""
        task_lower = task.lower()
        
        if any(w in task_lower for w in ['find', 'search', 'locate']):
            return 'search'
        elif any(w in task_lower for w in ['analyze', 'examine', 'study']):
            return 'analysis'
        elif any(w in task_lower for w in ['compare', 'contrast', 'versus']):
            return 'comparison'
        elif any(w in task_lower for w in ['list', 'enumerate', 'compile']):
            return 'compilation'
        return 'general'

    def _extract_semantic_entities(self, task: str) -> List[str]:
        """Extract semantic entities from task"""
        # Look for proper nouns and key entities
        entities = []
        words = task.split()
        for i, word in enumerate(words):
            if (word[0].isupper() and (i == 0 or not words[i-1].endswith('.'))) or \
               any(char.isdigit() for char in word):
                entities.append(word)
        return entities

    def _extract_requirements(self, task: str) -> List[str]:
        """Extract specific requirements from task"""
        requirements = []
        requirement_indicators = [
            'must', 'should', 'need to', 'required to', 'has to',
            'criteria:', 'requirements:', 'conditions:'
        ]
        
        sentences = task.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in requirement_indicators):
                requirements.append(sentence.strip())
                
        return requirements

    def _extract_temporal_context(self, task: str) -> Dict[str, Any]:
        """Extract temporal context from task text"""
        try:
            # Use existing temporal_processor to extract dates and periods
            temporal_info = {
                'dates': [],
                'periods': [],
                'relative_refs': [],
                'context': None
            }

            # Extract explicit dates using temporal_processor
            if hasattr(self.temporal_processor, 'extract_dates'):
                dates = self.temporal_processor.extract_dates(task)
                if dates:
                    temporal_info['dates'] = dates

            # Extract time periods (e.g., "2021 to 2023", "last 3 years")
            period_patterns = [
                r'(\d{4})\s*(?:to|through|until|-)?\s*(\d{4})',
                r'(?:last|past|previous)\s+(\d+)\s+(?:year|month|day)s?',
                r'(?:since|from)\s+(\d{4})',
                r'(?:until|through|to)\s+(\d{4})'
            ]

            for pattern in period_patterns:
                if matches := re.finditer(pattern, task, re.IGNORECASE):
                    temporal_info['periods'].extend(m.group() for m in matches)

            # Extract relative temporal references
            relative_patterns = [
                r'(?:current|this)\s+(?:year|month|quarter)',
                r'(?:next|previous|last)\s+(?:year|month|quarter)',
                r'(?:recently|lately|nowadays)',
                r'(?:earlier|later|before|after)'
            ]

            for pattern in relative_patterns:
                if matches := re.finditer(pattern, task, re.IGNORECASE):
                    temporal_info['relative_refs'].extend(m.group() for m in matches)

            # Set primary temporal context if available
            if temporal_info['dates']:
                temporal_info['context'] = temporal_info['dates'][0]
            elif temporal_info['periods']:
                temporal_info['context'] = temporal_info['periods'][0]
            elif temporal_info['relative_refs']:
                temporal_info['context'] = temporal_info['relative_refs'][0]

            return temporal_info

        except Exception as e:
            self.logger.warning(f"Temporal context extraction failed: {str(e)}")
            return {
                'dates': [],
                'periods': [],
                'relative_refs': [],
                'context': None
            }

    def _requires_information_gathering(self, task: str, context: Dict[str, Any]) -> bool:
        """Determine if task requires gathering information"""
        task_lower = task.lower()
        
        # Check semantic context
        semantic = context.get('semantic', {})
        if semantic.get('intent') in ['search', 'research', 'compilation']:
            return True
            
        # Check explicit indicators
        info_gathering_indicators = [
            'find', 'search', 'gather', 'collect', 'compile',
            'locate', 'identify', 'list', 'research',
            'what is', 'who is', 'where is', 'when'
        ]
        
        return any(indicator in task_lower for indicator in info_gathering_indicators)

    def _requires_analysis(self, task: str, context: Dict[str, Any]) -> bool:
        """Determine if task requires analysis"""
        task_lower = task.lower()
        
        # Check semantic context
        semantic = context.get('semantic', {})
        if semantic.get('intent') in ['analysis', 'comparison']:
            return True
            
        # Check explicit indicators
        analysis_indicators = [
            'analyze', 'analyse', 'examine', 'study',
            'compare', 'evaluate', 'assess', 'investigate',
            'explain', 'understand', 'determine'
        ]
        
        return any(indicator in task_lower for indicator in analysis_indicators)

    def _requires_generation(self, task: str, context: Dict[str, Any]) -> bool:
        """Determine if task requires content generation"""
        task_lower = task.lower()
        
        # Check semantic context
        semantic = context.get('semantic', {})
        if semantic.get('intent') in ['generation', 'creation']:
            return True
            
        # Check explicit indicators
        generation_indicators = [
            'create', 'generate', 'write', 'compose',
            'produce', 'make', 'develop', 'implement',
            'build', 'design', 'construct'
        ]
        
        return any(indicator in task_lower for indicator in generation_indicators)

    def _create_info_gathering_strategy(self) -> Dict[str, Any]:
        """Create strategy for information gathering tasks using available tools"""
        steps = []
        
        # Only add steps for tools we actually have
        if 'google_search' in self.available_tools:
            steps.append({'action': 'search', 'tool': 'google_search'})
        if 'web_scraper' in self.available_tools:
            steps.append({'action': 'extract', 'tool': 'web_scraper'})
            
        return {
            'type': 'information_gathering',
            'steps': steps,
            'fallback': {'action': 'search', 'tool': 'google_search'} if 'google_search' in self.available_tools else None
        }

    def _create_analysis_strategy(self) -> Dict[str, Any]:
        """Create strategy for analysis tasks"""
        return {
            'type': 'analysis',
            'steps': [
                {'action': 'gather', 'tool': 'google_search'},
                {'action': 'analyze', 'tool': 'content_generator', 'params': {'operation': 'analyze'}},
                {'action': 'summarize', 'tool': 'content_generator', 'params': {'operation': 'summarize'}}
            ],
            'fallback': {'action': 'analyze', 'tool': 'content_generator', 'params': {'operation': 'analyze'}}
        }

    def _create_generation_strategy(self) -> Dict[str, Any]:
        """Create strategy for generation tasks"""
        return {
            'type': 'generation',
            'steps': [
                {'action': 'research', 'tool': 'google_search'},
                {'action': 'generate', 'tool': 'content_generator'},
                {'action': 'refine', 'tool': 'content_refiner'}
            ],
            'fallback': {'action': 'generate', 'tool': 'content_generator'}
        }

    def _combine_strategies(self, strategies: List[Dict[str, Any]], context: Dict) -> Dict[str, Any]:
        """Combine multiple strategies into a single coherent strategy"""
        if not strategies:
            return self._create_info_gathering_strategy()
            
        if len(strategies) == 1:
            return strategies[0]
            
        # Combine steps from all strategies while removing duplicates
        combined_steps = []
        seen_actions = set()
        
        for strategy in strategies:
            for step in strategy.get('steps', []):
                action_key = f"{step['action']}_{step['tool']}"
                if action_key not in seen_actions:
                    combined_steps.append(step)
                    seen_actions.add(action_key)
        
        # Use the type of the highest priority strategy
        primary_type = strategies[0]['type']
        
        return {
            'type': primary_type,
            'steps': combined_steps,
            'fallback': strategies[0].get('fallback')
        }

    def _prepare_tool_params(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for tool execution based on action and context"""
        params = {}
        
        # Extract task/query from context
        task = context.get('task', '')
        
        # Default parameters based on action type
        if action == 'search':
            params['query'] = task
            params.update(self._prepare_search_params(task))
            
        elif action == 'extract' or action == 'scrape':
            params['url'] = context.get('url', '')
            params['max_length'] = 10000  # Reasonable default
            
        elif action == 'analyze':
            params['text'] = context.get('content', '')
            params['detailed'] = True
            
        elif action == 'filter':
            params['content'] = context.get('content', '')
            params['criteria'] = context.get('criteria', {})
            
        elif action == 'generate':
            params['prompt'] = task
            params['max_length'] = 2000
            
        elif action == 'summarize':
            params['text'] = context.get('content', '')
            params['max_length'] = 500
            
        return params

    async def _execute_step(self, step: Dict[str, str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step with proper parameter handling"""
        try:
            tool_name = step.get('tool')
            tool = self.tools.get(tool_name)
            
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            
            # Prepare parameters with proper fallbacks
            params = {
                'query': context.get('task', ''),
                'operation': step.get('action'),
                **self._prepare_tool_params(step.get('action'), context)
            }

            # Handle special cases
            if tool_name == 'web_scraper' and 'url' in context:
                params['url'] = context['url']
            
            # Execute tool
            result = await tool.execute(**params)
            
            if isinstance(result, dict):
                return {
                    'success': result.get('success', False),
                    'output': result.get('output', {}),
                    'error': result.get('error'),
                    'action': step.get('action'),
                    'tool': tool_name
                }
            
            return {
                'success': False,
                'error': 'Invalid tool response',
                'action': step.get('action'),
                'tool': tool_name
            }
            
        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': step.get('action', 'unknown'),
                'tool': step.get('tool', 'unknown')
            }

    def _combine_results(self, results: List[Dict[str, Any]], strategy: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Combine results from multiple steps into a final result"""
        if not results:
            return {
                'success': False,
                'error': 'No results to combine',
                'output': {'results': []}
            }
            
        # Count successful steps
        successful_steps = sum(1 for r in results if r.get('success', False))
        total_steps = len(results)
        
        # Calculate overall success and confidence
        success = successful_steps > 0
        confidence = (successful_steps / total_steps) if total_steps > 0 else 0.0
        
        # Combine outputs based on strategy type
        strategy_type = strategy.get('type', 'information_gathering')
        combined_output = self._combine_outputs_by_type(results, strategy_type, context)
        
        return {
            'success': success,
            'output': combined_output,
            'confidence': confidence,
            'steps_completed': successful_steps,
            'total_steps': total_steps
        }

    def _combine_outputs_by_type(self, results: List[Dict[str, Any]], strategy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Combine outputs based on strategy type"""
        if strategy_type == 'information_gathering':
            return self._combine_information_outputs(results)
        elif strategy_type == 'analysis':
            return self._combine_analysis_outputs(results)
        elif strategy_type == 'generation':
            return self._combine_generation_outputs(results)
        else:
            return {'results': [r.get('output', {}) for r in results if r.get('success', False)]}

    def _combine_information_outputs(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine information gathering outputs"""
        combined_results = []
        extracted_data = {}
        
        for result in results:
            if not result.get('success', False):
                continue
                
            output = result.get('output', {})
            if 'results' in output:
                combined_results.extend(output['results'])
            if 'extracted_data' in output:
                extracted_data.update(output['extracted_data'])
        
        return {
            'results': combined_results[:10],  # Limit to top 10 most relevant results
            'extracted_data': extracted_data
        }

    def _combine_analysis_outputs(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine analysis outputs"""
        analyses = []
        insights = []
        
        for result in results:
            if not result.get('success', False):
                continue
                
            output = result.get('output', {})
            if 'analysis' in output:
                analyses.append(output['analysis'])
            if 'insights' in output:
                insights.extend(output['insights'])
        
        return {
            'analyses': analyses,
            'insights': insights,
            'summary': self._generate_analysis_summary(analyses) if analyses else None
        }

    def _combine_generation_outputs(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine generation outputs"""
        generated_content = []
        metadata = {}
        
        for result in results:
            if not result.get('success', False):
                continue
                
            output = result.get('output', {})
            if 'content' in output:
                generated_content.append(output['content'])
            if 'metadata' in output:
                metadata.update(output['metadata'])
        
        return {
            'content': '\n'.join(generated_content),
            'metadata': metadata,
            'sources': [r.get('tool') for r in results if r.get('success', False)]
        }

    def _generate_analysis_summary(self, analyses: List[Dict[str, Any]]) -> str:
        """Generate a summary of multiple analyses"""
        if not analyses:
            return ""
            
        # Combine key points from all analyses
        key_points = []
        for analysis in analyses:
            if isinstance(analysis, dict):
                key_points.extend(analysis.get('key_points', []))
            elif isinstance(analysis, str):
                key_points.append(analysis)
                
        return "\n".join(f"- {point}" for point in key_points[:5])

    def _adapt_strategy(self, strategy: Dict[str, Any], step_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt strategy based on step execution results and context"""
        try:
            # Don't modify original strategy
            adapted_strategy = dict(strategy)
            remaining_steps = adapted_strategy.get('steps', [])[:]
            
            # If step failed, try alternative approach
            if not step_result.get('success', False):
                tool_name = step_result.get('tool')
                action = step_result.get('action')
                
                # Try to find alternative tool for same action
                alternative = self._find_alternative_tool(action, tool_name)
                if alternative:
                    # Replace failed step with alternative
                    for i, step in enumerate(remaining_steps):
                        if step['tool'] == tool_name and step['action'] == action:
                            remaining_steps[i] = {'action': action, 'tool': alternative}
                            break
                            
                # If no alternative tool, try fallback action
                elif fallback := strategy.get('fallback'):
                    remaining_steps.append(fallback)
            
            # Adjust strategy based on results
            adapted_strategy.update({
                'steps': remaining_steps,
                'confidence': self._calculate_strategy_confidence(strategy, step_result),
                'last_result': step_result
            })
            
            # Add any dynamic steps based on results
            if dynamic_steps := self._generate_dynamic_steps(step_result, context):
                adapted_strategy['steps'].extend(dynamic_steps)
            
            return adapted_strategy
            
        except Exception as e:
            self.logger.warning(f"Strategy adaptation failed: {str(e)}")
            return strategy

    def _find_alternative_tool(self, action: str, failed_tool: str) -> Optional[str]:
        """Find alternative tool for an action"""
        action_tools = {
            'search': ['google_search', 'duckduckgo_search', 'bing_search'],
            'extract': ['web_scraper', 'html_parser', 'content_extractor'],
            'analyze': ['content_analyzer', 'text_analyzer', 'semantic_analyzer'],
            'filter': ['content_filter', 'text_filter', 'relevance_filter'],
            'generate': ['content_generator', 'text_generator', 'llm_generator'],
            'summarize': ['summarizer', 'text_summarizer', 'content_summarizer']
        }
        
        if action in action_tools:
            alternatives = [tool for tool in action_tools[action] 
                          if tool in self.tools and tool != failed_tool]
            return alternatives[0] if alternatives else None
        return None

    def _calculate_strategy_confidence(self, strategy: Dict[str, Any], step_result: Dict[str, Any]) -> float:
        """Calculate strategy confidence based on step results"""
        base_confidence = strategy.get('confidence', 0.7)
        step_confidence = float(step_result.get('confidence', 0.0))
        
        if step_result.get('success', False):
            # Successful step slightly increases confidence
            return min(base_confidence * 1.1, 1.0)
        else:
            # Failed step significantly decreases confidence
            return max(base_confidence * 0.5, 0.1)

    def _generate_dynamic_steps(self, step_result: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate additional steps based on results"""
        dynamic_steps = []
        
        if step_result.get('success', False):
            output = step_result.get('output', {})
            
            # Add verification step for important information
            if output.get('critical_info'):
                dynamic_steps.append({
                    'action': 'verify',
                    'tool': 'fact_checker'
                })
            
            # Add refinement step for generated content
            if output.get('content'):
                dynamic_steps.append({
                    'action': 'refine',
                    'tool': 'content_refiner'
                })
            
            # Add summarization for large amounts of data
            if len(str(output)) > 1000:
                dynamic_steps.append({
                    'action': 'summarize',
                    'tool': 'summarizer'
                })
        
        return dynamic_steps

    async def execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step with proper async handling"""
        try:
            tool_name = step.get('tool')
            tool = self.tools.get(tool_name)
            
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")

            params = {
                'query': context.get('task', ''),
                'operation': step.get('action', 'generate'),
                'context': context
            }

            result = await tool.execute(**params)
            return result

        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': step.get('action', 'unknown'),
                'tool': step.get('tool', 'unknown')
            }

    # ...existing code...
