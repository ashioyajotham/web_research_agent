import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class TaskComponent:
    """Represents a component of a multistep task"""
    description: str
    required_entities: List[str]
    depends_on: Optional[str] = None  # Previous component this depends on
    search_strategy: str = "direct"  # direct, entity_focused, relationship

@dataclass 
class TaskAnalysis:
    """Enhanced task analysis with decomposition"""
    task_type: str
    complexity: str  # simple, multistep, comparative
    components: List[TaskComponent]
    synthesis_strategy: str
    expected_entities: List[str]
    information_flow: Dict[str, str]  # how information flows between components

class Comprehension:
    """Enhanced comprehension with task decomposition and entity awareness."""
    
    def __init__(self):
        self.model = None
        self.last_strategy = None
        # Pattern libraries for different task types
        self.multistep_patterns = [
            r"find.*?(?:ceo|coo|founder|president).*?(?:of|at).*?(?:company|organization).*?(?:that|which)",
            r"(?:what|who).*?(?:acquired|bought|purchased).*?by.*?(?:in|during)\s+\d{4}",
            r"(?:percentage|percent).*?(?:increase|decrease|change).*?(?:from|between).*?\d{4}.*?(?:to|and).*?\d{4}"
        ]
        
        self.entity_patterns = {
            'organization': r'\b[A-Z][a-zA-Z\s&,.]+(?:Inc|Corp|LLC|Ltd|Company|Group|Association|Foundation)\b',
            'person_role': r'\b(?:CEO|COO|CTO|President|Founder|Director|Manager)\s+(?:of\s+)?[A-Z][a-zA-Z\s]+',
            'temporal': r'\b(?:in\s+)?\d{4}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            'financial': r'\$[\d,]+(?:\.\d{2})?[BMK]?|\d+(?:\.\d+)?%|\d+(?:,\d{3})*\s+(?:million|billion|thousand)',
            'location': r'\b[A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2,})\b'
        }
    
    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Enhanced task analysis with decomposition and entity prediction."""
        logger.info(f"Analyzing task: {task_description}")
        
        # First, determine task complexity
        complexity = self._determine_complexity(task_description)
        
        if complexity == "multistep":
            return self._analyze_multistep_task(task_description)
        elif complexity == "comparative":
            return self._analyze_comparative_task(task_description)
        else:
            return self._analyze_simple_task(task_description)
    
    def _determine_complexity(self, task: str) -> str:
        """Determine if task is simple, multistep, or comparative."""
        task_lower = task.lower()
        
        # Check for multistep indicators
        multistep_indicators = [
            "find.*?of.*?that", "who.*?at.*?which", "what.*?by.*?that",
            "percentage.*?from.*?to", "compare.*?between", "difference.*?and"
        ]
        
        for pattern in multistep_indicators:
            if re.search(pattern, task_lower, re.IGNORECASE):
                return "multistep"
        
        # Check for comparison indicators
        if any(word in task_lower for word in ["compare", "versus", "vs", "difference", "better", "worse"]):
            return "comparative"
            
        return "simple"
    
    def _analyze_multistep_task(self, task: str) -> Dict[str, Any]:
        """Analyze multistep tasks and decompose them."""
        components = []
        
        # Example: "Find the COO of the organization that mediated talks between US and Chinese AI companies in Geneva in 2023"
        if re.search(r"find.*?(ceo|coo|cto|president|founder).*?of.*?organization.*?that", task.lower()):
            components.extend([
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
            ])
        
        # Detect expected entities from the task
        expected_entities = self._extract_expected_entities(task)
        
        return {
            "task_type": "multistep_research",
            "complexity": "multistep", 
            "components": components,
            "synthesis_strategy": "progressive_synthesis",
            "expected_entities": expected_entities,
            "information_flow": self._map_information_flow(components),
            "presentation_format": "structured_answer"
        }
    
    def _analyze_comparative_task(self, task: str) -> Dict[str, Any]:
        """Analyze comparative research tasks."""
        return {
            "task_type": "comparative_research",
            "complexity": "comparative",
            "components": [
                TaskComponent(
                    description="Gather information about first entity",
                    required_entities=self._extract_expected_entities(task),
                    search_strategy="direct"
                ),
                TaskComponent(
                    description="Gather information about second entity", 
                    required_entities=self._extract_expected_entities(task),
                    search_strategy="direct"
                )
            ],
            "synthesis_strategy": "comparative_synthesis",
            "expected_entities": self._extract_expected_entities(task),
            "presentation_format": "comparison_table"
        }
    
    def _analyze_simple_task(self, task: str) -> Dict[str, Any]:
        """Analyze simple, direct research tasks."""
        task_lower = task.lower()
        
        # Check for list compilation tasks
        if any(word in task_lower for word in ["list", "compile", "gather", "collect"]):
            return {
                "task_type": "information_gathering",
                "complexity": "simple",
                "components": [
                    TaskComponent(
                        description="Gather and compile requested information",
                        required_entities=self._extract_expected_entities(task),
                        search_strategy="direct"
                    )
                ],
                "synthesis_strategy": "collect_and_organize",
                "expected_entities": self._extract_expected_entities(task),
                "presentation_format": "list"
            }
        
        # Default simple research
        return {
            "task_type": "simple_research", 
            "complexity": "simple",
            "components": [
                TaskComponent(
                    description="Research the requested information",
                    required_entities=self._extract_expected_entities(task),
                    search_strategy="direct"
                )
            ],
            "synthesis_strategy": "extract_and_verify",
            "expected_entities": self._extract_expected_entities(task),
            "presentation_format": "direct_answer"
        }
    
    def _extract_expected_entities(self, task: str) -> List[str]:
        """Extract what types of entities we expect to find."""
        expected = []
        task_lower = task.lower()
        
        # Role-based entities
        if any(role in task_lower for role in ["ceo", "coo", "cto", "president", "founder", "director"]):
            expected.extend(["person", "role", "organization"])
            
        # Financial entities
        if any(word in task_lower for word in ["revenue", "profit", "percentage", "emissions", "billion", "million"]):
            expected.append("financial")
            
        # Temporal entities
        if re.search(r'\d{4}', task) or any(word in task_lower for word in ["year", "month", "date", "when"]):
            expected.append("temporal")
            
        # Location entities  
        if any(word in task_lower for word in ["where", "location", "country", "city", "geneva", "us", "china"]):
            expected.append("location")
            
        # Organizations
        if any(word in task_lower for word in ["company", "organization", "corp", "inc", "group"]):
            expected.append("organization")
            
        return list(set(expected)) if expected else ["general"]
    
    def _map_information_flow(self, components: List[TaskComponent]) -> Dict[str, str]:
        """Map how information flows between task components."""
        flow = {}
        for component in components:
            if component.depends_on:
                flow[component.description] = f"Requires {component.depends_on} from previous step"
        return flow
    
    def get_next_search_strategy(self, current_entities: Dict, target_component: TaskComponent) -> str:
        """Determine next search strategy based on current entities and target component."""
        if target_component.depends_on and current_entities:
            # We have dependencies, use entity-focused search
            return "entity_focused"
        elif target_component.search_strategy == "relationship":
            # Need to find relationships between entities
            return "relationship"
        else:
            return "direct"