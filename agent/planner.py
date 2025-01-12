from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class StepType(Enum):
    RESEARCH = "research"
    CODE = "code"
    ANALYSIS = "analysis"

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
        # Simple task analysis and step generation
        steps = []
        
        if any(keyword in task.lower() for keyword in ['research', 'find', 'search']):
            steps.append(ExecutionStep(
                type=StepType.RESEARCH,
                description="Perform web research",
                tool="google_search",
                params={"query": task}
            ))
            
        if any(keyword in task.lower() for keyword in ['code', 'implement', 'function']):
            steps.append(ExecutionStep(
                type=StepType.CODE,
                description="Generate code",
                tool="code_generator",
                params={"prompt": task}
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
