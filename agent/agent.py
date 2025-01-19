from typing import List, Dict
import google.generativeai as genai
from .memory import Memory
from .planner import Planner
from .learner import Learner
from tools.web_search import WebSearchTool
from tools.web_browse import WebBrowserTool
from tools.code_tools import CodeTools
from .comprehension.task_analyzer import TaskAnalyzer, TaskRequirements, TaskIntent
from .synthesis.synthesizer import ResultSynthesizer

class Agent:
    def __init__(self, api_key: str, serper_api_key: str):
        try:
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
            
            self.task_analyzer = TaskAnalyzer()
            self.synthesizer = ResultSynthesizer()
            
        except Exception as e:
            raise RuntimeError(f"Agent initialization failed: {str(e)}")

    async def execute_task(self, task: str) -> Dict:
        try:
            # Analyze task
            requirements = self.task_analyzer.analyze(task)
            
            # Create execution plan
            plan = await self.planner.create_plan(task, requirements)
            
            # Execute plan steps
            results = []
            for step in plan:
                step_result = await self._execute_step(step)
                if step_result.get('success'):
                    results.extend(step_result.get('result', {}).get('results', []))
            
            # Synthesize results
            synthesized_results = self.synthesizer.synthesize(results, requirements)
            
            return {
                "query": task,
                "intent": requirements.intent.value,
                "requirements": requirements.__dict__,
                "results": synthesized_results,
                "success": True
            }
            
        except Exception as e:
            return self._create_error_response(task, str(e))

    def _process_results(self, results: List[Dict], requirements: TaskRequirements) -> List[Dict]:
        """Process results based on task requirements"""
        if not results:
            return []
            
        processed = []
        seen_content = set()  # For deduplication
        
        if requirements.intent == TaskIntent.COMPILE:
            # Handle list compilation
            for result in results:
                content = result.get('snippet', '').strip()
                if content and content.lower() not in seen_content:
                    seen_content.add(content.lower())
                    processed.append({
                        'content': content,
                        'source': result.get('link'),
                        'date': result.get('date')
                    })
                    
            # Respect count requirement if specified
            if requirements.count:
                processed = processed[:requirements.count]
                
        elif requirements.intent == TaskIntent.FIND:
            # For fact-finding, use most relevant result
            return [{
                'answer': results[0].get('snippet'),
                'source': results[0].get('link'),
                'date': results[0].get('date')
            }]
            
        elif requirements.intent in [TaskIntent.ANALYZE, TaskIntent.CALCULATE]:
            # For analysis/calculation, combine relevant information
            relevant_info = []
            for result in results[:3]:  # Use top 3 results for analysis
                content = result.get('snippet', '').strip()
                if content and content.lower() not in seen_content:
                    seen_content.add(content.lower())
                    relevant_info.append({
                        'point': content,
                        'source': result.get('link')
                    })
            return relevant_info
            
        return processed

    def _create_error_response(self, task: str, error: str) -> Dict:
        """Create standardized error response"""
        return {
            "query": task,
            "results": [],
            "error": error,
            "success": False
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