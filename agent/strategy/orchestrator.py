from typing import List, Dict, Any, Tuple
from .base import Strategy, StrategyResult

class StrategyOrchestrator:
    def __init__(self, strategies: List[Strategy]):
        self.strategies = strategies
        self.execution_history = []
        self.strategy_metrics = {}

    async def execute_best_strategy(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        # Score each strategy's suitability
        strategy_scores = [(strategy, strategy.can_handle(task)) 
                         for strategy in self.strategies]
        
        # Sort by score and historical performance
        ranked_strategies = self._rank_strategies(strategy_scores, task)
        
        # Try strategies in order until success
        for strategy, score in ranked_strategies:
            try:
                result = await strategy.execute(task, context)
                self._update_metrics(strategy, result)
                
                if result.success:
                    return result
                    
            except Exception as e:
                continue
                
        return StrategyResult(success=False, error="All strategies failed")

    def _rank_strategies(self, 
                        scores: List[Tuple[Strategy, float]], 
                        task: str) -> List[Tuple[Strategy, float]]:
        """Rank strategies based on scores and historical performance"""
        ranked = []
        for strategy, base_score in scores:
            # Get historical performance
            metrics = self.strategy_metrics.get(strategy.__class__.__name__, {})
            success_rate = metrics.get('success_rate', 0.5)
            
            # Calculate final score
            final_score = base_score * 0.7 + success_rate * 0.3
            
            ranked.append((strategy, final_score))
            
        return sorted(ranked, key=lambda x: x[1], reverse=True)

    def _update_metrics(self, strategy: Strategy, result: StrategyResult) -> None:
        """Update strategy performance metrics"""
        name = strategy.__class__.__name__
        if name not in self.strategy_metrics:
            self.strategy_metrics[name] = {
                'total_executions': 0,
                'successful_executions': 0,
                'success_rate': 0.0,
                'average_confidence': 0.0
            }
            
        metrics = self.strategy_metrics[name]
        metrics['total_executions'] += 1
        if result.success:
            metrics['successful_executions'] += 1
            
        metrics['success_rate'] = (metrics['successful_executions'] / 
                                 metrics['total_executions'])
        metrics['average_confidence'] = (metrics['average_confidence'] * 0.9 + 
                                       result.confidence * 0.1)  # Moving average
