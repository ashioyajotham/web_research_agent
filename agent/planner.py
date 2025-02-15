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
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.current_plan: Dict[str, SubTask] = {}

    def _parse_plan(self, plan_json: str) -> Dict[str, SubTask]:
        """Parse the LLM's JSON response into SubTask objects"""
        try:
            # Clean up the response to ensure valid JSON
            plan_dict = json.loads(plan_json)
            
            # Convert each task definition into a SubTask object
            parsed_plan = {}
            for task_id, task_info in plan_dict.items():
                parsed_plan[task_id] = SubTask(
                    description=task_info.get('description', ''),
                    tools_needed=task_info.get('tools_needed', []),
                    dependencies=task_info.get('dependencies', [])
                )
            
            logger.info(f"Successfully parsed plan with {len(parsed_plan)} subtasks")
            return parsed_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON plan: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {plan_json}")
        except KeyError as e:
            logger.error(f"Missing required field in plan: {e}")
            raise ValueError(f"Incomplete task definition in plan: {plan_json}")
        except Exception as e:
            logger.error(f"Unexpected error parsing plan: {e}")
            raise

    async def create_plan(self, task: str) -> Dict[str, SubTask]:
        """
        Creates a structured plan from a high-level task by breaking it down into subtasks
        """
        prompt = f"""
        Given the following task: '{task}'
        Break it down into logical subtasks. For each subtask specify:
        1. A clear description of what needs to be done
        2. Required tools (web_search, code_generation, web_browse)
        3. Dependencies (IDs of other subtasks that must be completed first)
        
        Format: JSON with subtask IDs as keys and details as values
        """
        
        plan_json = await self.llm.generate(prompt)
        self.current_plan = self._parse_plan(plan_json)
        return self.current_plan

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

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None):
        """Updates the status and result of a subtask"""
        if task_id in self.current_plan:
            self.current_plan[task_id].status = status
            if result:
                self.current_plan[task_id].result = result