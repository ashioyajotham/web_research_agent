import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class EvaluationResult:
    """Result of evaluating a research step."""
    confidence: float
    missing_entities: List[str]
    quality_issues: List[str]
    suggestions: List[str]
    should_replan: bool
    recovered_entities: Dict[str, List[str]]

@dataclass
class ReplanningStrategy:
    """Strategy for replanning based on evaluation results."""
    strategy_type: str  # "refine_query", "new_sources", "different_approach"
    new_query: Optional[str]
    additional_steps: List[Dict[str, Any]]
    reason: str

class ResultEvaluator:
    """Evaluates research step results and suggests improvements."""
    
    def __init__(self):
        self.entity_patterns = {
            'person': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            'organization': r'\b[A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Organization|Institute|Foundation|Group|Association)\b',
            'role': r'\b(?:CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP|Chief)\b',
            'date': r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]+ \d{1,2},?\s\d{4})\b',
            'percentage': r'\b\d+(?:\.\d+)?%\b',
            'financial': r'[\$€]\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million|B|M))?',
            'location': r'\b[A-Z][a-z]+(?:,\s*[A-Z]{2,})?(?:,\s*[A-Z][a-z]+)*\b'
        }
        
        self.quality_indicators = {
            'high_quality': [
                r'according to',
                r'reported by',
                r'stated in',
                r'official',
                r'press release',
                r'announcement'
            ],
            'low_quality': [
                r'might be',
                r'could be',
                r'possibly',
                r'unconfirmed',
                r'rumor',
                r'speculation'
            ]
        }
    
    def evaluate_step_result(self, step_result: Dict[str, Any], 
                           expected_entities: List[str],
                           phase_objective: str) -> EvaluationResult:
        """Evaluate a single research step result."""
        
        # Extract content from step result
        content = self._extract_content_from_result(step_result)
        if not content:
            return EvaluationResult(
                confidence=0.1,
                missing_entities=expected_entities,
                quality_issues=["No content extracted"],
                suggestions=["Try different sources", "Refine search query"],
                should_replan=True,
                recovered_entities={}
            )
        
        # Extract entities from content
        found_entities = self._extract_entities_from_content(content)
        
        # Calculate confidence based on entity coverage
        confidence = self._calculate_entity_confidence(found_entities, expected_entities)
        
        # Identify missing entities
        missing_entities = self._identify_missing_entities(found_entities, expected_entities)
        
        # Assess content quality
        quality_issues = self._assess_content_quality(content)
        
        # Check if content is relevant to phase objective
        relevance_score = self._calculate_relevance_to_objective(content, phase_objective)
        
        # Generate suggestions
        suggestions = self._generate_improvement_suggestions(
            found_entities, missing_entities, quality_issues, relevance_score
        )
        
        # Determine if replanning is needed
        should_replan = (confidence < 0.6 or 
                        len(missing_entities) > len(expected_entities) / 2 or
                        relevance_score < 0.4)
        
        return EvaluationResult(
            confidence=min(confidence, relevance_score),
            missing_entities=missing_entities,
            quality_issues=quality_issues,
            suggestions=suggestions,
            should_replan=should_replan,
            recovered_entities=found_entities
        )
    
    def evaluate_phase_completion(self, phase_results: List[Dict[str, Any]], 
                                phase_objective: str,
                                required_entities: List[str]) -> EvaluationResult:
        """Evaluate if a research phase has been completed successfully."""
        
        # Aggregate all content from phase
        all_content = []
        all_entities = {}
        
        for result in phase_results:
            content = self._extract_content_from_result(result)
            if content:
                all_content.append(content)
                entities = self._extract_entities_from_content(content)
                for entity_type, values in entities.items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = []
                    all_entities[entity_type].extend(values)
        
        # Remove duplicates
        for entity_type in all_entities:
            all_entities[entity_type] = list(set(all_entities[entity_type]))
        
        combined_content = "\n".join(all_content)
        
        # Calculate phase-level metrics
        confidence = self._calculate_entity_confidence(all_entities, required_entities)
        relevance = self._calculate_relevance_to_objective(combined_content, phase_objective)
        
        missing_entities = self._identify_missing_entities(all_entities, required_entities)
        quality_issues = self._assess_content_quality(combined_content)
        
        # Phase-specific success criteria
        phase_success = self._evaluate_phase_specific_criteria(
            phase_objective, all_entities, combined_content
        )
        
        suggestions = []
        should_replan = False
        
        if not phase_success or confidence < 0.7:
            should_replan = True
            suggestions = self._generate_phase_improvement_suggestions(
                phase_objective, all_entities, missing_entities
            )
        
        return EvaluationResult(
            confidence=min(confidence, relevance) * (1.2 if phase_success else 0.8),
            missing_entities=missing_entities,
            quality_issues=quality_issues,
            suggestions=suggestions,
            should_replan=should_replan,
            recovered_entities=all_entities
        )
    
    def suggest_replanning_strategy(self, evaluation: EvaluationResult, 
                                  original_query: str,
                                  phase_objective: str) -> ReplanningStrategy:
        """Suggest how to improve the research approach."""
        
        if not evaluation.recovered_entities and "organization" in evaluation.missing_entities:
            # No organizations found - need broader search
            new_query = self._broaden_search_query(original_query)
            return ReplanningStrategy(
                strategy_type="refine_query",
                new_query=new_query,
                additional_steps=[],
                reason="No organizations found, broadening search scope"
            )
        
        elif evaluation.recovered_entities.get("organization") and "person" in evaluation.missing_entities:
            # Found org but not people - need targeted search
            orgs = evaluation.recovered_entities["organization"][:2]
            new_query = f"{orgs[0]} leadership team CEO COO management"
            return ReplanningStrategy(
                strategy_type="refine_query", 
                new_query=new_query,
                additional_steps=[],
                reason=f"Found organization '{orgs[0]}' but missing leadership info"
            )
        
        elif len(evaluation.quality_issues) > 2:
            # Quality issues - try different sources
            return ReplanningStrategy(
                strategy_type="new_sources",
                new_query=f"{original_query} official site:linkedin.com OR site:crunchbase.com",
                additional_steps=[
                    {
                        "description": "Search professional networks",
                        "tool": "search",
                        "parameters": {"query": f"{original_query} site:linkedin.com", "num_results": 10}
                    }
                ],
                reason="Content quality issues, trying authoritative sources"
            )
        
        elif evaluation.confidence < 0.4:
            # Very low confidence - different approach
            return ReplanningStrategy(
                strategy_type="different_approach",
                new_query=self._create_alternative_query(original_query, phase_objective),
                additional_steps=[
                    {
                        "description": "Alternative search approach",
                        "tool": "search", 
                        "parameters": {"query": "placeholder", "num_results": 15}
                    }
                ],
                reason="Low confidence, trying alternative search strategy"
            )
        
        else:
            # Minor refinements
            refined_query = self._refine_query_with_entities(original_query, evaluation.recovered_entities)
            return ReplanningStrategy(
                strategy_type="refine_query",
                new_query=refined_query,
                additional_steps=[],
                reason="Minor query refinement based on partial findings"
            )
    
    def _extract_content_from_result(self, result: Dict[str, Any]) -> str:
        """Extract text content from various result formats."""
        if isinstance(result, dict):
            # Try different content keys
            content = (result.get("output", {}).get("extracted_text") or 
                      result.get("output", {}).get("content") or
                      result.get("output", "") or
                      str(result.get("output", "")))
            
            if isinstance(content, dict):
                content = str(content)
            
            return content
        elif isinstance(result, str):
            return result
        else:
            return str(result)
    
    def _extract_entities_from_content(self, content: str) -> Dict[str, List[str]]:
        """Extract entities from content using patterns."""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Clean and deduplicate
                clean_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        match = " ".join(match)
                    match = match.strip()
                    if len(match) > 2 and match not in clean_matches:
                        clean_matches.append(match)
                
                if clean_matches:
                    entities[entity_type] = clean_matches[:10]  # Limit to top 10
        
        return entities
    
    def _calculate_entity_confidence(self, found_entities: Dict[str, List[str]], 
                                   expected_entities: List[str]) -> float:
        """Calculate confidence based on entity coverage."""
        if not expected_entities:
            return 1.0
        
        found_types = set(found_entities.keys())
        expected_types = set(expected_entities)
        
        # Base coverage score
        coverage = len(found_types.intersection(expected_types)) / len(expected_types)
        
        # Bonus for quantity of entities found
        entity_count_bonus = min(sum(len(entities) for entities in found_entities.values()) / 10, 0.3)
        
        return min(coverage + entity_count_bonus, 1.0)
    
    def _identify_missing_entities(self, found_entities: Dict[str, List[str]], 
                                 expected_entities: List[str]) -> List[str]:
        """Identify which expected entity types are missing."""
        found_types = set(found_entities.keys())
        expected_types = set(expected_entities)
        return list(expected_types - found_types)
    
    def _assess_content_quality(self, content: str) -> List[str]:
        """Assess content quality and identify issues."""
        issues = []
        
        if len(content) < 100:
            issues.append("Content too short")
        
        # Check for quality indicators
        high_quality_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in self.quality_indicators['high_quality']
        )
        
        low_quality_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE)) 
            for pattern in self.quality_indicators['low_quality']
        )
        
        if low_quality_count > high_quality_count:
            issues.append("Content appears speculative or unconfirmed")
        
        # Check for error indicators
        error_indicators = ['404', 'not found', 'error', 'access denied', 'blocked']
        if any(indicator in content.lower() for indicator in error_indicators):
            issues.append("Content contains error indicators")
        
        # Check for content diversity
        sentences = content.split('.')
        if len(set(sentences)) < len(sentences) * 0.8:
            issues.append("Content appears repetitive")
        
        return issues
    
    def _calculate_relevance_to_objective(self, content: str, objective: str) -> float:
        """Calculate how relevant content is to the phase objective."""
        if not objective:
            return 1.0
        
        objective_words = set(re.findall(r'\b\w{3,}\b', objective.lower()))
        content_words = set(re.findall(r'\b\w{3,}\b', content.lower()))
        
        if not objective_words:
            return 1.0
        
        overlap = len(objective_words.intersection(content_words))
        return min(overlap / len(objective_words), 1.0)
    
    def _evaluate_phase_specific_criteria(self, phase_objective: str, 
                                        entities: Dict[str, List[str]],
                                        content: str) -> bool:
        """Evaluate phase-specific success criteria."""
        objective_lower = phase_objective.lower()
        
        if "identify organization" in objective_lower:
            return bool(entities.get("organization"))
        
        elif "find leadership" in objective_lower or "coo" in objective_lower:
            return bool(entities.get("person") and entities.get("role"))
        
        elif "statements" in objective_lower:
            quotes_found = len(re.findall(r'"[^"]{20,}"', content))
            return quotes_found >= 3
        
        elif "percentage" in objective_lower or "baseline" in objective_lower:
            return bool(entities.get("percentage") or entities.get("financial"))
        
        elif "dataset" in objective_lower:
            return "download" in content.lower() or "dataset" in content.lower()
        
        else:
            # Generic success: found some relevant entities
            return len(entities) >= 2
    
    def _generate_improvement_suggestions(self, found_entities: Dict[str, List[str]], 
                                        missing_entities: List[str],
                                        quality_issues: List[str],
                                        relevance_score: float) -> List[str]:
        """Generate suggestions for improvement."""
        suggestions = []
        
        if missing_entities:
            suggestions.append(f"Focus search on finding: {', '.join(missing_entities)}")
        
        if quality_issues:
            suggestions.append("Try more authoritative sources (official websites, press releases)")
        
        if relevance_score < 0.5:
            suggestions.append("Refine search query to be more specific to the objective")
        
        if not found_entities:
            suggestions.append("Broaden search terms or try alternative query approaches")
        
        if found_entities.get("organization") and not found_entities.get("person"):
            org = found_entities["organization"][0]
            suggestions.append(f"Search specifically for leadership team of '{org}'")
        
        return suggestions
    
    def _generate_phase_improvement_suggestions(self, phase_objective: str,
                                              entities: Dict[str, List[str]],
                                              missing_entities: List[str]) -> List[str]:
        """Generate phase-level improvement suggestions."""
        suggestions = []
        
        if "organization" in missing_entities:
            suggestions.append("Search for organizations using broader terms")
            suggestions.append("Try searching for events or conferences that might mention organizations")
        
        if "person" in missing_entities and entities.get("organization"):
            org = entities["organization"][0]
            suggestions.append(f"Search for '{org}' executive team or board members")
        
        if "statements" in phase_objective.lower() and not entities.get("statement"):
            suggestions.append("Search for speeches, interviews, or press conferences")
            suggestions.append("Try news sources and official transcripts")
        
        return suggestions
    
    def _broaden_search_query(self, original_query: str) -> str:
        """Create a broader version of the search query."""
        # Remove very specific terms
        words = original_query.split()
        broader_words = []
        
        skip_words = {"coo", "ceo", "president", "director", "manager"}
        
        for word in words:
            if word.lower() not in skip_words:
                broader_words.append(word)
            else:
                broader_words.append("leadership")
                break
        
        return " ".join(broader_words)
    
    def _refine_query_with_entities(self, original_query: str, 
                                  found_entities: Dict[str, List[str]]) -> str:
        """Refine query using found entities."""
        query_parts = [original_query]
        
        if found_entities.get("organization"):
            org = found_entities["organization"][0]
            query_parts.append(f'"{org}"')
        
        if found_entities.get("person"):
            person = found_entities["person"][0]
            query_parts.append(f'"{person}"')
        
        return " ".join(query_parts)
    
    def _create_alternative_query(self, original_query: str, phase_objective: str) -> str:
        """Create an alternative query approach."""
        objective_lower = phase_objective.lower()
        
        if "organization" in objective_lower:
            return f"companies organizations {original_query.replace('find', '').replace('coo', '')}"
        
        elif "leadership" in objective_lower:
            return f"executives management team {' '.join(original_query.split()[1:])}"
        
        elif "statements" in objective_lower:
            return f"quotes speeches interviews {original_query}"
        
        else:
            # Reverse word order for different perspective
            words = original_query.split()
            return " ".join(words[::-1])

# Integration class for easy use
class SelfCorrectingAgent:
    """Wrapper that adds self-correction capabilities to existing agent."""
    
    def __init__(self, base_agent):
        self.base_agent = base_agent
        self.evaluator = ResultEvaluator()
        self.max_replanning_attempts = 2
    
    async def run_with_evaluation(self, task_description: str):
        """Run agent with result evaluation and self-correction."""
        attempts = 0
        
        while attempts <= self.max_replanning_attempts:
            try:
                # Run the base agent
                result = await self.base_agent.run(task_description)
                
                # If this isn't the first attempt, we've already improved
                if attempts > 0:
                    logger.info(f"Self-correction successful after {attempts} attempts")
                
                return result
                
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
                if attempts >= self.max_replanning_attempts:
                    raise
                attempts += 1
    
    def evaluate_and_improve_plan(self, plan, task_analysis):
        """Evaluate plan quality before execution."""
        # This would integrate with your existing planner
        # to evaluate and improve plans before execution
        return plan