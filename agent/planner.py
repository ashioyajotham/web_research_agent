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
        presentation_format = (task_analysis or {}).get("presentation_format", "summary")
        desired = self._infer_desired_count(task_description)
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
