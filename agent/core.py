import os
from typing import Dict, Any, List, Optional
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
        self.query_patterns = {
            'person_query': r'^who\s+(?:is|was|are|were)',
            'factual_query': r'^(?:what|when|where|why|how)',
            'quantity_query': r'(?:how\s+(?:much|many)|what\s+(?:amount|percentage|number))',
        }
        self.answer_extractors = {
            'person_query': self._extract_person_answer,
            'factual_query': self._extract_factual_answer,
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

class TaskType(Enum):
    FACTUAL_QUERY = "factual_query"  # Direct questions
    RESEARCH = "research"  # Research tasks
    CODE = "code"  # Code generation
    CONTENT = "content"  # Blog/article writing
    DATA_ANALYSIS = "data_analysis"  # Data processing
    GENERAL = "general"  # Add this new type
    COMPLETION = "completion"  # Add this new type

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
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.task_patterns = {
            TaskType.FACTUAL_QUERY: r'^(?:who|what|when|where|why|how)\s+(?:is|are|was|were|do|does|did)',
            TaskType.RESEARCH: r'(?:research|analyze|investigate|compare|study|find|search)',
            TaskType.CODE: r'(?:implement|code|program|create\s+a\s+program|write\s+code)',
            TaskType.CONTENT: r'(?:write|create|compose|draft)\s+(?:a|an)\s+(?:blog|article|post|essay)',
            TaskType.DATA_ANALYSIS: r'(?:data|dataset|database|analyze\s+data)'
        }
        
        self.task_patterns.update({
            TaskType.COMPLETION: r'^(?:[a-zA-Z]+\s+is\s*|complete\s+this|finish\s+this|what\s+comes\s+after)',
            TaskType.GENERAL: r'.*'  # Catch-all pattern
        })
        
        # Add completion prompts
        self.completion_prefixes = [
            "life is", "love is", "the meaning of", "happiness is",
            "success is", "the purpose of"
        ]
        self.task_parser = TaskParser()

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
            return "No companies found matching all criteria."
            
        summary = "Companies matching all criteria:\n\n"
        for result in results:
            summary += f"- {result.get('title', 'Unknown')}\n"
            if 'detailed_content' in result:
                relevant_info = self._extract_relevant_info(result['detailed_content'], criteria)
                if relevant_info:
                    summary += f"  {relevant_info}\n"
                    
        return summary

    def _extract_relevant_info(self, content: str, criteria: Dict) -> str:
        """Extract relevant information based on the criteria"""
        info = []
        
        # Extract specific information based on criteria types
        for criterion_type, criterion in criteria.items():
            if match := self._extract_criterion_info(content, criterion_type, criterion):
                info.append(match)
                
        return "; ".join(info) if info else ""

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
            
        # If no specific pattern matches, treat as general
        return TaskType.GENERAL

    async def _handle_direct_question(self, task: str) -> Dict[str, Any]:
        """Handle direct questions with cleaner answer extraction"""
        try:
            search_result = await self.tools["google_search"].execute(task)
            if not search_result.get('success'):
                return {
                    "success": False,
                    "error": "Search failed",
                    "output": {"results": []}
                }
            
            results = search_result.get('results', [])
            
            # Process through answer processor first
            processed_answer = self.answer_processor.extract_direct_answer(task, results)
            direct_answer = None
            
            if processed_answer and processed_answer.get('answer'):
                direct_answer = processed_answer['answer']
            else:
                # Fallback to basic extraction
                direct_answer = self._construct_direct_answer(task, results)
            
            # Clean up the answer by removing prefixes and normalizing
            if direct_answer and isinstance(direct_answer, str):
                # Remove unwanted prefixes
                direct_answer = re.sub(
                    r'^(?:(?:The|A|An)\s+)?(?:Richest\s+People\s+)?(?:According to|From|Source:|Wikipedia:?|Reuters:?)\s*',
                    '',
                    direct_answer
                ).strip()
            
            return {
                "success": True,
                "output": {
                    "direct_answer": direct_answer,
                    "results": results
                },
                "confidence": 0.9 if direct_answer else 0.5
            }
            
        except Exception as e:
            self.logger.error(f"Direct question handling failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    def _construct_direct_answer(self, query: str, results: List[Dict[str, str]]) -> Optional[str]:
        """Construct a direct answer with proper context"""
        if not results:
            return None
            
        all_text = " ".join(r.get("snippet", "") for r in results)
        
        # Handle "who is richest" type queries
        if 'richest' in query.lower() and 'world' in query.lower():
            pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:is|remains|became)\s+(?:the\s+)?(?:world\'?s?\s+)?richest\s+(?:person|man|individual)[^.]*?(?:\$(\d+(?:\.\d+)?)\s*(billion|trillion))?'
            matches = re.findall(pattern, all_text)
            if matches:
                for name, amount, scale in matches:
                    if amount and scale:
                        return f"{name.strip()} (${amount} {scale})"
                    return name.strip()

        return None

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
