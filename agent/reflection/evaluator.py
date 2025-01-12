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
    confidence: float
    quality_score: float
    improvement_areas: list[str]
    notes: str
    metadata: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from metadata or main fields"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.metadata.get(key, default)

class Evaluator:
    def __init__(self):
        self.performance_thresholds = {
            'execution_time': 30.0,  # seconds
            'confidence': 0.7,
            'success_rate': 0.8
        }

    def evaluate_execution(self, 
                         task: str,
                         result: Any,
                         execution_data: Dict[str, Any]) -> EvaluationResult:
        """Evaluate the execution of a task"""
        success = execution_data.get('success_rate', 0) > 0.5
        confidence = execution_data.get('confidence', 0.0)
        
        return EvaluationResult(
            success=success,
            confidence=confidence,
            quality_score=self._calculate_quality(result, execution_data),
            improvement_areas=self._identify_improvements(execution_data),
            notes=self._generate_notes(task, result),
            metadata=execution_data
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

    def _identify_improvements(self, execution_data: Dict[str, Any]) -> list[str]:
        """Identify areas for improvement"""
        improvements = []
        if execution_data.get('success_rate', 0) < 1.0:
            improvements.append("Increase step success rate")
        if execution_data.get('confidence', 0) < 0.8:
            improvements.append("Improve confidence level")
        return improvements

    def _generate_notes(self, task: str, result: Any) -> str:
        """Generate evaluation notes"""
        if not result:
            return "No results generated"
        return f"Task completed with result available"

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

    def _calculate_quality(self, result: Any, execution_data: Dict[str, Any]) -> float:
        """Calculate quality score based on multiple factors"""
        if not result:
            return 0.0

        # Calculate base metrics
        metrics = self._calculate_metrics(execution_data)
        
        # Calculate component scores
        execution_score = self._normalize_time_score(metrics.execution_time)
        success_score = metrics.success_rate
        confidence_score = metrics.average_confidence if metrics.average_confidence else execution_data.get('confidence', 0.0)
        
        # Tool diversity bonus (reward using multiple tools appropriately)
        tool_diversity = len(metrics.tool_usage_counts) / max(len(execution_data.get('steps', [])), 1)
        
        # Combine scores with weights
        weights = {
            'execution': 0.2,
            'success': 0.4,
            'confidence': 0.3,
            'diversity': 0.1
        }
        
        quality_score = (
            execution_score * weights['execution'] +
            success_score * weights['success'] +
            confidence_score * weights['confidence'] +
            tool_diversity * weights['diversity']
        )
        
        return min(1.0, max(0.0, quality_score))
