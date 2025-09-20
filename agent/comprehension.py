from utils.logger import get_logger
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = get_logger(__name__)

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
        """Synthesize findings specifically for the given task."""
        task_lower = task_description.lower()
        synthesis = {}
        
        # Task-specific synthesis
        if "statements" in task_lower and "biden" in task_lower:
            statements = self.working_hypothesis.get("statements", [])
            # Filter and format Biden statements
            biden_statements = []
            for stmt in statements:
                if isinstance(stmt, dict) and stmt.get("speaker", "").lower() == "biden":
                    biden_statements.append(stmt)
            synthesis["biden_statements"] = biden_statements
        
        elif "coo" in task_lower:
            roles = self.working_hypothesis.get("roles_people", [])
            coo_info = [r for r in roles if isinstance(r, dict) and "coo" in r.get("role", "").lower()]
            synthesis["coo_candidates"] = coo_info
        
        elif "percentage" in task_lower:
            numerical = self.working_hypothesis.get("numerical_data", [])
            percentages = [n for n in numerical if isinstance(n, dict) and n.get("unit") == "percentage"]
            synthesis["percentage_data"] = percentages
        
        # Add confidence scores
        synthesis["confidence_summary"] = {
            key: score for key, score in self.confidence_scores.items()
            if score > 0.5
        }
        
        return synthesis

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
    """Enhanced text understanding and reasoning capabilities with progressive synthesis."""
    
    def __init__(self):
        """Initialize the comprehension module."""
        self.model = None
        self.last_strategy = None
        self.progressive_synthesis = ProgressiveSynthesis()
        self.context_window = ContextWindow()
        self.entity_patterns = self._initialize_entity_patterns()
    
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
        
        # Traditional pattern detection (enhanced)
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
                "complexity": task_analysis["complexity"]
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
        
        # Pattern 1: COO/Role finding
        if re.search(r'find.*(?:coo|ceo|cto|president|director).*(?:organization|company)', task_lower):
            return {
                "is_multi_step": True,
                "pattern": "role_finding",
                "entities": ["organization", "person", "role"],
                "phases": ["identify_organization", "find_leadership"],
                "answer_type": "specific_person",
                "format": "factual",
                "complexity": "medium"
            }
        
        # Pattern 2: Statement compilation
        elif re.search(r'compile.*\d+.*statement.*by.*about', task_lower):
            count = re.search(r'\b(\d+)\b', task_description)
            target_count = int(count.group(1)) if count else 10
            return {
                "is_multi_step": False,
                "pattern": "statement_compilation",
                "entities": ["person", "statement", "date", "source"],
                "phases": ["gather_statements"],
                "answer_type": "structured_list",
                "format": "list",
                "complexity": "high",
                "target_count": target_count
            }
        
        # Pattern 3: Percentage calculation
        elif re.search(r'(?:what percentage|by what percentage).*(?:reduce|increase|change)', task_lower):
            return {
                "is_multi_step": True,
                "pattern": "percentage_calculation",
                "entities": ["organization", "metric", "date", "baseline", "current"],
                "phases": ["find_baseline", "find_current", "calculate"],
                "answer_type": "calculation",
                "format": "numerical",
                "complexity": "medium"
            }
        
        # Pattern 4: Dataset extraction
        elif re.search(r'download.*dataset.*extract', task_lower):
            return {
                "is_multi_step": True,
                "pattern": "dataset_extraction",
                "entities": ["organization", "dataset", "timeline", "metrics"],
                "phases": ["locate_dataset", "extract_data", "format_timeline"],
                "answer_type": "time_series",
                "format": "timeline",
                "complexity": "high"
            }
        
        # Pattern 5: Company listing with criteria
        elif re.search(r'(?:list|compile).*compan.*(?:criteria|satisfying)', task_lower):
            return {
                "is_multi_step": True,
                "pattern": "company_listing",
                "entities": ["organization", "location", "sector", "revenue", "emissions"],
                "phases": ["identify_candidates", "verify_criteria"],
                "answer_type": "filtered_list",
                "format": "list",
                "complexity": "high"
            }
        
        return {
            "is_multi_step": False,
            "pattern": "general",
            "entities": ["general"],
            "phases": ["research"],
            "answer_type": "summary",
            "format": "summary",
            "complexity": "low"
        }
    
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
            "identify_organization": ["organization", "company", "mediated", "talks", "geneva"],
            "find_leadership": ["coo", "ceo", "president", "director", "leadership"],
            "gather_statements": ["said", "stated", "declared", "quoted", "biden"],
            "find_baseline": ["2021", "baseline", "emissions", "scope 1", "scope 2"],
            "find_current": ["2023", "current", "latest", "recent"],
            "locate_dataset": ["dataset", "download", "epoch ai", "models"],
            "extract_data": ["compute", "training", "maximum", "record"],
            "identify_candidates": ["eu", "european", "motor vehicle", "automotive"],
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
