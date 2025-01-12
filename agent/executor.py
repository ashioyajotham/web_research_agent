from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio
import logging
from .planner import ExecutionPlan, ExecutionStep

# Add logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StepResult:
    success: bool
    output: Any
    error: Optional[str] = None
    tool_name: Optional[str] = None

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
        """Execute a plan and handle results"""
        try:
            results = []
            if self.parallel:
                results = await self._execute_parallel(plan.steps[:max_steps])
            else:
                results = await self._execute_sequential(plan.steps[:max_steps])

            # Log execution results
            for idx, result in enumerate(results):
                logger.info(f"Step {idx + 1} result: success={result.success}, error={result.error}")

            # Calculate success rate
            success_rate = sum(1 for r in results if r.success) / len(results) if results else 0
            
            # Combine outputs from successful steps
            combined_output = self._combine_results(results)
            
            # Log final output
            logger.info(f"Plan execution completed: success_rate={success_rate}, has_output={combined_output is not None}")

            return ExecutionResult(
                success=any(r.success for r in results),  # Changed from all() to any()
                output=combined_output,
                confidence=plan.confidence if success_rate > 0 else 0.0,
                success_rate=success_rate,
                steps=[{
                    'type': str(step.type.value),
                    'description': step.description,
                    'tool': step.tool,
                    'success': result.success,
                    'error': result.error,
                    'result': result.output
                } for step, result in zip(plan.steps, results)]
            )
        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                output=None,
                confidence=0.0,
                success_rate=0.0,
                steps=[{'error': str(e)}]
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
        """Execute a single step with better error handling"""
        try:
            if step.tool not in self.tools:
                raise KeyError(f"Tool '{step.tool}' not found")
            
            tool = self.tools[step.tool]
            logger.info(f"Executing tool: {step.tool} with params: {step.params}")
            
            result = await tool.execute(**step.params)
            
            if result is None:
                return StepResult(
                    success=False,
                    output=None,
                    error="Tool returned None",
                    tool_name=step.tool
                )
                
            return StepResult(
                success=True,
                output=result,
                tool_name=step.tool
            )
            
        except Exception as e:
            logger.error(f"Step execution failed: {str(e)}", exc_info=True)
            return StepResult(
                success=False,
                output=None,
                error=str(e),
                tool_name=step.tool
            )

    def _combine_results(self, results: List[StepResult]) -> Any:
        """Combine results with better handling of failed steps"""
        successful_outputs = [r.output for r in results if r.success and r.output is not None]
        
        if not successful_outputs:
            return None
            
        if len(successful_outputs) == 1:
            return successful_outputs[0]
            
        # Combine multiple outputs into a list
        return successful_outputs
