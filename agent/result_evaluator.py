"""
Result Evaluation and Adaptive Replanning System
Inspired by modern agent self-reflection capabilities
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class EvaluationResult:
    """Results of evaluating a research step or phase."""
    confidence: float  # 0.0 to 1.0
    completeness: float  # 0.0 to 1.0
    relevance: float  # 0.0 to 1.0
    overall_score: float  # 0.0 to 1.0
    missing_entities: List[str]
    quality_issues: List[str]
    suggested_actions: List[str]
    should_replan: bool


@dataclass
class ReplanningStrategy:
    """Strategy for replanning when objectives aren't met."""
    strategy_type: str  # "expand_search", "refine_query", "change_approach", "additional_phase"
    new_query: Optional[str] = None
    additional_sources: int = 0
    new_phase_description: Optional[str] = None
    explanation: str = ""


class ResultEvaluator:
    """
    Evaluates research results and suggests replanning when objectives aren't met.
    
    This implements the self-reflection capabilities that modern agents need
    for reliable performance across diverse tasks.
    """
    
    def __init__(self):
        self.evaluation_history = []
        self.success_patterns = {}  # Learn from successful research patterns
        self.failure_patterns = {}  # Learn from failed patterns
        
    def evaluate_step_result(self, step_result: Dict[str, Any], 
                           expected_entities: List[str],
                           research_objective: str) -> EvaluationResult:
        """
        Evaluate the result of a single research step.
        
        Args:
            step_result: The output from a tool execution
            expected_entities: List of entity types expected to be found
            research_objective: The objective this step was meant to achieve
        """
        # Extract content from step result
        content = self._extract_content_from_result(step_result)
        
        # Evaluate different dimensions
        confidence = self._assess_confidence(content, step_result)
        completeness = self._assess_completeness(content, expected_entities, research_objective)
        relevance = self._assess_relevance(content, research_objective)
        
        # Overall score is weighted average
        overall_score = (confidence * 0.3 + completeness * 0.4 + relevance * 0.3)
        
        # Identify issues and suggestions
        missing_entities = self._identify_missing_entities(content, expected_entities)
        quality_issues = self._identify_quality_issues(content, step_result)
        suggested_actions = self._generate_action_suggestions(
            overall_score, missing_entities, quality_issues, research_objective
        )
        
        # Decide if replanning is needed
        should_replan = overall_score < 0.6 or len(missing_entities) > len(expected_entities) / 2
        
        result = EvaluationResult(
            confidence=confidence,
            completeness=completeness,
            relevance=relevance,
            overall_score=overall_score,
            missing_entities=missing_entities,
            quality_issues=quality_issues,
            suggested_actions=suggested_actions,
            should_replan=should_replan
        )
        
        # Store for learning
        self.evaluation_history.append({
            "timestamp": datetime.now().isoformat(),
            "objective": research_objective,
            "result": result,
            "content_length": len(content) if content else 0
        })
        
        return result
    
    def evaluate_phase_completion(self, phase_results: List[Dict[str, Any]], 
                                phase_objective: str,
                                required_entities: List[str]) -> EvaluationResult:
        """Evaluate whether a research phase has met its objectives."""
        
        # Aggregate content from all phase results
        all_content = []
        total_confidence = 0.0
        
        for result in phase_results:
            content = self._extract_content_from_result(result)
            if content:
                all_content.append(content)
                total_confidence += self._assess_confidence(content, result)
        
        combined_content = " ".join(all_content)
        avg_confidence = total_confidence / len(phase_results) if phase_results else 0.0
        
        # Evaluate phase completion
        completeness = self._assess_completeness(combined_content, required_entities, phase_objective)
        relevance = self._assess_relevance(combined_content, phase_objective)
        
        overall_score = (avg_confidence * 0.3 + completeness * 0.4 + relevance * 0.3)
        
        missing_entities = self._identify_missing_entities(combined_content, required_entities)
        quality_issues = self._identify_quality_issues_for_phase(phase_results, phase_objective)
        suggested_actions = self._generate_phase_action_suggestions(
            overall_score, missing_entities, quality_issues, phase_objective
        )
        
        should_replan = overall_score < 0.7 or len(missing_entities) > 0
        
        return EvaluationResult(
            confidence=avg_confidence,
            completeness=completeness,
            relevance=relevance,
            overall_score=overall_score,
            missing_entities=missing_entities,
            quality_issues=quality_issues,
            suggested_actions=suggested_actions,
            should_replan=should_replan
        )
    
    def suggest_replanning_strategy(self, evaluation: EvaluationResult, 
                                  original_objective: str,
                                  previous_queries: List[str]) -> ReplanningStrategy:
        """Suggest a specific replanning strategy based on evaluation results."""
        
        if evaluation.completeness < 0.5:
            # Need more comprehensive search
            return ReplanningStrategy(
                strategy_type="expand_search",
                additional_sources=5,
                explanation=f"Completeness score {evaluation.completeness:.2f} indicates insufficient coverage. Need broader search."
            )
        
        elif evaluation.relevance < 0.6:
            # Need more targeted search
            return ReplanningStrategy(
                strategy_type="refine_query",
                new_query=self._generate_refined_query(original_objective, evaluation.missing_entities),
                explanation=f"Relevance score {evaluation.relevance:.2f} indicates off-target results. Need more focused query."
            )
        
        elif len(evaluation.missing_entities) > 0:
            # Need entity-focused search
            return ReplanningStrategy(
                strategy_type="additional_phase",
                new_phase_description=f"Entity-focused search for: {', '.join(evaluation.missing_entities)}",
                new_query=self._generate_entity_focused_query(evaluation.missing_entities, original_objective),
                explanation=f"Missing critical entities: {', '.join(evaluation.missing_entities)}"
            )
        
        else:
            # Change approach entirely
            return ReplanningStrategy(
                strategy_type="change_approach",
                new_query=self._generate_alternative_query(original_objective, previous_queries),
                explanation="Previous approach not yielding results. Trying alternative search strategy."
            )
    
    def _extract_content_from_result(self, result: Dict[str, Any]) -> str:
        """Extract text content from various result formats."""
        if not result:
            return ""
        
        # Handle different result structures
        if "output" in result:
            output = result["output"]
            if isinstance(output, dict):
                return output.get("extracted_text", "") or output.get("content", "") or str(output)
            elif isinstance(output, str):
                return output
        
        if "extracted_text" in result:
            return result["extracted_text"]
        
        if "content" in result:
            return result["content"]
        
        return str(result)
    
    def _assess_confidence(self, content: str, result: Dict[str, Any]) -> float:
        """Assess confidence in the result quality."""
        if not content:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Content length indicates substance
        if len(content) > 500:
            confidence += 0.2
        elif len(content) > 200:
            confidence += 0.1
        
        # Check for error indicators
        error_indicators = ["error", "not found", "access denied", "404", "blocked"]
        if any(indicator in content.lower() for indicator in error_indicators):
            confidence -= 0.3
        
        # Check for quality indicators
        quality_indicators = ["published", "source", "date", "author", "official"]
        quality_score = sum(1 for indicator in quality_indicators if indicator in content.lower())
        confidence += min(quality_score * 0.05, 0.2)
        
        # Check result status
        if result.get("status") == "success":
            confidence += 0.1
        elif result.get("status") == "error":
            confidence -= 0.4
        
        return max(0.0, min(1.0, confidence))
    
    def _assess_completeness(self, content: str, expected_entities: List[str], objective: str) -> float:
        """Assess how completely the content addresses the research objective."""
        if not content:
            return 0.0
        
        content_lower = content.lower()
        objective_lower = objective.lower()
        
        # Check for expected entities
        entity_coverage = 0.0
        if expected_entities:
            found_entities = sum(1 for entity in expected_entities 
                               if entity.lower() in content_lower)
            entity_coverage = found_entities / len(expected_entities)
        
        # Check for objective keywords
        objective_words = [word for word in objective_lower.split() 
                          if len(word) > 3 and word not in ["find", "identify", "locate"]]
        if objective_words:
            keyword_coverage = sum(1 for word in objective_words 
                                 if word in content_lower) / len(objective_words)
        else:
            keyword_coverage = 0.5
        
        # Weighted average
        completeness = entity_coverage * 0.6 + keyword_coverage * 0.4
        
        return max(0.0, min(1.0, completeness))
    
    def _assess_relevance(self, content: str, objective: str) -> float:
        """Assess how relevant the content is to the research objective."""
        if not content:
            return 0.0
        
        content_lower = content.lower()
        objective_lower = objective.lower()
        
        # Simple relevance based on keyword overlap
        objective_keywords = set(word for word in objective_lower.split() if len(word) > 3)
        content_words = set(word for word in content_lower.split() if len(word) > 3)
        
        if not objective_keywords:
            return 0.5
        
        overlap = len(objective_keywords.intersection(content_words))
        relevance = overlap / len(objective_keywords)
        
        # Boost for exact phrase matches
        if any(phrase in content_lower for phrase in objective_lower.split()):
            relevance += 0.2
        
        return max(0.0, min(1.0, relevance))
    
    def _identify_missing_entities(self, content: str, expected_entities: List[str]) -> List[str]:
        """Identify which expected entities are missing from the content."""
        if not content:
            return expected_entities.copy()
        
        content_lower = content.lower()
        missing = []
        
        for entity in expected_entities:
            entity_lower = entity.lower()
            # Check for entity or related terms
            if entity_lower not in content_lower:
                # Check for variations
                if entity_lower == "person" and not any(term in content_lower for term in ["ceo", "president", "director", "manager"]):
                    missing.append(entity)
                elif entity_lower == "organization" and not any(term in content_lower for term in ["company", "corporation", "firm"]):
                    missing.append(entity)
                elif entity_lower not in ["person", "organization"]:
                    missing.append(entity)
        
        return missing
    
    def _identify_quality_issues(self, content: str, result: Dict[str, Any]) -> List[str]:
        """Identify quality issues with the content."""
        issues = []
        
        if not content:
            issues.append("No content extracted")
            return issues
        
        # Check for various quality issues
        if len(content) < 100:
            issues.append("Content too short")
        
        if "error" in content.lower():
            issues.append("Contains error messages")
        
        if content.count(".") < 3:  # Very few sentences
            issues.append("Insufficient detail")
        
        # Check for blocked/denied content
        blocked_indicators = ["access denied", "blocked", "403", "401", "subscription required"]
        if any(indicator in content.lower() for indicator in blocked_indicators):
            issues.append("Access restrictions")
        
        return issues
    
    def _identify_quality_issues_for_phase(self, results: List[Dict[str, Any]], objective: str) -> List[str]:
        """Identify quality issues across a phase."""
        issues = []
        
        if not results:
            issues.append("No results in phase")
            return issues
        
        # Check for consistent failures
        error_count = sum(1 for result in results if result.get("status") == "error")
        if error_count > len(results) / 2:
            issues.append("High error rate in phase")
        
        # Check for insufficient content
        total_content_length = sum(len(self._extract_content_from_result(result)) for result in results)
        if total_content_length < 1000:
            issues.append("Insufficient content gathered")
        
        return issues
    
    def _generate_action_suggestions(self, score: float, missing_entities: List[str], 
                                   issues: List[str], objective: str) -> List[str]:
        """Generate specific action suggestions based on evaluation."""
        suggestions = []
        
        if score < 0.4:
            suggestions.append("Consider changing search strategy entirely")
        elif score < 0.7:
            suggestions.append("Refine search terms for better results")
        
        if missing_entities:
            suggestions.append(f"Add entity-focused search for: {', '.join(missing_entities)}")
        
        if "Content too short" in issues:
            suggestions.append("Try alternative sources or expand search scope")
        
        if "Access restrictions" in issues:
            suggestions.append("Find alternative sources without access restrictions")
        
        return suggestions
    
    def _generate_phase_action_suggestions(self, score: float, missing_entities: List[str],
                                         issues: List[str], objective: str) -> List[str]:
        """Generate suggestions for phase-level improvements."""
        suggestions = []
        
        if score < 0.5:
            suggestions.append("Add additional research phase with different approach")
        
        if missing_entities:
            suggestions.append(f"Create focused phase for missing entities: {', '.join(missing_entities)}")
        
        if "High error rate in phase" in issues:
            suggestions.append("Switch to alternative data sources")
        
        return suggestions
    
    def _generate_refined_query(self, objective: str, missing_entities: List[str]) -> str:
        """Generate a more refined search query."""
        base_terms = objective.split()[:5]  # Take first 5 words
        
        if missing_entities:
            entity_terms = " ".join(missing_entities)
            return f"{' '.join(base_terms)} {entity_terms}".strip()
        
        return " ".join(base_terms)
    
    def _generate_entity_focused_query(self, missing_entities: List[str], objective: str) -> str:
        """Generate a query focused on finding specific entities."""
        entity_terms = " ".join(missing_entities)
        objective_key_terms = [word for word in objective.split() if len(word) > 4][:3]
        
        return f"{entity_terms} {' '.join(objective_key_terms)}".strip()
    
    def _generate_alternative_query(self, objective: str, previous_queries: List[str]) -> str:
        """Generate an alternative query different from previous attempts."""
        import random
        
        # Extract key concepts from objective
        words = objective.split()
        key_words = [w for w in words if len(w) > 3]
        
        # Use synonyms or alternative phrasings
        alternatives = {
            "find": ["locate", "identify", "discover"],
            "company": ["organization", "corporation", "firm"],
            "statements": ["quotes", "remarks", "comments"],
            "percentage": ["rate", "proportion", "ratio"]
        }
        
        new_words = []
        for word in key_words:
            word_lower = word.lower()
            if word_lower in alternatives:
                new_words.append(random.choice(alternatives[word_lower]))
            else:
                new_words.append(word)
        
        return " ".join(new_words[:6])  # Limit query length
    
    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get a summary of evaluation patterns for learning."""
        if not self.evaluation_history:
            return {"message": "No evaluation history available"}
        
        recent_evaluations = self.evaluation_history[-10:]  # Last 10 evaluations
        
        avg_confidence = sum(e["result"].confidence for e in recent_evaluations) / len(recent_evaluations)
        avg_completeness = sum(e["result"].completeness for e in recent_evaluations) / len(recent_evaluations)
        avg_relevance = sum(e["result"].relevance for e in recent_evaluations) / len(recent_evaluations)
        
        return {
            "total_evaluations": len(self.evaluation_history),
            "recent_performance": {
                "avg_confidence": avg_confidence,
                "avg_completeness": avg_completeness,
                "avg_relevance": avg_relevance
            },
            "replan_rate": sum(1 for e in recent_evaluations if e["result"].should_replan) / len(recent_evaluations)
        }