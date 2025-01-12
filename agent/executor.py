from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio
import logging
from planning.task_planner import TaskPlan, PlanStep, TaskType

# Add logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StepResult:
    success: bool
    output: Any
    error: Optional[str] = None
    tool_name: Optional[str] = None
    metrics: Dict[str, Any] = None
    context: Dict[str, Any] = None

@dataclass
class ExecutionResult:
    success: bool
    output: Any
    confidence: float
    success_rate: float
    steps: List[Dict[str, Any]]
    partial_results: Dict[str, Any] = None
    execution_metrics: Dict[str, Any] = None

class Executor:
    def __init__(self, tools: Dict[str, Any], parallel: bool = True):
        self.tools = tools
        self.parallel = parallel
        self._execution_cache = {}
        self._step_metrics = {}

    async def execute_plan(self, plan: TaskPlan, model: Any, max_steps: int) -> ExecutionResult:
        """Execute a plan and handle results"""
        try:
            # Track metrics for this execution
            execution_metrics = {
                'start_time': asyncio.get_event_loop().time(),
                'completed_steps': 0,
                'failed_steps': 0,
                'total_steps': len(plan.steps)
            }

            # Execute steps with dependency handling
            results = await self._execute_with_dependencies(
                plan.steps[:max_steps], 
                model,
                execution_metrics
            )

            # Calculate success metrics
            success_rate = self._calculate_success_rate(results)
            execution_metrics['success_rate'] = success_rate
            execution_metrics['end_time'] = asyncio.get_event_loop().time()
            
            # Combine and process results
            combined_output = self._combine_results(results, plan.metadata.get("task_type"))
            
            return ExecutionResult(
                success=any(r.success for r in results),
                output=combined_output,
                confidence=self._calculate_confidence(results, plan),
                success_rate=success_rate,
                steps=[self._format_step_result(step, result) 
                       for step, result in zip(plan.steps, results)],
                execution_metrics=execution_metrics,
                partial_results=self._get_partial_results(results)
            )

        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}", exc_info=True)
            return ExecutionResult(
                success=False,
                output=None,
                confidence=0.0,
                success_rate=0.0,
                steps=[{'error': str(e)}],
                execution_metrics={'error': str(e)}
            )

    async def _execute_with_dependencies(
        self, 
        steps: List[PlanStep],
        model: Any,
        metrics: Dict[str, Any]
    ) -> List[StepResult]:
        """Execute steps respecting dependencies"""
        results = []
        pending_steps = steps.copy()
        completed_steps = set()

        while pending_steps:
            # Find steps whose dependencies are met
            executable_steps = [
                step for step in pending_steps
                if not step.dependencies or all(dep in completed_steps for dep in step.dependencies)
            ]

            if not executable_steps:
                # Handle dependency cycle or invalid dependencies
                logger.error("Dependency resolution failed for remaining steps")
                break

            # Execute available steps
            if self.parallel:
                step_results = await asyncio.gather(*[
                    self._execute_step(step, model) for step in executable_steps
                ])
            else:
                step_results = []
                for step in executable_steps:
                    result = await self._execute_step(step, model)
                    step_results.append(result)

            # Update tracking
            results.extend(step_results)
            for step in executable_steps:
                completed_steps.add(step.id)
                pending_steps.remove(step)

            # Update metrics
            metrics['completed_steps'] = len(completed_steps)
            metrics['failed_steps'] = sum(1 for r in results if not r.success)

        return results

    async def _execute_step(self, step: PlanStep, model: Any) -> StepResult:
        """Execute a single step with enhanced error handling and caching"""
        cache_key = f"{step.type}:{step.tool}:{hash(str(step.params))}"
        
        # Check cache for identical previous executions
        if cache_key in self._execution_cache:
            logger.info(f"Using cached result for step {step.id}")
            return self._execution_cache[cache_key]

        try:
            start_time = asyncio.get_event_loop().time()
            tool = self.tools[step.tool]
            
            # Add execution context
            step.params['model'] = model if step.type in [TaskType.CODE, TaskType.ANALYSIS] else None
            
            result = await tool.execute(**step.params)
            
            # Calculate metrics
            execution_time = asyncio.get_event_loop().time() - start_time
            step_metrics = {
                'execution_time': execution_time,
                'tool': step.tool,
                'type': step.type
            }
            
            step_result = StepResult(
                success=True,
                output=result,
                tool_name=step.tool,
                metrics=step_metrics,
                context={'step_id': step.id}
            )
            
            # Cache successful results
            self._execution_cache[cache_key] = step_result
            self._step_metrics[step.id] = step_metrics
            
            return step_result
            
        except Exception as e:
            logger.error(f"Step execution failed: {str(e)}", exc_info=True)
            return StepResult(
                success=False,
                output=None,
                error=str(e),
                tool_name=step.tool,
                metrics={'error': str(e)},
                context={'step_id': step.id}
            )

    def _calculate_confidence(self, results: List[StepResult], plan: TaskPlan) -> float:
        """Calculate overall execution confidence"""
        if not results:
            return 0.0
            
        # Weight successful results by their tool's confidence
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for result in results:
            if result.success:
                tool_weight = 1.0
                if result.metrics:
                    execution_time = result.metrics.get('execution_time', 0)
                    # Adjust weight based on execution time
                    tool_weight *= max(0.5, 1.0 - (execution_time / 60.0))  # Reduce confidence for long-running steps
                    
                weighted_confidence += plan.confidence * tool_weight
                total_weight += tool_weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0

    def _get_partial_results(self, results: List[StepResult]) -> Dict[str, Any]:
        """Collect partial results from successful steps"""
        partial_results = {}
        
        for result in results:
            if result.success and result.output is not None:
                step_id = result.context.get('step_id', 'unknown')
                partial_results[step_id] = {
                    'output': result.output,
                    'metrics': result.metrics
                }
                
        return partial_results if partial_results else None

    def _combine_results(self, results: List[StepResult], task_type: Optional[TaskType] = None) -> Any:
        """Combine results with better handling of failed steps"""
        successful_outputs = [r.output for r in results if r.success and r.output is not None]
        
        if not successful_outputs:
            return None
            
        if len(successful_outputs) == 1:
            return successful_outputs[0]
            
        # Combine multiple outputs into a list
        return successful_outputs

    def _calculate_success_rate(self, results: List[StepResult]) -> float:
        """Calculate the success rate of the execution"""
        return sum(1 for r in results if r.success) / len(results) if results else 0

    def _format_step_result(self, step: PlanStep, result: StepResult) -> Dict[str, Any]:
        """Format the step result for the final execution result"""
        return {
            'type': str(step.type.value),
            'description': step.description,
            'tool': step.tool,
            'success': result.success,
            'error': result.error,
            'result': result.output,
            'metrics': result.metrics,
            'context': result.context
        }
