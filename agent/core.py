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
from .strategy import ResearchStrategy  # Change from strategy.research to .strategy

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
        
        # Enhanced patterns for person extraction
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+is\s+(?:the|a)\s+)?([^,.]+)',
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
                    best_match = f"{name.strip()} ({context.strip()})"
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

    async def process_tasks(self, tasks: List[str]) -> List[Dict[str, Any]]:
        return await asyncio.gather(*[
            self.process_task(task) for task in tasks
        ])

    async def process_task(self, task: str) -> Dict[str, Any]:
        try:
            task_type = self._detect_task_type(task)
            
            if task_type == TaskType.FACTUAL_QUERY:
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
        """Improved task type detection"""
        task_lower = task.lower()
        
        # Code Generation Patterns
        code_patterns = [
            r'implement (?:a|an|the)?\s+\w+',
            r'create (?:a|an|the)?\s+(?:\w+\s+)?(?:class|function|implementation)',
            r'write (?:a|an|the)?\s+(?:\w+\s+)?(?:code|program|algorithm)',
        ]
        
        # Content Generation Patterns
        content_patterns = [
            r'write (?:a|an|the)?\s+(?:blog|article|post|guide)',
            r'create (?:a|an|the)?\s+(?:tutorial|documentation)',
            r'explain (?:how|why|what)'
        ]
        
        # Check code patterns first
        for pattern in code_patterns:
            if re.search(pattern, task_lower):
                return TaskType.CODE
                
        # Then content patterns
        for pattern in content_patterns:
            if re.search(pattern, task_lower):
                return TaskType.CONTENT
                
        # Then check other patterns
        for task_type, pattern in self.task_patterns.items():
            if re.search(pattern, task_lower):
                return task_type
                
        return TaskType.RESEARCH  # Default to research

    async def _handle_direct_question(self, task: str) -> Dict[str, Any]:
        """Handle direct questions with entity extraction"""
        try:
            search_result = await self.tools["google_search"].execute(task)
            if not search_result.get('success'):
                return {
                    "success": False,
                    "error": "Search failed",
                    "output": {"results": []}
                }
            
            # Extract entities and relationships
            entities = self._extract_entities(search_result.get('results', []))
            
            # Get direct answer
            direct_answer = self._construct_direct_answer(task, entities, search_result)
            
            return {
                "success": True,
                "output": {
                    "direct_answer": direct_answer,
                    "results": search_result.get('results', [])
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

    def _construct_direct_answer(self, query: str, entities: Dict[str, Any], results: Dict[str, Any]) -> Optional[str]:
        """Construct a direct answer with proper context"""
        if not results or not isinstance(results, dict) or 'results' not in results:
            return None
            
        search_results = results.get('results', [])
        if not search_results:
            return None

        # Process through answer processor
        processed_answer = self.answer_processor.extract_direct_answer(query, search_results)
        
        if processed_answer and processed_answer['answer']:
            return processed_answer['answer']
            
        # Fallback to basic extraction for person queries
        all_text = " ".join(r.get("snippet", "") for r in search_results)
        
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
            try:
                experiences = self.memory.get_relevant_experiences(task)
            except Exception:
                experiences = []
            
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
            else:
                result = await self._execute_basic_task(task)
                return self._finalize_result(task, result, time.time() - start_time)
                
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
