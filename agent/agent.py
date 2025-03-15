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
            
            # Special handling for search results - extract entities early from snippets
            if step.tool_name == "search":
                tool = self.tool_registry.get_tool(step.tool_name)
                if tool:
                    try:
                        output = tool.execute(step.parameters, self.memory)
                        
                        if isinstance(output, dict) and "results" in output:
                            # Extract entities from search snippets for immediate use
                            self._extract_entities_from_snippets(output["results"], step.parameters.get("query", ""))
                            
                            # Store results in memory
                            self.memory.search_results = output["results"]
                            
                        # Store the step result
                        results.append({"step": step.description, "status": "success", "output": output})
                        self.memory.add_result(step.description, output)
                        
                    except Exception as e:
                        logger.error(f"Error executing search: {str(e)}")
                        results.append({"step": step.description, "status": "error", "output": str(e)})
                    
                    # Display the result of this step
                    display_result = next((r for r in results if r["step"] == step.description), None)
                    if display_result:
                        self._display_step_result(step_index+1, step.description, display_result["status"], display_result["output"])
                    
                    continue  # Skip the normal execution flow for this step
            
            # Normal tool execution for non-search steps
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
                    elif step.tool_name == "browser" and "error" in output and "403" in str(output.get("error", "")):
                        # If we got a 403/blocked error, try a fallback approach
                        logger.warning("Website blocked access - attempting fallback to search result snippets")
                        
                        # Create fallback content from search result snippets
                        if hasattr(self.memory, 'search_results') and self.memory.search_results:
                            # Combine snippets into a single document
                            combined_text = f"# Content extracted from search snippets\n\n"
                            for i, result in enumerate(self.memory.search_results[:5]):  # Use top 5 results
                                title = result.get("title", f"Result {i+1}")
                                snippet = result.get("snippet", "No description")
                                link = result.get("link", "#")
                                combined_text += f"## {title}\n\n{snippet}\n\nSource: {link}\n\n"
                            
                            # Override the output with our generated content
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
                
                # Pattern 3: [URL from search results] or any bracketed URL reference
                if re.match(r"\[.*URL.*\]", value, re.IGNORECASE) or \
                   re.match(r"\[.*link.*\]", value, re.IGNORECASE) or \
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
                return True, f"Search returned {len(result_output['results'])} results"
            else:
                return False, "Search did not return expected result format"
        
        elif step.tool_name == "browser":
            # Check if content was extracted
            if isinstance(result_output, dict) and "content" in result_output:
                if not result_output["content"] or len(result_output["content"]) < 50:
                    return False, "Browser returned minimal or no content"
                
                # Check if the content includes any anti-scraping signals
                content = result_output["content"].lower()
                anti_bot_signals = ["captcha", "detected unusual traffic", "automated access", "blocked", "denied access"]
                
                if any(signal in content for signal in anti_bot_signals):
                    return False, "Browser may have been blocked by anti-scraping measures"
                    
                # Check for relevant content
                keywords = self._extract_keywords_from_step(step.description)
                if keywords and any(keyword.lower() in content for keyword in keywords):
                    return True, "Content appears relevant to the task"
                    
                return True, f"Successfully extracted {len(result_output['content'])} characters"
            else:
                return False, "Browser did not return expected content"
        
        # For steps that should produce specific entities
        if "identify" in step.description.lower() or "find" in step.description.lower():
            entity_types = []
            if "person" in step.description.lower() or "who" in step.description.lower():
                entity_types.append("person")
            if "organization" in step.description.lower():
                entity_types.append("organization")
            if "role" in step.description.lower() or any(role in step.description.lower() for role in 
                                                       ["coo", "ceo", "cfo", "president", "founder", "director"]):
                entity_types.append("role")
            
            # Check if we have any of the expected entity types in memory
            if entity_types and hasattr(self.memory, 'extracted_entities'):
                for entity_type in entity_types:
                    if entity_type in self.memory.extracted_entities and self.memory.extracted_entities[entity_type]:
                        return True, f"Found {entity_type} entities: {self.memory.extracted_entities[entity_type]}"
        
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
        Refine a search query using extracted entities with a more general approach.
        
        Args:
            original_query (str): Original search query
            entities (dict): Extracted entities
            
        Returns:
            str: Refined search query
        """
        if not entities:
            return original_query
        
        # Extract keywords from original query for context
        query_keywords = self._extract_keywords_from_text(original_query.lower())
        query_type = self._determine_query_type(original_query.lower())
        
        # Entity additions with context awareness
        entity_additions = []
        
        # Select most relevant entities across different types based on query context
        relevant_entities = {}
        
        # Build mapping of entity relevance scores
        entity_scores = {}
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # Skip very short entities
                if len(entity) < 3:
                    continue
                    
                # Skip if entity is already part of the query
                if entity.lower() in original_query.lower():
                    continue
                
                # Calculate relevance score based on query keywords
                score = self._calculate_entity_relevance(entity, query_keywords, query_type, entity_type)
                entity_scores[(entity_type, entity)] = score
        
        # Get top 3 entities across all types, sorted by relevance
        sorted_entities = sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)
        top_entities = [item[0] for item in sorted_entities[:3]]  # Take top 3 entities
        
        # Format additions based on entity types
        for (entity_type, entity) in top_entities:
            # Format based on entity type
            if entity_type == "organization" or entity_type == "location" or len(entity.split()) > 1:
                # Quote multi-word entities or organizations
                entity_additions.append(f'"{entity}"')
            else:
                entity_additions.append(entity)
        
        # Add entity additions if we have any
        if entity_additions:
            # Check if the query already ends with a question mark
            if original_query.strip().endswith('?'):
                refined_query = original_query.strip()[:-1] + " " + " ".join(entity_additions) + "?"
            else:
                refined_query = original_query + " " + " ".join(entity_additions)
            
            logger.info(f"Refined query: '{original_query}' -> '{refined_query}'")
            return refined_query
        
        return original_query

    def _calculate_entity_relevance(self, entity, query_keywords, query_type, entity_type):
        """Calculate relevance score for an entity based on query context."""
        entity_lower = entity.lower()
        score = 0
        
        # Match direct keyword presence
        for keyword in query_keywords:
            if keyword in entity_lower or entity_lower in keyword:
                score += 3
                break
        
        # Match based on entity type and query type
        type_matches = {
            "who_is": ["person", "role"],
            "what_is": ["organization", "concept", "technology"],
            "when": ["date", "time", "year"],
            "where": ["location", "place"],
            "why": ["reason", "cause"],
            "how": ["method", "process"],
            "quantity": ["number", "percentage", "monetary_value"]
        }
        
        # Boost score for entity types relevant to the query type
        if query_type in type_matches and entity_type in type_matches[query_type]:
            score += 2
        
        # Boost for longer, more specific entities
        word_count = len(entity.split())
        if word_count > 1:
            score += word_count - 1  # More words = more specific = higher score
            
        # Penalize very long entities slightly (might be too specific)
        if word_count > 4:
            score -= 1
            
        return score

    def _extract_keywords_from_text(self, text):
        """Extract keywords from text for entity relevance calculation."""
        # Simplified version - remove common stop words and extract meaningful terms
        stop_words = {"a", "an", "the", "and", "or", "but", "if", "for", "not", "on", "in", "to", "from", "by",
                     "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
                     "what", "which", "who", "whom", "whose", "when", "where", "why", "how"}
        
        words = text.lower().split()
        return [word for word in words if word not in stop_words and len(word) > 2]

    def _determine_query_type(self, query):
        """Determine the general type/intent of a query."""
        # Simple pattern-based classification
        if re.search(r'\bwho\b|\bwhose\b|\bperson\b', query):
            return "who_is"
        elif re.search(r'\bwhat\b|\bdefinition\b|\bmean\b|\bdescribe\b', query):
            return "what_is"
        elif re.search(r'\bwhen\b|\bdate\b|\btime\b|\byear\b', query):
            return "when"
        elif re.search(r'\bwhere\b|\blocation\b|\bplace\b', query):
            return "where"
        elif re.search(r'\bwhy\b|\breason\b|\bcause\b', query):
            return "why"
        elif re.search(r'\bhow\b', query):
            return "how"
        elif re.search(r'\bmany\b|\bmuch\b|\bnumber\b|\bcount\b|\bpercent', query):
            return "quantity"
        else:
            return "general"

    def _extract_entities_from_snippets(self, search_results, query):
        """
        Extract entities from search result snippets with improved generalization.
        
        Args:
            search_results (list): List of search result dictionaries
            query (str): The search query that produced these results
        """
        # Combine all snippets into a single text for entity extraction
        combined_text = ""
        for result in search_results:
            if "snippet" in result and result["snippet"]:
                combined_text += result["snippet"] + "\n\n"
            if "title" in result and result["title"]:
                combined_text += result["title"] + "\n"
        
        if not combined_text:
            return
        
        # Analyze query to determine appropriate entity types
        query_type = self._determine_query_type(query.lower())
        
        # Define entity types based on query type and context
        entity_types = ["person", "organization"]  # Base types for all queries
        
        # Add query-specific entity types
        query_entity_map = {
            "who_is": ["person", "organization", "role"],
            "what_is": ["concept", "technology", "organization"],
            "when": ["date", "time"],
            "where": ["location", "organization"],
            "why": ["reason", "cause", "event"],
            "quantity": ["percentage", "number", "monetary_value"]
        }
        
        if query_type in query_entity_map:
            entity_types.extend(query_entity_map[query_type])
        
        # Deduplicate entity types
        entity_types = list(set(entity_types))
        
        try:
            # Extract entities using focused entity types
            entities = self.comprehension.extract_entities(combined_text, entity_types)
            
            # Add extracted entities to memory
            self.memory.add_entities(entities)
            
            # Process entity relationships more generally
            self._process_entity_relationships(entities, query)
                    
        except Exception as e:
            logger.error(f"Error extracting entities from snippets: {str(e)}")

    def _process_entity_relationships(self, entities, query):
        """
        Process relationships between extracted entities in a more general way.
        
        Args:
            entities (dict): Extracted entities
            query (str): The search query for context
        """
        # Need at least two entity types for relationships
        if len(entities) < 2:
            return entities
            
        # Check for potential relationship patterns
        has_person = "person" in entities and entities["person"]
        has_org = "organization" in entities and entities["organization"]
        has_role = "role" in entities and entities["role"]
        has_location = "location" in entities and entities["location"]
        
        # Store enhanced relationships
        entity_relationships = []
        
        # Handle person-organization relationships
        if has_person and has_org:
            for person in entities["person"][:2]:  # Focus on top 2 persons
                for org in entities["organization"][:2]:  # Focus on top 2 orgs
                    # Look for role information
                    role_term = self._infer_role_from_context(query, entities)
                    
                    if role_term:
                        # Format relationship with any available role information
                        relationship = {
                            "type": "person_org",
                            "person": person,
                            "organization": org,
                            "role": role_term,
                            "formatted": f"{role_term.upper()}: {person} @ {org}" if role_term else None
                        }
                        entity_relationships.append(relationship)
                        
                        # Add to role entities if not already present
                        role_entry = relationship["formatted"]
                        if role_entry and ("role" not in entities or role_entry not in entities["role"]):
                            if "role" not in entities:
                                entities["role"] = []
                            entities["role"].append(role_entry)
        
        # Update memory with our enhanced entities
        if entity_relationships:
            self.memory.update_entities(entities)
            logger.info(f"Created {len(entity_relationships)} entity relationships")

    def _infer_role_from_context(self, query, entities):
        """Infer role information from query context and existing entities."""
        # Check for common role terms in the query
        common_roles = ["ceo", "cfo", "coo", "president", "founder", "director", "chief",
                       "head", "leader", "manager", "chair", "executive"]
        
        query_lower = query.lower()
        
        # Check for exact role matches in query
        for role in common_roles:
            if role in query_lower:
                return role
        
        # Check if we have role entities
        if "role" in entities and entities["role"]:
            # Try to extract just the role type from existing role entities
            for role_entry in entities["role"]:
                if ":" in role_entry:
                    role_parts = role_entry.split(":")
                    if role_parts[0].strip().lower() in common_roles:
                        return role_parts[0].strip()
                
                # Check for common role terms in the role entity
                for role in common_roles:
                    if role in role_entry.lower():
                        return role
        
        # Default fallback based on query intent
        if "who" in query_lower and "ceo" in query_lower:
            return "CEO"
        elif "who" in query_lower and "founder" in query_lower:
            return "founder"
        elif "who" in query_lower and "head" in query_lower:
            return "head"
        elif "who" in query_lower and "lead" in query_lower:
            return "leader"
        
        # No clear role found
        return None

    def _display_step_result(self, step_number, step_description, status, output):
        """
        Display a formatted result from a step execution.
        For internal use by the agent when executing steps.
        
        Args:
            step_number (int): Step number
            step_description (str): Description of the step
            status (str): Status of step execution (success/error)
            output (any): Output from the step
        """
        logger.debug(f"Step {step_number}: {step_description} - Status: {status}")
        
        # No visual output needed here since this is meant for internal display
        # The actual visual display is handled by the CLI or UI layer
        # This method exists to support potential console.print operations
        # that may have been removed from this version of the agent
        pass