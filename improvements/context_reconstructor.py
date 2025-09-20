import json
import hashlib
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import re

@dataclass
class KeyFact:
    """A distilled key fact from research."""
    fact_id: str
    content: str
    fact_type: str  # "entity", "relationship", "statement", "metric", "temporal"
    confidence: float
    sources: List[str]
    extraction_context: str  # How this fact was derived
    dependencies: List[str] = field(default_factory=list)  # Other facts this depends on
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class WorkspaceSnapshot:
    """A reconstructed workspace for a research phase."""
    phase_id: str
    objective: str
    essential_facts: Dict[str, KeyFact]
    working_hypothesis: Dict[str, Any]
    confidence_scores: Dict[str, float]
    next_research_targets: List[str]
    workspace_size: int  # Character count of reconstructed context

class ContextReconstructor:
    """Reconstructs focused research context from accumulated information."""
    
    def __init__(self, max_workspace_size: int = 4000):
        self.max_workspace_size = max_workspace_size
        self.fact_extractors = {
            "entity": self._extract_entity_facts,
            "relationship": self._extract_relationship_facts,
            "statement": self._extract_statement_facts,
            "metric": self._extract_metric_facts,
            "temporal": self._extract_temporal_facts
        }
        
        # Fact importance weights by type
        self.fact_weights = {
            "entity": 1.0,
            "relationship": 1.2,  # Relationships are often key insights
            "statement": 0.9,
            "metric": 1.1,
            "temporal": 0.8
        }
    
    def reconstruct_workspace(self, 
                            phase_results: List[Dict[str, Any]], 
                            phase_objective: str,
                            current_hypothesis: Dict[str, Any] = None) -> WorkspaceSnapshot:
        """Reconstruct a focused workspace from research results."""
        
        # Extract all facts from phase results
        all_facts = self._extract_all_facts(phase_results)
        
        # Score facts for relevance to current phase
        scored_facts = self._score_facts_for_phase(all_facts, phase_objective)
        
        # Select essential facts within workspace size limit
        essential_facts = self._select_essential_facts(scored_facts, phase_objective)
        
        # Build working hypothesis from essential facts
        working_hypothesis = self._build_working_hypothesis(essential_facts, current_hypothesis)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(essential_facts)
        
        # Identify next research targets
        next_targets = self._identify_research_gaps(essential_facts, phase_objective)
        
        # Calculate workspace size
        workspace_text = self._build_workspace_text(essential_facts, working_hypothesis)
        workspace_size = len(workspace_text)
        
        phase_id = hashlib.md5(f"{phase_objective}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        return WorkspaceSnapshot(
            phase_id=phase_id,
            objective=phase_objective,
            essential_facts=essential_facts,
            working_hypothesis=working_hypothesis,
            confidence_scores=confidence_scores,
            next_research_targets=next_targets,
            workspace_size=workspace_size
        )
    
    def _extract_all_facts(self, phase_results: List[Dict[str, Any]]) -> List[KeyFact]:
        """Extract all key facts from phase results."""
        all_facts = []
        
        for result in phase_results:
            content = self._extract_content_from_result(result)
            source_url = self._extract_source_from_result(result)
            
            if not content:
                continue
            
            # Apply all fact extractors
            for fact_type, extractor in self.fact_extractors.items():
                facts = extractor(content, source_url, result)
                all_facts.extend(facts)
        
        return all_facts
    
    def _extract_entity_facts(self, content: str, source_url: str, result: Dict) -> List[KeyFact]:
        """Extract entity facts from content."""
        facts = []
        
        # Extract organizations with context
        org_pattern = r'\b([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Organization|Institute|Foundation|Group))\b'
        for match in re.finditer(org_pattern, content):
            org_name = match.group(1).strip()
            
            # Get context around the organization mention
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            
            fact_id = hashlib.md5(f"org_{org_name}_{source_url}".encode()).hexdigest()[:12]
            
            fact = KeyFact(
                fact_id=fact_id,
                content=f"Organization: {org_name}",
                fact_type="entity",
                confidence=0.8,
                sources=[source_url],
                extraction_context=context
            )
            facts.append(fact)
        
        # Extract people with roles
        role_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,?\s*(CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP)\b'
        for match in re.finditer(role_pattern, content, re.IGNORECASE):
            person_name = match.group(1).strip()
            role = match.group(2).strip()
            
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            
            fact_id = hashlib.md5(f"person_{person_name}_{role}_{source_url}".encode()).hexdigest()[:12]
            
            fact = KeyFact(
                fact_id=fact_id,
                content=f"Person: {person_name}, Role: {role}",
                fact_type="entity",
                confidence=0.9,
                sources=[source_url],
                extraction_context=context
            )
            facts.append(fact)
        
        return facts
    
    def _extract_relationship_facts(self, content: str, source_url: str, result: Dict) -> List[KeyFact]:
        """Extract relationship facts between entities."""
        facts = []
        
        # Pattern: [Person] [role] at/of [Organization]
        relationship_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:is\s+(?:the\s+)?)?(?:CEO|COO|CTO|President|Director)\s+(?:of|at)\s+([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company))\b',
            r'\b([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company))\s+(?:CEO|COO|CTO|President|Director)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            r'\b([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company))\s+.*?mediated.*?(?:talks|negotiations|meeting)\b'
        ]
        
        for pattern in relationship_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                if len(groups) >= 2:
                    entity1, entity2 = groups[0].strip(), groups[1].strip()
                    
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    context = content[start:end]
                    
                    fact_id = hashlib.md5(f"rel_{entity1}_{entity2}_{source_url}".encode()).hexdigest()[:12]
                    
                    fact = KeyFact(
                        fact_id=fact_id,
                        content=f"Relationship: {entity1} ↔ {entity2}",
                        fact_type="relationship",
                        confidence=0.8,
                        sources=[source_url],
                        extraction_context=context
                    )
                    facts.append(fact)
        
        return facts
    
    def _extract_statement_facts(self, content: str, source_url: str, result: Dict) -> List[KeyFact]:
        """Extract statement/quote facts."""
        facts = []
        
        # Extract quotes with attribution
        quote_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:said|stated|declared|remarked):\s*"([^"]{30,200})"',
            r'"([^"]{30,200})"\s*,?\s*(?:said|stated|declared)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'"([^"]{30,200})".*?-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in quote_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                groups = match.groups()
                if len(groups) == 2:
                    # Determine which group is speaker and which is quote
                    if len(groups[0]) > len(groups[1]):
                        quote, speaker = groups[0], groups[1]
                    else:
                        speaker, quote = groups[0], groups[1]
                    
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]
                    
                    fact_id = hashlib.md5(f"stmt_{speaker}_{quote[:20]}_{source_url}".encode()).hexdigest()[:12]
                    
                    fact = KeyFact(
                        fact_id=fact_id,
                        content=f"Statement by {speaker}: \"{quote[:100]}{'...' if len(quote) > 100 else quote}\"",
                        fact_type="statement",
                        confidence=0.9,
                        sources=[source_url],
                        extraction_context=context
                    )
                    facts.append(fact)
        
        return facts
    
    def _extract_metric_facts(self, content: str, source_url: str, result: Dict) -> List[KeyFact]:
        """Extract numerical/metric facts."""
        facts = []
        
        # Patterns for different metrics
        metric_patterns = [
            (r'(\d+(?:\.\d+)?)\s*%\s*(?:reduction|decrease|increase)', 'percentage_change'),
            (r'[\$€](\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:billion|million|B|M)', 'financial'),
            (r'(\d+(?:,\d{3})*)\s*(?:tons?|tonnes?|kg|mt)\s*(?:of\s+)?(?:CO2|emissions|greenhouse)', 'emissions'),
            (r'(\d{4})\s*(?:to|[-–])\s*(\d{4})', 'time_period')
        ]
        
        for pattern, metric_type in metric_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = match.group(1) if match.groups() else match.group(0)
                
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                
                fact_id = hashlib.md5(f"metric_{metric_type}_{value}_{source_url}".encode()).hexdigest()[:12]
                
                fact = KeyFact(
                    fact_id=fact_id,
                    content=f"Metric ({metric_type}): {value}",
                    fact_type="metric",
                    confidence=0.8,
                    sources=[source_url],
                    extraction_context=context
                )
                facts.append(fact)
        
        return facts
    
    def _extract_temporal_facts(self, content: str, source_url: str, result: Dict) -> List[KeyFact]:
        """Extract temporal/date facts."""
        facts = []
        
        # Date patterns with context
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', 
            r'\b([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b'
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                date_str = match.group(1)
                
                start = max(0, match.start() - 150)
                end = min(len(content), match.end() + 150)
                context = content[start:end]
                
                fact_id = hashlib.md5(f"date_{date_str}_{source_url}".encode()).hexdigest()[:12]
                
                fact = KeyFact(
                    fact_id=fact_id,
                    content=f"Date: {date_str}",
                    fact_type="temporal",
                    confidence=0.7,
                    sources=[source_url],
                    extraction_context=context
                )
                facts.append(fact)
        
        return facts
    
    def _score_facts_for_phase(self, facts: List[KeyFact], phase_objective: str) -> List[Tuple[float, KeyFact]]:
        """Score facts for relevance to current phase objective."""
        scored_facts = []
        objective_words = set(re.findall(r'\b\w{3,}\b', phase_objective.lower()))
        
        for fact in facts:
            score = fact.confidence * self.fact_weights.get(fact.fact_type, 1.0)
            
            # Boost score for objective relevance
            fact_words = set(re.findall(r'\b\w{3,}\b', fact.content.lower()))
            fact_context_words = set(re.findall(r'\b\w{3,}\b', fact.extraction_context.lower()))
            
            # Calculate relevance overlap
            content_overlap = len(objective_words.intersection(fact_words)) / max(len(objective_words), 1)
            context_overlap = len(objective_words.intersection(fact_context_words)) / max(len(objective_words), 1)
            
            relevance_boost = max(content_overlap, context_overlap) * 0.5
            score += relevance_boost
            
            # Phase-specific boosts
            if "organization" in phase_objective.lower() and fact.fact_type == "entity" and "Organization:" in fact.content:
                score += 0.3
            elif "coo" in phase_objective.lower() and "COO" in fact.content:
                score += 0.4
            elif "percentage" in phase_objective.lower() and fact.fact_type == "metric":
                score += 0.3
            
            scored_facts.append((score, fact))
        
        # Sort by score descending
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return scored_facts
    
    def _select_essential_facts(self, scored_facts: List[Tuple[float, KeyFact]], 
                              phase_objective: str) -> Dict[str, KeyFact]:
        """Select essential facts within workspace size constraints."""
        essential_facts = {}
        current_size = 0
        fact_types_seen = set()
        
        for score, fact in scored_facts:
            # Estimate fact size contribution
            fact_size = len(fact.content) + len(fact.extraction_context[:200])
            
            # Always include the highest scoring fact of each type
            if (fact.fact_type not in fact_types_seen or 
                current_size + fact_size <= self.max_workspace_size):
                
                essential_facts[fact.fact_id] = fact
                current_size += fact_size
                fact_types_seen.add(fact.fact_type)
                
                if current_size >= self.max_workspace_size * 0.9:
                    break
        
        return essential_facts
    
    def _build_working_hypothesis(self, essential_facts: Dict[str, KeyFact], 
                                current_hypothesis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build working hypothesis from essential facts."""
        hypothesis = current_hypothesis.copy() if current_hypothesis else {}
        
        # Group facts by type
        facts_by_type = defaultdict(list)
        for fact in essential_facts.values():
            facts_by_type[fact.fact_type].append(fact)
        
        # Build hypothesis components
        if facts_by_type["entity"]:
            organizations = [f.content for f in facts_by_type["entity"] if "Organization:" in f.content]
            people = [f.content for f in facts_by_type["entity"] if "Person:" in f.content]
            
            if organizations:
                hypothesis["primary_organization"] = organizations[0].replace("Organization: ", "")
            if people:
                hypothesis["key_personnel"] = [p.replace("Person: ", "") for p in people[:3]]
        
        if facts_by_type["relationship"]:
            hypothesis["relationships"] = [f.content.replace("Relationship: ", "") 
                                         for f in facts_by_type["relationship"][:3]]
        
        if facts_by_type["statement"]:
            hypothesis["key_statements"] = [f.content for f in facts_by_type["statement"][:5]]
        
        if facts_by_type["metric"]:
            hypothesis["metrics"] = [f.content.replace("Metric ", "") 
                                   for f in facts_by_type["metric"][:3]]
        
        return hypothesis
    
    def _calculate_confidence_scores(self, essential_facts: Dict[str, KeyFact]) -> Dict[str, float]:
        """Calculate confidence scores for different aspects."""
        confidence_scores = {}
        
        # Group by fact type
        facts_by_type = defaultdict(list)
        for fact in essential_facts.values():
            facts_by_type[fact.fact_type].append(fact)
        
        # Calculate type-level confidence
        for fact_type, facts in facts_by_type.items():
            if facts:
                avg_confidence = sum(f.confidence for f in facts) / len(facts)
                source_diversity = len(set().union(*[f.sources for f in facts]))
                
                # Boost confidence based on source diversity
                diversity_boost = min(source_diversity / 5.0, 0.2)
                confidence_scores[f"{fact_type}_confidence"] = min(avg_confidence + diversity_boost, 1.0)
        
        # Overall confidence
        if confidence_scores:
            confidence_scores["overall_confidence"] = sum(confidence_scores.values()) / len(confidence_scores)
        
        return confidence_scores
    
    def _identify_research_gaps(self, essential_facts: Dict[str, KeyFact], 
                               phase_objective: str) -> List[str]:
        """Identify what information is still missing."""
        gaps = []
        objective_lower = phase_objective.lower()
        
        facts_by_type = defaultdict(list)
        for fact in essential_facts.values():
            facts_by_type[fact.fact_type].append(fact)
        
        # Check for common gaps based on objective
        if "organization" in objective_lower and not facts_by_type["entity"]:
            gaps.append("organization_identity")
        
        if ("coo" in objective_lower or "leadership" in objective_lower) and not any(
            "COO" in f.content or "CEO" in f.content for f in facts_by_type["entity"]
        ):
            gaps.append("leadership_information")
        
        if "percentage" in objective_lower and not facts_by_type["metric"]:
            gaps.append("numerical_data")
        
        if "statements" in objective_lower and not facts_by_type["statement"]:
            gaps.append("quote_attribution")
        
        # Generic gaps
        if len(facts_by_type) < 2:
            gaps.append("insufficient_information_diversity")
        
        return gaps
    
    def _build_workspace_text(self, essential_facts: Dict[str, KeyFact], 
                            working_hypothesis: Dict[str, Any]) -> str:
        """Build the actual workspace text."""
        sections = []
        
        # Working Hypothesis section
        sections.append("=== WORKING HYPOTHESIS ===")
        for key, value in working_hypothesis.items():
            sections.append(f"{key}: {value}")
        
        # Essential Facts section
        sections.append("\n=== ESSENTIAL FACTS ===")
        
        # Group facts by type for organized presentation
        facts_by_type = defaultdict(list)
        for fact in essential_facts.values():
            facts_by_type[fact.fact_type].append(fact)
        
        for fact_type in ["entity", "relationship", "statement", "metric", "temporal"]:
            if facts_by_type[fact_type]:
                sections.append(f"\n{fact_type.upper()}:")
                for fact in facts_by_type[fact_type]:
                    sections.append(f"• {fact.content}")
                    if len(fact.extraction_context) < 200:
                        sections.append(f"  Context: {fact.extraction_context}")
        
        return "\n".join(sections)
    
    def _extract_content_from_result(self, result: Dict[str, Any]) -> str:
        """Extract content from result dict."""
        if isinstance(result, dict):
            output = result.get("output", {})
            if isinstance(output, dict):
                return (output.get("extracted_text") or 
                       output.get("content") or 
                       output.get("text") or "")
            else:
                return str(output)
        return str(result)
    
    def _extract_source_from_result(self, result: Dict[str, Any]) -> str:
        """Extract source URL from result dict."""
        if isinstance(result, dict):
            output = result.get("output", {})
            if isinstance(output, dict):
                return output.get("url") or output.get("source") or "unknown"
        return "unknown"
    
    def get_workspace_summary(self, workspace: WorkspaceSnapshot) -> str:
        """Get a concise summary of the workspace."""
        summary_parts = []
        
        summary_parts.append(f"PHASE: {workspace.objective}")
        summary_parts.append(f"FACTS: {len(workspace.essential_facts)} essential facts")
        summary_parts.append(f"CONFIDENCE: {workspace.confidence_scores.get('overall_confidence', 0):.2f}")
        
        if workspace.working_hypothesis:
            summary_parts.append("HYPOTHESIS:")
            for key, value in workspace.working_hypothesis.items():
                if isinstance(value, list):
                    summary_parts.append(f"  {key}: {len(value)} items")
                else:
                    summary_parts.append(f"  {key}: {str(value)[:50]}...")
        
        if workspace.next_research_targets:
            summary_parts.append(f"GAPS: {', '.join(workspace.next_research_targets)}")
        
        return "\n".join(summary_parts)
    
    def merge_workspaces(self, workspaces: List[WorkspaceSnapshot]) -> WorkspaceSnapshot:
        """Merge multiple workspaces into a final comprehensive workspace."""
        all_facts = {}
        merged_hypothesis = {}
        all_confidence_scores = {}
        all_targets = []
        
        for workspace in workspaces:
            # Merge facts (avoid duplicates by ID)
            all_facts.update(workspace.essential_facts)
            
            # Merge hypotheses
            for key, value in workspace.working_hypothesis.items():
                if key not in merged_hypothesis:
                    merged_hypothesis[key] = value
                elif isinstance(value, list) and isinstance(merged_hypothesis[key], list):
                    # Merge lists without duplicates
                    merged_hypothesis[key] = list(set(merged_hypothesis[key] + value))
            
            # Merge confidence scores (take average)
            for key, score in workspace.confidence_scores.items():
                if key in all_confidence_scores:
                    all_confidence_scores[key] = (all_confidence_scores[key] + score) / 2
                else:
                    all_confidence_scores[key] = score
            
            all_targets.extend(workspace.next_research_targets)
        
        # Remove duplicate targets
        unique_targets = list(set(all_targets))
        
        # Build merged workspace text
        workspace_text = self._build_workspace_text(all_facts, merged_hypothesis)
        
        return WorkspaceSnapshot(
            phase_id="merged_workspace",
            objective="Final comprehensive workspace",
            essential_facts=all_facts,
            working_hypothesis=merged_hypothesis,
            confidence_scores=all_confidence_scores,
            next_research_targets=unique_targets,
            workspace_size=len(workspace_text)
        )