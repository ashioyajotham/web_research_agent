import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

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

class Planner:
    """Creates execution plans for tasks."""
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
        STOP = {
            "the","and","for","with","that","this","from","into","over","under","their","your","our",
            "they","them","are","was","were","have","has","had","each","must","made","more","than",
            "list","compile","find","show","what","which","who","when","where","why","how","of","to",
            "in","on","by","as","it","an","a","or","be","is","any","all","data","information"
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
        presentation_format = (task_analysis or {}).get("presentation_format", "summary")
        return f"""
Create a JSON plan using these tools: search, browser, present.
Use search → browser → present. Use placeholders like {{search_result_0_url}} if needed.

TASK: {task_description}
FORMAT: {presentation_format}

Return JSON:
{{
  "steps":[
    {{"description":"Search","tool":"search","parameters":{{"query":"...","num_results":10}}}},
    {{"description":"Browse","tool":"browser","parameters":{{"url":"{{search_result_0_url}}","extract_type":"main_content","top_k":5}}}},
    {{"description":"Present","tool":"present","parameters":{{"prompt":"Organize findings","format_type":"{presentation_format}","title":"Results"}}}}
  ]
}}
""".strip()

    def _parse_plan_response(self, response_text: str) -> Optional[Plan]:
        if not response_text:
            return None
        # Accept raw or fenced JSON
        import re as _re, json as _json
        m = _re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, _re.DOTALL)
        raw = m.group(1) if m else response_text.strip()
        try:
            obj = _json.loads(raw)
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
            logger.debug(f"Failed to parse plan JSON: {e}")
        return None

    def _create_default_plan(self, task_description: str) -> Plan:
        q = self._create_targeted_search_query(task_description)
        steps = [
            PlanStep(
                description=f"Search for: {q}",
                tool_name="search",
                parameters={"query": q, "num_results": 20}
            ),
            PlanStep(
                description="Fetch and extract content from top search results",
                tool_name="browser",
                parameters={"url": "{search_result_0_url}", "extract_type": "main_content", "top_k": 10}
            ),
            PlanStep(
                description="Organize and present findings",
                tool_name="present",
                parameters={"prompt": f"Organize and present information for: {task_description}", "format_type":"summary","title":"Research Results"}
            )
        ]
        return Plan(task=task_description, steps=steps)

def create_plan(task: str, analysis: dict) -> dict:
    planner = Planner()
    plan = planner.create_plan(task, analysis)
    return {"task": plan.task, "steps": [{"description": s.description, "tool": s.tool_name, "parameters": s.parameters} for s in plan.steps]}
