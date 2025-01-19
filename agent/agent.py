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
        try:
            steps = self.planner.create_plan(task)
            print(f"Generated plan with {len(steps)} steps")
            
            results = []
            for step in steps:
                # Add detailed parameter debugging
                print(f"\nStep details:")
                print(f"Tool: {step.tool}")
                print(f"Params type: {type(step.params)}")
                print(f"Params content: {json.dumps(step.params, indent=2)}")
                
                tool_name = step.tool
                params = step.params
                
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                # Debug the actual parameters being passed
                print(f"Calling {tool_name} with params: {json.dumps(params, indent=2)}")
                
                step_result = await self.tools[tool_name](**params)
                self.memory.add(step, step_result)
                
                # Learn from execution
                self.learner.update(step, step_result)
                results.append({
                    'step': {'tool': step.tool, 'params': step.params},
                    'result': step_result
                })
            
            return {
                'task': task,
                'results': results,
                'success': True
            }
            
        except Exception as e:
            print(f"Error in execute_task: {str(e)}")  # Debug
            return {
                'task': task,
                'error': str(e),
                'success': False
            }