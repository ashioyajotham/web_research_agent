import json
from typing import List, Dict
import google.generativeai as genai
from dataclasses import dataclass

@dataclass
class Step:
    tool: str
    params: Dict
    dependencies: List[int] = None

class Planner:
    def __init__(self, model=None):
        self.model = model
        self.planning_prompt = """Return ONLY a JSON object in this exact format (no other text):
{"steps":[{"tool":"web_search","params":{"query":"search query","num_results":5}}]}

Example input: "Find Tesla news"
Example output: {"steps":[{"tool":"web_search","params":{"query":"Tesla recent news","num_results":5}}]}

Task: {task}"""

    def create_plan(self, task: str) -> Dict:
        try:
            # Generate plan
            response = self.model.generate_content(self.planning_prompt.format(task=task))
            raw_text = response.text.strip()
            print(f"Raw response: {repr(raw_text)}")
            
            # Extract JSON
            cleaned_text = raw_text
            if "```" in cleaned_text:
                parts = cleaned_text.split("```")
                for part in parts:
                    if "{" in part:
                        cleaned_text = part[part.find("{"):part.rfind("}")+1]
                        break
            
            print(f"Cleaned text: {repr(cleaned_text)}")
            
            # Parse JSON
            plan = json.loads(cleaned_text)
            print(f"Parsed plan: {json.dumps(plan, indent=2)}")
            
            # Validate structure
            if not isinstance(plan, dict) or "steps" not in plan:
                raise ValueError("Invalid plan structure")
                
            return plan
            
        except Exception as e:
            print(f"Plan creation error: {str(e)}")
            return self._get_fallback_plan(task)

    def _validate_step(self, step: Dict) -> bool:
        if not isinstance(step, dict):
            return False
            
        if "tool" not in step or step["tool"] not in self.available_tools:
            return False
            
        if "params" not in step or not isinstance(step["params"], dict):
            return False
            
        tool_info = self.available_tools[step["tool"]]
        return all(param in step["params"] for param in tool_info["required"])

    def _get_fallback_plan(self, task: str) -> Dict:
        return {
            "steps": [{
                "tool": "web_search",
                "params": {
                    "query": task,
                    "num_results": 5
                }
            }]
        }