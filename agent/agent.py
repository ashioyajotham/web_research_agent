from .memory import Memory
from .planner import Planner
from .comprehension import Comprehension
from tools.tool_registry import ToolRegistry
from utils.formatters import format_results
from utils.logger import get_logger
import re

logger = get_logger(__name__)

class WebResearchAgent:
    """Main agent class for web research."""
    
    def __init__(self):
        """Initialize the web research agent with its components."""
        self.memory = Memory()
        self.planner = Planner()
        self.comprehension = Comprehension()
        self.tool_registry = ToolRegistry()
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register the default set of tools."""
        from tools.search import SearchTool
        from tools.browser import BrowserTool
        from tools.code_generator import CodeGeneratorTool
        
        self.tool_registry.register_tool("search", SearchTool())
        self.tool_registry.register_tool("browser", BrowserTool())
        self.tool_registry.register_tool("code", CodeGeneratorTool())
    
    def execute_task(self, task_description):
        """
        Execute a research task based on the given description.
        
        Args:
            task_description (str): Description of the task to perform
            
        Returns:
            str: Formatted results of the task
        """
        logger.info(f"Starting task: {task_description}")
        
        # Store task in memory
        self.memory.add_task(task_description)
        
        # Understand the task
        task_analysis = self.comprehension.analyze_task(task_description)
        logger.info(f"Task analysis: {task_analysis}")
        
        # Create a plan
        plan = self.planner.create_plan(task_description, task_analysis)
        logger.info(f"Created plan with {len(plan.steps)} steps")
        
        # Execute the plan
        results = []
        for step_index, step in enumerate(plan.steps):
            logger.info(f"Executing step: {step.description}")
            
            # Get the appropriate tool
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                error_msg = f"Tool '{step.tool_name}' not found"
                logger.error(error_msg)
                results.append({"step": step.description, "status": "error", "output": error_msg})
                continue
            
            # Prepare parameters with variable substitution
            parameters = self._substitute_parameters(step.parameters, results)
            
            # Execute the tool
            try:
                output = tool.execute(parameters, self.memory)
                results.append({"step": step.description, "status": "success", "output": output})
                self.memory.add_result(step.description, output)
            except Exception as e:
                logger.error(f"Error executing tool {step.tool_name}: {str(e)}")
                results.append({"step": step.description, "status": "error", "output": str(e)})
        
        # Format the results
        formatted_results = format_results(task_description, plan, results)
        return formatted_results
    
    def _substitute_parameters(self, parameters, previous_results):
        """
        Substitute variables in parameters using results from previous steps.
        
        Args:
            parameters (dict): Step parameters with potential variables
            previous_results (list): Results from previous steps
            
        Returns:
            dict: Parameters with variables substituted
        """
        substituted = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # Handle search result URL placeholders
                if re.match(r"\{search_result_(\d+)_url\}", value):
                    index = int(re.search(r"\{search_result_(\d+)_url\}", value).group(1))
                    # Find the most recent search result
                    for result in reversed(previous_results):
                        if result["status"] == "success" and "output" in result["output"] and "results" in result["output"]:
                            if index < len(result["output"]["results"]):
                                substituted[key] = result["output"]["results"][index]["link"]
                                logger.info(f"Substituted parameter {key}: {value} -> {substituted[key]}")
                                break
                    # If not found, keep original
                    if key not in substituted:
                        substituted[key] = value
                else:
                    # Handle other variable types if needed
                    substituted[key] = value
            else:
                # Non-string values pass through unchanged
                substituted[key] = value
        
        return substituted