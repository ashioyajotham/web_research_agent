import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio
import time
import google.generativeai as genai
from datetime import datetime

from .executor import Executor, ExecutionResult
from .reflection import Evaluator
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
    enable_reflection: bool = True
    memory_path: str = "agent_memory.json"
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
        self.evaluator = Evaluator()
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
        
        try:
            # Check memory and pattern learning first
            if self.config.pattern_learning_enabled and self.pattern_learner:
                similar_patterns = self.memory.retrieve_similar_patterns(task)
                if similar_patterns:
                    similar_solutions = [(p["solution"], p["effectiveness"]) for p in similar_patterns]
                    generalized_solution = self.pattern_learner.generalize_solution(similar_solutions)
                    if generalized_solution:
                        result = await self._execute_with_solution(task, generalized_solution)
                        if result.get("success"):
                            return self._finalize_result(task, result, time.time() - start_time)

            # If no pattern match or it failed, use planner
            if self.config.planning_enabled and self.planner:
                plan = self.planner.create_plan(task, {"previous_attempts": similar_patterns})
                result = await self.executor.execute_plan(plan, self.model, self.config.max_steps)
            else:
                result = await self._execute_basic_task(task)

            # Store results and learn
            if result.get("success"):
                self.memory.store_memory(
                    task_type=self.planner._analyze_task_type(task) if self.planner else "general",
                    pattern=task,
                    solution=result,
                    effectiveness=self._calculate_effectiveness(result)
                )
                if self.pattern_learner:
                    self.pattern_learner.add_pattern(task, result)

            return self._finalize_result(task, result, time.time() - start_time)

        except Exception as e:
            self.logger.error(str(e), f"Task: {task[:50]}...")
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    def _finalize_result(self, task: str, result: Dict, execution_time: float) -> Dict[str, Any]:
        """Finalize the result with metadata"""
        return {
            "success": result.get("success", False),
            "output": result.get("output", {}),
            "confidence": result.get("confidence", 0.0),
            "execution_time": execution_time,
            "task": task
        }

    async def _execute_with_solution(self, task: str, solution: Dict) -> Dict:
        """Execute task using a generalized solution"""
        # Implementation specific to solution adaptation
        pass

    async def _execute_basic_task(self, task: str) -> Dict:
        """Basic task execution without planning"""
        # Implementation for basic task processing
        pass

    def _calculate_effectiveness(self, result: Dict) -> float:
        """Calculate solution effectiveness"""
        # Implementation for calculating effectiveness
        pass

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
        
        # Get relevant past experiences
        experiences = self.memory.get_relevant_experiences(task)
        
        # Create and validate plan if planning is enabled
        if self.config.planning_enabled and self.planner:
            plan = self.planner.create_plan(
                task=task,
                context={"experiences": experiences}
            )
            result = await self.executor.execute_plan(
                plan=plan,
                model=self.model,
                max_steps=self.config.max_steps
            )
        else:
            # Fallback to simple execution
            result = await self._process_task(task)
        
        # Evaluate and learn
        if self.config.enable_reflection:
            evaluation = await self._reflect_on_execution(task, plan, result)
            await self._learn_from_execution(task, plan, result, evaluation)
        
        execution_time = time.time() - start_time
        
        return {
            'success': result.success,
            'output': result.output,
            'confidence': result.confidence,
            'steps_taken': len(result.steps),
            'execution_time': execution_time,
            'task': task
        }

    async def _reflect_on_execution(self, 
                                  task: str, 
                                  plan: ExecutionPlan,
                                  result: ExecutionResult) -> Dict[str, Any]:
        """Reflect on task execution"""
        # Evaluate execution
        evaluation = self.evaluator.evaluate_execution(
            task=task,
            result=result.output,
            execution_data={
                'steps': result.steps,
                'success_rate': result.success_rate,
                'confidence': result.confidence
            }
        )
        
        # Convert evaluation to dict for storage
        evaluation_dict = {
            'success': evaluation.success,
            'confidence': evaluation.confidence,
            'quality_score': evaluation.quality_score,
            'improvement_areas': evaluation.improvement_areas,
            'notes': evaluation.notes,
            'metadata': evaluation.metadata
        }
        
        # Store experience
        self.memory.store_experience(
            Experience(
                task=task,
                plan=plan,
                result=result,
                evaluation=evaluation_dict,
                timestamp=datetime.now()
            )
        )
        
        return evaluation_dict

    async def _learn_from_execution(self,
                                  task: str,
                                  plan: ExecutionPlan,
                                  result: ExecutionResult,
                                  evaluation: Dict[str, Any]) -> None:
        """Learn from task execution"""
        self.learner.learn_from_execution(
            task=task,
            execution_data={
                'plan': plan,
                'steps': result.steps,
                'success': result.success
            },
            evaluation_result=evaluation
        )
