from typing import List, Dict
import google.generativeai as genai
from .memory import Memory
from .planner import Planner
from .learner import Learner

class Agent:
    def __init__(self, api_key: str):
        self.memory = Memory()
        self.planner = Planner()
        self.learner = Learner()
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.tools = {
            'web_search': self._web_search,
            'web_browse': self._web_browse,
            'code_generate': self._code_generate
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