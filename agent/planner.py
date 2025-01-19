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
        Break down this task into specific steps. For each step specify:
        1. Tool to use (web_search, web_browse, code_generate)
        2. Required parameters:
           - web_search: {"query": "search query", "num_results": 5}
           - web_browse: {"url": "webpage url", "elements": ["main", "article"]}
           - code_generate: {"instruction": "what to code", "language": "python", "context": "any context"}
        3. Dependencies on other steps
        
        Respond in this exact JSON format:
        {
            "steps": [
                {
                    "tool": "web_search",
                    "params": {
                        "query": "your search query",
                        "num_results": 5
                    },
                    "dependencies": []
                }
            ]
        }
        
        Task: {task}
        Previous context: {context}
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
        prompt = self.planning_prompt.format(
            task=task,
            context=str(context) if context else "No previous context"
        )
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            print(f"\nRaw response for task: {task[:30]}...\n{response_text}\n")

            # Extract JSON part
            if "```" in response_text:
                parts = response_text.split("```")
                for part in parts:
                    if part.strip().startswith(('json', '{')):
                        response_text = part.replace('json', '').strip()
                        break
            
            # Remove any remaining markdown or formatting
            response_text = response_text.strip('`').strip()
            print(f"\nCleaned response:\n{response_text}\n")

            try:
                plan = json.loads(response_text)
                # Ensure steps array exists
                if "steps" not in plan:
                    plan = {"steps": [plan]}  # Wrap single step in steps array
                    
                # Ensure each step has required fields and proper parameter structure
                for step in plan["steps"]:
                    if "params" not in step:
                        step["params"] = {}
                    if isinstance(step["params"], str):
                        # Fix: Properly structure string params based on tool type
                        if step["tool"] == "web_search":
                            step["params"] = {"query": step["params"]}
                        elif step["tool"] == "web_browse":
                            step["params"] = {"url": step["params"]}
                        elif step["tool"] == "code_generate":
                            step["params"] = {"instruction": step["params"]}
                    if "dependencies" not in step:
                        step["dependencies"] = []

                return plan

            except json.JSONDecodeError as e:
                print(f"\nJSON Parse error: {str(e)}\n")
                return self._get_fallback_plan(task)

        except Exception as e:
            print(f"\nGeneral error in plan generation: {str(e)}\n")
            return self._get_fallback_plan(task)

    def _get_fallback_plan(self, task: str) -> Dict:
        """Improved fallback plan to ensure proper parameter structure"""
        return {
            "steps": [{
                "tool": "web_search",
                "params": {
                    "query": str(task),  # Ensure query is string
                    "num_results": 5
                },
                "dependencies": []
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