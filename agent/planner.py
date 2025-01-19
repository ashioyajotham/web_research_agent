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
        self.planning_prompt = """
        Create a plan to accomplish this task. Respond with JSON only:
        {
          "steps": [
            {
              "tool": "web_search",
              "params": {
                "query": "actual search query here",
                "num_results": 5
              }
            }
          ]
        }
        
        Task: {task}
        Context: {context}
        """
        
        # Set default parameters
        self.default_params = {
            'web_search': {
                'num_results': 5
            },
            'web_browse': {
                'elements': ['main']
            },
            'code_generate': {
                'language': 'python'
            }
        }
        
        self.available_tools = {
            'web_search': {
                'description': 'Search the web using Google',
                'params': ['query', 'num_results']
            },
            'web_browse': {
                'description': 'Extract content from webpage',
                'params': ['url', 'elements']
            },
            'code_generate': {
                'description': 'Generate or modify code',
                'params': ['instruction', 'language', 'context']
            }
        }

    def create_plan(self, task: str, context: Dict = None) -> List[Step]:
        # Generate initial plan using LLM
        plan_response = self._generate_plan(task, context)
        
        # Validate and structure the plan
        validated_steps = self._validate_steps(plan_response['steps'])
        
        # Resolve dependencies
        ordered_steps = self._resolve_dependencies(validated_steps)
        
        return ordered_steps

    def _generate_plan(self, task: str, context: Dict = None) -> Dict:
        # Format prompt using class template
        prompt = self.planning_prompt.format(
            task=task,
            context=str(context) if context else "No previous context"
        )
        
        try:
            # Generate and debug print
            print(f"\nSending prompt:\n{prompt}")
            response = self.model.generate_content(prompt)
            print(f"\nRaw LLM Response:\n{response.text}")
            
            json_str = response.text
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            
            print(f"\nCleaned JSON string:\n{json_str}")    
            plan = json.loads(json_str.strip())
            print(f"\nParsed plan:\n{json.dumps(plan, indent=2)}")
            
            return plan
            
        except Exception as e:
            print(f"Plan Generation Error: {e}")
            return self._get_fallback_plan(task)

    def _get_fallback_plan(self, task: str) -> Dict:
        return {
            "steps": [{
                "tool": "web_search",
                "params": {"query": task, "num_results": 5}
            }]
        }

    def _validate_steps(self, steps: List[Dict]) -> List[Step]:
        validated = []
        for step in steps:
            if step['tool'] not in self.available_tools:
                raise ValueError(f"Unknown tool: {step['tool']}")
                
            # Add default parameters if missing
            if step['tool'] in self.default_params:
                for param, value in self.default_params[step['tool']].items():
                    step['params'].setdefault(param, value)
            
            # Validate required parameters
            required_params = self.available_tools[step['tool']]['params']
            for param in required_params:
                if param not in step['params']:
                    raise ValueError(f"Missing parameter {param} for tool {step['tool']}")
            
            validated.append(Step(
                tool=step['tool'],
                params=step['params'],
                dependencies=step.get('dependencies', [])
            ))
        return validated

    def _resolve_dependencies(self, steps: List[Step]) -> List[Step]:
        """
        Sorts steps based on dependencies using topological sort
        """
        # Create adjacency list
        graph = {i: step.dependencies for i, step in enumerate(steps)}
        
        # Perform topological sort
        visited = set()
        ordered = []
        
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph[node]:
                dfs(dep)
            ordered.append(steps[node])
            
        for i in range(len(steps)):
            dfs(i)
            
        return ordered