from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
from datetime import datetime
from planning.task_planner import TaskPlan, PlanStep, TaskType
from .utils.temporal_processor import TemporalProcessor

# Enhance logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExecutionContext:
    """Execution context for better tracking and adaptation"""
    temporal_context: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    patterns: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=dict)

    def update_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value
        
    def add_to_history(self, entry: Dict[str, Any]) -> None:
        self.history.append({**entry, 'timestamp': datetime.now()})

@dataclass
class StepResult:
    success: bool
    output: Any
    error: Optional[str] = None
    tool_name: Optional[str] = None
    metrics: Dict[str, Any] = None
    context: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    retries: int = 0

@dataclass
class ExecutionResult:
    success: bool = False
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    timing: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.output, dict):
            self.output = {"results": [str(self.output)]}
        elif "results" not in self.output:
            self.output["results"] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "success": bool(self.success),
            "output": self.output,
            "confidence": float(self.confidence),
            "success_rate": float(self.success_rate),
            "steps": self.steps,
            "execution_metrics": self.execution_metrics or {},
            "partial_results": self.partial_results
        }

    def add_timing(self, phase: str, duration: float) -> None:
        self.timing[phase] = duration

class ExecutionStrategy:
    """Flexible execution strategy handler"""
    def __init__(self, parallel: bool = True, max_retries: int = 3):
        self.parallel = parallel
        self.max_retries = max_retries
        self.timeout = 60
        self.fallback_handlers = {}

    def set_timeout(self, timeout: int) -> None:
        self.timeout = timeout

    async def execute(self, step: PlanStep, tool: Any, context: ExecutionContext) -> StepResult:
        start_time = asyncio.get_event_loop().time()
        retries = 0
        
        while retries <= self.max_retries:
            try:
                result = await asyncio.wait_for(
                    tool.execute(**step.params),
                    timeout=self.timeout
                )
                
                execution_time = asyncio.get_event_loop().time() - start_time
                return StepResult(
                    success=True,
                    output=result,
                    tool_name=step.tool,
                    context={'step_id': step.id},
                    execution_time=execution_time,
                    retries=retries
                )
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    break
                await asyncio.sleep(1 * retries)
                
        return StepResult(
            success=False,
            output=None,
            error=f"Execution failed after {retries} retries",
            tool_name=step.tool,
            context={'step_id': step.id},
            execution_time=asyncio.get_event_loop().time() - start_time,
            retries=retries
        )

class Executor:
    def __init__(self, tools: Dict[str, Any], parallel: bool = True):
        self.tools = tools
        self.execution_strategy = ExecutionStrategy(parallel=parallel)
        self._execution_cache = {}
        self._step_metrics = {}
        self.temporal_processor = TemporalProcessor()
        self.context = ExecutionContext()
        self.logger = logging.getLogger(__name__)

    async def execute_plan(self, plan: TaskPlan, model: Any, max_steps: int) -> ExecutionResult:
        """Execute plan with enhanced context awareness and adaptability"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Update execution context
            self.context.temporal_context = datetime.now()
            self.context.add_to_history({
                'action': 'plan_execution_start',
                'plan_id': id(plan),
                'steps': len(plan.steps)
            })

            # Execute steps with dependency handling
            results = await self._execute_with_dependencies(
                plan.steps[:max_steps],
                model,
                self.context
            )

            # Process and combine results
            success_rate = self._calculate_success_rate(results)
            confidence = self._calculate_confidence(results, plan)
            
            # Update execution statistics
            execution_time = asyncio.get_event_loop().time() - start_time
            self.context.execution_stats.update({
                'total_time': execution_time,
                'success_rate': success_rate,
                'confidence': confidence
            })

            return ExecutionResult(
                success=any(r.success for r in results),
                output=self._combine_results(results, plan.metadata.get("task_type")),
                confidence=confidence,
                success_rate=success_rate,
                steps=[self._format_step_result(step, result) 
                       for step, result in zip(plan.steps, results)],
                context=self.context,
                timing={'total_execution': execution_time}
            )

        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}", exc_info=True)
            return ExecutionResult(
                success=False,
                output={"results": []},
                confidence=0.0,
                success_rate=0.0,
                steps=[{'error': str(e)}],
                context=self.context,
                timing={'total_execution': asyncio.get_event_loop().time() - start_time}
            )

    async def _execute_with_dependencies(
        self,
        steps: List[PlanStep],
        model: Any,
        context: ExecutionContext
    ) -> List[StepResult]:
        """Enhanced dependency-aware execution with context"""
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
            if self.execution_strategy.parallel:
                step_results = await asyncio.gather(*[
                    self.execution_strategy.execute(step, self.tools[step.tool], context) for step in executable_steps
                ])
            else:
                step_results = []
                for step in executable_steps:
                    result = await self.execution_strategy.execute(step, self.tools[step.tool], context)
                    step_results.append(result)

            # Update tracking
            results.extend(step_results)
            for step in executable_steps:
                completed_steps.add(step.id)
                pending_steps.remove(step)

            # Update metrics
            context.update_metric('completed_steps', len(completed_steps))
            context.update_metric('failed_steps', sum(1 for r in results if not r.success))

        return results

    async def execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> ExecutionResult:
        start_time = datetime.now()
        
        try:
            tool_name = step.get('tool')
            if not tool_name:
                raise ValueError("No tool specified for step")

            tool = context.get('tools', {}).get(tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")

            # Prepare parameters
            params = {
                'query': context.get('query', ''),
                **step.get('params', {})
            }

            # Execute tool with proper async handling
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**params)
            else:
                result = await asyncio.to_thread(tool.execute, **params)

            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExecutionResult(
                success=True,
                output=result,
                timing={'execution_time': execution_time},
                steps=[{
                    'tool': tool_name,
                    'status': 'completed',
                    'execution_time': execution_time
                }]
            )

        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                error=str(e),
                steps=[{
                    'tool': step.get('tool', 'unknown'),
                    'status': 'failed',
                    'error': str(e)
                }]
            )

    async def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single step with proper async handling"""
        try:
            tool_name = step.get('tool')
            tool = self.tools.get(tool_name)
            
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")

            result = await tool.execute(
                query=context.get('task', ''),
                operation=step.get('action', 'generate'),
                context=context
            )

            return result if isinstance(result, dict) else {
                'success': False,
                'error': 'Invalid tool response'
            }

        except Exception as e:
            return {
                'success': False, 
                'error': str(e)
            }

    async def execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> ExecutionResult:
        results = []
        for step in plan:
            result = await self.execute_step(step, context)
            results.append(result)
            if not result.success:
                break
                
        return ExecutionResult(
            success=all(r.success for r in results),
            output={'results': [r.output for r in results]},
            steps=[step for r in results for step in r.steps]
        )

    def _calculate_confidence(self, results: List[StepResult], plan: TaskPlan) -> float:
        """Enhanced confidence calculation with context consideration"""
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

    def _combine_results(self, results: List[StepResult], task_type: Optional[TaskType] = None) -> Dict[str, Any]:
        """Improved result combination with better type handling"""
        if not results:
            return {"results": []}
            
        successful_outputs = [r.output for r in results if r.success and r.output]
        
        if task_type == TaskType.FACTUAL_QUERY:
            # For factual queries, focus on direct answer
            for output in successful_outputs:
                if isinstance(output, dict) and output.get("direct_answer"):
                    return {
                        "direct_answer": output["direct_answer"],
                        "results": output.get("results", [])
                    }
                    
        elif task_type == TaskType.RESEARCH:
            # Combine research results
            all_results = []
            for output in successful_outputs:
                if isinstance(output, dict) and "results" in output:
                    all_results.extend(output["results"])
            return {"results": all_results}
            
        if task_type == TaskType.FACTUAL_QUERY:
            # For factual queries, focus on direct answer
            direct_answers = [out.get("direct_answer") for out in successful_outputs if isinstance(out, dict)]
            if direct_answers:
                return {
                    "direct_answer": direct_answers[0],
                    "supporting_info": direct_answers[1:],
                    "results": successful_outputs
                }
                
        elif task_type == TaskType.CONTENT:
            # For content tasks, combine text content
            content_parts = []
            for output in successful_outputs:
                if isinstance(output, dict) and "content" in output:
                    content_parts.append(output["content"])
            return {
                "content": "\n\n".join(content_parts),
                "type": "article",
                "results": successful_outputs
            }
            
        # Handle different result types
        if task_type == TaskType.CODE:
            return {
                "code": successful_outputs[0] if successful_outputs else None,
                "results": successful_outputs
            }
        elif task_type == TaskType.DATA:
            return {
                "data": successful_outputs[0] if successful_outputs else None,
                "results": successful_outputs
            }
        else:
            # For research tasks, combine all results
            combined_results = []
            for output in successful_outputs:
                if isinstance(output, dict):
                    if "results" in output:
                        combined_results.extend(output["results"])
                    else:
                        combined_results.append(output)
                else:
                    combined_results.append(str(output))
                    
            return {"results": combined_results}

    def _calculate_success_rate(self, results: List[StepResult]) -> float:
        """Calculate success rate with validation"""
        if not results:
            return 0.0
            
        successes = sum(1 for r in results 
                       if r.success and r.output is not None 
                       and (isinstance(r.output, dict) and r.output.get("results")))
                       
        return successes / len(results)

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
