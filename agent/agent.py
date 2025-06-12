import re
import time

from .memory import Memory
from .planner import Planner
from .comprehension import Comprehension
from tools.tool_registry import ToolRegistry
from utils.formatters import format_results
from utils.logger import get_logger

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
        Execute a research task with enhanced URL resolution.
        
        Args:
            task_description (str): Description of the task to perform
            
        Returns:
            str: Formatted results of the task
        """
        # Reset memory and tools at the beginning of each task
        self.memory = Memory()
        self.tool_registry = ToolRegistry()
        self._register_default_tools()
        
        # Initialize entity context tracking
        self._entity_context_mentions = {}
        
        logger.info(f"Starting new task with clean memory: {task_description}")
        
        # Store task in memory
        self.memory.add_task(task_description)
        
        # Analyze task
        task_analysis = self.comprehension.analyze_task(task_description)
        logger.info(f"Task analysis: {task_analysis}")
        
        # Create plan
        plan = self.planner.create_plan(task_description, task_analysis)
        logger.info(f"Created plan with {len(plan.steps)} steps")
        
        # Execute the plan
        results = []
        for step_index, step in enumerate(plan.steps):
            logger.info(f"Executing step {step_index+1}/{len(plan.steps)}: {step.description}")
            
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
            
            # Get the tool
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                error_msg = f"Tool '{step.tool_name}' not found"
                logger.error(error_msg)
                results.append({
                    "step": step.description, 
                    "status": "error",
                    "output": error_msg
                })
                continue
            
            # Prepare parameters with enhanced variable substitution
            parameters = self._substitute_parameters(step.parameters, results)
            
            # Special handling for browser steps with unresolved URLs
            if (step.tool_name == "browser" and 
                (not parameters.get("url") or parameters.get("use_search_snippets"))):
                
                logger.info("Browser step will use search snippets due to URL resolution failure")
                # The browser tool will handle snippet extraction
            
            # Execute the tool
            try:
                output = tool.execute(parameters, self.memory)
                
                # Check if the step actually accomplished its objective
                verified, message = self._verify_step_completion(step, output)
                if not verified:
                    logger.warning(
                        f"Step {step_index+1} did not achieve its objective: {message}"
                    )
                    
                    # Try to recover with more specific parameters if appropriate
                    if step.tool_name == "search" and step_index > 0:
                        # If previous steps found relevant entities, use them to refine the search
                        entities = self.memory.get_entities()
                        refined_query = self._refine_query_with_entities(step.parameters.get("query", ""), entities)
                        logger.info(f"Refining search query to: {refined_query}")
                        
                        # Re-run with refined query
                        parameters["query"] = refined_query
                        output = tool.execute(parameters, self.memory)
                    elif step.tool_name == "browser" and "error" in output and "403" in str(output.get("error", "")):
                        # If we got a 403/blocked error, try a fallback approach
                        logger.warning("Website blocked access - attempting fallback to search result snippets")
                        
                        # Create fallback content from search result snippets
                        if hasattr(self.memory, 'search_results') and self.memory.search_results:
                            # Combine snippets into a single document
                            combined_text = f"# Content extracted from search snippets\n\n"
                            for i, result_item in enumerate(self.memory.search_results[:5]):  # Use top 5
                                title = result_item.get("title", f"Result {i+1}")
                                snippet = result_item.get("snippet", "No description")
                                link = result_item.get("link", "#")
                                combined_text += f"## {title}\n\n{snippet}\n\nSource: {link}\n\n"
                            
                            # Override the output with generated content
                            output = {
                                "url": "search_results_combined",
                                "title": "Combined search result content (Anti-scraping fallback)",
                                "extract_type": "fallback",
                                "content": combined_text
                            }
                            logger.info("Created fallback content from search snippets")
                
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
                if (step.tool_name == "search" and 
                    isinstance(output, dict) and 
                    "results" in output):
                    self.memory.search_results = output["results"]
                    logger.info(
                        f"Stored {len(self.memory.search_results)} search results in memory"
                    )
            
            except Exception as e:
                logger.error(f"Error executing step {step_index+1}: {str(e)}")
                results.append({"step": step.description, "status": "error", "output": str(e)})
    
        # After each successful step, update entity context information
        if "status" in results[-1] and results[-1]["status"] == "success":
            self._update_entity_context_from_step(results[-1], task_description)
    
        # Format results based on task type and entity relevance
        formatted_results = self._format_results(task_description, plan, results)
        return formatted_results

    def _update_entity_context_from_step(self, step_result, task_description):
        """
        Update entity context information based on step results.
        
        Args:
            step_result (dict): Result from a step
            task_description (str): The task description
        """
        if not hasattr(self, '_entity_context_mentions'):
            self._entity_context_mentions = {}
            
        # Track entities that appear together
        if hasattr(self.memory, 'extracted_entities'):
            for entity_type, entities in self.memory.extracted_entities.items():
                for entity in entities:
                    entity_str = str(entity).lower()
                    if entity_str not in self._entity_context_mentions:
                        self._entity_context_mentions[entity_str] = 0
                    self._entity_context_mentions[entity_str] += 1

    def _substitute_parameters(self, parameters, previous_results):
        """
        Enhanced parameter substitution with dynamic placeholder detection and resolution.
        
        Args:
            parameters (dict): Step parameters with potential variables
            previous_results (list): Results from previous steps
            
        Returns:
            dict: Parameters with variables substituted
        """
        substituted = {}
        
        for key, value in parameters.items():
            if key == "url" and value is None:
                # Resolve URL from previous search results
                resolved_url = self._resolve_url_from_search_results(previous_results)
                if resolved_url:
                    substituted[key] = resolved_url
                    logger.info(f"Resolved URL to: {resolved_url}")
                else:
                    # Use search snippets instead
                    substituted["use_search_snippets"] = True
                    substituted[key] = None
                    logger.warning("Could not resolve URL, will use search snippets")
            else:
                substituted[key] = value
    
        return substituted

    def _resolve_url_from_search_results(self, previous_results):
        """Resolve URL from most recent search results."""
        for result in reversed(previous_results):
            if (result.get("status") == "success" and 
                "search" in result.get("step", "").lower()):
            
                search_output = result.get("output", {})
                search_results = search_output.get("results", [])
                
                # Get first valid URL
                for search_result in search_results:
                    url = search_result.get("link")
                    if url and self._is_valid_url(url):
                        return url
    
        return None

    def _is_valid_url(self, url):
        """Validate URL format."""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check for placeholder patterns
        placeholder_patterns = [
            r'\[.*?\]',
            r'\{.*?\}',
            r'<.*?>',
            r'INSERT',
            r'PLACEHOLDER'
        ]
        
        for pattern in placeholder_patterns:  # FIXED - no unpacking
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))

    def _is_placeholder_url(self, url):
        """Detect placeholder URLs that shouldn't be used."""
        if not url or not isinstance(url, str):
            return True
        
        # Check for common placeholder patterns
        placeholder_patterns = [
            r'\[.*?(?:url|link|insert|from).*?\]',  # [Insert URL from search results]
            r'\{.*?(?:url|link|result).*?\}',       # {search_result_url}
            r'<.*?(?:url|link).*?>',                # <URL here>
            r'INSERT.*?URL',                        # INSERT URL HERE
            r'PLACEHOLDER',                         # PLACEHOLDER
            r'EXAMPLE\.COM',                        # example.com
            r'^\[',                                 # Starts with [
        ]
        
        url_upper = url.upper()
        return any(re.search(pattern, url_upper, re.IGNORECASE) for pattern in placeholder_patterns)

    def _resolve_dynamic_placeholders(self, value, previous_results):
        """
        Dynamically resolve various types of placeholders in parameter values.
        """
        if not isinstance(value, str):
            return value
        
        # For now, return the value as-is if it's not a URL
        # This method can be expanded for other types of placeholders
        return value

    def _can_execute_step(self, step_index, previous_results):
        """Check if a step can be executed based on prior steps' statuses."""
        # Always allow first step
        if step_index == 0:
            return True, "First step"
        
        # Check if any critical previous steps failed
        critical_failures = 0
        for i, result in enumerate(previous_results):
            if result.get("status") == "error":
                critical_failures += 1
        
        # Allow if not too many failures
        if critical_failures < len(previous_results) * 0.7:
            return True, "Sufficient previous success"
        
        return False, f"Too many previous failures ({critical_failures}/{len(previous_results)})"

    def _extract_entities_from_snippets(self, search_results, query):
        """Extract entities from search result snippets."""
        if not search_results:
            return
        
        # Combine all snippets
        combined_text = ""
        for result in search_results:
            if isinstance(result, dict):
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                combined_text += f"{title} {snippet} "
        
        # Extract entities using the comprehension module
        if combined_text.strip():
            entities = self.comprehension.extract_entities(combined_text)
            if entities:
                self.memory.add_entities(entities)
                logger.info(f"Extracted entities from search snippets: {entities}")

    def _verify_step_completion(self, step, output):
        """Verify if a step achieved its intended objective."""
        if not output:
            return False, "No output generated"
        
        if isinstance(output, dict) and "error" in output:
            return False, f"Step error: {output['error']}"
        
        # Basic verification - step ran successfully if it has meaningful output
        if isinstance(output, dict):
            if "results" in output and output["results"]:
                return True, "Search results found"
            elif "content" in output and len(str(output["content"])) > 50:
                return True, "Content extracted successfully"
            elif "url" in output:
                return True, "URL processed"
        
        if isinstance(output, str) and len(output) > 20:
            return True, "Text output generated"
        
        # Default to success if we can't detect a failure
        return True, "Step completed"

    def _refine_query_with_entities(self, original_query, entities):
        """Refine a search query using discovered named entities."""
        if not entities:
            return original_query
        
        # Add relevant entities to query
        additional_terms = []
        for entity_type, entity_list in entities.items():
            if entity_type in ["organization", "person", "location"] and entity_list:
                # Add first few discovered entity names
                for entity in entity_list[:2]:
                    entity_str = str(entity).strip()
                    if entity_str and entity_str not in original_query:
                        additional_terms.append(f'"{entity_str}"')
        
        if additional_terms:
            refined_query = f"{original_query} {' '.join(additional_terms)}"
            return refined_query
        
        return original_query

    def _display_step_result(self, step_number, description, status, output):
        """Display the result of a step execution (logging in this implementation)."""
        logger.info(f"Step {step_number} ({description}): {status}")
        if isinstance(output, dict) and "results" in output:
            result_count = len(output["results"]) if output["results"] else 0
            logger.info(f"  Found {result_count} search results")
        elif isinstance(output, dict) and "content" in output:
            content_length = len(str(output["content"])) if output["content"] else 0
            logger.info(f"  Extracted {content_length} characters of content")
    
    def _format_results(self, task_description, plan, results):
        """
        Format the results of task execution.
        
        Args:
            task_description (str): The original task description
            plan: The plan that was executed
            results (list): List of step results
            
        Returns:
            str: Formatted results
        """
        # Determine the appropriate synthesis strategy based on task analysis
        task_analysis = self.comprehension.analyze_task(task_description)
        synthesis_strategy = task_analysis.get("synthesis_strategy", "comprehensive_synthesis")
        
        logger.info(f"Formatting results using strategy: {synthesis_strategy}")
        
        # Use the appropriate synthesis method
        if synthesis_strategy == "extract_and_verify":
            return self._synthesize_extract_and_verify(task_description, results)
        elif synthesis_strategy == "aggregate_and_filter":
            return self._synthesize_aggregate_and_filter(task_description, results)
        elif synthesis_strategy == "collect_and_organize":
            return self._synthesize_collect_and_organize(task_description, results)
        else:
            return self._synthesize_comprehensive_synthesis(task_description, results)

    def _synthesize_extract_and_verify(self, task_description, results):
        """Synthesize results for extract and verify strategy."""
        output = [f"# {task_description}\n"]
        
        # Find successful results
        successful_results = [r for r in results if r.get("status") == "success"]
        
        if not successful_results:
            output.append("## No Results Found\n")
            output.append("The research was unable to find the requested information.\n")
            return "\n".join(output)
        
        # Extract key information
        output.append("## Answer\n")
        
        for result in successful_results:
            if isinstance(result.get("output"), dict) and "extracted_text" in result["output"]:
                output.append(result["output"]["extracted_text"])
                output.append("\n")
        
        # Add source verification
        output.append("## Source Verification\n")
        output.append("Sources that support this finding:\n\n")
        
        for result in successful_results:
            if isinstance(result.get("output"), dict):
                urls = result["output"].get("urls", [])
                for url in urls:
                    if url and not self._is_placeholder_url(url):
                        title = result["output"].get("title", "Unknown Source")
                        output.append(f"- {url} ({title})\n")
        
        return "\n".join(output)

    def _synthesize_aggregate_and_filter(self, task_description, results):
        """Synthesize results for aggregate and filter strategy."""
        output = [f"# {task_description}\n"]
        
        # Collect all entities and organize them
        all_entities = []
        search_results = []
        
        for result in results:
            if result.get("status") == "success":
                result_output = result.get("output", {})
                
                # Collect search results
                if isinstance(result_output, dict) and "results" in result_output:
                    search_results.extend(result_output["results"])
                
                # Collect entities from memory
                entities = self.memory.get_entities()
                all_entities.extend(entities)
        
        output.append("## Results\n")
        output.append("| Item | Details | Status |\n")
        output.append("|------|---------|--------|\n")
        
        # Add unique entities
        seen_items = set()
        for entity in all_entities:
            if entity not in seen_items:
                output.append(f"| {entity} | Found in research | Requires verification |\n")
                seen_items.add(entity)
        
        # Add search results as potential items
        for result in search_results[:20]:  # Limit to prevent overwhelming output
            title = result.get("title", "Unknown")
            if title not in seen_items:
                output.append(f"| {title} | Found in research | Requires verification |\n")
                seen_items.add(title)
        
        output.append(f"\n**Total found:** {len(seen_items)}\n")
        
        return "\n".join(output)

    def _synthesize_collect_and_organize(self, task_description, results):
        """Synthesize results for collect and organize strategy."""
        output = [f"# {task_description}\n"]
        
        output.append("## Research Findings\n")
        
        # Extract and organize entities
        entities = self.memory.get_entities()
        if entities:
            output.append("### Entities Identified\n")
            
            # Group entities by type if possible
            people = [e for e in entities if any(title in e.lower() for title in ["president", "secretary", "director", "minister"])]
            organizations = [e for e in entities if any(word in e.lower() for word in ["government", "cabinet", "council", "agency"])]
            roles = [e for e in entities if " @ " in e]  # Entities with role assignments
            
            if people:
                output.append(f"**Person:** {', '.join(people[:10])}\n")  # Limit output
            if organizations:
                output.append(f"**Organization:** {', '.join(organizations[:10])}\n")
            if roles:
                output.append(f"**Role:** {', '.join(roles[:10])}\n")
        
        # Add content from successful steps
        successful_results = [r for r in results if r.get("status") == "success"]
        for i, result in enumerate(successful_results):
            if isinstance(result.get("output"), dict):
                content = result["output"].get("extracted_text", "")
                if content and len(content) > 50:  # Only include substantial content
                    output.append(f"\n### Source {i+1}\n")
                    output.append(content[:500] + "..." if len(content) > 500 else content)
                    
                    # Add source URL if available
                    urls = result["output"].get("urls", [])
                    if urls and not self._is_placeholder_url(urls[0]):
                        output.append(f"\n**Source {i+1}:** {urls[0]}\n")
        
        return "\n".join(output)

    def _synthesize_comprehensive_synthesis(self, task_description, results):
        """Synthesize results for comprehensive synthesis strategy."""
        output = [f"# {task_description}\n"]
        
        output.append("## Research Findings\n")
        
        # Get search results for analysis
        search_results = []
        snippet_content = []
        
        for result in results:
            if result.get("status") == "success":
                result_output = result.get("output", {})
                
                # Collect search results
                if isinstance(result_output, dict):
                    if "results" in result_output:
                        search_results.extend(result_output["results"])
                    elif "search_results" in result_output:
                        search_results.extend(result_output["search_results"])
                    
                    # Collect snippet content from browser fallbacks
                    if result_output.get("source") == "search_snippets":
                        content = result_output.get("extracted_text", "")
                        if content and len(content) > 100:
                            snippet_content.append(content)
        
        # If we have snippet content, use it
        if snippet_content:
            output.append("### Information Found\n")
            for i, content in enumerate(snippet_content):
                output.append(f"**Source {i+1}:**\n")
                # Show relevant excerpts
                lines = content.split('\n')
                relevant_lines = [line for line in lines if line.strip() and not line.startswith('**')]
                for line in relevant_lines[:10]:  # Show first 10 relevant lines
                    output.append(f"- {line.strip()}\n")
                output.append("\n")
        
        # Show search results found
        if search_results:
            output.append("### Search Results Found\n")
            for i, result in enumerate(search_results[:5]):
                title = result.get("title", "Unknown")
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                
                output.append(f"**{i+1}. {title}**\n")
                if snippet:
                    output.append(f"{snippet}\n")
                if link:
                    output.append(f"Source: {link}\n")
                output.append("\n")
        
        # Add research summary
        output.append("## Research Summary\n")
        
        search_count = len([r for r in results if "search" in r.get("step", "").lower() and r.get("status") == "success"])
        browser_count = len([r for r in results if "browse" in r.get("step", "").lower() and r.get("status") == "success"])
        snippet_count = len(snippet_content)
        
        output.append(f"**Research completed using comprehensive_synthesis strategy.**\n\n")
        output.append(f"**Research scope:**\n")
        output.append(f"- {search_count} search operations completed\n")
        output.append(f"- {browser_count} web pages processed\n")
        output.append(f"- {snippet_count} content extracts from search snippets\n")
        output.append(f"- {len(search_results)} search results analyzed\n")
        
        return "\n".join(output)