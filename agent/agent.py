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
            # Clean task string to prevent JSON escape issues
            task = task.encode('ascii', 'ignore').decode('ascii')
            
            plan = self.planner.create_plan(task)
            results = []
            
            for step in plan.get('steps', []):
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