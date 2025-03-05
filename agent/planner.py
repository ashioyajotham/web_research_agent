from dataclasses import dataclass
from typing import List, Dict, Any
from utils.logger import get_logger
from config.config import get_config
import google.generativeai as genai

logger = get_logger(__name__)

@dataclass
class PlanStep:
    """A step in the execution plan."""
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    
@dataclass
class Plan:
    """A complete execution plan."""
    task: str
    steps: List[PlanStep]

class Planner:
    """Creates execution plans for tasks."""
    
    def __init__(self):
        """Initialize the planner."""
        config = get_config()
        genai.configure(api_key=config.get("gemini_api_key"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def create_plan(self, task_description, task_analysis):
        """
        Create a plan for executing the given task.
        
        Args:
            task_description (str): Description of the task
            task_analysis (dict): Analysis of the task from comprehension
            
        Returns:
            Plan: Execution plan with steps
        """
        logger.info(f"Creating plan for task: {task_description}")
        
        # Use LLM to generate a plan
        prompt = self._create_planning_prompt(task_description, task_analysis)
        
        # Updated API call format
        response = self.model.generate_content(prompt)
        
        try:
            # Parse the LLM response into a structured plan
            plan_dict = self._parse_plan_response(response.text)
            
            # Convert to plan object
            steps = []
            for step_dict in plan_dict.get("steps", []):
                step = PlanStep(
                    description=step_dict.get("description", ""),
                    tool_name=step_dict.get("tool", ""),
                    parameters=step_dict.get("parameters", {})
                )
                steps.append(step)
                
            return Plan(task=task_description, steps=steps)
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            # Fallback to a simple default plan if parsing fails
            return self._create_default_plan(task_description)
    
    def _create_planning_prompt(self, task_description, task_analysis):
        """Create a prompt for the LLM to generate a plan."""
        return f"""
        As an AI research assistant, create a detailed execution plan for the following task:
        
        TASK: {task_description}
        
        TASK ANALYSIS: {task_analysis}
        
        Available tools:
        1. search - Searches Google via serper.dev
           Parameters: query (str), num_results (int, optional)
        
        2. browser - Fetches and processes web content
           Parameters: url (str), extract_type (str, optional: 'full', 'main_content', 'summary')
        
        3. code - Generates or analyzes code
           Parameters: prompt (str), language (str, optional)
        
        Create a step-by-step plan in valid JSON format. Follow these JSON formatting rules strictly:
        - Use double quotes for strings, not single quotes
        - Add commas between array elements and object properties
        - Don't add trailing commas
        - Make sure all opening brackets/braces have matching closing brackets/braces
        
        Expected JSON structure:
        {{
            "steps": [
                {{
                    "description": "Step description",
                    "tool": "tool_name",
                    "parameters": {{
                        "param1": "value1",
                        "param2": "value2"
                    }}
                }},
                {{
                    "description": "Another step description",
                    "tool": "another_tool_name",
                    "parameters": {{
                        "param1": "value1"
                    }}
                }}
            ]
        }}
        """
    
    def _parse_plan_response(self, response_text):
        """Parse the LLM response into a structured plan."""
        # Extract JSON from the response
        import re
        import json
        
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'({[\s\S]*"steps"[\s\S]*})', response_text)
            if (json_match):
                plan_json = json_match.group(1)
            else:
                raise ValueError("Could not extract JSON from response")
        
        # Parse the JSON
        try:
            return json.loads(plan_json)
        except json.JSONDecodeError:
            # Try to fix common JSON errors
            plan_json = plan_json.replace("'", '"')
            return json.loads(plan_json)
    
    def _create_default_plan(self, task_description):
        """Create a simple default plan if the LLM planning fails."""
        search_query = task_description
        
        steps = [
            PlanStep(
                description=f"Search for information about: {search_query}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 5}
            ),
            PlanStep(
                description="Browse the first search result to gather information",
                logger.error(f"Failed to fix JSON: {str(e2)}. Final attempt with jsonlib...")
                tool_name="browser",
                parameters={"url": "{search_result_0_url}", "extract_type": "main_content"}
            ),
            PlanStep(
                description="Generate a summary report",
                tool_name="code",
                parameters={"prompt": f"Generate a detailed report for the task: {task_description}", "language": "markdown"}
            )
        ]
        
        return Plan(task=task_description, steps=steps)

                
                try:
                    # Last resort: try a more lenient parser if available
                    try:
                        import jsonlib
                        return jsonlib.loads(plan_json)
                    except ImportError:
                        # Or try to use a simple eval-based approach (note: can be unsafe with untrusted input)
                        import ast
                        plan_dict_str = plan_json.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                        return ast.literal_eval(plan_dict_str)
                except Exception as e3:
                    logger.critical(f"All JSON parsing attempts failed: {str(e3)}")
                    raise ValueError(f"Could not parse plan JSON: {str(e)}")
    
    def _create_default_plan(self, task_description):
        """Create a simple default plan if the LLM planning fails."""
        search_query = task_description
        
        steps = [
            PlanStep(
                description=f"Search for information about: {search_query}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 5}
            ),
            PlanStep(
                description="Browse the first search result to gather information",
                tool_name="browser",
                parameters={"url": "{search_result_0_url}", "extract_type": "main_content"}
            ),
            PlanStep(
                description="Generate a summary report",
                tool_name="code",
                parameters={"prompt": f"Generate a detailed report for the task: {task_description}", "language": "markdown"}
            )
        ]
        
        return Plan(task=task_description, steps=steps)
