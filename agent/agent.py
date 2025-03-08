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
            
            # Add entity extraction for certain step types
            if "identify" in step.description.lower() or "find" in step.description.lower():
                if step.tool_name == "browser":
                    parameters["extract_entities"] = True
                    entity_types = []
                    if "person" in step.description.lower():
                        entity_types.append("person")
                    if "organization" in step.description.lower():
                        entity_types.append("organization")
                    if "role" in step.description.lower() or "coo" in step.description.lower() or "ceo" in step.description.lower():
                        entity_types.append("role")
                    if entity_types:
                        parameters["entity_types"] = entity_types
            
            # Execute the tool
            try:
                output = tool.execute(parameters, self.memory)
                
                # Check if the step actually accomplished its objective
                verified, message = self._verify_step_completion(step, output)
                if not verified:
                    logger.warning(f"Step {step_index+1} did not achieve its objective: {message}")
                    
                    # Try to recover with more specific parameters if appropriate
                    if step.tool_name == "search" and step_index > 0:
                        # If previous steps found relevant entities, use them to refine the search
                        entities = self.memory.get_entities()
                        refined_query = self._refine_query_with_entities(step.parameters.get("query", ""), entities)
                        logger.info(f"Refining search query to: {refined_query}")
                        
                        # Re-run with refined query
                        parameters["query"] = refined_query
                        output = tool.execute(parameters, self.memory)
                
                # Record the result with verification status
                results.append({
                    "step": step.description, 
                    "status": "success", 
                    "output": output,
                    "verified": verified,
                    "verification_message": message
                })
                
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
        
        Args:
            task_description (str): Original task description
            plan (Plan): The plan that was executed
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
            tuple: (can_execute, reason)
        """
        # Steps before current
        previous_steps = results[:step_index]
        
        # Check if any previous step has failed
        for i, result in enumerate(previous_steps):
            if result["status"] == "error":
                return False, f"Previous step {i+1} failed: {result.get('output', 'Unknown error')}"
            
            # Check if output is a dictionary with an error key
            if isinstance(result.get("output"), dict) and "error" in result["output"]:
                return False, f"Previous step {i+1} returned error: {result['output']['error']}"
        
        # If all previous steps are successful, we can execute this step
        return True, ""

    def _verify_step_completion(self, step, result_output):
        """
        Verify if a step achieved its intended objective.
        
        Args:
            step (PlanStep): The step that was executed
            result_output (Any): Output from the step execution
            
        Returns:
            tuple: (success, message) - whether the step was successful and why/why not
        """
        # Basic verification - check if there's no error
        if isinstance(result_output, dict) and "error" in result_output:
            return False, f"Step returned an error: {result_output['error']}"
        
        # Specific verifications based on step type
        if step.tool_name == "search":
            # Check if search returned results
            if isinstance(result_output, dict) and "results" in result_output:
                if len(result_output["results"]) == 0:
                    return False, "Search returned no results"
            else:
                return False, "Search did not return expected result format"
        
        elif step.tool_name == "browser":
            # Check if content was extracted
            if isinstance(result_output, dict) and "content" in result_output:
                if not result_output["content"] or len(result_output["content"]) < 50:
                    return False, "Browser returned minimal or no content"
            else:
                return False, "Browser did not return expected content"
        
        # For steps that should produce specific entities
        if "identify" in step.description.lower() or "find" in step.description.lower():
            entity_types = []
            if "person" in step.description.lower() or "who" in step.description.lower():
                entity_types.append("person")
            if "organization" in step.description.lower():
                entity_types.append("organization")
            if "role" in step.description.lower() or "coo" in step.description.lower() or "ceo" in step.description.lower():
                entity_types.append("role")
            
            # Check if we have any of the expected entity types in memory
            if entity_types and hasattr(self.memory, 'extracted_entities'):
                for entity_type in entity_types:
                    if entity_type in self.memory.extracted_entities and self.memory.extracted_entities[entity_type]:
                        return True, f"Found {entity_type} entities: {self.memory.extracted_entities[entity_type]}"
        
        # Check if the content seems relevant to our task
        keywords = self._extract_keywords_from_step(step.description)
        if keywords and step.tool_name == "browser":
            content = result_output.get("content", "")
            if any(keyword.lower() in content.lower() for keyword in keywords):
                return True, "Content appears relevant to the task"
        
        # Default to success if no specific checks failed
        return True, "Step completed successfully"

    def _verify_code_results(self, step, result_output):
        """Verify code generation results."""
        if isinstance(result_output, str):
            if len(result_output) < 10:
                return False, "Generated code is too short"
            
            if "```" not in result_output and "def " not in result_output and "class " not in result_output:
                return False, "Output does not appear to contain code"
        
        return True, "Code generation completed"

    def _extract_keywords_from_step(self, step_description):
        """Extract relevant keywords from step description for verification."""
        # Remove common stop words and extract potential keywords
        stop_words = {"a", "an", "the", "and", "or", "but", "if", "for", "not", "from", "to", 
                      "search", "find", "look", "browse", "extract", "identify", "determine"}
        
        words = step_description.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Extract quoted phrases which are often important
        quoted = re.findall(r'"([^"]*)"', step_description)
        quoted.extend(re.findall(r"'([^']*)'", step_description))
        
        return list(set(keywords + quoted))

    def _refine_query_with_entities(self, original_query, entities):
        """
        Refine a search query using extracted entities.
        
        Args:
            original_query (str): Original search query
            entities (dict): Extracted entities
            
        Returns:
            str: Refined search query
        """
        refined_query = original_query
        entity_additions = []
        
        # Add organization names if available and relevant
        if "organization" in entities and entities["organization"]:
            # Sort by length - longer names are often more specific/relevant
            orgs = sorted(entities["organization"], key=len, reverse=True)[:2]
            for org in orgs:
                if len(org) > 3 and org.lower() not in original_query.lower():
                    entity_additions.append(f'"{org}"')
        
        # Add role specifics if available and relevant
        if "role" in entities and entities["role"]:
            role_keywords = []
            for role in entities["role"]:
                # Extract just the role part (e.g., "CEO" from "CEO: John Smith @ Acme")
                role_parts = role.split(":")
                if len(role_parts) > 0:
                    role_title = role_parts[0].strip()
                    if role_title not in original_query and role_title not in role_keywords:
                        role_keywords.append(role_title)
            
            for role in role_keywords[:2]:  # Limit to top 2 roles
                entity_additions.append(role)
        
        # Add person names if the query seems to be about finding information on people
        if "person" in entities and entities["person"] and any(term in original_query.lower() for term in ["who", "person", "name"]):
            # Sort by length - longer names are often more specific/relevant
            persons = sorted(entities["person"], key=len, reverse=True)[:1]
            for person in persons:
                if len(person) > 3 and person.lower() not in original_query.lower():
                    entity_additions.append(f'"{person}"')
        
        # Add entity additions if we have any
        if entity_additions:
            # Check if the query already ends with a question mark
            if original_query.strip().endswith('?'):
                refined_query = original_query.strip()[:-1] + " " + " ".join(entity_additions) + "?"
            else:
                refined_query = original_query + " " + " ".join(entity_additions)
        
        logger.info(f"Refined query: '{original_query}' -> '{refined_query}'")
        return refined_query