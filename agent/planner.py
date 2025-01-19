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
            # Get response from model
            response = self.model.generate_content(prompt)
            
            # Extract and clean response text
            response_text = response.text.strip()
            
            # Remove code blocks if present
            if response_text.startswith("```"):
                response_text = "\n".join(response_text.split("\n")[1:-1])
                
            # Remove any JSON markers
            response_text = response_text.replace("```json", "").replace("```", "")
            
            # Clean any escaped quotes
            response_text = response_text.replace('\\"', '"')
            
            try:
                plan = json.loads(response_text)
                # Validate required structure
                if "steps" not in plan or not isinstance(plan["steps"], list):
                    raise ValueError("Invalid plan structure")
                return plan
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing plan: {e}")
                # Return fallback plan
                return {
                    "steps": [{
                        "tool": "web_search",
                        "params": {
                            "query": task,
                            "num_results": 5
                        },
                        "dependencies": []
                    }]
                }
                
        except Exception as e:
            print(f"Plan generation error: {e}")
            return self._get_fallback_plan(task)

    def _get_fallback_plan(self, task: str) -> Dict:
        return {
            "steps": [{
                "tool": "web_search",
                "params": {
                    "query": task,
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