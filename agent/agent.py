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
            # Handle criteria-based tasks
            if "Criteria:\n" in task:
                main_task, criteria = task.split("Criteria:\n", 1)
                criteria_list = [c.strip() for c in criteria.split('\n') if c.strip()]
                
                # Build a more focused search query
                search_parts = [main_task.strip()]
                search_parts.extend([f"AND {c}" for c in criteria_list])
                search_query = " ".join(search_parts)
                
                search_result = await self._web_search_tool.search(search_query, silent=True)
            else:
                search_result = await self._web_search_tool.search(task, silent=True)
            
            # Process results
            processed_results = []
            seen_content = set()
            
            # Analyze task type
            is_list_task = any(word in task.lower() for word in ['list', 'compile', 'gather'])
            is_quote_task = 'statements' in task.lower() or 'quotes' in task.lower()
            
            for result in search_result.get('results', []):
                content = result.get('snippet', '').strip()
                if not content:
                    continue
                    
                # Handle quotes differently
                if is_quote_task:
                    quotes = self._extract_quotes(content)
                    for quote in quotes:
                        quote_key = quote.lower()
                        if quote_key not in seen_content:
                            seen_content.add(quote_key)
                            processed_results.append({
                                'title': "Quote",
                                'snippet': quote,
                                'link': result.get('link'),
                                'date': result.get('date')
                            })
                else:
                    # Regular content handling
                    content_key = content.lower()
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        processed_results.append({
                            'title': result.get('title', 'Result'),
                            'snippet': content,
                            'link': result.get('link'),
                            'date': result.get('date')
                        })
            
            return {
                'success': True,
                'results': processed_results[:5]  # Limit to top 5 results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_quotes(self, text: str) -> List[str]:
        quotes = []
        parts = text.split('"')
        for i in range(1, len(parts), 2):
            quote = parts[i].strip()
            if quote:
                quotes.append(quote)
        return quotes

    def _process_results(self, results: List[Dict], requirements: TaskRequirements) -> List[Dict]:
        """Process results based on task requirements"""
        if not results:
            return []
            
        processed = []
        seen_content = set()
        
        # Use manual iteration with a counter instead of slicing
        if requirements.intent == TaskIntent.COMPILE:
            count = 0
            max_count = requirements.count if requirements.count else len(results)
            
            for result in results:
                if count >= max_count:
                    break
                    
                content = result.get('snippet', '').strip()
                content_key = content.lower() if content else ''
                
                if content and content_key not in seen_content:
                    seen_content.add(content_key)
                    processed.append({
                        'content': content,
                        'source': result.get('link'),
                        'date': result.get('date')
                    })
                    count += 1
                    
        elif requirements.intent == TaskIntent.FIND:
            if results:
                return [{
                    'answer': results[0].get('snippet'),
                    'source': results[0].get('link'),
                    'date': results[0].get('date')
                }]
                
        elif requirements.intent in [TaskIntent.ANALYZE, TaskIntent.CALCULATE]:
            count = 0
            for result in results:
                if count >= 3:  # Limit to top 3 results
                    break
                    
                content = result.get('snippet', '').strip()
                content_key = content.lower() if content else ''
                
                if content and content_key not in seen_content:
                    seen_content.add(content_key)
                    processed.append({
                        'point': content,
                        'source': result.get('link')
                    })
                    count += 1
                    
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