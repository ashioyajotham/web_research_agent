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
from .task_parser import TaskParser, ParsedTask
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
        # Simplified query patterns to be more generic
        self.query_patterns = {
            'temporal_query': r'^when\s+.+',
            'entity_query': r'^(?:who|what)\s+.+',
            'location_query': r'^where\s+.+',
            'reason_query': r'^(?:why|how)\s+.+',
            'quantity_query': r'(?:how\s+(?:much|many)|what\s+(?:amount|number))'
        }
        self.answer_extractors = {
            'temporal_query': self._extract_temporal_answer,
            'entity_query': self._extract_entity_answer,
            'location_query': self._extract_location_answer,
            'reason_query': self._extract_reason_answer,
            'quantity_query': self._extract_quantity_answer
        }

    def extract_direct_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        query_type = self._detect_query_type(query.lower())
        extractor = self.answer_extractors.get(query_type)
        
        if extractor:
            return extractor(query, results)
        return {"answer": None, "confidence": 0.0}

    def _detect_query_type(self, query: str) -> str:
        for qtype, pattern in self.query_patterns.items():
            if re.search(pattern, query):
                return qtype
        return 'general'

    def _extract_person_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract person-related answers with context"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        
        # Refined patterns for person extraction - remove prefix phrases
        patterns = [
            # Direct mention pattern
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+is\s+(?:the|a)\s+)?([^,.]+?)(?:\s*[,.]|$)',
            # Context pattern
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s*,\s*([^,.]+))',
        ]
        
        best_match = None
        max_confidence = 0.0
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                # Count occurrences to find most mentioned
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    name, context = candidate
                    # Remove any prefix phrases like "Richest People" or "The person"
                    name = re.sub(r'^(?:(?:The|A|An)\s+)?(?:Person|People|Man|Woman|Individual)\s+', '', name.strip())
                    best_match = f"{name} ({context.strip()})"
                    max_confidence = confidence
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": "person"
        }

    def _extract_factual_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract answers for general factual queries"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        
        # Patterns for different types of factual answers
        patterns = {
            'definition': r'(?:is|are|was|were)\s+((?:a|an|the)\s+[^.!?]+)',
            'date': r'(?:on|in|at|during)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            'location': r'(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'quantity': r'(\d+(?:\.\d+)?)\s+(?:percent|kg|miles|dollars|years)'
        }
        
        best_match = None
        max_confidence = 0.0
        answer_type = None
        
        for ans_type, pattern in patterns.items():
            matches = re.findall(pattern, all_text)
            if matches:
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    best_match = candidate
                    max_confidence = confidence
                    answer_type = ans_type
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": answer_type
        }

    def _extract_quantity_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract numerical answers with units"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        
        # Patterns for different types of quantities
        quantity_patterns = [
            # Money amounts
            r'\$\s*(\d+(?:\.\d+)?)\s*(billion|million|trillion)?',
            # Percentages
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)',
            # Measurements
            r'(\d+(?:\.\d+)?)\s*(kg|km|miles|feet|meters)',
            # Time periods
            r'(\d+(?:\.\d+)?)\s*(years|months|days|hours)'
        ]
        
        best_match = None
        max_confidence = 0.0
        
        for pattern in quantity_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                # Count occurrences to find most cited value
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    # Format the quantity with its unit
                    if len(candidate) > 1:  # Has unit
                        value, unit = candidate
                        best_match = f"{value} {unit}"
                    else:  # Just the value
                        best_match = candidate[0]
                    max_confidence = confidence
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": "quantity"
        }

    def _extract_temporal_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract any temporal information from text"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        
        # Generic date patterns without specific event types
        date_patterns = [
            r'(?:on|at|in)\s+([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',
            r'([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',
            r'(?:in|during)\s+([A-Z][a-z]+\s+\d{4})',
            r'(\d{4})'
        ]
        
        return self._extract_with_patterns(date_patterns, all_text, 'temporal')

    def _extract_with_patterns(self, patterns: List[str], text: str, answer_type: str) -> Dict[str, Any]:
        """Generic pattern extraction with confidence scoring"""
        best_match = None
        max_confidence = 0.0
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    best_match = candidate.strip()
                    max_confidence = confidence
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": answer_type
        }

    def _extract_location_answer(self, query: str, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract location-related answers"""
        all_text = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)
        
        location_patterns = [
            r'(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+)?)',
            r'(?:location|place|city|country):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:located|situated)\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        best_match = None
        max_confidence = 0.0
        
        for pattern in location_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                counter = Counter(matches)
                candidate = counter.most_common(1)[0][0]
                confidence = min(0.5 + (counter[candidate] / len(matches)) * 0.5, 0.95)
                
                if confidence > max_confidence:
                    best_match = candidate.strip()
                    max_confidence = confidence
        
        return {
            "answer": best_match,
            "confidence": max_confidence,
            "type": "location"
        }

class TaskType(Enum):
    QUERY = "query"          # Any question or information request
    ANALYSIS = "analysis"    # Any analytical task
    GENERATION = "generation"  # Any content generation task
    GENERAL = "general"      # Fallback type

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
        self.completion_prefixes = [
            "life is", "love is", "the meaning of", "happiness is",
            "success is", "the purpose of"
        ]
        self.task_parser = TaskParser()

        # Replace rigid metric types with flexible pattern matching
        self.metric_patterns = {
            # Generic numerical patterns
            'number': MetricType(r'(\d+(?:\.\d+)?)\s*(?:units?)?'),
            'percentage': MetricType(r'(\d+(?:\.\d+)?)\s*%'),
            'currency': MetricType(r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:billion|million)?'),
            'measurement': MetricType(r'(\d+(?:\.\d+)?)\s*(?:kg|km|m|ft|lbs)')
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

    async def _handle_criteria_search(self, parsed_task: ParsedTask) -> Dict[str, Any]:
        """Handle multi-criteria search using progressive filtering"""
        try:
            # Extract actual criteria from parsed task
            criteria = parsed_task.components[0].criteria if parsed_task.components else []
            
            # Use first line as base query
            base_query = parsed_task.main_task
            
            # Build search parameters from actual criteria
            search_params = {
                'location': next((c for c in criteria if 'EU' in c), None),
                'industry': next((c for c in criteria if 'motor vehicle sector' in c), None),
                'requirements': [c for c in criteria if any(term in c.lower() for term in 
                    ['environmental', 'emissions', 'revenue', 'subsidiary'])]
            }

            # Step 1: Get initial broad results
            initial_results = await self.tools["google_search"].execute(
                query=base_query,
                params={"detailed": True, "num": 20}  # Get more initial results
            )

            if not initial_results.get('success'):
                return initial_results

            results = initial_results.get('output', {}).get('results', [])
            
            # Step 2: Progressive filtering
            filtered_results = []
            for result in results:
                # Get detailed information for each potential match
                try:
                    details = await self.tools["web_scraper"].execute(url=result.get('link', ''))
                    if details:
                        result['detailed_content'] = details
                except:
                    continue

                # Check all criteria at once
                matches_all = True
                for criterion_type, criterion in criteria.items():
                    if not await self._check_criterion(result, criterion_type, criterion):
                        matches_all = False
                        break

                if matches_all:
                    filtered_results.append(result)

            # Step 3: Format final results
            return {
                "success": True,
                "output": {
                    "results": filtered_results,
                    "total_matches": len(filtered_results),
                    "applied_criteria": list(criteria.keys()),
                    "original_query": base_query,
                    "summary": self._generate_criteria_summary(filtered_results, criteria)
                },
                "confidence": self._calculate_criteria_confidence(filtered_results, criteria),
                "task_type": "criteria_search"
            }

        except Exception as e:
            self.logger.error(f"Criteria search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _check_criterion(self, result: Dict, criterion_type: str, criterion: str) -> bool:
        """Check a single criterion against a result"""
        content = f"{result.get('title', '')} {result.get('snippet', '')} {result.get('detailed_content', '')}"
        
        if criterion_type == 'location':
            # Check location criteria
            location_pattern = rf"(?:headquartered|based)\s+in\s+{criterion}"
            return bool(re.search(location_pattern, content, re.IGNORECASE))
            
        elif criterion_type == 'industry':
            # Check industry/sector criteria
            return criterion.lower() in content.lower()
            
        elif criterion_type == 'financial':
            # Check financial criteria (revenue, market cap, etc.)
            if 'revenue' in criterion.lower():
                amount = re.search(r'(\d+(?:\.\d+)?)\s*(?:billion|million|trillion)?', criterion)
                if amount:
                    return self._check_financial_amount(content, amount.group())
            return False
            
        elif criterion_type == 'status':
            # Check company status (subsidiary, public, etc.)
            if 'subsidiary' in criterion.lower():
                return not bool(re.search(r'subsidiary\s+of', content, re.IGNORECASE))
            
        return False

    def _check_financial_amount(self, content: str, target_amount: str) -> bool:
        """Compare financial amounts with unit conversion"""
        try:
            # Extract numbers with units from content
            amounts = re.findall(r'(\d+(?:\.\d+)?)\s*(billion|million|trillion)?', content)
            target_val = float(re.search(r'\d+(?:\.\d+)?', target_amount).group())
            
            # Convert to same scale (billions)
            scales = {'trillion': 1000, 'billion': 1, 'million': 0.001}
            target_scale = next((s for s in scales if s in target_amount.lower()), 'billion')
            target_val *= scales[target_scale]
            
            for amount, scale in amounts:
                val = float(amount) * scales.get(scale.lower() if scale else 'billion', 1)
                if val >= target_val:
                    return True
            
            return False
        except:
            return False

    def _generate_criteria_summary(self, results: List[Dict], criteria: Dict) -> str:
        """Generate a human-readable summary of the matching results"""
        if not results:
            return "No matches found for the given criteria."
        
        # Detect entity type from criteria or task context
        entity_type = self._detect_entity_type(criteria)
        
        summary = f"Matching {entity_type}s:\n\n"
        for result in results:
            # Basic info
            name = result.get('title', 'Unknown')
            summary += f"- {name}\n"
            
            # Add matching criteria details
            if 'detailed_content' in result:
                summary += "  Matching criteria:\n"
                for criterion, value in result['detailed_content'].items():
                    summary += f"    • {criterion}: {value}\n"
            summary += "\n"
        
        return summary

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
        try:
            task_type = self._detect_task_type(task)
            
            if task_type == TaskType.COMPLETION:
                return await self._handle_completion(task)
            elif task_type == TaskType.GENERAL:
                return await self._handle_general_query(task)
            elif task_type == TaskType.FACTUAL_QUERY:
                return await self._handle_direct_question(task)
            elif task_type == TaskType.RESEARCH:
                return await self._handle_research(task)
            elif task_type == TaskType.CODE:
                return await self._handle_code_generation(task)
            elif task_type == TaskType.CONTENT:
                return await self._handle_content_creation(task)
            elif task_type == TaskType.NUMERICAL_COMPARISON:
                return await self._handle_numerical_comparison(task)
            else:
                return await self._handle_data_task(task)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task": task
            }

    def _detect_task_type(self, task: str) -> TaskType:
        """Enhanced task type detection"""
        task_lower = task.lower()
        
        # Check for completion patterns first
        if any(task_lower.startswith(prefix.lower()) for prefix in self.completion_prefixes):
            return TaskType.COMPLETION
            
        # Check for direct questions
        if re.match(r'^(?:who|what|when|where|why|how)\s+(?:is|are|was|were|do|does|did)', task_lower):
            return TaskType.FACTUAL_QUERY
            
        # Check for research/analysis tasks
        if any(term in task_lower for term in ['research', 'analyze', 'investigate', 'compare']):
            return TaskType.RESEARCH
            
        # Check for code tasks
        if any(term in task_lower for term in ['code', 'implement', 'program', 'function']):
            return TaskType.CODE
            
        # Check for content tasks
        if any(term in task_lower for term in ['write', 'compose', 'create article']):
            return TaskType.CONTENT
            
        # Add numerical comparison detection
        if any(term in task_lower for term in ['increase', 'decrease', 'reduce', 'change', 'compare']):
            if any(term in task_lower for term in ['percent', '%', 'ratio', 'amount']):
                return TaskType.NUMERICAL_COMPARISON
            
        # If no specific pattern matches, treat as general
        return TaskType.GENERAL

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
            # Get relevant experiences with error handling
            experiences = []
            if self.config.learning_enabled:
                try:
                    experiences = self.memory.get_relevant_experiences(task)
                except Exception as e:
                    self.logger.warning(f"Memory retrieval failed: {str(e)}")
            
            # Try pattern matching first if enabled
            if self.config.pattern_learning_enabled and self.pattern_learner:
                try:
                    similar_patterns = self.pattern_learner.find_similar_patterns(task)
                    if similar_patterns:
                        solution = self.pattern_learner.generalize_solution(similar_patterns)
                        if solution:
                            result = await self._execute_with_solution(task, solution)
                            if result.get('success'):
                                return result
                except Exception as e:
                    self.logger.warning(f"Pattern matching failed: {str(e)}")
            
            # Proceed with normal execution
            if self.config.planning_enabled and self.planner:
                plan = self.planner.create_plan(
                    task=task,
                    context={"experiences": experiences}
                )
                exec_result = await self.executor.execute_plan(
                    plan=plan,
                    model=self.model,
                    max_steps=self.config.max_steps
                )
                
                result = self._format_execution_result(exec_result, task, start_time)
            else:
                result = await self._execute_basic_task(task)
                result = self._finalize_result(task, result, time.time() - start_time)
            
            # Store successful results for learning
            if result.get('success') and self.config.learning_enabled:
                try:
                    self.pattern_learner.add_pattern(
                        task=task,
                        solution=result.get('output', {}),
                        performance=self._calculate_effectiveness(result)
                    )
                except Exception as e:
                    self.logger.warning(f"Learning storage failed: {str(e)}")
            
            return result
                
        except Exception as e:
            self.logger.error(str(e), context=f"Task: {task[:50]}...", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []},
                'confidence': 0.0,
                'execution_time': time.time() - start_time,
                'task': task
            }

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
        """Handle pattern completion tasks using Gemini"""
        try:
            # Prepare prompt for pattern completion
            prompt = f"Complete this phrase naturally: {task}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if response and response.text:
                completion = response.text.strip()
                return {
                    "success": True,
                    "output": {
                        "completion": completion,
                        "type": "completion"
                    },
                    "confidence": 0.9
                }
            
            return {
                "success": False,
                "error": "Could not generate completion",
                "output": {"results": []}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _handle_general_query(self, task: str) -> Dict[str, Any]:
        """Handle general queries using Gemini"""
        try:
            # Prepare prompt for general query
            prompt = f"Answer this query: {task}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if response and response.text:
                answer = response.text.strip()
                return {
                    "success": True,
                    "output": {
                        "answer": answer,
                        "type": "general"
                    },
                    "confidence": 0.8
                }
            
            return {
                "success": False,
                "error": "Could not generate answer",
                "output": {"results": []}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

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
