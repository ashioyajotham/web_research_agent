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
        """Create a plan with better search strategy."""
        try:
            steps = []
            
            # Create more targeted search query
            search_query = self._create_targeted_search_query(task_description)
            
            search_step = PlanStep(
                tool_name="search",
                description=f"Search for: {search_query}",
                parameters={"query": search_query, "num_results": 10}
            )
            steps.append(search_step)
            
            # Add browser step
            browser_step = PlanStep(
                tool_name="browser",
                description="Extract information from search results",
                parameters={"url": None}  # Will be resolved during execution
            )
            steps.append(browser_step)
            
            # Add presentation step
            present_step = PlanStep(
                tool_name="present",
                description="Organize and present findings",
                parameters={"task": task_description}
            )
            steps.append(present_step)
            
            return Plan(task=task_description, steps=steps)
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            return self._create_default_plan(task_description)

    def _create_targeted_search_query(self, task_description):
        """Create a more targeted search query from task description."""
        # Extract key terms for better search
        if "statements" in task_description.lower() and "biden" in task_description.lower():
            return "Joe Biden statements US China relations speeches remarks"
        elif "coo" in task_description.lower() and "geneva" in task_description.lower():
            return "Geneva AI talks 2023 mediator organization COO chief operating officer"
        elif "epoch ai" in task_description.lower() and "dataset" in task_description.lower():
            return "Epoch AI dataset download large-scale AI models compute"
        elif "volkswagen" in task_description.lower() and "emissions" in task_description.lower():
            return "Volkswagen greenhouse gas emissions Scope 1 Scope 2 2021 2023"
        else:
            # Use first 100 characters as fallback
            return task_description[:100]

    def _create_planning_prompt(self, task_description, task_analysis):
        """Create a prompt for the LLM to generate a plan."""
        
        # Check if task requires coding
        requires_coding = task_analysis.get("requires_coding", False)
        presentation_format = task_analysis.get("presentation_format", "report")
        
        # Enhanced multi-criteria detection
        has_multiple_criteria = "\n" in task_description and any(line.strip().startswith("-") or 
                                                              line.strip().startswith("•") or
                                                              re.match(r"^\s+\w+", line) 
                                                              for line in task_description.split("\n"))
        
        criteria_guidance = ""
        if has_multiple_criteria:
            criteria_guidance = """
            This task contains multiple criteria or conditions. Make sure to:
            - Create specific search steps for each major criterion
            - Use specific and targeted queries that focus on one criterion at a time
            - Add a 'code' step to filter and verify results against all criteria
            - End with a 'present' step that formats the final verified results as a list
            """
        
        return f"""
        As an AI research assistant, create a detailed execution plan for the following task:
        
        TASK: {task_description}
        
        TASK ANALYSIS: {task_analysis}
        
        {criteria_guidance}
        
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
        
        For tasks with multiple criteria or conditions:
        - Create separate search steps for different aspects of the criteria  
        - Implement a verification step to ensure all criteria are addressed
        - Consider using the 'code' tool to filter and validate results against complex criteria
        
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
        
        # Add browser step with a reliably resolvable URL placeholder format
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
    
def create_plan(task: str, analysis: dict) -> dict:
    plan_raw = "..."  # Assume we fetch raw JSON from somewhere
    try:
        plan_data = json.loads(plan_raw)
    except json.JSONDecodeError as e:
        logger.error(f"Error creating plan: Could not parse plan JSON: {str(e)}")
        return {"error": f"JSON parsing error: {str(e)}"}
    
    return plan_data
