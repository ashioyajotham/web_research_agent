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
        self.current_plan = {}

    def _parse_plan(self, plan_json: str) -> Dict[str, SubTask]:
        """Parse the LLM's JSON response into SubTask objects"""
        try:
            # Clean up the response
            cleaned_json = plan_json.strip()
            if cleaned_json.startswith('```json'):
                cleaned_json = cleaned_json[7:]
            if cleaned_json.endswith('```'):
                cleaned_json = cleaned_json[:-3]
            cleaned_json = cleaned_json.strip()
            
            # Parse JSON
            plan_dict = json.loads(cleaned_json)
            
            # Ensure we have the expected structure
            if not isinstance(plan_dict, dict):
                raise ValueError("Expected JSON object at root level")
                
            # Handle both possible structures
            subtasks = plan_dict.get('subtasks', plan_dict)
            if not isinstance(subtasks, dict):
                raise ValueError("Subtasks must be a dictionary")
            
            # Convert to SubTask objects
            parsed_plan = {}
            for task_id, task_info in subtasks.items():
                if not isinstance(task_info, dict):
                    continue
                    
                tools = task_info.get('tools_needed', task_info.get('tools', []))
                if isinstance(tools, str):
                    tools = [tools]
                    
                parsed_plan[task_id] = SubTask(
                    description=str(task_info.get('description', '')),
                    tools_needed=list(tools),
                    dependencies=list(task_info.get('dependencies', [])),
                    status="pending"
                )
            
            if not parsed_plan:
                raise ValueError("No valid subtasks found in plan")
                
            logger.info(f"Successfully parsed plan with {len(parsed_plan)} subtasks")
            return parsed_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON plan: {e}\nInput was: {plan_json}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing plan: {e}")
            raise

    async def create_plan(self, task: str) -> Dict[str, SubTask]:
        """Creates a dynamic plan based on task understanding"""
        try:
            # Use comprehension service to understand task
            task_context = await self.comprehension._understand_task(task)
            
            # Generate dynamic planning prompt based on task type
            prompt = f"""Given this task analysis:
{json.dumps(task_context, indent=2)}

Create a research plan with appropriate subtasks.
Return as JSON with this structure:
{{
    "subtasks": {{
        "task1": {{
            "description": "...",
            "tools_needed": ["web_search", "web_browse", "code_generation"],
            "dependencies": []
        }},
        "task2": {{
            "description": "...",
            "tools_needed": ["..."],
            "dependencies": ["task1"]
        }}
    }}
}}"""

            plan_json = await self.llm.generate(prompt)
            self.current_plan = self._parse_plan(plan_json)
            return self.current_plan

        except Exception as e:
            logger.error(f"Failed to create plan: {str(e)}")
            raise

    def get_next_tasks(self) -> List[SubTask]:
        """Returns list of subtasks that are ready to be executed"""
        ready_tasks = []
        for task_id, task in self.current_plan.items():
            if task.status == "pending":
                dependencies_met = all(
                    self.current_plan[dep].status == "completed"
                    for dep in task.dependencies
                    if dep in self.current_plan
                )
                if dependencies_met:
                    ready_tasks.append(task)
        return ready_tasks

    def is_plan_completed(self) -> bool:
        """Check if all subtasks in the current plan are completed"""
        if not self.current_plan:
            return False
        return all(task.status == "completed" for task in self.current_plan.values())

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None):
        """Updates the status and result of a subtask"""
        if task_id in self.current_plan:
            self.current_plan[task_id].status = status
            if result:
                self.current_plan[task_id].result = result
            logger.info(f"Updated task {task_id} status to {status}")