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
        self.available_tools = {
            'web_search': {
                'params': ['query', 'num_results'],
                'required': ['query']
            },
            'web_browse': {
                'params': ['url', 'elements'],
                'required': ['url']
            },
            'code_generate': {
                'params': ['instruction', 'language'],
                'required': ['instruction']
            }
        }
        
        self.planning_prompt = """Generate a plan as a single-line JSON with NO formatting:
{"steps":[{"tool":"tool_name","params":{"param1":"value1"}}]}

Available tools:
- web_search: {"params":{"query":"search terms","num_results":5}}
- web_browse: {"params":{"url":"webpage_url","elements":["main"]}}
- code_generate: {"params":{"instruction":"task","language":"python"}}

Example:
Task: "Find Tesla news"
{"steps":[{"tool":"web_search","params":{"query":"Tesla recent news","num_results":5}}]}

Current Task: {task}"""

    def create_plan(self, task: str) -> Dict:
        try:
            # Generate initial plan
            response = self.model.generate_content(self.planning_prompt.format(task=task))
            raw_text = response.text.strip()
            
            # Clean response
            if "```" in raw_text:
                parts = raw_text.split("```")
                for part in parts:
                    if part.strip().startswith(('{', '[')):
                        raw_text = part.strip()
                        break
            
            # Parse JSON
            plan = json.loads(raw_text)
            
            # Validate structure
            if not isinstance(plan, dict) or "steps" not in plan:
                raise ValueError("Invalid plan structure")
            
            # Validate each step
            validated_steps = []
            for step in plan["steps"]:
                if not self._validate_step(step):
                    raise ValueError(f"Invalid step: {step}")
                validated_steps.append(step)
            
            return {"steps": validated_steps}
            
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