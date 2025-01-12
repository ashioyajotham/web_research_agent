from dataclasses import dataclass
from typing import List, Dict, Any
import asyncio
from .planner import ExecutionPlan, ExecutionStep

@dataclass
class StepResult:
    success: bool
    output: Any
    error: str = None

@dataclass
class ExecutionResult:
    success: bool
    output: Any
    confidence: float
    success_rate: float
    steps: List[Dict[str, Any]]

class Executor:
    def __init__(self, tools: Dict[str, Any], parallel: bool = True):
        self.tools = tools
        self.parallel = parallel

    async def execute_plan(self, plan: ExecutionPlan, model: Any, max_steps: int) -> ExecutionResult:
        results = []
        
        if self.parallel:
            results = await self._execute_parallel(plan.steps[:max_steps])
        else:
            results = await self._execute_sequential(plan.steps[:max_steps])
            
        success_rate = sum(1 for r in results if r.success) / len(results)
        
        return ExecutionResult(
            success=all(r.success for r in results),
            output=self._combine_results(results),
            confidence=plan.confidence,
            success_rate=success_rate,
            steps=[{
                'type': step.type.value,
                'description': step.description,
                'result': result.output
            } for step, result in zip(plan.steps, results)]
        )

    async def _execute_parallel(self, steps: List[ExecutionStep]) -> List[StepResult]:
        tasks = [self._execute_step(step) for step in steps]
        return await asyncio.gather(*tasks)

    async def _execute_sequential(self, steps: List[ExecutionStep]) -> List[StepResult]:
        results = []
        for step in steps:
            result = await self._execute_step(step)
            results.append(result)
            if not result.success:
                break
        return results

    async def _execute_step(self, step: ExecutionStep) -> StepResult:
        try:
            tool = self.tools[step.tool]
            result = await tool.execute(**step.params)
            return StepResult(success=True, output=result)
        except Exception as e:
            return StepResult(success=False, output=None, error=str(e))

    def _combine_results(self, results: List[StepResult]) -> Any:
        # Combine results from multiple steps
        outputs = [r.output for r in results if r.success]
        return outputs if len(outputs) > 1 else outputs[0] if outputs else None
