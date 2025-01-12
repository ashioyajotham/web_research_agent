import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio
import time
import google.generativeai as genai
from datetime import datetime

from .executor import Executor, ExecutionResult
from .utils.prompts import PromptManager
from tools.base import BaseTool
from utils.logger import AgentLogger
from planning.task_planner import TaskPlanner
from memory.memory_store import MemoryStore
from learning.pattern_learner import PatternLearner

@dataclass
class AgentConfig:
    max_steps: int = 10
    min_confidence: float = 0.7
    timeout: int = 300
    learning_enabled: bool = True
    memory_path: str = "agent_memory.db"
    parallel_execution: bool = True
    planning_enabled: bool = True
    pattern_learning_enabled: bool = True

class Agent:
    def __init__(self, tools: Dict[str, BaseTool], config: Optional[AgentConfig] = None):
        # Initialize components
        self.config = config or AgentConfig()
        self.tools = tools
        self.memory = MemoryStore(self.config.memory_path)
        self.planner = TaskPlanner(available_tools=list(tools.keys())) if self.config.planning_enabled else None
        self.pattern_learner = PatternLearner() if self.config.pattern_learning_enabled else None
        self.executor = Executor(tools, parallel=self.config.parallel_execution)
        self.logger = AgentLogger()
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    async def process_tasks(self, tasks: List[str]) -> List[Dict[str, Any]]:
        """Process multiple tasks in parallel"""
        return await asyncio.gather(*[
            self.process_task(task) for task in tasks
        ])

    async def process_task(self, task: str) -> Dict[str, Any]:
        """Process a task with proper timeout and error handling"""
        self.logger.task_start(task)
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Add timeout protection
                result = await asyncio.wait_for(
                    self._safe_execute_task(task),
                    timeout=self.config.timeout
                )
                
                if result.get('success'):
                    return self._finalize_result(task, result, time.time() - start_time)
                
                # If failed but not due to error, try alternative approach
                if not result.get('error'):
                    basic_result = await self._execute_basic_task(task)
                    if (basic_result.get('success')):
                        return self._finalize_result(task, basic_result, time.time() - start_time)
                
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1 * retry_count)  # Exponential backoff
                    continue
                
                return self._finalize_result(task, result, time.time() - start_time)
                
            except asyncio.TimeoutError:
                self.logger.error(f"Task timed out after {self.config.timeout}s: {task[:50]}...")
                return {
                    "success": False,
                    "error": f"Task timed out after {self.config.timeout} seconds",
                    "output": {"results": []},
                    "confidence": 0.0
                }
            except Exception as e:
                self.logger.error(str(e), f"Task: {task[:50]}...")
                retry_count += 1
                if retry_count >= max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "output": {"results": []},
                        "confidence": 0.0
                    }
                await asyncio.sleep(1 * retry_count)  # Exponential backoff

    def _finalize_result(self, task: str, result: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Finalize and validate the result"""
        if isinstance(result, dict):
            return {
                "success": bool(result.get("success", False)),
                "output": result.get("output", {"results": []}),
                "confidence": float(result.get("confidence", 0.0)),
                "execution_time": float(execution_time),
                "error": result.get("error"),
                "task": task,
                "metrics": result.get("metrics", {})
            }
        elif isinstance(result, ExecutionResult):
            return {
                "success": bool(result.success),
                "output": result.output or {"results": []},
                "confidence": float(result.confidence),
                "execution_time": float(execution_time),
                "task": task,
                "metrics": result.execution_metrics or {}
            }
        else:
            return {
                "success": False,
                "error": "Invalid result type",
                "output": {"results": []},
                "confidence": 0.0,
                "execution_time": float(execution_time),
                "task": task
            }

    async def _execute_with_solution(self, task: str, solution: Dict) -> Dict:
        """Execute task using a generalized solution"""
        try:
            # Adapt the solution to the current task
            task_type = self.planner._analyze_task_type(task) if self.planner else "research"
            
            if task_type == "CODE" and solution.get("code"):
                # For code tasks, use the generalized solution as a template
                result = await self.tools["code_generator"].execute(
                    query=task,
                    template=solution.get("code")
                )
            else:
                # For other tasks, use the solution's parameters
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
        """Basic task execution without planning"""
        try:
            # Determine task type and select appropriate tool
            task_type = self.planner._analyze_task_type(task) if self.planner else "research"
            
            if task_type == "CODE":
                result = await self.tools["code_generator"].execute(query=task)
            elif task_type == "DATA":
                result = await self.tools["dataset"].execute(query=task)
            else:
                # Default to google search for research tasks
                result = await self.tools["google_search"].execute(query=task)
            
            if isinstance(result, dict) and result.get("success"):
                return {
                    "success": True,
                    "output": result,
                    "confidence": 0.7,
                    "execution_time": 0.0,
                    "task": task
                }
            else:
                return {
                    "success": False,
                    "output": {"results": []},
                    "confidence": 0.0,
                    "error": "Tool execution failed",
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
        """Calculate solution effectiveness"""
        try:
            # Base effectiveness on multiple factors
            effectiveness = 0.0
            
            # Success is the primary factor
            if result.get("success"):
                effectiveness += 0.5
                
                # Add points for output quality
                output = result.get("output", {})
                if isinstance(output, dict):
                    if "results" in output and output["results"]:
                        effectiveness += min(len(output["results"]) * 0.1, 0.3)
                    if "code" in output:
                        effectiveness += 0.2
                    if "data" in output:
                        effectiveness += 0.2
                
                # Consider confidence
                effectiveness *= max(0.1, min(1.0, result.get("confidence", 0.0)))
            
            return min(1.0, effectiveness)
            
        except Exception as e:
            self.logger.error(f"Effectiveness calculation failed: {str(e)}")
            return 0.0

    async def _safe_execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with retries and cleanup"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await self._execute_task(task)
                return result
            except asyncio.CancelledError:
                # Ensure cleanup of any pending operations
                await self._cleanup_cancelled_task()
                raise
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                self.logger.log('WARNING', f"Retry {retry_count}/{max_retries} due to: {str(e)}", "Retry")
                await asyncio.sleep(1 * retry_count)  # Exponential backoff

    async def _cleanup_cancelled_task(self):
        """Clean up resources when a task is cancelled"""
        try:
            # Cancel any pending subtasks
            for task in asyncio.all_tasks():
                if task != asyncio.current_task():
                    task.cancel()
            # Wait for cancellation to complete
            await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()},
                               return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}", "Cleanup")

    def get_partial_results(self) -> Dict[str, Any]:
        """Get any partial results that were obtained before timeout"""
        # Implement gathering of partial results
        return {}

    async def _execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with full pipeline"""
        start_time = time.time()
        
        try:
            # Get relevant experiences, handle failure gracefully
            try:
                experiences = self.memory.get_relevant_experiences(task)
            except Exception:
                experiences = []  # Continue without previous experiences if memory fails
            
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
                
                # Convert ExecutionResult to dict with proper error handling
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
                    # Handle unexpected result type
                    return {
                        'success': False,
                        'error': 'Invalid execution result type',
                        'output': {'results': []},
                        'confidence': 0.0,
                        'execution_time': time.time() - start_time,
                        'task': task
                    }
            else:
                # Direct task execution without planning
                result = await self._execute_basic_task(task)
                return self._finalize_result(task, result, time.time() - start_time)
                
        except Exception as e:
            # Update error logging to use proper format
            self.logger.error(str(e), context=f"Task: {task[:50]}...", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []},
                'confidence': 0.0,
                'execution_time': time.time() - start_time,
                'task': task
            }
