import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio
import time
import google.generativeai as genai
from datetime import datetime

from .memory import Memory, Experience
from .planner import Planner, ExecutionPlan
from .executor import Executor, ExecutionResult
from .reflection import Evaluator, Learner
from .utils.prompts import PromptManager
from tools.base import BaseTool

@dataclass
class AgentConfig:
    max_steps: int = 10
    min_confidence: float = 0.7
    timeout: int = 300
    enable_reflection: bool = True
    memory_path: str = "agent_memory.json"
    parallel_execution: bool = True

class Agent:
    def __init__(self, tools: Dict[str, BaseTool], config: Optional[AgentConfig] = None):
        # Initialize components
        self.config = config or AgentConfig()
        self.tools = tools
        self.memory = Memory(self.config.memory_path)
        self.planner = Planner()
        self.executor = Executor(tools, parallel=self.config.parallel_execution)
        self.evaluator = Evaluator()
        self.learner = Learner()
        self.prompt_manager = PromptManager()
        
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
        """Process a single task"""
        async with asyncio.timeout(self.config.timeout):
            try:
                return await self._execute_task(task)
            except asyncio.TimeoutError:
                return {
                    'success': False,
                    'error': 'Task execution timed out',
                    'task': task
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'task': task
                }

    async def _execute_task(self, task: str) -> Dict[str, Any]:
        """Execute task with full pipeline"""
        start_time = time.time()
        
        # Get relevant past experiences
        experiences = self.memory.get_relevant_experiences(task)
        
        # Create and validate plan
        plan = self.planner.create_plan(task, experiences)
        
        # Execute plan
        result = await self.executor.execute_plan(
            plan=plan,
            model=self.model,
            max_steps=self.config.max_steps
        )
        
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
