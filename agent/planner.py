from typing import List, Dict
import google.generativeai as genai
from dataclasses import dataclass
from .comprehension.task_analyzer import TaskIntent, TaskRequirements

@dataclass
class Step:
    tool: str
    params: Dict
    dependencies: List[int] = None

class Planner:
    def __init__(self, model: genai.GenerativeModel):
        self.model = model

    async def create_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create a dynamic plan based on task requirements"""
        
        step_templates = {
            TaskIntent.COMPILE: self._create_compilation_plan,
            TaskIntent.FIND: self._create_fact_finding_plan,
            TaskIntent.ANALYZE: self._create_analysis_plan,
            TaskIntent.CALCULATE: self._create_calculation_plan,
            TaskIntent.EXTRACT: self._create_extraction_plan,
            TaskIntent.VERIFY: self._create_verification_plan
        }
        
        # Get appropriate planning function and execute without await
        plan_creator = step_templates.get(requirements.intent, self._create_default_plan)
        return plan_creator(task, requirements)  # Remove await since these are not async functions

    def _create_compilation_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create plan for compilation tasks"""
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'silent': True
            }
        }]

    def _create_fact_finding_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'silent': True
            }
        }]

    def _create_analysis_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        steps = []
        searches = self._break_down_analysis(task)
        for search in searches:
            steps.append({
                'tool': 'web_search',
                'params': {
                    'query': search,
                    'silent': True
                }
            })
        return steps

    def _create_calculation_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'silent': True
            }
        }]

    def _create_extraction_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'silent': True
            }
        }]

    def _create_verification_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'silent': True
            }
        }]

    def _break_down_analysis(self, task: str) -> List[str]:
        """Break down complex analysis tasks into subtasks"""
        base_query = task.lower()
        queries = [base_query]
        
        # Add supporting queries based on task content
        if 'compare' in base_query:
            parts = base_query.split('compare')
            if len(parts) > 1:
                queries.extend([f"statistics {p.strip()}" for p in parts[1].split('and')])
                
        elif 'trend' in base_query or 'over time' in base_query:
            queries.append(f"{base_query} historical data")
            queries.append(f"{base_query} latest statistics")
            
        return queries[:3]  # Limit to 3 searches

    def _create_default_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create a basic plan for unspecified task types"""
        return [{
            'tool': 'web_search',
            'params': {
                'query': task,
                'num_results': 5
            }
        }]