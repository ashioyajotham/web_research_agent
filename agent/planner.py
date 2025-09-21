from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import json

from utils.logger import get_logger
from config.config import get_config

logger = get_logger(__name__)

try:
    import google.generativeai as genai
except Exception:
    genai = None

@dataclass
class PlanStep:
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    component_id: Optional[str] = None  # Which task component this serves
    depends_on_entities: List[str] = None  # What entities this step needs

@dataclass
class Plan:
    task: str
    steps: List[PlanStep]
    strategy: str  # overall planning strategy used

class AdaptivePlanner:
    """Creates adaptive execution plans based on task analysis."""
    
    def __init__(self):
        self.config = get_config()
        self.model = None
        if genai and self.config.get("gemini_api_key"):
            try:
                genai.configure(api_key=self.config.get("gemini_api_key"))
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                logger.warning(f"GenAI init failed; using adaptive planning: {e}")
                self.model = None
    
    def create_plan(self, task_description: str, task_analysis: Dict[str, Any]) -> Plan:
        """Create an adaptive plan based on task complexity and components."""
        try:
            complexity = task_analysis.get("complexity", "simple")
            
            if complexity == "multistep":
                return self._create_multistep_plan(task_description, task_analysis)
            elif complexity == "comparative":
                return self._create_comparative_plan(task_description, task_analysis)
            else:
                return self._create_simple_plan(task_description, task_analysis)
                
        except Exception as e:
            logger.warning(f"Adaptive planning failed, using fallback: {e}")
            return self._create_fallback_plan(task_description)
    
    def _create_multistep_plan(self, task: str, analysis: Dict) -> Plan:
        """Create plan for multistep tasks with progressive entity discovery."""
        steps = []
        components = analysis.get("components", [])
        
        for i, component in enumerate(components):
            # Phase 1: Initial search for this component
            search_query = self._create_component_search_query(task, component, i)
            steps.append(PlanStep(
                description=f"Search for component {i+1}: {component.description}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 15},
                component_id=f"component_{i}"
            ))
            
            # Phase 2: Browse top results for this component
            for j in range(3):  # Fewer browser calls per component, more focused
                steps.append(PlanStep(
                    description=f"Extract content for component {i+1} from result {j}",
                    tool_name="browser", 
                    parameters={"url": f"{{search_result_{j}_url}}", "extract_type": "main_content"},
                    component_id=f"component_{i}",
                    depends_on_entities=component.required_entities
                ))
            
            # Phase 3: Entity-focused refinement search if this isn't the last component
            if i < len(components) - 1:
                steps.append(PlanStep(
                    description=f"Refine search based on entities found in component {i+1}",
                    tool_name="search",
                    parameters={"query": "{entity_focused_query}", "num_results": 10},
                    component_id=f"component_{i}_refine"
                ))
        
        # Final synthesis
        steps.append(PlanStep(
            description="Synthesize findings from all components",
            tool_name="present",
            parameters={
                "prompt": self._create_multistep_synthesis_prompt(task, analysis),
                "format_type": analysis.get("presentation_format", "structured_answer"),
                "title": "Research Results",
                "synthesis_mode": "progressive"
            }
        ))
        
        return Plan(task=task, steps=steps, strategy="multistep_progressive")
    
    def _create_comparative_plan(self, task: str, analysis: Dict) -> Plan:
        """Create plan for comparative research tasks."""
        steps = []
        entities = self._extract_comparison_entities(task)
        
        # Search for each entity separately
        for i, entity in enumerate(entities):
            search_query = f'"{entity}" {self._extract_comparison_context(task)}'
            steps.append(PlanStep(
                description=f"Search for information about {entity}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 10},
                component_id=f"entity_{i}"
            ))
            
            # Browse top results for this entity
            for j in range(2):
                steps.append(PlanStep(
                    description=f"Extract content about {entity} from result {j}",
                    tool_name="browser",
                    parameters={"url": f"{{search_result_{j}_url}}", "extract_type": "main_content"},
                    component_id=f"entity_{i}"
                ))
        
        # Synthesis with comparison focus
        steps.append(PlanStep(
            description="Compare and synthesize findings",
            tool_name="present",
            parameters={
                "prompt": self._create_comparative_synthesis_prompt(task, analysis),
                "format_type": "comparison_table",
                "title": "Comparison Results",
                "synthesis_mode": "comparative"
            }
        ))
        
        return Plan(task=task, steps=steps, strategy="comparative_parallel")
    
    def _create_simple_plan(self, task: str, analysis: Dict) -> Plan:
        """Create plan for simple, direct research tasks."""
        search_query = self._create_targeted_search_query(task)
        
        steps = [
            PlanStep(
                description=f"Search for: {search_query}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 12}
            )
        ]
        
        # Browse fewer results but more strategically
        for i in range(4):
            steps.append(PlanStep(
                description=f"Extract content from search result {i}",
                tool_name="browser",
                parameters={"url": f"{{search_result_{i}_url}}", "extract_type": "main_content"}
            ))
        
        steps.append(PlanStep(
            description="Organize and present findings",
            tool_name="present", 
            parameters={
                "prompt": self._create_simple_synthesis_prompt(task, analysis),
                "format_type": analysis.get("presentation_format", "direct_answer"),
                "title": "Research Results",
                "suppress_debug": analysis.get("presentation_format") == "direct_answer"
            }
        ))
        
        return Plan(task=task, steps=steps, strategy="direct_research")
    
    def _create_component_search_query(self, task: str, component, phase: int) -> str:
        """Create focused search query for a task component."""
        if phase == 0 and "organization" in component.required_entities:
            # First component usually needs to identify the organization
            return self._extract_organization_search_terms(task)
        elif component.depends_on:
            # Subsequent components depend on previous findings
            return f"{{{component.depends_on}_entity}} {self._extract_role_search_terms(task)}"
        else:
            return self._create_targeted_search_query(task)
    
    def _extract_organization_search_terms(self, task: str) -> str:
        """Extract terms for finding organizations mentioned in task."""
        # Remove stopwords but keep context
        context_words = []
        words = re.findall(r'\b\w+\b', task.lower())
        
        important_context = []
        for i, word in enumerate(words):
            if word in ["mediated", "talks", "negotiations", "meeting", "conference"]:
                # Include surrounding context
                start = max(0, i-2)
                end = min(len(words), i+3)
                important_context.extend(words[start:end])
        
        return " ".join(important_context[:8]) if important_context else self._create_targeted_search_query(task)
    
    def _extract_role_search_terms(self, task: str) -> str:
        """Extract role-specific search terms."""
        roles = re.findall(r'\b(CEO|COO|CTO|President|Founder|Director|Manager)\b', task, re.IGNORECASE)
        return roles[0] if roles else "leadership team"
    
    def _create_targeted_search_query(self, task: str) -> str:
        """Create targeted search query removing less useful words."""
        # Improved stopword list - more strategic
        STOP_WORDS = {
            "the", "and", "for", "with", "that", "this", "from", "into", "over", "under",
            "they", "them", "are", "was", "were", "have", "has", "had", "each", "must", 
            "made", "more", "than", "what", "which", "who", "when", "where", "why", "how",
            "of", "to", "in", "on", "by", "as", "it", "an", "a", "or", "be", "is", "any", "all"
        }
        
        # Keep task-specific words that might seem like stopwords
        KEEP_WORDS = {
            "find", "list", "compile", "gather", "between", "us", "china", "geneva", 
            "organization", "company", "talks", "percentage", "emissions"
        }
        
        words = re.findall(r"[A-Za-z0-9%€$-]+", task or "")
        filtered_words = []
        
        for word in words:
            word_lower = word.lower()
            if (len(word) >= 3 and 
                (word_lower not in STOP_WORDS or word_lower in KEEP_WORDS)):
                filtered_words.append(word)
        
        return " ".join(filtered_words[:10]) if filtered_words else task.strip()
    
    def _extract_comparison_entities(self, task: str) -> List[str]:
        """Extract entities to compare from task description."""
        # Simple extraction - in practice would be more sophisticated
        words = task.split()
        entities = []
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entities.append(word)
        return entities[:2]  # Limit to two main entities
    
    def _extract_comparison_context(self, task: str) -> str:
        """Extract comparison context (what to compare about)."""
        return self._create_targeted_search_query(task)
    
    def _create_multistep_synthesis_prompt(self, task: str, analysis: Dict) -> str:
        """Create synthesis prompt for multistep tasks."""
        components = analysis.get("components", [])
        component_descriptions = [comp.description for comp in components]
        
        return f"""
Based on the research findings, answer this multistep question: {task}

The task has been broken down into these components:
{chr(10).join(f"{i+1}. {desc}" for i, desc in enumerate(component_descriptions))}

Provide a direct, factual answer that addresses each component. Include:
- The specific information requested
- Source citations where possible
- Clear connections between the components

Format as a structured answer with clear sections for each component.
"""
    
    def _create_comparative_synthesis_prompt(self, task: str, analysis: Dict) -> str:
        """Create synthesis prompt for comparative tasks."""
        return f"""
Based on the research findings, provide a comparison for: {task}

Create a structured comparison that includes:
- Key similarities between the entities
- Key differences between the entities  
- Relevant metrics or data points
- Source citations

Format as a comparison table or structured analysis.
"""
    
    def _create_simple_synthesis_prompt(self, task: str, analysis: Dict) -> str:
        """Create synthesis prompt for simple tasks."""
        format_type = analysis.get("presentation_format", "direct_answer")
        
        if format_type == "list":
            return f"""
Based on the research findings, create a list for: {task}

Provide:
- Clear, factual list items
- Source citations for each item
- No duplicates or redundant information

Format as a numbered or bulleted list.
"""
        else:
            return f"""
Based on the research findings, provide a direct answer to: {task}

Include:
- The specific information requested
- Supporting evidence
- Source citations
- Clear, factual presentation
"""
    
    def _create_fallback_plan(self, task: str) -> Plan:
        """Fallback plan when adaptive planning fails."""
        query = self._create_targeted_search_query(task)
        steps = [
            PlanStep(
                description=f"Search for: {query}",
                tool_name="search", 
                parameters={"query": query, "num_results": 10}
            )
        ]
        
        for i in range(3):
            steps.append(PlanStep(
                description=f"Extract content from result {i}",
                tool_name="browser",
                parameters={"url": f"{{search_result_{i}_url}}", "extract_type": "main_content"}
            ))
        
        steps.append(PlanStep(
            description="Present findings",
            tool_name="present",
            parameters={
                "prompt": f"Answer: {task}",
                "format_type": "summary"
            }
        ))
        
        return Plan(task=task, steps=steps, strategy="fallback")

# Backward compatibility
class Planner(AdaptivePlanner):
    """Alias for backward compatibility"""
    pass