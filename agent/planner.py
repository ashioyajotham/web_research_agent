from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
import json

class StepType(str, Enum):  # Make it inherit from str
    RESEARCH = "research"
    CODE = "code"
    ANALYSIS = "analysis"

    def __str__(self):
        return self.value

@dataclass
class ExecutionStep:
    type: StepType
    description: str
    tool: str
    params: Dict[str, Any]

@dataclass
class ExecutionPlan:
    steps: List[ExecutionStep]
    estimated_time: float
    confidence: float

class Planner:
    def create_plan(self, task: str, experiences: List[Any]) -> ExecutionPlan:
        # Analyze task and create execution plan
        steps = self._analyze_task(task, experiences)
        
        return ExecutionPlan(
            steps=steps,
            estimated_time=self._estimate_execution_time(steps),
            confidence=self._calculate_plan_confidence(steps)
        )

    def _analyze_task(self, task: str, experiences: List[Any]) -> List[ExecutionStep]:
        """Analyze task and determine required steps"""
        steps = []
        task_lower = task.lower()
        
        # Research/Information tasks
        if any(keyword in task_lower for keyword in ['what', 'how', 'why', 'find', 'search', 'research', 'summarize']):
            steps.append(ExecutionStep(
                type=StepType.RESEARCH,
                description="Perform web research",
                tool="google_search",
                params={"query": task}
            ))
        
        # Code generation tasks
        if any(keyword in task_lower for keyword in ['implement', 'create', 'write', 'generate', 'code', 'function', 'script']):
            steps.append(ExecutionStep(
                type=StepType.CODE,
                description="Generate code implementation",
                tool="code_generator",
                params={"prompt": task}
            ))
        
        # Analysis tasks
        if any(keyword in task_lower for keyword in ['analyze', 'analyse', 'evaluate', 'assess']):
            steps.append(ExecutionStep(
                type=StepType.ANALYSIS,
                description="Perform analysis",
                tool="code_analysis",
                params={"code": task}
            ))

        # If no steps determined, default to research
        if not steps:
            steps.append(ExecutionStep(
                type=StepType.RESEARCH,
                description="Perform web research",
                tool="google_search",
                params={"query": task}
            ))

        return steps

    def _estimate_execution_time(self, steps: List[ExecutionStep]) -> float:
        # Simple estimation based on step types
        time_estimates = {
            StepType.RESEARCH: 30,
            StepType.CODE: 20,
            StepType.ANALYSIS: 15
        }
        return sum(time_estimates[step.type] for step in steps)

    def _calculate_plan_confidence(self, steps: List[ExecutionStep]) -> float:
        # Simple confidence calculation
        if not steps:
            return 0.0
        return 0.8  # Default confidence
