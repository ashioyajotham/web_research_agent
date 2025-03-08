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
        from tools.presentation_tool import PresentationTool
        
        self.tool_registry.register_tool("search", SearchTool())
        self.tool_registry.register_tool("browser", BrowserTool())
        self.tool_registry.register_tool("code", CodeGeneratorTool())
        self.tool_registry.register_tool("present", PresentationTool())
    
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
            
            # Check if dependencies are met
            can_execute, reason = self._can_execute_step(step_index, results)
            if not can_execute:
                logger.warning(f"Skipping step {step_index+1}: {reason}")
                results.append({
                    "step": step.description, 
                    "status": "error", 
                    "output": f"Skipped step due to previous failures: {reason}"
                })
                continue
            
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
                
                # Store search results specifically for easy reference
                if step.tool_name == "search" and isinstance(output, dict) and "results" in output:
                    self.memory.search_results = output["results"]
                    logger.info(f"Stored {len(self.memory.search_results)} search results in memory")
            except Exception as e:
                logger.error(f"Error executing tool {step.tool_name}: {str(e)}")
                results.append({"step": step.description, "status": "error", "output": str(e)})
        
        # Format the results
        formatted_results = self._format_results(task_description, plan, results)
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
                # Different pattern matches for URL placeholders and variables
                
                # Pattern 1: {search_result_X_url}
                search_placeholder_match = re.match(r"\{search_result_(\d+)_url\}", value)
                if search_placeholder_match:
                    index = int(search_placeholder_match.group(1))
                    substituted[key] = self._get_search_result_url(index, previous_results)
                    continue
                    
                # Pattern 2: [Insert URL from search result X]
                placeholder_match = re.search(r"\[.*search result\s*(\d+).*\]", value, re.IGNORECASE)
                if placeholder_match:
                    try:
                        index = int(placeholder_match.group(1))
                        substituted[key] = self._get_search_result_url(index, previous_results)
                        continue
                    except (ValueError, IndexError):
                        logger.warning(f"Failed to extract index from placeholder: {value}")
                
                # Pattern 3: [Insert URL from search results]
                if re.match(r"\[.*URL.*search results.*\]", value, re.IGNORECASE) or \
                   re.match(r"\[Insert.*\]", value, re.IGNORECASE):
                    # Default to first result
                    substituted[key] = self._get_search_result_url(0, previous_results)
                    continue
                
                # If no special pattern is matched, use the original value
                substituted[key] = value
            else:
                # Non-string values pass through unchanged
                substituted[key] = value
        
        return substituted

    def _get_search_result_url(self, index, previous_results):
        """
        Get a URL from search results at the specified index.
        
        Args:
            index (int): Index of the search result
            previous_results (list): Previous step results
            
        Returns:
            str: URL or original placeholder if not found
        """
        # First try memory's stored search results
        search_results = getattr(self.memory, 'search_results', None)
        
        if search_results and index < len(search_results):
            url = search_results[index].get("link", "")
            logger.info(f"Found URL in memory search results at index {index}: {url}")
            return url
        
        # Fall back to searching in previous results
        for result in reversed(previous_results):
            if result["status"] == "success":
                output = result.get("output", {})
                if isinstance(output, dict) and "results" in output:
                    results_list = output["results"]
                    if index < len(results_list):
                        url = results_list[index].get("link", "")
                        logger.info(f"Found URL in previous results at index {index}: {url}")
                        return url
        
        # If we couldn't find a URL, log a warning and return a fallback
        logger.warning(f"Could not find URL at index {index}, using memory's first result as fallback")
        
        # Last resort: try to use the first result
        if search_results and len(search_results) > 0:
            return search_results[0].get("link", "No URL found") 
        
        return f"No URL found at index {index}"

    def _format_results(self, task_description, plan, results):
        """
        Format results using the formatter utility.
            task_description (str): Original task description
        
        Args:
            task_description (str): Original task description
            plan (Plan): The plan that was executed
            results (list): Results from each step of the plan
            
        Returns:
            str: Formatted results
        """
        from utils.formatters import format_results
        return format_results(task_description, plan, results)
            results (list): Results from each step of the plan
            
        Returns:
            str: Formatted results
        """
        from utils.formatters import format_results
        return format_results(task_description, plan, results)

    def _can_execute_step(self, step_index, results):
        """
        Determine if a step can be executed based on previous step results.
        
        Args:
            step_index (int): Current step index
            results (list): Previous results
            
        Returns:
            if isinstance(result.get("output"), dict) and "error" in result["output"]:
                return False, f"Previous step {i+1} returned error: {result['output']['error']}"
        
        # If all previous steps are successful, we can execute this step
        return True, ""
            tuple: (can_execute, reason)
        """
        # Steps before current
        previous_steps = results[:step_index]
        
        # Check if any previous step has failed
        for i, result in enumerate(previous_steps):
            if result["status"] == "error":
                return False, f"Previous step {i+1} failed: {result.get('output', 'Unknown error')}"
            
            # Check if output is a dictionary with an error key
            plan (Plan): The plan that was executed
            results (list): Results from each step of the plan
            
        Returns:
            str: Formatted results
        """
        from utils.formatters import format_results
        return format_results(task_description, plan, results)