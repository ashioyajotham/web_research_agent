from typing import List, Dict
import json
import google.generativeai as genai
from .memory import Memory
from .planner import Planner
from .learner import Learner
from tools.web_search import WebSearchTool
from tools.web_browse import WebBrowserTool
from tools.code_tools import CodeTools

class Agent:
    def __init__(self, api_key: str, serper_api_key: str):
        try:
            # Initialize Gemini
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Initialize components
            self.memory = Memory()
            self.planner = Planner(model=self.model)
            self.learner = Learner()
            
            # Initialize tools
            self._web_search_tool = WebSearchTool(serper_api_key)
            self._web_browser_tool = WebBrowserTool()
            self._code_tools = CodeTools()
            
            self.tools = {
                'web_search': self._web_search_tool.search,
                'web_browse': self._web_browser_tool.browse,
                'code_generate': self._code_tools.generate_code
            }
            
        except Exception as e:
            raise RuntimeError(f"Agent initialization failed: {str(e)}")

    async def execute_task(self, task: str) -> Dict:
        try:
            plan = self.planner.create_plan(task)
            if not isinstance(plan, dict) or "steps" not in plan:
                raise ValueError("Invalid plan structure")
                
            results = []
            for step in plan["steps"]:  # Direct list access instead of get()
                if not isinstance(step, dict):
                    continue
                    
                result = await self._execute_step(step)
                outcome = {
                    'success': result.get('success', False),
                    'error': result.get('error', None)
                }
                
                self.learner.update(step, result, outcome)
                results.append({'step': step, 'result': result})
            
            return {
                'task': task,
                'results': results,
                'success': True
            }
            
        except Exception as e:
            return {
                'task': task,
                'error': str(e),
                'success': False
            }

    async def _execute_step(self, step: dict) -> Dict:
        try:
            # Validate step
            if not isinstance(step, dict):
                raise ValueError("Invalid step format")
                
            tool_name = step.get('tool')
            if not tool_name or tool_name not in self.tools:
                raise ValueError(f"Unknown tool: {tool_name}")
                
            params = step.get('params', {})
            print(f"\nExecuting {tool_name} with params: {params}")
            
            # Execute tool
            result = await self.tools[tool_name](**params)
            
            return {
                'success': True,
                'result': result,
                'tool': tool_name,
                'params': params
            }
            
        except Exception as e:
            print(f"Step execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tool': step.get('tool'),
                'params': step.get('params', {})
            }