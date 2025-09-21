from utils.logger import get_logger
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = get_logger(__name__)

@dataclass
class TaskComponent:
    """Represents a component of a multistep task."""
    description: str
    required_entities: List[str]
    depends_on: Optional[str] = None  # Previous component this depends on
    search_strategy: str = "direct"  # direct, entity_focused, relationship

@dataclass 
class TaskAnalysis:
    """Enhanced task analysis with decomposition."""
    task_type: str
    complexity: str  # simple, multistep, comparative
    components: List[TaskComponent]
    synthesis_strategy: str
    expected_entities: List[str]
    information_flow: Dict[str, str]  # how information flows between components

class ProgressiveSynthesis:
    """Manages progressive synthesis of research findings with hypothesis tracking."""
    
    def __init__(self):
        self.working_hypothesis = {}  # Current understanding of the research
        self.evidence_for = {}  # Supporting evidence for each hypothesis
        self.evidence_against = {}  # Contradicting evidence
        self.confidence_scores = {}  # Confidence in each finding
        self.structured_findings = {}  # Extracted structured data
        
    def integrate_new_information(self, content: str, source_url: str, current_phase: str) -> Dict[str, Any]:
        """Integrate new content into working hypothesis."""
        findings = {}
        
        # Extract structured information based on content patterns
        findings.update(self._extract_statements(content, source_url))
        findings.update(self._extract_roles_and_people(content, source_url))
        findings.update(self._extract_organizations(content, source_url))
        findings.update(self._extract_dates_and_events(content, source_url))
        findings.update(self._extract_numerical_data(content, source_url))
        
        # Update working hypothesis
        for key, value in findings.items():
            if key not in self.working_hypothesis:
                self.working_hypothesis[key] = []
                self.evidence_for[key] = []
                self.confidence_scores[key] = 0.0
            
            # Add evidence
            self.evidence_for[key].append({
                "content": value,
                "source": source_url,
                "phase": current_phase,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update confidence based on source credibility and content quality
            source_credibility = self._assess_source_credibility(source_url)
            content_quality = self._assess_content_quality(str(value))
            new_confidence = (source_credibility + content_quality) / 2
            
            # Weighted average of confidence scores
            total_evidence = len(self.evidence_for[key])
            self.confidence_scores[key] = (
                (self.confidence_scores[key] * (total_evidence - 1) + new_confidence) / total_evidence
            )
            
            # Add to working hypothesis if confidence is high enough
            if new_confidence > 0.6 and value not in self.working_hypothesis[key]:
                self.working_hypothesis[key].append(value)
        
        return findings
    
    def _extract_statements(self, content: str, source_url: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract direct statements/quotes from content."""
        statements = []
        
        # Pattern for quoted statements
        quote_patterns = [
            r'"([^"]{20,300})"',  # Direct quotes
            r"'([^']{20,300})'",  # Single quotes
            r'said:\s*"([^"]{20,300})"',  # Said: quotes
            r'stated:\s*"([^"]{20,300})"',  # Stated: quotes
        ]
        
        for pattern in quote_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                quote = match.group(1).strip()
                # Extract context around the quote
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                
                # Try to extract speaker and date
                speaker = self._extract_speaker_from_context(context)
                date = self._extract_date_from_context(context)
                
                statements.append({
                    "quote": quote,
                    "speaker": speaker,
                    "date": date,
                    "source": source_url,
                    "context": context.strip(),
                    "confidence": 0.8
                })
        
        return {"statements": statements} if statements else {}
    
    def _extract_roles_and_people(self, content: str, source_url: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract people and their roles from content."""
        roles_people = []
        
        # Pattern for role assignments
        role_patterns = [
            r'(\w+(?:\s+\w+)*)\s+(?:serves as|is the|acts as|holds the position of)\s+(CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP)',
            r'(CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP)\s+(\w+(?:\s+\w+)*)',
            r'(\w+(?:\s+\w+)*),?\s+(CEO|COO|CTO|President|Director|Manager|Secretary|Chairman|Vice President|VP)',
        ]
        
        for pattern in role_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) == 2:
                    person, role = groups[0].strip(), groups[1].strip()
                    # Validate that person looks like a name
                    if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', person):
                        roles_people.append({
                            "person": person,
                            "role": role,
                            "source": source_url,
                            "confidence": 0.7
                        })
        
        return {"roles_people": roles_people} if roles_people else {}
    
    def _extract_organizations(self, content: str, source_url: str) -> Dict[str, List[str]]:
        """Extract organization names from content."""
        organizations = []
        
        # Patterns for organizations
        org_patterns = [
            r'\b([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Organization|Institute|Foundation|Group|Association))\b',
            r'\b([A-Z][A-Z\s&]+)\b',  # All caps organizations
        ]
        
        for pattern in org_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                org = match.strip()
                if 3 < len(org) < 100:  # Reasonable length
                    organizations.append(org)
        
        return {"organizations": list(set(organizations))} if organizations else {}
    
    def _extract_dates_and_events(self, content: str, source_url: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract dates and associated events."""
        events = []
        
        # Date patterns
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
            r'\b([A-Z][a-z]+ \d{1,2},?\s\d{4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                date = match.group(1)
                # Extract context around date
                start = max(0, match.start() - 200)
                end = min(len(content), match.end() + 200)
                context = content[start:end]
                
                events.append({
                    "date": date,
                    "context": context.strip(),
                    "source": source_url,
                    "confidence": 0.6
                })
        
        return {"events": events} if events else {}
    
    def _extract_numerical_data(self, content: str, source_url: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract numerical data and metrics."""
        numerical_data = []
        
        # Patterns for percentages, emissions, revenue, etc.
        number_patterns = [
            r'(\d+(?:\.\d+)?)\s*%',  # Percentages
            r'€(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:billion|million|B|M)',  # European currency
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:billion|million|B|M)',  # US currency
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:tons?|tonnes?|kg|mt)',  # Emissions/weight
        ]
        
        for pattern in number_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                # Extract context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                
                numerical_data.append({
                    "value": value,
                    "unit": self._extract_unit_from_match(match.group(0)),
                    "context": context.strip(),
                    "source": source_url,
                    "confidence": 0.7
                })
        
        return {"numerical_data": numerical_data} if numerical_data else {}
    
    def _extract_speaker_from_context(self, context: str) -> Optional[str]:
        """Extract speaker name from quote context."""
        # Look for patterns like "Biden said", "President Biden stated"
        speaker_patterns = [
            r'(?:President\s+)?(\w+)\s+(?:said|stated|remarked|noted|declared)',
            r'(?:said|stated|according to)\s+(?:President\s+)?(\w+)',
        ]
        
        for pattern in speaker_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_date_from_context(self, context: str) -> Optional[str]:
        """Extract date from quote context."""
        date_patterns = [
            r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
            r'\b([A-Z][a-z]+ \d{1,2},?\s\d{4})\b',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        return None
    
    def _extract_unit_from_match(self, match_text: str) -> str:
        """Extract unit from numerical match."""
        if '%' in match_text:
            return 'percentage'
        elif '€' in match_text:
            return 'euros'
        elif '$' in match_text:
            return 'dollars'
        elif any(unit in match_text.lower() for unit in ['ton', 'kg', 'mt']):
            return 'emissions'
        return 'number'
    
    def _assess_source_credibility(self, source_url: str) -> float:
        """Assess credibility of source based on domain."""
        high_credibility_domains = [
            'gov', 'edu', 'org', 'reuters.com', 'bloomberg.com', 'wsj.com',
            'ft.com', 'bbc.com', 'cnn.com', 'nytimes.com', 'washingtonpost.com'
        ]
        
        medium_credibility_domains = [
            'com', 'net', 'co.uk', 'wikipedia.org'
        ]
        
        for domain in high_credibility_domains:
            if domain in source_url:
                return 0.9
        
        for domain in medium_credibility_domains:
            if domain in source_url:
                return 0.7
        
        return 0.5  # Default credibility
    
    def _assess_content_quality(self, content: str) -> float:
        """Assess content quality based on length and structure."""
        if len(content) < 10:
            return 0.3
        elif len(content) < 50:
            return 0.5
        elif len(content) < 200:
            return 0.7
        else:
            return 0.8
    
    def get_high_confidence_findings(self, confidence_threshold: float = 0.7) -> Dict[str, List[Any]]:
        """Get findings above confidence threshold."""
        high_confidence = {}
        
        for key, findings in self.working_hypothesis.items():
            if self.confidence_scores.get(key, 0) >= confidence_threshold:
                high_confidence[key] = findings
        
        return high_confidence
    
    def synthesize_for_task(self, task_description: str) -> Dict[str, Any]:
        """Synthesize findings specifically for the given task using semantic analysis."""
        task_lower = task_description.lower()
        synthesis = {}
        
        # Task-agnostic synthesis based on patterns
        if any(term in task_lower for term in ["statements", "quotes", "said", "declared"]):
            # Statement extraction task
            statements = self.working_hypothesis.get("statements", [])
            synthesis["statements"] = [
                stmt for stmt in statements
                if isinstance(stmt, dict) and stmt.get("confidence", 0) > 0.6
            ]
        
        elif any(term in task_lower for term in ["coo", "ceo", "cto", "president", "director"]):
            # Role-based search task
            roles = self.working_hypothesis.get("roles_people", [])
            # Extract role mentioned in task
            target_roles = [role for role in ["coo", "ceo", "cto", "president", "director"] if role in task_lower]
            role_info = []
            for role in roles:
                if isinstance(role, dict):
                    role_title = role.get("role", "").lower()
                    if any(target in role_title for target in target_roles):
                        role_info.append(role)
            synthesis["role_candidates"] = role_info
        
        elif any(term in task_lower for term in ["percentage", "percent", "rate", "number"]):
            # Quantitative data task
            numerical = self.working_hypothesis.get("numerical_data", [])
            # Filter by relevance to task
            relevant_data = []
            for data in numerical:
                if isinstance(data, dict) and data.get("confidence", 0) > 0.5:
                    relevant_data.append(data)
            synthesis["numerical_data"] = relevant_data
        
        # Add confidence scores
        synthesis["confidence_summary"] = {
            key: score for key, score in self.confidence_scores.items()
            if score > 0.5
        }
        
        return synthesis

class WorkspaceReconstructor:
    """Implements Tongyi's IterResearch workspace reconstruction pattern."""
    
    def __init__(self):
        self.research_rounds = []  # History of research rounds
        self.essential_facts = {}  # Core findings that persist
        self.entity_graph = {}  # Discovered entity relationships
        self.current_workspace = {}  # Clean workspace for current round
        
    def reconstruct_workspace_for_round(self, research_objective: str, 
                                      previous_round_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Reconstruct a clean, focused workspace for the current research round.
        
        This is Tongyi's key innovation: instead of accumulating all context,
        extract only essential insights and start each round with a clean slate.
        """
        # Extract essential insights from previous round
        if previous_round_results:
            essential_insights = self._extract_essential_insights(previous_round_results)
            self._update_essential_facts(essential_insights)
            self._update_entity_graph(essential_insights)
        
        # Create focused workspace
        self.current_workspace = {
            "objective": research_objective,
            "essential_facts": dict(self.essential_facts),
            "known_entities": self._get_relevant_entities(research_objective),
            "research_gaps": self._identify_research_gaps(research_objective),
            "search_strategy": self._determine_search_strategy(research_objective)
        }
        
        return self.current_workspace
    
    def _extract_essential_insights(self, round_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only the most essential insights from a research round."""
        insights = {
            "verified_facts": {},
            "discovered_entities": {},
            "relationships": {},
            "confidence_scores": {}
        }
        
        # Extract high-confidence findings
        if "findings" in round_results:
            for finding_type, findings in round_results["findings"].items():
                if isinstance(findings, list):
                    # Keep only high-confidence findings
                    high_conf_findings = [
                        f for f in findings 
                        if isinstance(f, dict) and f.get("confidence", 0) > 0.7
                    ]
                    if high_conf_findings:
                        insights["verified_facts"][finding_type] = high_conf_findings
        
        # Extract entity mentions and relationships
        if "entities" in round_results:
            for entity_type, entities in round_results["entities"].items():
                if entities:
                    insights["discovered_entities"][entity_type] = entities
        
        return insights
    
    def _update_essential_facts(self, insights: Dict[str, Any]):
        """Update the persistent essential facts with new insights."""
        for fact_type, facts in insights.get("verified_facts", {}).items():
            if fact_type not in self.essential_facts:
                self.essential_facts[fact_type] = []
            
            # Merge new facts, avoiding duplicates
            existing_facts = {str(f) for f in self.essential_facts[fact_type]}
            for fact in facts:
                if str(fact) not in existing_facts:
                    self.essential_facts[fact_type].append(fact)
    
    def _update_entity_graph(self, insights: Dict[str, Any]):
        """Update the entity relationship graph with new discoveries."""
        for entity_type, entities in insights.get("discovered_entities", {}).items():
            if entity_type not in self.entity_graph:
                self.entity_graph[entity_type] = {}
            
            for entity in entities:
                entity_name = entity if isinstance(entity, str) else entity.get("name", str(entity))
                if entity_name not in self.entity_graph[entity_type]:
                    self.entity_graph[entity_type][entity_name] = {
                        "mentions": [],
                        "relationships": {},
                        "attributes": {}
                    }
    
    def _get_relevant_entities(self, objective: str) -> Dict[str, List[str]]:
        """Get entities relevant to the current research objective."""
        relevant = {}
        objective_lower = objective.lower()
        
        for entity_type, entities in self.entity_graph.items():
            relevant_entities = []
            for entity_name, entity_data in entities.items():
                # Check if entity is mentioned in objective
                if entity_name.lower() in objective_lower:
                    relevant_entities.append(entity_name)
                # Check if entity has relevant attributes
                elif any(attr.lower() in objective_lower for attr in entity_data.get("attributes", {}).keys()):
                    relevant_entities.append(entity_name)
            
            if relevant_entities:
                relevant[entity_type] = relevant_entities
        
        return relevant
    
    def _identify_research_gaps(self, objective: str) -> List[str]:
        """Identify what information is still needed for the objective."""
        gaps = []
        
        # Abstract gap detection based on objective structure
        if "who" in objective.lower() or "person" in objective.lower():
            if not any("person" in entities for entities in self.entity_graph.values()):
                gaps.append("Need to identify key people")
        
        if "organization" in objective.lower() or "company" in objective.lower():
            if not any("organization" in entities for entities in self.entity_graph.values()):
                gaps.append("Need to identify organizations")
        
        if "when" in objective.lower() or "date" in objective.lower():
            if "events" not in self.essential_facts:
                gaps.append("Need to find dates and timeline")
        
        if "how much" in objective.lower() or "percentage" in objective.lower():
            if "numerical_data" not in self.essential_facts:
                gaps.append("Need quantitative data")
        
        return gaps
    
    def _determine_search_strategy(self, objective: str) -> str:
        """Determine the best search strategy for current objective."""
        objective_lower = objective.lower()
        
        # If we have relevant entities, use entity-focused search
        if self._get_relevant_entities(objective):
            return "entity_focused"
        
        # If we need specific data types, use targeted search
        if any(term in objective_lower for term in ["statements", "quotes", "said"]):
            return "statement_extraction"
        elif any(term in objective_lower for term in ["percentage", "number", "amount"]):
            return "quantitative_search"
        elif any(term in objective_lower for term in ["list", "compile", "enumerate"]):
            return "comprehensive_collection"
        else:
            return "exploratory"
    
    def get_current_workspace_summary(self) -> str:
        """Get a concise summary of the current workspace for context."""
        summary_parts = []
        
        if self.current_workspace.get("essential_facts"):
            summary_parts.append("Essential Facts:")
            for fact_type, facts in self.current_workspace["essential_facts"].items():
                summary_parts.append(f"- {fact_type}: {len(facts)} items")
        
        if self.current_workspace.get("known_entities"):
            summary_parts.append("Known Entities:")
            for entity_type, entities in self.current_workspace["known_entities"].items():
                summary_parts.append(f"- {entity_type}: {', '.join(entities[:3])}")
        
        if self.current_workspace.get("research_gaps"):
            summary_parts.append("Research Gaps:")
            for gap in self.current_workspace["research_gaps"]:
                summary_parts.append(f"- {gap}")
        
        return "\n".join(summary_parts) if summary_parts else "Clean workspace - starting fresh research"

class ContextWindow:
    """Manages context window with relevance-based filtering."""
    
    def __init__(self, max_size: int = 8000):
        self.max_size = max_size
        self.core_facts = {}  # Always preserved
        self.phase_context = {}  # Current phase relevant info
        self.entity_summaries = {}  # Compressed entity knowledge
        self.content_priority = {}  # Priority scores for content
        
    def add_content(self, content: str, source_url: str, relevance_score: float, 
                   phase: str, content_type: str = "general"):
        """Add content with relevance scoring."""
        content_id = f"{phase}_{len(self.phase_context)}"
        
        self.phase_context[content_id] = {
            "content": content,
            "source": source_url,
            "relevance": relevance_score,
            "phase": phase,
            "type": content_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.content_priority[content_id] = relevance_score
        
        # Manage context size
        self._manage_context_size()
    
    def get_focused_context(self, current_phase: str, target_entities: List[str]) -> str:
        """Get context focused on current phase and target entities."""
        context_parts = []
        
        # Always include core facts
        if self.core_facts:
            context_parts.append("=== Core Facts ===")
            for key, fact in self.core_facts.items():
                context_parts.append(f"{key}: {fact}")
        
        # Add relevant phase context
        relevant_content = []
        for content_id, content_info in self.phase_context.items():
            if (content_info["phase"] == current_phase or 
                any(entity.lower() in content_info["content"].lower() for entity in target_entities)):
                relevant_content.append((content_info["relevance"], content_info))
        
        # Sort by relevance and add top content
        relevant_content.sort(key=lambda x: x[0], reverse=True)
        
        if relevant_content:
            context_parts.append(f"\n=== Phase Context: {current_phase} ===")
            for _, content_info in relevant_content[:5]:  # Top 5 most relevant
                context_parts.append(f"Source: {content_info['source']}")
                context_parts.append(content_info["content"][:500] + "...")
                context_parts.append("")
        
        return "\n".join(context_parts)
    """Manages context window with relevance-based filtering."""
    
    def __init__(self, max_size: int = 8000):
        self.max_size = max_size
        self.core_facts = {}  # Always preserved
        self.phase_context = {}  # Current phase relevant info
        self.entity_summaries = {}  # Compressed entity knowledge
        self.content_priority = {}  # Priority scores for content
        
    def add_content(self, content: str, source_url: str, relevance_score: float, 
                   phase: str, content_type: str = "general"):
        """Add content with relevance scoring."""
        content_id = f"{phase}_{len(self.phase_context)}"
        
        self.phase_context[content_id] = {
            "content": content,
            "source": source_url,
            "relevance": relevance_score,
            "phase": phase,
            "type": content_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.content_priority[content_id] = relevance_score
        
        # Manage context size
        self._manage_context_size()
    
    def get_focused_context(self, current_phase: str, target_entities: List[str]) -> str:
        """Get context focused on current phase and target entities."""
        context_parts = []
        
        # Always include core facts
        if self.core_facts:
            context_parts.append("=== Core Facts ===")
            for key, fact in self.core_facts.items():
                context_parts.append(f"{key}: {fact}")
        
        # Add relevant phase context
        relevant_content = []
        for content_id, content_info in self.phase_context.items():
            if (content_info["phase"] == current_phase or 
                any(entity.lower() in content_info["content"].lower() for entity in target_entities)):
                relevant_content.append((content_info["relevance"], content_info))
        
        # Sort by relevance and add top content
        relevant_content.sort(key=lambda x: x[0], reverse=True)
        
        if relevant_content:
            context_parts.append(f"\n=== Phase Context: {current_phase} ===")
            for _, content_info in relevant_content[:5]:  # Top 5 most relevant
                context_parts.append(f"Source: {content_info['source']}")
                context_parts.append(content_info["content"][:500] + "...")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _manage_context_size(self):
        """Remove lowest priority content if size exceeded."""
        total_size = sum(len(str(content)) for content in self.phase_context.values())
        
        if total_size > self.max_size:
            # Sort by priority and remove lowest
            sorted_content = sorted(
                self.content_priority.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Keep only top priority content
            keep_count = len(sorted_content) // 2
            content_to_remove = [item[0] for item in sorted_content[keep_count:]]
            
            for content_id in content_to_remove:
                self.phase_context.pop(content_id, None)
                self.content_priority.pop(content_id, None)
    
    def add_core_fact(self, key: str, value: Any):
        """Add a core fact that persists across phases."""
        self.core_facts[key] = value
    
    def clear_phase_context(self, phase: str):
        """Clear context for a specific phase."""
        to_remove = [
            content_id for content_id, content_info in self.phase_context.items()
            if content_info["phase"] == phase
        ]
        
        for content_id in to_remove:
            self.phase_context.pop(content_id, None)
            self.content_priority.pop(content_id, None)

class Comprehension:
    """Enhanced text understanding and reasoning capabilities with workspace reconstruction."""
    
    def __init__(self):
        """Initialize the comprehension module."""
        self.model = None
        self.last_strategy = None
        self.progressive_synthesis = ProgressiveSynthesis()
        self.context_window = ContextWindow()
        self.workspace_reconstructor = WorkspaceReconstructor()  # Tongyi's IterResearch pattern
        self.entity_patterns = self._initialize_entity_patterns()
        self.current_research_round = 0
    
    def _initialize_entity_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for different entity types."""
        return {
            "multi_step_indicators": [
                "find.*(?:coo|ceo|cto).*(?:organization|company)",
                "compile.*statements.*by.*about",
                "(?:what percentage|how much).*(?:reduce|increase)",
                "download.*dataset.*extract",
                "list.*companies.*criteria"
            ],
            "entity_requirements": {
                "coo_search": ["organization", "person", "role"],
                "statements_compilation": ["person", "statement", "source", "date"],
                "percentage_calculation": ["organization", "metric", "date", "baseline"],
                "dataset_extraction": ["organization", "dataset", "timeline", "metrics"],
                "company_listing": ["organization", "location", "sector", "criteria"]
            }
        }
    
    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Enhanced task analysis with multi-step detection and entity requirements."""
        logger.info(f"Analyzing task: {task_description}")
        
        task_lower = task_description.lower()
        
        # Detect task patterns and required entities
        task_analysis = self._detect_task_pattern(task_description)
        
        # Detect direct factual questions
        if re.search(r'^(who|what|when|where|which|how many|how much)\s+', task_lower, re.IGNORECASE):
            analysis = {
                "task_type": "factual_question",
                "answer_type": "direct_answer",
                "synthesis_strategy": "direct_extraction",
                "presentation_format": "direct_answer",
                "required_entities": ["answer"],
                "multi_step": False
            }
            self.last_strategy = "direct_extraction"
            return analysis
        is_list_intent = any(w in task_lower for w in ["compile", "list", "gather", "collect"])
        targets_statements = any(w in task_lower for w in ["statement", "statements", "quote", "quotes", "remark", "remarks", "said", "says"])
        
        if is_list_intent and targets_statements:
            analysis = {
                "task_type": "information_gathering",
                "answer_type": "list_compilation",
                "information_targets": ["statements", "quotes", "remarks"],
                "synthesis_strategy": "progressive_extraction",
                "presentation_format": "list",
                "required_entities": ["person", "statement", "date", "source"],
                "multi_step": False,
                "extraction_focus": "statements_with_attribution"
            }
            self.last_strategy = "progressive_extraction"
            return analysis
        
        # Enhanced multi-step detection
        if task_analysis["is_multi_step"]:
            analysis = {
                "task_type": "multi_step_research",
                "answer_type": task_analysis["answer_type"],
                "synthesis_strategy": "progressive_synthesis",
                "presentation_format": task_analysis["format"],
                "required_entities": task_analysis["entities"],
                "multi_step": True,
                "research_phases": task_analysis["phases"],
                "complexity": task_analysis["complexity"],
                "components": task_analysis.get("components", []),
                "information_flow": task_analysis.get("information_flow", {})
            }
            self.last_strategy = "progressive_synthesis"
            return analysis
        
        # Fallback for general research
        analysis = {
            "task_type": "general_research",
            "synthesis_strategy": "comprehensive_synthesis",
            "presentation_format": "summary",
            "required_entities": ["general"],
            "multi_step": False
        }
        self.last_strategy = "comprehensive_synthesis"
        return analysis
    
    def _detect_task_pattern(self, task_description: str) -> Dict[str, Any]:
        """Detect specific task patterns and their requirements."""
        task_lower = task_description.lower()
        
        # Pattern 1: COO/Role finding with sophisticated decomposition
        if re.search(r'find.*(?:coo|ceo|cto|president|director).*(?:organization|company)', task_lower):
            components = [
                TaskComponent(
                    description="Identify the organization that performed the action",
                    required_entities=["organization", "event", "location", "temporal"],
                    search_strategy="entity_focused"
                ),
                TaskComponent(
                    description="Find the specific role holder at that organization", 
                    required_entities=["person", "role"],
                    depends_on="organization",
                    search_strategy="relationship"
                )
            ]
            
            return {
                "is_multi_step": True,
                "pattern": "role_finding",
                "entities": ["organization", "person", "role"],
                "phases": ["identify_organization", "find_leadership"],
                "answer_type": "specific_person",
                "format": "factual",
                "complexity": "medium",
                "components": components,
                "information_flow": self._map_component_flow(components)
            }
        
        # Pattern 2: Statement compilation with detailed component analysis
        elif re.search(r'compile.*\d+.*statement.*by.*about', task_lower):
            count = re.search(r'\b(\d+)\b', task_description)
            target_count = int(count.group(1)) if count else 10
            
            components = [
                TaskComponent(
                    description="Gather statements from various sources",
                    required_entities=["person", "statement", "date", "source"],
                    search_strategy="comprehensive_collection"
                )
            ]
            
            return {
                "is_multi_step": False,
                "pattern": "statement_compilation",
                "entities": ["person", "statement", "date", "source"],
                "phases": ["gather_statements"],
                "answer_type": "structured_list",
                "format": "list",
                "complexity": "high",
                "target_count": target_count,
                "components": components,
                "information_flow": self._map_component_flow(components)
            }
        
        # Pattern 3: Percentage calculation with multi-step analysis
        elif re.search(r'(?:what percentage|by what percentage).*(?:reduce|increase|change)', task_lower):
            components = [
                TaskComponent(
                    description="Find baseline metrics",
                    required_entities=["organization", "metric", "date", "baseline"],
                    search_strategy="quantitative_search"
                ),
                TaskComponent(
                    description="Find current metrics",
                    required_entities=["organization", "metric", "date", "current"],
                    depends_on="baseline",
                    search_strategy="quantitative_search"
                ),
                TaskComponent(
                    description="Calculate percentage change",
                    required_entities=["calculation"],
                    depends_on="current",
                    search_strategy="analytical"
                )
            ]
            
            return {
                "is_multi_step": True,
                "pattern": "percentage_calculation",
                "entities": ["organization", "metric", "date", "baseline", "current"],
                "phases": ["find_baseline", "find_current", "calculate"],
                "answer_type": "calculation",
                "format": "numerical",
                "complexity": "medium",
                "components": components,
                "information_flow": self._map_component_flow(components)
            }

        # Pattern 4: Dataset extraction with sophisticated workflow
        elif re.search(r'download.*dataset.*extract', task_lower):
            components = [
                TaskComponent(
                    description="Locate the dataset source",
                    required_entities=["organization", "dataset", "location"],
                    search_strategy="direct"
                ),
                TaskComponent(
                    description="Extract timeline data",
                    required_entities=["timeline", "metrics"],
                    depends_on="dataset",
                    search_strategy="data_extraction"
                ),
                TaskComponent(
                    description="Format as structured timeline",
                    required_entities=["formatted_data"],
                    depends_on="timeline",
                    search_strategy="formatting"
                )
            ]
            
            return {
                "is_multi_step": True,
                "pattern": "dataset_extraction",
                "entities": ["organization", "dataset", "timeline", "metrics"],
                "phases": ["locate_dataset", "extract_data", "format_timeline"],
                "answer_type": "time_series",
                "format": "timeline",
                "complexity": "high",
                "components": components,
                "information_flow": self._map_component_flow(components)
            }

        # Pattern 5: Company listing with criteria filtering
        elif re.search(r'(?:list|compile).*compan.*(?:criteria|satisfying)', task_lower):
            components = [
                TaskComponent(
                    description="Identify candidate companies",
                    required_entities=["organization", "location", "sector"],
                    search_strategy="comprehensive_collection"
                ),
                TaskComponent(
                    description="Verify criteria compliance",
                    required_entities=["revenue", "emissions", "metrics"],
                    depends_on="candidates",
                    search_strategy="verification"
                )
            ]
            
            return {
                "is_multi_step": True,
                "pattern": "company_listing",
                "entities": ["organization", "location", "sector", "revenue", "emissions"],
                "phases": ["identify_candidates", "verify_criteria"],
                "answer_type": "filtered_list",
                "format": "list",
                "complexity": "high",
                "components": components,
                "information_flow": self._map_component_flow(components)
            }

        # Default general pattern
        components = [
            TaskComponent(
                description="Research the requested information",
                required_entities=["general"],
                search_strategy="direct"
            )
        ]
        
        return {
            "is_multi_step": False,
            "pattern": "general",
            "entities": ["general"],
            "phases": ["research"],
            "answer_type": "summary",
            "format": "summary",
            "complexity": "low",
            "components": components,
            "information_flow": self._map_component_flow(components)
        }
    
    def _map_component_flow(self, components: List[TaskComponent]) -> Dict[str, str]:
        """Map how information flows between task components."""
        flow = {}
        for component in components:
            if component.depends_on:
                flow[component.description] = f"Requires {component.depends_on} from previous step"
            else:
                flow[component.description] = "Independent starting component"
        return flow

    def process_content(self, content: str, source_url: str, current_phase: str = "general") -> Dict[str, Any]:
        """Process content with progressive synthesis."""
        # Extract entities and integrate into synthesis
        findings = self.progressive_synthesis.integrate_new_information(content, source_url, current_phase)
        
        # Add to context window with relevance scoring
        relevance_score = self._calculate_relevance(content, current_phase)
        self.context_window.add_content(content, source_url, relevance_score, current_phase)
        
        # Extract key insights for immediate use
        insights = self._extract_key_insights(content, current_phase)
        
        return {
            "findings": findings,
            "insights": insights,
            "relevance_score": relevance_score,
            "entity_count": len(findings),
            "processed_phase": current_phase
        }
    
    def _calculate_relevance(self, content: str, current_phase: str) -> float:
        """Calculate relevance score for content based on current phase."""
        relevance = 0.5  # Base relevance
        
        content_lower = content.lower()
        
        # Phase-specific relevance boosters
        phase_keywords = {
            "identify_organization": ["organization", "company", "mediated", "talks"],
            "find_leadership": ["coo", "ceo", "president", "director", "leadership"],
            "gather_statements": ["said", "stated", "declared", "quoted"],
            "find_baseline": ["baseline", "emissions", "scope 1", "scope 2"],
            "find_current": ["current", "latest", "recent"],
            "locate_dataset": ["dataset", "download"],
            "extract_data": ["compute", "training", "maximum", "record"],
            "identify_candidates": ["motor vehicle", "automotive"],
            "verify_criteria": ["revenue", "billion", "emissions", "subsidiary"]
        }
        
        keywords = phase_keywords.get(current_phase, [])
        for keyword in keywords:
            if keyword in content_lower:
                relevance += 0.1
        
        # Content quality factors
        if len(content) > 500:
            relevance += 0.1
        if '"' in content:  # Has quotes
            relevance += 0.1
        if re.search(r'\b\d{4}\b', content):  # Has years
            relevance += 0.1
        
        return min(relevance, 1.0)
    
    def _extract_key_insights(self, content: str, current_phase: str) -> List[str]:
        """Extract key insights from content for immediate use."""
        insights = []
        
        # Look for direct answers based on phase
        if current_phase == "identify_organization":
            # Look for organization names
            org_matches = re.findall(r'\b([A-Z][a-zA-Z\s&,.-]+(?:Inc|Corp|LLC|Ltd|Company|Organization|Institute|Foundation|Group))\b', content)
            for org in org_matches[:3]:
                insights.append(f"Potential organization: {org}")
        
        elif current_phase == "find_leadership":
            # Look for role assignments
            role_matches = re.findall(r'(CEO|COO|CTO|President|Director)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', content, re.IGNORECASE)
            for role, person in role_matches:
                insights.append(f"Found role: {person} is {role}")
        
        elif current_phase == "gather_statements":
            # Look for quotes
            quote_matches = re.findall(r'"([^"]{30,200})"', content)
            for quote in quote_matches[:2]:
                insights.append(f"Found statement: \"{quote[:100]}...\"")
        
        return insights
    
    def get_synthesis_summary(self) -> Dict[str, Any]:
        """Get current synthesis summary."""
        return {
            "high_confidence_findings": self.progressive_synthesis.get_high_confidence_findings(),
            "total_evidence_sources": len(set(
                evidence["source"] for evidence_list in self.progressive_synthesis.evidence_for.values()
                for evidence in evidence_list
            )),
            "confidence_scores": self.progressive_synthesis.confidence_scores,
            "context_size": len(self.context_window.phase_context)
        }
    
    def synthesize_final_answer(self, task_description: str) -> Dict[str, Any]:
        """Create final synthesized answer for the task."""
        return self.progressive_synthesis.synthesize_for_task(task_description)
