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
        # Initialize Gemini first
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.memory = Memory()
        self.planner = Planner(model=self.model)  # Pass model to Planner
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
    
    async def execute_task(self, task: str) -> Dict:
        # 1. Plan task decomposition
        plan = self.planner.create_plan(task)
        
        # 2. Execute steps while maintaining context
        result = {}
        for step in plan:
            # Execute step using appropriate tool
            step_result = await self._execute_step(step)
            self.memory.add(step, step_result)
            
            # Learn from execution
            self.learner.update(step, step_result)
            
        return result

    async def _execute_step(self, step: dict) -> Dict:
        tool_name = step['tool']
        if tool_name in self.tools:
            return await self.tools[tool_name](step['params'])
        return {'error': f'Unknown tool: {tool_name}'}