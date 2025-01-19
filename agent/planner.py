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
        
        # Define step templates based on intent
        step_templates = {
            TaskIntent.COMPILE: self._create_compilation_plan,
            TaskIntent.FIND: self._create_fact_finding_plan,
            TaskIntent.ANALYZE: self._create_analysis_plan,
            TaskIntent.CALCULATE: self._create_calculation_plan,
            TaskIntent.EXTRACT: self._create_extraction_plan,
            TaskIntent.VERIFY: self._create_verification_plan
        }
        
        # Get appropriate planning function
        plan_creator = step_templates.get(requirements.intent, self._create_default_plan)
        return plan_creator(task, requirements)

    def _create_compilation_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create plan for compilation tasks"""
        steps = []
        
        # Initial broad search
        steps.append({
            'tool': 'web_search',
            'params': {
                'query': task,
                'num_results': max(requirements.count * 2 if requirements.count else 10, 5)
            }
        })
        
        # Add verification step if sources required
        if requirements.sources_required:
            steps.append({
                'tool': 'web_browse',
                'params': {'verify_sources': True}
            })
            
        return steps

    def _create_fact_finding_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create plan for fact-finding tasks"""
        steps = []
        
        # Start with focused search
        steps.append({
            'tool': 'web_search',
            'params': {
                'query': task,
                'search_type': 'specific',
                'num_results': 3
            }
        })
        
        # Add source verification if required
        if requirements.sources_required:
            steps.append({
                'tool': 'web_browse',
                'params': {'verify_sources': True}
            })
            
        return steps

    def _create_analysis_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create plan for analysis tasks"""
        steps = []
        
        # Multiple searches for comprehensive analysis
        searches = self._break_down_analysis(task)
        for search in searches:
            steps.append({
                'tool': 'web_search',
                'params': {
                    'query': search,
                    'search_type': 'comprehensive'
                }
            })
            
        return steps

    def _create_calculation_plan(self, task: str, requirements: TaskRequirements) -> List[Dict]:
        """Create plan for calculation tasks"""
        steps = []
        
        # Search for numerical data
        steps.append({
            'tool': 'web_search',
            'params': {
                'query': task,
                'search_type': 'numeric',
                'num_results': 5
            }
        })
        
        # Add data extraction step
        steps.append({
            'tool': 'web_browse',
            'params': {'extract_numbers': True}
        })
        
        return steps

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