import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from utils.logger import get_logger
from config.config import get_config

logger = get_logger(__name__)

try:
    import google.generativeai as genai  # Optional; used only if configured
except Exception:
    genai = None

@dataclass
class PlanStep:
    """A step in the execution plan."""
    description: str
    tool_name: str
    parameters: Dict[str, Any]

@dataclass
class Plan:
    """A complete execution plan."""
    task: str
    steps: List[PlanStep]

class Planner:
    """Creates execution plans for tasks."""

    def __init__(self):
        """Initialize the planner."""
        self.config = get_config()
        self.model = None
        if genai and self.config.get("gemini_api_key"):
            try:
                genai.configure(api_key=self.config.get("gemini_api_key"))
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                logger.warning(f"GenAI model init failed; using default planning. Error: {e}")
                self.model = None

    def create_plan(self, task_description: str, task_analysis: Dict[str, Any]) -> Plan:
        """Create a plan with better search strategy (task-agnostic)."""
        try:
            # Attempt LLM-assisted planning if available (optional)
            if self.model:
                prompt = self._create_planning_prompt(task_description, task_analysis)
                response = self.model.generate_content(prompt)
                # Try to get text from response safely
                text = ""
                if hasattr(response, "text") and response.text:
                    text = response.text
                elif getattr(response, "candidates", None):
                    try:
                        text = response.candidates[0].content.parts[0].text
                    except Exception:
                        text = ""
                plan = self._parse_plan_response(text)
                if plan:
                    return plan
        except Exception as e:
            logger.warning(f"LLM planning failed, falling back to default plan: {e}")

        # Fallback to robust default plan
        return self._create_default_plan(task_description)

    def _create_targeted_search_query(self, task_description: str) -> str:
        """Generic keyword extraction for search query."""
        STOP = {
            "the","and","for","with","that","this","from","into","over","under","their","your","our",
            "they","them","are","was","were","have","has","had","each","must","made","more","than",
            "list","compile","find","show","what","which","who","when","where","why","how","of","to",
            "in","on","by","as","it","an","a","or","be","is","any","all","data","information"
        }
        words = re.findall(r"[A-Za-z0-9%€\-]+", task_description)
        keywords, seen = [], set()
        for w in words:
            wl = w.lower()
            if wl in STOP or len(wl) < 3:
                continue
            if wl not in seen:
                keywords.append(w)
                seen.add(wl)
        return " ".join(keywords[:12]) if keywords else task_description.strip()

    def _create_planning_prompt(self, task_description: str, task_analysis: Dict[str, Any]) -> str:
        """Prompt to obtain JSON steps (optional)."""
        presentation_format = task_analysis.get("presentation_format", "summary")

        # Minimal criteria detection
        has_multiple_criteria = "\n" in task_description and any(
            line.strip().startswith(("-", "•")) or re.match(r"^\s{2,}\w+", line)
            for line in task_description.split("\n")
        )
        criteria_guidance = ""
        if has_multiple_criteria:
            criteria_guidance = "Ensure each criterion is addressed by a dedicated search/browse step and add a verification step."

        return f"""
Create a step-by-step plan in JSON for this research task.

TASK: {task_description}

TASK ANALYSIS: {json.dumps(task_analysis)}

Guidance:
- Use 'search' first with a concise query.
- Use 'browser' next; if URL is unresolved, it will be resolved at execution from search results.
- Use 'present' to organize results. Avoid 'code' unless the task requires computation.
- Format: {presentation_format}. {criteria_guidance}

Tools:
- search(query:str, num_results?:int)
- browser(url:str, extract_type?:'full'|'main_content'|'summary')
- present(prompt:str, format_type?:'table'|'list'|'summary'|'comparison', title?:str)

Return JSON:
{{
  "steps":[
    {{
      "description":"Search...",
      "tool":"search",
      "parameters":{{"query":"...", "num_results":10}}
    }},
    {{
      "description":"Browse...",
      "tool":"browser",
      "parameters":{{"url":"{{search_result_0_url}}","extract_type":"main_content"}}
    }},
    {{
      "description":"Present...",
      "tool":"present",
      "parameters":{{"prompt":"...", "format_type":"summary","title":"Results"}}
    }}
  ]
}}
""".strip()

    def _parse_plan_response(self, response_text: str) -> Optional[Plan]:
        """Parse JSON plan from LLM response."""
        if not response_text:
            return None
        # Try to extract fenced JSON first
        m = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
        raw = m.group(1) if m else response_text.strip()
        try:
            obj = json.loads(raw)
            steps = []
            for s in obj.get("steps", []):
                steps.append(PlanStep(
                    description=s.get("description", "Step"),
                    tool_name=s.get("tool", "search"),
                    parameters=s.get("parameters", {}) or {}
                ))
            if steps:
                return Plan(task=obj.get("task") or "LLM Plan", steps=steps)
        except Exception as e:
            logger.debug(f"Failed to parse LLM plan JSON: {e}")
        return None

    def _create_default_plan(self, task_description: str) -> Plan:
        """Fallback plan: search → browser (adaptive) → present."""
        search_query = self._create_targeted_search_query(task_description)

        steps: List[PlanStep] = [
            PlanStep(
                description=f"Search for: {search_query}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 10}
            ),
            PlanStep(
                description="Fetch and extract content from top search results",
                tool_name="browser",
                parameters={
                    "url": "{search_result_0_url}",  # resolved via substitution if possible
                    "top_k": 5,                      # agent will multi-browse when URL is unresolved
                    "extract_type": "main_content"
                }
            ),
            PlanStep(
                description="Organize and present findings",
                tool_name="present",
                parameters={
                    "prompt": f"Organize and present the information for the task: {task_description}",
                    "format_type": "summary",
                    "title": "Research Results"
                }
            ),
        ]
        return Plan(task=task_description, steps=steps)

def create_plan(task: str, analysis: dict) -> dict:
    """Legacy helper that returns a serializable plan dict."""
    planner = Planner()
    plan = planner.create_plan(task, analysis)
    return {
        "task": plan.task,
        "steps": [
            {
                "description": s.description,
                "tool": s.tool_name,
                "parameters": s.parameters
            } for s in plan.steps
        ]
    }
