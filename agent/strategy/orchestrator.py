from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .base import Strategy, StrategyResult
import numpy as np
from functools import lru_cache

@dataclass
class StrategyMetrics:
    success_rate: float
    avg_confidence: float
    avg_execution_time: float
    complexity_handling: float
    adaptability: float

class StrategyOrchestrator:
    def __init__(self, strategies: List[Strategy]):
        self.strategies = strategies
        self.execution_history = []
        self.strategy_metrics = {}
        
        # Enhanced configuration
        self.composition_threshold = 0.7
        self.max_composite_strategies = 3
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.cache_timeout = 300  # 5 minutes
        
        # Enhanced tracking
        self.strategy_performance = {}
        self.task_patterns = {}
        self.strategy_weights = {s.__class__.__name__: 1.0 for s in strategies}

    async def execute_best_strategy(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        """Execute best strategy with dynamic composition"""
        try:
            # Analyze task complexity and requirements
            complexity = self._analyze_task_complexity(task)
            requirements = self._analyze_requirements(task)
            
            # Get candidate strategies
            candidates = self._get_candidate_strategies(task, complexity, requirements)
            
            # Check if task needs composite strategy
            if complexity > self.composition_threshold:
                return await self._execute_composite_strategy(task, candidates, context)
            
            # Execute single best strategy with fallback
            return await self._execute_with_fallback(task, candidates, context)
            
        except Exception as e:
            return StrategyResult(success=False, error=str(e))

    @lru_cache(maxsize=100)
    def _analyze_task_complexity(self, task: str) -> float:
        """Optimized task complexity analysis"""
        # Simplified complexity scoring
        complexity_indicators = {
            'research_terms': ['find', 'search', 'research', 'look up'],
            'analysis_terms': ['analyze', 'compare', 'evaluate', 'assess'],
            'synthesis_terms': ['combine', 'summarize', 'conclude'],
            'validation_terms': ['verify', 'validate', 'confirm', 'check']
        }
        
        task_lower = task.lower()
        score = 0.0
        
        for category, terms in complexity_indicators.items():
            matches = sum(1 for term in terms if term in task_lower)
            score += matches * 0.2
        
        return min(1.0, score)

    def _analyze_requirements(self, task: str) -> Dict[str, float]:
        """Analyze task requirements for strategy matching"""
        requirements = {
            'research': 0.0,
            'analysis': 0.0,
            'synthesis': 0.0,
            'validation': 0.0
        }
        
        # Update requirements based on task characteristics
        words = task.lower().split()
        
        if any(w in words for w in ['find', 'search', 'look', 'research']):
            requirements['research'] = 0.8
            
        if any(w in words for w in ['analyze', 'compare', 'evaluate']):
            requirements['analysis'] = 0.7
            
        if any(w in words for w in ['summarize', 'conclude', 'synthesize']):
            requirements['synthesis'] = 0.6
            
        if any(w in words for w in ['verify', 'validate', 'confirm']):
            requirements['validation'] = 0.7
            
        return requirements

    async def _execute_composite_strategy(self, task: str, candidates: List[Tuple[Strategy, float]], context: Dict[str, Any]) -> StrategyResult:
        """Enhanced composite strategy execution"""
        results = []
        total_confidence = 0.0
        
        # Apply strategy weights
        weighted_candidates = [
            (s, score * self.strategy_weights[s.__class__.__name__])
            for s, score in candidates
        ]
        
        sorted_candidates = sorted(weighted_candidates, key=lambda x: x[1], reverse=True)
        top_candidates = sorted_candidates[:self.max_composite_strategies]
        
        # Execute strategies and collect results
        for strategy, score in top_candidates:
            try:
                result = await strategy.execute(task, context)
                results.append(result)
                
                if result.success:
                    total_confidence += result.confidence * score
                    
            except Exception:
                continue
                
        # Combine results
        combined_result = self._combine_results(results, total_confidence)
        return combined_result

    def _combine_results(self, results: List[StrategyResult], total_confidence: float) -> StrategyResult:
        """Combine results from multiple strategies"""
        if not results:
            return StrategyResult(success=False, error="No results to combine")
            
        # Combine outputs
        combined_output = {}
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return StrategyResult(success=False, error="All strategies failed")
            
        # Merge different types of outputs
        for result in successful_results:
            for key, value in result.output.items():
                if key not in combined_output:
                    combined_output[key] = []
                if isinstance(value, list):
                    combined_output[key].extend(value)
                else:
                    combined_output[key].append(value)
                    
        # Deduplicate and sort
        for key in combined_output:
            if isinstance(combined_output[key], list):
                combined_output[key] = list(dict.fromkeys(combined_output[key]))
                
        return StrategyResult(
            success=True,
            output=combined_output,
            confidence=total_confidence / len(successful_results)
        )

    async def _execute_with_fallback(self, task: str, candidates: List[Tuple[Strategy, float]], context: Dict[str, Any]) -> StrategyResult:
        """Execute strategy with automatic fallback"""
        for strategy, score in candidates:
            try:
                result = await strategy.execute(task, context)
                
                # Update strategy metrics
                self._update_strategy_metrics(strategy, result)
                
                if result.success and result.confidence >= self.composition_threshold:
                    return result
                    
            except Exception:
                continue
                
        # If all strategies fail, try general fallback
        return await self._execute_fallback_strategy(task, context)

    def _update_strategy_metrics(self, strategy: Strategy, result: StrategyResult):
        """Enhanced metrics updating"""
        name = strategy.__class__.__name__
        if name not in self.strategy_metrics:
            self.strategy_metrics[name] = StrategyMetrics(
                success_rate=0.0,
                avg_confidence=0.0,
                avg_execution_time=0.0,
                complexity_handling=0.0,
                adaptability=0.0
            )
            
        metrics = self.strategy_metrics[name]
        
        # Update with exponential moving average
        metrics.success_rate = (1 - self.learning_rate) * metrics.success_rate + self.learning_rate * float(result.success)
        metrics.avg_confidence = (1 - self.learning_rate) * metrics.avg_confidence + self.learning_rate * result.confidence
        
        # Update strategy weights based on performance
        if result.success:
            self.strategy_weights[name] *= (1 + self.learning_rate * result.confidence)
        else:
            self.strategy_weights[name] *= (1 - self.learning_rate * 0.5)
        
        # Normalize weights
        total_weight = sum(self.strategy_weights.values())
        for k in self.strategy_weights:
            self.strategy_weights[k] /= total_weight
        
        # Update task patterns
        self._update_task_patterns(strategy, result)

    def _update_task_patterns(self, strategy: Strategy, result: StrategyResult):
        """Learn task patterns for better strategy selection"""
        name = strategy.__class__.__name__
        if name not in self.task_patterns:
            self.task_patterns[name] = {
                'successful_patterns': [],
                'failed_patterns': []
            }
            
        # Extract and store patterns
        patterns = self._extract_task_patterns(result.task)
        if result.success:
            self.task_patterns[name]['successful_patterns'].extend(patterns)
        else:
            self.task_patterns[name]['failed_patterns'].extend(patterns)
