from typing import List, Dict, Any, Optional, Tuple
import re
from .base import Strategy, StrategyResult
from datetime import datetime
from dateutil import parser
from dataclasses import dataclass, field

@dataclass
class ResearchPattern:
    """Dynamic research pattern that can adapt based on results"""
    pattern: str
    weight: float = 1.0
    success_count: int = 0
    fail_count: int = 0
    contexts: List[str] = field(default_factory=list)
    
    def update_effectiveness(self, success: bool, context: str = None):
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        if context:
            self.contexts.append(context)
            self.contexts = self.contexts[-10:]  # Keep last 10 contexts
            
    @property
    def effectiveness_score(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return (self.success_count / total) * self.weight

class ResearchStrategyV2(Strategy):
    def __init__(self):
        super().__init__()
        
        # Dynamic patterns that can learn
        self.dynamic_patterns = {
            'extraction': [
                ResearchPattern(r'(?P<date>\w+\s+\d{1,2},?\s+\d{4})\s*[:-]\s*(?P<event>.*?)(?=\w+\s+\d{1,2},?\s+\d{4}|\Z)'),
                ResearchPattern(r'(?:in|on|during)\s+(?P<date>\w+\s+\d{4})[,:\s]+(?P<event>.*?)(?=(?:in|on|during)\s+\w+\s+\d{4}|\Z)'),
                ResearchPattern(r'(?P<date>\d{4})\s*:\s*(?P<event>.*?)(?=\d{4}:|\Z)')
            ],
            'metrics': [
                ResearchPattern(r'(\d+(?:\.\d+)?)\s*(?:percent|%)'),
                ResearchPattern(r'(?:USD|€|£)?\s*(\d+(?:\.\d+)?)\s*(?:billion|million)'),
                ResearchPattern(r'(\d+(?:\.\d+)?)\s*(?:kg|km|m|ft|lbs)')
            ]
        }
        
        # Adaptive search phases that can be reordered based on effectiveness
        self.search_phases = [
            ('broad', self._initial_broad_search, 1.0),
            ('recent', self._recent_news_search, 1.0),
            ('specific', self._specific_detail_search, 1.0),
            ('organization', self._organization_search, 1.0)
        ]
        
        # Dynamic credibility scoring that learns from results
        self.credibility_factors = {
            'domain': {
                'academic': 0.9,
                'official': 0.8,
                'industry': 0.7,
                'news': 0.6
            },
            'content': {
                'data_richness': 0.3,
                'citation_count': 0.2,
                'date_presence': 0.1
            }
        }
        
        # Metric extraction integration
        self.metric_categories = {
            'numerical': ['percent', 'amount', 'quantity'],
            'temporal': ['duration', 'frequency', 'period'],
            'comparative': ['increase', 'decrease', 'change']
        }

    async def execute(self, task: str, context: Dict[str, Any]) -> StrategyResult:
        try:
            # Get metric extractor from context
            metric_extractor = context.get('tools', {}).get('metric_extractor')
            
            # Dynamic phase execution based on task analysis
            complexity = self._analyze_task_complexity(task)
            phases = self._select_phases(complexity)
            
            all_results = []
            for phase_name, phase_func, weight in phases:
                try:
                    results = await phase_func(task, context.get('tools', {}))
                    if results:
                        # Extract metrics if available
                        if metric_extractor:
                            for result in results:
                                metrics = metric_extractor.extract_metrics(
                                    result.get('event', ''),
                                    self._detect_metric_types(result.get('event', ''))
                                )
                                if metrics:
                                    result['metrics'] = metrics
                        
                        # Update pattern effectiveness
                        self._update_pattern_effectiveness(phase_name, True, task)
                        all_results.extend(results)
                    else:
                        self._update_pattern_effectiveness(phase_name, False, task)
                except Exception as e:
                    self._update_pattern_effectiveness(phase_name, False, task)
                    continue
            
            if not all_results:
                return StrategyResult(success=False, error="No results found")
            
            # Process and validate results
            processed_results = await self._process_results(all_results, context)
            
            return StrategyResult(
                success=True,
                output=processed_results,
                confidence=self._calculate_confidence(processed_results)
            )
            
        except Exception as e:
            return StrategyResult(success=False, error=str(e))

    async def _process_results(self, results: List[Dict], context: Dict) -> Dict[str, Any]:
        """Process results with metric integration and validation"""
        # Deduplicate and sort results
        unique_results = self._deduplicate_events(results)
        
        # Extract and validate metrics
        processed_results = []
        for result in unique_results:
            metrics = result.get('metrics', [])
            if metrics:
                # Validate metrics against expected ranges
                validated_metrics = self._validate_metrics(metrics)
                result['validated_metrics'] = validated_metrics
            
            # Calculate result confidence
            result['confidence'] = self._calculate_result_confidence(result)
            processed_results.append(result)
        
        return {
            'timeline': self._group_events(processed_results),
            'major_milestones': self._extract_major_milestones(processed_results),
            'metrics_summary': self._summarize_metrics(processed_results),
            'sources': self._format_sources(processed_results),
            'patterns_used': self._get_effective_patterns()
        }

    def _validate_metrics(self, metrics: List[Tuple[float, str]]) -> List[Dict[str, Any]]:
        """Validate extracted metrics against expected ranges"""
        validated = []
        for value, unit in metrics:
            confidence = 1.0
            
            # Check for anomalous values based on unit
            if unit == '%' and (value < 0 or value > 100):
                confidence *= 0.5
            elif unit in ['tCO2e', 'kg'] and value < 0:
                confidence *= 0.5
            
            validated.append({
                'value': value,
                'unit': unit,
                'confidence': confidence
            })
        
        return validated

    # ...existing code...

    def _update_pattern_effectiveness(self, phase: str, success: bool, context: str):
        """Update effectiveness scores for patterns"""
        patterns = self.dynamic_patterns.get(phase, [])
        for pattern in patterns:
            pattern.update_effectiveness(success, context)

    def _get_effective_patterns(self) -> List[Dict[str, Any]]:
        """Get most effective patterns for each category"""
        effective_patterns = {}
        for category, patterns in self.dynamic_patterns.items():
            sorted_patterns = sorted(patterns, key=lambda p: p.effectiveness_score, reverse=True)
            effective_patterns[category] = [
                {'pattern': p.pattern, 'score': p.effectiveness_score}
                for p in sorted_patterns[:3]  # Top 3 most effective
            ]
        return effective_patterns

    def _detect_metric_types(self, text: str) -> Optional[str]:
        """Detect relevant metric types from text"""
        text_lower = text.lower()
        
        for category, indicators in self.metric_categories.items():
            if any(indicator in text_lower for indicator in indicators):
                return category
                
        return None

    def _analyze_task_complexity(self, task: str) -> float:
        """Analyze task complexity for dynamic phase selection"""
        # More sophisticated complexity analysis
        factors = {
            'length': len(task.split()) / 20,  # Normalized by typical length
            'metric_density': self._calculate_metric_density(task),
            'temporal_span': self._calculate_temporal_span(task),
            'domain_specificity': self._calculate_domain_specificity(task)
        }
        
        return sum(factors.values()) / len(factors)

    def _calculate_metric_density(self, text: str) -> float:
        """Calculate density of metric-related terms"""
        metric_indicators = sum(
            text.lower().count(indicator)
            for category in self.metric_categories.values()
            for indicator in category
        )
        return min(1.0, metric_indicators / len(text.split()))

    # ...existing code...
