from dataclasses import dataclass
from typing import List, Dict, Optional
from models.llm import LLMInterface
import json
from utils.helpers import logger

@dataclass
class SubTask:
    description: str
    tools_needed: List[str]
    dependencies: List[str]
    status: str = "pending"
    result: Optional[str] = None

class TaskPlanner:
    def __init__(self, llm, comprehension):
        self.llm = llm
        self.comprehension = comprehension
        self.current_plan = []
        self.task_status = {}
        self.results_cache = {}

    async def create_plan(self, task: str) -> List[Dict]:
        """Create execution plan with result handling strategy"""
        # Analyze task requirements
        task_analysis = await self.comprehension.analyze_task(task)
        
        # Determine result handling needs
        needs_sources = 'search' in task.lower() or 'find' in task.lower()
        needs_structured = 'list' in task.lower() or 'compile' in task.lower()
        
        base_tasks = [
            {
                'id': 'search',
                'description': task,
                'type': 'search',
                'dependencies': [],
                'needs_sources': needs_sources,
                'needs_structured': needs_structured
            }
        ]

        # Add result processing task
        if needs_sources:
            base_tasks.append({
                'id': 'process',
                'description': 'Process and validate sources',
                'type': 'process',
                'dependencies': ['search'],
                'output_format': task_analysis.get('format', 'default')
            })

        return base_tasks

    def update_task_status(self, task_id: str, result: Dict):
        """Track results through processing"""
        if task_id in self.task_status:
            self.task_status[task_id]['completed'] = True
            self.task_status[task_id]['result'] = result
            # Cache results for dependent tasks
            self.results_cache[task_id] = result

    def _create_default_plan(self) -> List[Dict]:
        """Create a default task plan"""
        return [
            {
                'id': 'research',
                'description': 'Search for relevant information',
                'type': 'search',
                'dependencies': []
            },
            {
                'id': 'analyze',
                'description': 'Analyze and filter search results',
                'type': 'analysis',
                'dependencies': ['research']
            },
            {
                'id': 'synthesize',
                'description': 'Compile findings into final format',
                'type': 'synthesis',
                'dependencies': ['analyze']
            }
        ]

    async def get_next_tasks(self) -> List[Dict]:
        if not self.current_plan:
            return []

        ready_tasks = []
        for task in self.current_plan:
            task_id = task['id']
            if not self.task_status[task_id]['completed']:
                # Check dependencies and maintain result context
                if self._are_dependencies_met(task):
                    # Attach previous results context if needed
                    task['context'] = self._build_task_context(task)
                    ready_tasks.append(task)
        return ready_tasks

    def _are_dependencies_met(self, task: Dict) -> bool:
        for dep in task['dependencies']:
            if not self.task_status[dep]['completed']:
                return False
            # Ensure required results exist
            if dep in self.results_cache:
                return True
        return True

    def _build_task_context(self, task: Dict) -> Dict:
        context = {
            'task_type': task.get('type', 'default'),
            'requirements': task.get('requirements', {}),
            'previous_results': {}
        }
        
        # Gather results from dependencies
        for dep in task['dependencies']:
            if dep in self.results_cache:
                context['previous_results'][dep] = self.results_cache[dep]
        
        return context

    def is_plan_completed(self) -> bool:
        """Check if all tasks are completed"""
        return all(status['completed'] for status in self.task_status.values())

    def add_dynamic_task(self, task: Dict):
        """Add new task dynamically during execution"""
        if task['id'] not in self.task_status:
            self.current_plan.append(task)
            self.task_status[task['id']] = {'completed': False, 'result': None}