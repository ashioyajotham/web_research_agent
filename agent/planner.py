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
    def __init__(self, llm=None, comprehension=None):
        self.llm = llm
        self.comprehension = comprehension
        self.tasks = []
        self.current_plan = None
        self.task_status = {}

    async def create_plan(self, task: str) -> List[Dict]:
        """Create dynamic task plan based on task requirements"""
        self.current_plan = []
        self.task_status = {}

        # Use LLM to analyze task if available
        if self.llm and self.comprehension:
            try:
                # Get task analysis from LLM
                analysis = await self.comprehension.analyze_task(task)
                subtasks = analysis.get('subtasks', [])
                
                # Convert subtasks to plan format
                for idx, subtask in enumerate(subtasks):
                    self.current_plan.append({
                        'id': f'task_{idx}',
                        'description': subtask,
                        'type': 'search' if 'search' in subtask.lower() else 'analysis',
                        'dependencies': [f'task_{i}' for i in range(idx)]
                    })
            except Exception as e:
                logger.warning(f"Failed to create plan using LLM: {str(e)}")
                # Fall back to default plan
                self.current_plan = self._create_default_plan()
        else:
            # Use default plan if no LLM available
            self.current_plan = self._create_default_plan()

        # Initialize task status
        self.task_status = {
            task['id']: {'completed': False, 'result': None} 
            for task in self.current_plan
        }
        
        return self.current_plan

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

    def get_next_tasks(self) -> List[Dict]:
        """Get tasks that are ready to execute (dependencies met)"""
        if not self.current_plan:
            return []

        ready_tasks = []
        for task in self.current_plan:
            if not self.task_status[task['id']]['completed']:
                if all(self.task_status[dep]['completed'] for dep in task['dependencies']):
                    ready_tasks.append(task)
        
        return ready_tasks

    def update_task_status(self, task_id: str, status: Dict):
        """Update task status and results"""
        if task_id in self.task_status:
            self.task_status[task_id].update(status)

    def is_plan_completed(self) -> bool:
        """Check if all tasks are completed"""
        return all(status['completed'] for status in self.task_status.values())

    def add_dynamic_task(self, task: Dict):
        """Add new task dynamically during execution"""
        if task['id'] not in self.task_status:
            self.current_plan.append(task)
            self.task_status[task['id']] = {'completed': False, 'result': None}