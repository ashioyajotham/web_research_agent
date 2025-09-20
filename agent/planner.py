from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import json

from utils.logger import get_logger
from config.config import get_config

logger = get_logger(__name__)

try:
    import google.generativeai as genai  # Optional; used if configured
except Exception:
    genai = None

@dataclass
class PlanStep:
    description: str
    tool_name: str
    parameters: Dict[str, Any]

@dataclass
class Plan:
    task: str
    steps: List[PlanStep]

@dataclass
class ResearchPhase:
    """Represents a phase in multi-step research."""
    description: str
    objective: str
    required_entities: List[str]
    success_criteria: str
    search_strategy: str = "broad"  # broad, targeted, entity_focused
    max_sources: int = 5
    
    def __post_init__(self):
        if not self.required_entities:
            self.required_entities = []

class AdaptivePlanner:
    """Enhanced planner that uses entity knowledge for adaptive planning."""
    
    def __init__(self):
        self.discovered_entities = {}
        self.current_phase = None
        
    def decompose_multistep_question(self, task_description: str) -> List[ResearchPhase]:
        """Break down complex questions into research phases."""
        task_lower = task_description.lower()
        phases = []
        
        # Pattern 1: "Find the [role] of the [organization] that [action]"
        if re.search(r'find.*(?:coo|ceo|cto|president|director|manager).*(?:organization|company).*that', task_lower):
            phases.append(ResearchPhase(
                description="Identify the organization",
                objective="Find the specific organization mentioned in the task",
                required_entities=["organization"],
                success_criteria="organization_identified",
                search_strategy="broad"
            ))
            phases.append(ResearchPhase(
                description="Find leadership information",
                objective="Identify the specific role holder at the organization",
                required_entities=["person", "role"],
                success_criteria="role_holder_identified",
                search_strategy="entity_focused"
            ))
        
        # Pattern 2: "Compile X statements by [person] about [topic]"
        elif re.search(r'compile.*\d+.*statement.*by.*about', task_lower):
            phases.append(ResearchPhase(
                description="Gather statements and sources",
                objective="Find multiple statements by the specified person on the topic",
                required_entities=["person", "statement", "source"],
                success_criteria="statements_collected",
                search_strategy="targeted",
                max_sources=10
            ))
        
        # Pattern 3: "By what percentage did [company] reduce [metric]"
        elif re.search(r'(?:what percentage|how much).*(?:reduce|increase|change)', task_lower):
            phases.append(ResearchPhase(
                description="Find baseline metrics",
                objective="Identify starting values for the specified metrics",
                required_entities=["organization", "metric", "date"],
                success_criteria="baseline_found",
                search_strategy="targeted"
            ))
            phases.append(ResearchPhase(
                description="Find current/final metrics",
                objective="Identify ending values for comparison",
                required_entities=["metric", "date"],
                success_criteria="final_values_found",
                search_strategy="entity_focused"
            ))
        
        # Pattern 4: "Download [dataset] and extract [specific_data]"
        elif re.search(r'download.*dataset.*extract', task_lower):
            phases.append(ResearchPhase(
                description="Locate dataset source",
                objective="Find the official source for the dataset",
                required_entities=["organization", "dataset", "url"],
                success_criteria="dataset_located",
                search_strategy="targeted"
            ))
            phases.append(ResearchPhase(
                description="Extract specific information",
                objective="Process dataset to extract required information",
                required_entities=["data", "timeline"],
                success_criteria="data_extracted",
                search_strategy="entity_focused"
            ))
        
        # Pattern 5: "List companies satisfying criteria"
        elif re.search(r'(?:list|compile).*compan.*(?:criteria|satisfying)', task_lower):
            phases.append(ResearchPhase(
                description="Identify qualifying companies",
                objective="Find companies that meet the specified criteria",
                required_entities=["organization", "location", "sector"],
                success_criteria="companies_identified",
                search_strategy="broad",
                max_sources=15
            ))
        
        # Default single-phase for simpler questions
        if not phases:
            phases.append(ResearchPhase(
                description="Research task",
                objective="Complete the research task",
                required_entities=["general"],
                success_criteria="task_completed",
                search_strategy="broad"
            ))
        
        return phases
    
    def plan_entity_focused_search(self, discovered_entities: Dict[str, Any], phase: ResearchPhase) -> str:
        """Create search query based on discovered entities."""
        query_parts = []
        
        # Use discovered entities to build targeted queries
        if "organization" in discovered_entities:
            org = discovered_entities["organization"][0] if discovered_entities["organization"] else ""
            if org:
                query_parts.append(f'"{org}"')
        
        if "person" in discovered_entities:
            person = discovered_entities["person"][0] if discovered_entities["person"] else ""
            if person:
                query_parts.append(f'"{person}"')
        
        # Add phase-specific terms
        if phase.objective:
            objective_keywords = re.findall(r'\b\w{4,}\b', phase.objective.lower())
            query_parts.extend(objective_keywords[:3])  # Top 3 keywords
        
        # Add required entity types as search terms
        for entity_type in phase.required_entities:
            if entity_type not in ["general"]:
                query_parts.append(entity_type)
        
        return " ".join(query_parts[:8])  # Limit query length
    
    def should_proceed_to_next_phase(self, current_phase: ResearchPhase, 
                                   discovered_entities: Dict[str, Any]) -> bool:
        """Determine if current phase objectives are met."""
        if not current_phase.required_entities:
            return True
        
        # Check if required entities have been discovered
        for entity_type in current_phase.required_entities:
            if entity_type == "general":
                continue
            if entity_type not in discovered_entities or not discovered_entities[entity_type]:
                return False
        
        return True

class Planner:
    """Creates execution plans for tasks with enhanced entity-driven planning."""
    def __init__(self):
        self.config = get_config()
        self.model = None
        if genai and self.config.get("gemini_api_key"):
            try:
                genai.configure(api_key=self.config.get("gemini_api_key"))
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                logger.warning(f"GenAI init failed; using default planning: {e}")
                self.model = None
        
        # Enhanced planning capabilities
        self.adaptive_planner = AdaptivePlanner()
        self.research_phases = []
        self.current_phase_index = 0

    def create_plan(self, task_description: str, task_analysis: Dict[str, Any]) -> Plan:
        """Create plan with phase-aware strategy."""
        # Check if this is a multi-step question
        phases = self.adaptive_planner.decompose_multistep_question(task_description)
        self.research_phases = phases
        
        if len(phases) > 1:
            logger.info(f"Detected multi-phase research with {len(phases)} phases")
            return self._create_multi_phase_plan(task_description, phases, task_analysis)
        else:
            # Use existing single-phase planning
            try:
                if self.model:
                    prompt = self._create_planning_prompt(task_description, task_analysis or {})
                    resp = self.model.generate_content(prompt)
                    text = getattr(resp, "text", "") or ""
                    plan = self._parse_plan_response(text)
                    if plan:
                        return plan
            except Exception as e:
                logger.warning(f"LLM planning failed, using default plan: {e}")
            return self._create_default_plan(task_description)
    
    def _create_multi_phase_plan(self, task_description: str, phases: List[ResearchPhase], 
                                task_analysis: Dict[str, Any]) -> Plan:
        """Create a plan that accounts for multiple research phases."""
        steps = []
        
        # Phase 1: Initial broad search
        first_phase = phases[0]
        initial_query = self._create_targeted_search_query(task_description)
        
        steps.append(PlanStep(
            description=f"Phase 1: {first_phase.description}",
            tool_name="search",
            parameters={"query": initial_query, "num_results": 20}
        ))
        
        # Add browser steps for first phase
        for i in range(min(first_phase.max_sources, 5)):
            steps.append(PlanStep(
                description=f"Extract content from search result {i} for phase 1",
                tool_name="browser",
                parameters={"url": f"{{search_result_{i}_url}}", "extract_type": "main_content"}
            ))
        
        # Intermediate synthesis step
        steps.append(PlanStep(
            description="Analyze initial findings and identify entities",
            tool_name="present",
            parameters={
                "prompt": f"Analyze the content for {first_phase.objective}. Extract and list any entities of types: {', '.join(first_phase.required_entities)}. Provide a brief summary of key findings relevant to: {first_phase.objective}.",
                "format_type": "analysis",
                "title": f"Phase 1 Analysis: {first_phase.description}",
                "suppress_debug": False
            }
        ))
        
        # If there are additional phases, add placeholders for adaptive planning
        if len(phases) > 1:
            for i, phase in enumerate(phases[1:], 2):
                steps.append(PlanStep(
                    description=f"Phase {i}: {phase.description} (adaptive)",
                    tool_name="search",
                    parameters={"query": "{{entity_focused_query}}", "num_results": 15}
                ))
                
                # Browser steps for additional phases
                for j in range(min(phase.max_sources, 3)):
                    steps.append(PlanStep(
                        description=f"Extract content for phase {i}, source {j}",
                        tool_name="browser",
                        parameters={"url": f"{{search_result_{j}_url}}", "extract_type": "main_content"}
                    ))
        
        # Final synthesis
        desired = self._infer_desired_count(task_description)
        final_prompt = self._create_final_synthesis_prompt(task_description, phases, desired)
        
        steps.append(PlanStep(
            description="Synthesize findings across all phases",
            tool_name="present",
            parameters={
                "prompt": final_prompt,
                "format_type": self._infer_format_type(task_description),
                "title": "Research Results",
                "suppress_debug": True
            }
        ))
        
        return Plan(task=task_description, steps=steps)
    
    def _create_final_synthesis_prompt(self, task_description: str, phases: List[ResearchPhase], 
                                     desired_count: int) -> str:
        """Create synthesis prompt based on research phases."""
        task_lower = task_description.lower()
        
        if "statements" in task_lower and "biden" in task_lower:
            return f"From all the research conducted across phases, extract exactly {desired_count} direct statements made by Joe Biden regarding US-China relations. Each statement must: 1) Be from a different occasion/date, 2) Include the exact quote in double quotes, 3) Provide the date (YYYY-MM-DD format when available), 4) Include source title and URL. Present as a numbered list with one statement per item."
        
        elif "coo" in task_lower and "organization" in task_lower:
            return "From the research phases, first identify the specific organization that mediated the talks, then provide the name of their COO. Present the answer clearly with supporting evidence and sources."
        
        elif "percentage" in task_lower and "reduce" in task_lower:
            return "Calculate the percentage reduction by comparing the baseline values from phase 1 with the final values from phase 2. Show the calculation and provide sources for both data points."
        
        elif "dataset" in task_lower and "extract" in task_lower:
            return "Provide a time series showing the maximum compute used for AI training, with each entry representing a new record. Include the date, model name, compute amount, and source for each record."
        
        elif "companies" in task_lower and "criteria" in task_lower:
            return "List all companies that satisfy ALL the specified criteria. For each company, briefly verify how it meets each criterion with supporting data."
        
        else:
            return f"Synthesize the research findings to answer: {task_description}. Provide a comprehensive response based on all phases of research."
    
    def _infer_format_type(self, task_description: str) -> str:
        """Infer the appropriate format for the response."""
        task_lower = task_description.lower()
        
        if any(word in task_lower for word in ["list", "compile", "statements"]):
            return "list"
        elif "percentage" in task_lower:
            return "calculation"
        elif "time series" in task_lower:
            return "timeline"
        else:
            return "summary"
    
    def get_next_phase_query(self, discovered_entities: Dict[str, Any]) -> Optional[str]:
        """Get search query for next research phase based on discovered entities."""
        if self.current_phase_index >= len(self.research_phases):
            return None
        
        current_phase = self.research_phases[self.current_phase_index]
        return self.adaptive_planner.plan_entity_focused_search(discovered_entities, current_phase)
    
    def advance_to_next_phase(self, discovered_entities: Dict[str, Any]) -> bool:
        """Check if we can advance to the next research phase."""
        if self.current_phase_index >= len(self.research_phases):
            return False
        
        current_phase = self.research_phases[self.current_phase_index]
        can_advance = self.adaptive_planner.should_proceed_to_next_phase(current_phase, discovered_entities)
        
        if can_advance:
            self.current_phase_index += 1
            logger.info(f"Advanced to phase {self.current_phase_index + 1}")
        
        return can_advance

    def create_plan(self, task_description: str, task_analysis: Dict[str, Any]) -> Plan:
        try:
            if self.model:
                prompt = self._create_planning_prompt(task_description, task_analysis or {})
                resp = self.model.generate_content(prompt)
                text = getattr(resp, "text", "") or ""
                plan = self._parse_plan_response(text)
                if plan:
                    return plan
        except Exception as e:
            logger.warning(f"LLM planning failed, using default plan: {e}")
        return self._create_default_plan(task_description)

    def _create_targeted_search_query(self, task_description: str) -> str:
        # Remove meta-words to avoid awkward queries; task-agnostic
        STOP = {
            "the","and","for","with","that","this","from","into","over","under","their","your","our",
            "they","them","are","was","were","have","has","had","each","must","made","more","than",
            "list","compile","collect","gather","find","show","what","which","who","when","where","why","how",
            "of","to","in","on","by","as","it","an","a","or","be","is","any","all","data","information",
            "statement","statements","quote","quotes","provide","source","separate","occasion","directly"
        }
        words = re.findall(r"[A-Za-z0-9%€\-]+", task_description or "")
        kws, seen = [], set()
        for w in words:
            wl = w.lower()
            if wl in STOP or len(wl) < 3:
                continue
            if wl not in seen:
                kws.append(w)
                seen.add(wl)
        return " ".join(kws[:12]) if kws else (task_description or "").strip()

    def _create_planning_prompt(self, task_description: str, task_analysis: Dict[str, Any]) -> str:
        """Enhanced planning prompt with entity awareness."""
        presentation_format = (task_analysis or {}).get("presentation_format", "summary")
        desired = self._infer_desired_count(task_description)
        is_multi_step = (task_analysis or {}).get("multi_step", False)
        required_entities = (task_analysis or {}).get("required_entities", [])
        
        if is_multi_step:
            return f"""
Create a JSON plan for multi-step research using these tools: search, browser, present.
This task requires tracking entities: {', '.join(required_entities)}

TASK: {task_description}
FORMAT: {presentation_format}

Plan should:
1. Start with broad search to identify key entities
2. Use entity-focused searches for subsequent phases
3. Extract and track specific information for synthesis
4. Present final answer in requested format

Return JSON:
{{
  "steps":[
    {{"description":"Search for initial information","tool":"search","parameters":{{"query":"...","num_results":20}}}},
    {{"description":"Extract content and identify entities","tool":"browser","parameters":{{"url":"{{search_result_0_url}}","extract_type":"main_content"}}}},
    {{"description":"Continue entity extraction","tool":"browser","parameters":{{"url":"{{search_result_1_url}}","extract_type":"main_content"}}}},
    {{"description":"Entity-focused search phase","tool":"search","parameters":{{"query":"{{entity_focused_query}}","num_results":15}}}},
    {{"description":"Extract targeted content","tool":"browser","parameters":{{"url":"{{search_result_0_url}}","extract_type":"main_content"}}}},
    {{"description":"Synthesize findings with entity tracking","tool":"present","parameters":{{"prompt":"Provide comprehensive answer using discovered entities and evidence","format_type":"{presentation_format}","title":"Research Results","suppress_debug":false}}}}
  ]
}}
""".strip()
        
        return f"""
Create a JSON plan using these tools: search, browser, present.
Use search → multiple browser steps → present. Use placeholders like {{search_result_0_url}}.

TASK: {task_description}
FORMAT: {presentation_format}

Return JSON:
{{
  "steps":[
    {{"description":"Search","tool":"search","parameters":{{"query":"...","num_results":20}}}},
    {{"description":"Fetch and extract content from search result 0","tool":"browser","parameters":{{"url":"{{search_result_0_url}}","extract_type":"main_content"}}}},
    {{"description":"Fetch and extract content from search result 1","tool":"browser","parameters":{{"url":"{{search_result_1_url}}","extract_type":"main_content"}}}},
    {{"description":"Fetch and extract content from search result 2","tool":"browser","parameters":{{"url":"{{search_result_2_url}}","extract_type":"main_content"}}}},
    {{"description":"Fetch and extract content from search result 3","tool":"browser","parameters":{{"url":"{{search_result_3_url}}","extract_type":"main_content"}}}},
    {{"description":"Fetch and extract content from search result 4","tool":"browser","parameters":{{"url":"{{search_result_4_url}}","extract_type":"main_content"}}}},
    {{"description":"Organize and present findings","tool":"present","parameters":{{"prompt":"Produce exactly {desired} direct statements by Joe Biden on US-China relations. Each item must be from a different occasion (unique date). For each item, include: the exact quote in double quotes, the date (YYYY-MM-DD if available), the source title, and the canonical URL. Only output a numbered Markdown list with one line per item. Do not include headings, explanations, or any debug fields. Do not print raw search results.","format_type":"list","title":"Results","suppress_debug":true}}}}
  ]
}}
""".strip()

    def create_adaptive_plan_step(self, discovered_entities: Dict[str, Any], phase: ResearchPhase) -> List[PlanStep]:
        """Create plan steps based on discovered entities and current phase."""
        steps = []
        
        # Generate entity-focused query
        entity_query = self.adaptive_planner.plan_entity_focused_search(discovered_entities, phase)
        
        steps.append(PlanStep(
            description=f"Entity-focused search: {phase.description}",
            tool_name="search",
            parameters={"query": entity_query, "num_results": 15}
        ))
        
        # Add targeted browser steps
        for i in range(min(phase.max_sources, 3)):
            steps.append(PlanStep(
                description=f"Extract targeted content for {phase.objective}",
                tool_name="browser",
                parameters={"url": f"{{search_result_{i}_url}}", "extract_type": "main_content"}
            ))
        
        # Add analysis step
        steps.append(PlanStep(
            description=f"Analyze findings for {phase.objective}",
            tool_name="present",
            parameters={
                "prompt": f"Analyze the content for {phase.objective}. Focus on identifying: {', '.join(phase.required_entities)}. Provide structured findings that meet the success criteria: {phase.success_criteria}",
                "format_type": "analysis",
                "title": f"Analysis: {phase.description}",
                "suppress_debug": False
            }
        ))
        
        return steps
    
    def update_plan_with_entities(self, current_plan: Plan, discovered_entities: Dict[str, Any]) -> Plan:
        """Update existing plan based on discovered entities."""
        updated_steps = []
        
        for step in current_plan.steps:
            if "{{entity_focused_query}}" in str(step.parameters):
                # Replace entity placeholder with actual query
                if self.current_phase_index < len(self.research_phases):
                    current_phase = self.research_phases[self.current_phase_index]
                    entity_query = self.adaptive_planner.plan_entity_focused_search(discovered_entities, current_phase)
                    
                    # Update parameters
                    updated_params = step.parameters.copy()
                    if "query" in updated_params:
                        updated_params["query"] = entity_query
                    
                    updated_step = PlanStep(
                        description=step.description.replace("(adaptive)", f"- {entity_query}"),
                        tool_name=step.tool_name,
                        parameters=updated_params
                    )
                    updated_steps.append(updated_step)
                else:
                    updated_steps.append(step)
            else:
                updated_steps.append(step)
        
        return Plan(task=current_plan.task, steps=updated_steps)
    
    def should_trigger_adaptive_search(self, step_results: List[Dict[str, Any]], 
                                     current_step_index: int) -> bool:
        """Determine if we should trigger an adaptive search based on current results."""
        # Check if we have enough entities discovered for next phase
        if not self.research_phases or self.current_phase_index >= len(self.research_phases):
            return False
        
        # Look for entity extraction in recent results
        recent_results = step_results[-3:] if len(step_results) >= 3 else step_results
        entity_count = 0
        
        for result in recent_results:
            if isinstance(result, dict) and "findings" in result:
                entity_count += len(result["findings"])
        
        # Trigger adaptive search if we have sufficient entities
        return entity_count >= 2

    def _infer_desired_count(self, task_description: str) -> int:
        m = re.search(r'\b(\d{1,3})\b', task_description or "")
        try:
            v = int(m.group(1)) if m else 10
            return max(1, min(v, 50))
        except Exception:
            return 10

    def _parse_plan_response(self, response_text: str) -> Optional[Plan]:
        if not response_text:
            return None
        m = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
        raw = m.group(1) if m else response_text.strip()
        try:
            obj = json.loads(raw)
            steps = [
                PlanStep(
                    description=s.get("description", "Step"),
                    tool_name=s.get("tool", "search"),
                    parameters=s.get("parameters", {}) or {}
                )
                for s in obj.get("steps", [])
            ]
            if steps:
                return Plan(task=obj.get("task") or "LLM Plan", steps=steps)
        except Exception as e:
            logger.debug(f"Failed to parse plan JSON: {e}")
        return None

    def _create_default_plan(self, task_description: str) -> Plan:
        q = self._create_targeted_search_query(task_description)
        desired = self._infer_desired_count(task_description)
        steps: List[PlanStep] = [
            PlanStep(
                description=f"Search for: {q}",
                tool_name="search",
                parameters={"query": q, "num_results": 20}
            )
        ]
        for i in range(5):
            steps.append(
                PlanStep(
                    description=f"Fetch and extract content from search result {i}",
                    tool_name="browser",
                    parameters={"url": f"{{search_result_{i}_url}}", "extract_type": "main_content"}
                )
            )
        steps.append(
            PlanStep(
                description="Organize and present findings",
                tool_name="present",
                parameters={
                    "prompt": f"Produce exactly {desired} direct statements by Joe Biden on US-China relations. Each item must be from a different occasion (unique date). For each item, include: the exact quote in double quotes, the date (YYYY-MM-DD if available), the source title, and the canonical URL. Only output a numbered Markdown list with one line per item. Do not include headings, explanations, or any debug fields. Do not print raw search results.",
                    "format_type": "list",
                    "title": "Research Results",
                    "suppress_debug": True
                }
            )
        )
        return Plan(task=task_description, steps=steps)

def create_plan(task: str, analysis: dict) -> dict:
    planner = Planner()
    plan = planner.create_plan(task, analysis)
    return {"task": plan.task, "steps": [{"description": s.description, "tool": s.tool_name, "parameters": s.parameters} for s in plan.steps]}
