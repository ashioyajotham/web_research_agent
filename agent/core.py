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


@dataclass
class AgentConfig:
    max_steps: int = 5
    min_confidence: float = 0.7
    timeout: int = 300
    learning_enabled: bool = True
    memory_path: str = "agent_memory.db"
    parallel_execution: bool = True
    planning_enabled: bool = True
    pattern_learning_enabled: bool = True
    extraction_patterns: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.extraction_patterns is None:
            self.extraction_patterns = {
                'numerical': [
                    r'(\d+\.?\d*)%',
                    r'\$?\s*(\d+\.?\d*)\s*(?:billion|million|trillion)',
                    r'(\d+\.?\d*)\s*(?:percent|points?)'
                ],
                'date_bounded': [
                    r'(?:in|during|for)\s*(?:20\d{2})',
                    r'(?:as of|since|until)\s*(?:20\d{2})'
                ],
                'comparison': [
                    r'(?:increased|decreased|grew|fell)\s*(?:by|to)\s*(\d+\.?\d*)',
                    r'(?:higher|lower|more|less)\s*than\s*(\d+\.?\d*)'
                ],
                'entity': [
                    r'([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)'
                ]
            }

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
    
    @classmethod
    def infer_type(cls, task: str, context: Dict = None) -> 'TaskType':
        """Dynamically infer task type based on context and patterns"""
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
            TaskType.GENERAL: r'.*'
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
            
            # Determine processing strategy
            strategy = await self._determine_strategy(task, context)
            
            # Execute with chosen strategy
            result = await self._execute_with_strategy(task, strategy, context)
            
            # Learn from execution
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
                step_result = await self._execute_step(step, context)
                results.append(step_result)
                
                # Adapt strategy based on results
                strategy = self._adapt_strategy(strategy, step_result, context)
                
            except Exception as e:
                self.logger.error(f"Step execution failed: {str(e)}")
                continue
        
        return self._combine_results(results, strategy, context)

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
        
        while retry_count < max_retries:
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
            r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b'  # Months
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
