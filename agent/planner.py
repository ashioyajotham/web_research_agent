from dataclasses import dataclass
from typing import List, Dict, Any
from utils.logger import get_logger
from config.config import get_config
import google.generativeai as genai
import re
import json

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
    steps: List[PlanStep]  # Fixed: using proper square brackets for type annotation

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
        
        # Check if task requires coding
        requires_coding = task_analysis.get("requires_coding", False)
        presentation_format = task_analysis.get("presentation_format", "report")
        
        return f"""
        As an AI research assistant, create a detailed execution plan for the following task:
        
        TASK: {task_description}
        
        TASK ANALYSIS: {task_analysis}
        
        Available tools:
        1. search - Searches Google via serper.dev
           Parameters: query (str), num_results (int, optional)
        
        2. browser - Fetches and processes web content
           Parameters: url (str), extract_type (str, optional: 'full', 'main_content', 'summary')
        
        3. code - Generates or analyzes code. Only use this tool if the task explicitly requires writing code.
           Parameters: prompt (str), language (str, optional), operation (str, optional: 'generate', 'debug', 'explain')
        
        4. present - Organizes and formats information without writing code
           Parameters: prompt (str), format_type (str, optional: 'table', 'list', 'summary', 'comparison'), title (str, optional)
        
        IMPORTANT: 
        - Only use the 'code' tool when the task explicitly requires writing computer code or programming.
        - Use the 'present' tool for tasks that need data organization or presentation of results.
        - This task {'' if requires_coding else 'does not '} appear to require coding based on analysis.
        - The suggested presentation format is '{presentation_format}'.
        
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
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'({[\s\S]*"steps"[\s\S]*})', response_text)
            if json_match:
                plan_json = json_match.group(1)
            else:
                logger.warning(f"Could not extract JSON from response, using default plan. Response: {response_text[:200]}...")
                raise ValueError("Could not extract JSON from response")
        
        # Log the extracted JSON for debugging
        logger.debug(f"Extracted JSON: {plan_json[:200]}...")
        
        # Parse the JSON with enhanced error handling
        try:
            return json.loads(plan_json)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {str(e)}. Attempting to fix...")
            
            # Common JSON formatting issues to fix
            # 1. Replace single quotes with double quotes
            plan_json = plan_json.replace("'", '"')
            
            # 2. Fix missing commas between objects in arrays
            plan_json = re.sub(r'}\s*{', '},{', plan_json)
            
            # 3. Fix trailing commas in arrays and objects
            plan_json = re.sub(r',\s*}', '}', plan_json)
            plan_json = re.sub(r',\s*]', ']', plan_json)
            
            # 4. Fix missing quotes around keys
            plan_json = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', plan_json)
            
            # 5. Remove comments
            plan_json = re.sub(r'//.*?(\n|$)', '', plan_json)
            
            try:
                return json.loads(plan_json)
            except json.JSONDecodeError as e2:
                logger.error(f"Failed to fix JSON: {str(e2)}. Final attempt with jsonlib...")
                
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
        
        # Determine if this looks like a coding task
        coding_keywords = ["write", "code", "program", "script", "function", "implement", "develop", "algorithm"]
        requires_coding = any(keyword in task_description.lower() for keyword in coding_keywords)
        
        steps = [
            PlanStep(
                description=f"Search for information about: {search_query}",
                tool_name="search",
                parameters={"query": search_query, "num_results": 10}
            )
        ]
        
        # Add browser step with specific URL structure
        steps.append(
            PlanStep(
                description="Browse the first search result to gather information",
                tool_name="browser",
                parameters={"url": "{search_result_0_url}", "extract_type": "main_content"}
            )
        )
        
        # Add the final step based on whether the task appears to require coding
        if requires_coding:
            steps.append(
                PlanStep(
                    description="Generate code based on gathered information",
                    tool_name="code",
                    parameters={
                        "prompt": f"Based on the gathered information, generate code for: {task_description}",
                        "language": "python"
                    }
                )
            )
        else:
            # For non-coding tasks, use the presentation tool
            steps.append(
                PlanStep(
                    description="Organize and present the gathered information",
                    tool_name="present",
                    parameters={
                        "prompt": f"Organize and present the information for the task: {task_description}",
                        "format_type": "summary",
                        "title": "Research Results"
                    }
                )
            )
        
        return Plan(task=task_description, steps=steps)
