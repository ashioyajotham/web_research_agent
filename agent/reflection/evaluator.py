from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time

@dataclass
class ExecutionMetrics:
    execution_time: float
    tool_usage_counts: Dict[str, int]
    steps_taken: int
    success_rate: float
    average_confidence: float

@dataclass
class EvaluationResult:
    success: bool
    performance_score: float
    areas_for_improvement: List[str]
    metrics: ExecutionMetrics
    suggestions: Dict[str, Any]

class Evaluator:
    def __init__(self):
        self.performance_thresholds = {
            'execution_time': 30.0,  # seconds
            'confidence': 0.7,
            'success_rate': 0.8
        }

    def evaluate_execution(self, 
                         task: str,
                         result: str,
                         execution_data: Dict[str, Any]) -> EvaluationResult:
        """Evaluate the execution of a task"""
        metrics = self._calculate_metrics(execution_data)
        performance_score = self._calculate_performance_score(metrics)
        improvements = self._identify_improvements(metrics, execution_data)
        
        return EvaluationResult(
            success=metrics.success_rate >= self.performance_thresholds['success_rate'],
            performance_score=performance_score,
            areas_for_improvement=improvements,
            metrics=metrics,
            suggestions=self._generate_suggestions(improvements, metrics)
        )

    def _calculate_metrics(self, execution_data: Dict[str, Any]) -> ExecutionMetrics:
        """Calculate execution metrics"""
        return ExecutionMetrics(
            execution_time=execution_data.get('execution_time', 0.0),
            tool_usage_counts=self._count_tool_usage(execution_data.get('steps', [])),
            steps_taken=len(execution_data.get('steps', [])),
            success_rate=execution_data.get('success_rate', 0.0),
            average_confidence=execution_data.get('average_confidence', 0.0)
        )

    def _count_tool_usage(self, steps: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count how many times each tool was used"""
        counts: Dict[str, int] = {}
        for step in steps:
            tool = step.get('tool')
            if tool:
                counts[tool] = counts.get(tool, 0) + 1
        return counts

    def _calculate_performance_score(self, metrics: ExecutionMetrics) -> float:
        """Calculate overall performance score"""
        scores = [
            self._normalize_time_score(metrics.execution_time),
            metrics.success_rate,
            metrics.average_confidence
        ]
        return sum(scores) / len(scores)

    def _normalize_time_score(self, execution_time: float) -> float:
        """Convert execution time to a 0-1 score"""
        threshold = self.performance_thresholds['execution_time']
        return max(0.0, min(1.0, 1.0 - (execution_time / threshold)))

    def _identify_improvements(self, 
                            metrics: ExecutionMetrics, 
                            execution_data: Dict[str, Any]) -> List[str]:
        """Identify areas needing improvement"""
        improvements = []
        
        if metrics.execution_time > self.performance_thresholds['execution_time']:
            improvements.append("execution_time")
            
        if metrics.average_confidence < self.performance_thresholds['confidence']:
            improvements.append("confidence")
            
        if metrics.success_rate < self.performance_thresholds['success_rate']:
            improvements.append("success_rate")
            
        if metrics.steps_taken > 10:
            improvements.append("steps_optimization")
            
        return improvements

    def _generate_suggestions(self, 
                           improvements: List[str], 
                           metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Generate improvement suggestions"""
        suggestions = {}
        
        improvement_strategies = {
            "execution_time": self._suggest_time_optimization,
            "confidence": self._suggest_confidence_improvement,
            "success_rate": self._suggest_success_improvement,
            "steps_optimization": self._suggest_steps_optimization
        }
        
        for improvement in improvements:
            if improvement in improvement_strategies:
                suggestions[improvement] = improvement_strategies[improvement](metrics)
                
        return suggestions

    def _suggest_time_optimization(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Suggest ways to optimize execution time"""
        suggestions = {
            "description": "Execution time optimization needed",
            "recommendations": [
                "Consider caching frequently used search results",
                "Optimize tool selection based on execution time",
                "Implement parallel tool execution where possible"
            ]
        }
        
        if metrics.tool_usage_counts.get('web_scraper', 0) > 3:
            suggestions["recommendations"].append(
                "Reduce web scraping operations by combining requests"
            )
            
        return suggestions

    def _suggest_confidence_improvement(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Suggest ways to improve confidence"""
        return {
            "description": "Confidence improvement needed",
            "recommendations": [
                "Implement cross-verification of results",
                "Use multiple sources for critical information",
                "Add fact-checking steps for important claims"
            ]
        }

    def _suggest_success_improvement(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Suggest ways to improve success rate"""
        return {
            "description": "Success rate improvement needed",
            "recommendations": [
                "Implement better error handling",
                "Add fallback strategies for failed steps",
                "Improve task decomposition"
            ]
        }

    def _suggest_steps_optimization(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Suggest ways to optimize number of steps"""
        return {
            "description": "Step count optimization needed",
            "recommendations": [
                "Combine related steps",
                "Implement better task planning",
                "Use more efficient search strategies"
            ]
        }
