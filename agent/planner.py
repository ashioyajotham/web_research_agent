from typing import List, Dict
import google.generativeai as genai
from dataclasses import dataclass

@dataclass
class Step:
    tool: str
    params: Dict
    dependencies: List[int] = None

class Planner:
    def __init__(self):
        self.planning_prompt = """
        Break down this task into specific steps. For each step specify:
        1. The tool to use (web_search, web_browse, code_generate)
        2. Required parameters
        3. Dependencies on other steps
        
        Task: {task}
        Previous context: {context}
        
        Respond in JSON format.
        """
        
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
        
        # Use correct Gemini API method
        response = self.model.generate_content(prompt)
        try:
            # Parse response text into JSON
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "steps": [{
                    "tool": "web_search",
                    "params": {"query": task}
                }]
            }

    def _validate_steps(self, steps: List[Dict]) -> List[Step]:
        validated = []
        for step in steps:
            if step['tool'] not in self.available_tools:
                raise ValueError(f"Unknown tool: {step['tool']}")
                
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