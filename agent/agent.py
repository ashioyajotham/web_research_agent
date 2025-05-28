from .memory import Memory
from .planner import Planner
from .comprehension import Comprehension
from tools.tool_registry import ToolRegistry
from utils.formatters import format_results
from utils.logger import get_logger
import re
import time

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
            if isinstance(value, str):
                # Dynamic placeholder detection using multiple patterns
                resolved_value = self._resolve_dynamic_placeholders(value, previous_results)
                substituted[key] = resolved_value
            else:
                substituted[key] = value
        
        return substituted

    def _resolve_dynamic_placeholders(self, value, previous_results):
        """
        Dynamically resolve various types of placeholders in parameter values.
        
        Args:
            value (str): Parameter value that may contain placeholders
            previous_results (list): Results from previous steps
            
        Returns:
            str: Resolved value with placeholders substituted
        """
        original_value = value
        
        # Pattern 1: Explicit URL placeholders like {search_result_X_url}
        url_pattern = re.search(r'\{search_result_(\d+)_url\}', value)
        if url_pattern:
            index = int(url_pattern.group(1))
            url = self._get_search_result_url(index, previous_results)
            return url
        
        # Pattern 2: Natural language placeholders [Insert URL from search result X]
        natural_pattern = re.search(r'\[.*?(?:url|link).*?(?:search\s*result|result)\s*(\d+).*?\]', value, re.IGNORECASE)
        if natural_pattern:
            index = int(natural_pattern.group(1))
            url = self._get_search_result_url(index, previous_results)
            return url
        
        # Pattern 3: Generic URL requests
        generic_url_patterns = [
            r'\[urls?\s+(?:of|from).*?\]',
            r'\[.*?website.*?urls?\]',
            r'\[.*?link.*?\]',
            r'https?://[a-zA-Z\s]+from\s+previous\s+step',
            r'https?://[a-zA-Z\s]+from\s+[a-zA-Z\s]+results?'
        ]
        
        for pattern in generic_url_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                # Extract the best available URL from previous results
                url = self._extract_best_url_from_results(previous_results, value)
                if url:
                    return url
        
        # Pattern 4: Generic data requests
        data_patterns = [
            r'results?\s+from\s+previous\s+step',
            r'data\s+from\s+(?:search|previous)',
            r'information\s+from\s+(?:search|results?)'
        ]
        
        for pattern in data_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                # Return structured data instead of treating as URL
                data = self._extract_relevant_data_from_results(previous_results, value)
                return data
        
        # If no patterns match, return original value
        return original_value

    def _extract_best_url_from_results(self, previous_results, context):
        """
        Extract the most relevant URL from previous results based on context.
        
        Args:
            previous_results (list): Results from previous steps
            context (str): Context of what type of URL is needed
            
        Returns:
            str: Best matching URL or fallback URL
        """
        # Priority order for URL extraction
        url_candidates = []
        
        # Check memory first for stored search results
        if hasattr(self.memory, 'search_results') and self.memory.search_results:
            for result in self.memory.search_results:
                if isinstance(result, dict) and 'link' in result:
                    url_candidates.append(result['link'])
        
        # Check previous step results
        for result in reversed(previous_results):
            if result.get("status") == "success" and "output" in result:
                output = result["output"]
                
                # Extract URLs from search results
                if isinstance(output, dict) and "search_results" in output:
                    search_results = output["search_results"]
                    if isinstance(search_results, list):
                        for search_result in search_results:
                            if isinstance(search_result, dict) and "link" in search_result:
                                url_candidates.append(search_result["link"])
                
                # Extract URLs from content
                elif isinstance(output, dict) and "content" in output:
                    content = output["content"]
                    urls = re.findall(r'https?://[^\s<>"]+', content)
                    url_candidates.extend(urls)
        
        # Filter URLs based on context
        filtered_urls = self._filter_urls_by_context(url_candidates, context)
        
        if filtered_urls:
            return filtered_urls[0]
        elif url_candidates:
            return url_candidates[0]
        else:
            # Return a safe fallback URL that won't cause network errors
            return "https://example.com/placeholder-url"

    def _filter_urls_by_context(self, urls, context):
        """
        Filter URLs based on the context of what's being requested.
        
        Args:
            urls (list): List of candidate URLs
            context (str): Context string describing what type of URL is needed
            
        Returns:
            list: Filtered URLs sorted by relevance
        """
        context_lower = context.lower()
        scored_urls = []
        
        for url in urls:
            score = 0
            url_lower = url.lower()
            
            # Context-based scoring
            if 'linkedin' in context_lower and 'linkedin.com' in url_lower:
                score += 10
            elif 'organization' in context_lower or 'company' in context_lower:
                if any(domain in url_lower for domain in ['.org', '.com', 'about', 'company']):
                    score += 5
            elif 'official' in context_lower or 'government' in context_lower:
                if any(domain in url_lower for domain in ['.gov', '.edu', 'official']):
                    score += 8
            elif 'news' in context_lower:
                if any(domain in url_lower for domain in ['reuters', 'bbc', 'cnn', 'news']):
                    score += 6
            
            # General quality indicators
            if 'wikipedia' in url_lower:
                score += 3
            if url_lower.startswith('https://'):
                score += 1
            
            # Avoid certain problematic domains
            if any(bad in url_lower for bad in ['example.com', 'placeholder', 'localhost']):
                score -= 10
            
            scored_urls.append((score, url))
        
        # Sort by score (highest first) and return URLs
        scored_urls.sort(key=lambda x: x[0], reverse=True)
        return [url for score, url in scored_urls if score > 0]

    def _extract_relevant_data_from_results(self, previous_results, context):
        """
        Extract relevant data from previous results when URL is not appropriate.
        
        Args:
            previous_results (list): Results from previous steps
            context (str): Context of what data is needed
            
        Returns:
            str: Relevant data or summary
        """
        relevant_data = []
        
        for result in reversed(previous_results):
            if result.get("status") == "success" and "output" in result:
                output = result["output"]
                
                # Extract search results data
                if isinstance(output, dict) and "search_results" in output:
                    search_results = output["search_results"]
                    if isinstance(search_results, list):
                        for i, search_result in enumerate(search_results[:5]):  # Limit to top 5
                            if isinstance(search_result, dict):
                                title = search_result.get("title", "")
                                link = search_result.get("link", "")
                                snippet = search_result.get("snippet", "")
                                relevant_data.append(f"Result {i+1}: {title} ({link}) - {snippet}")
                
                # Extract content data
                elif isinstance(output, dict) and "content" in output:
                    content = output["content"]
                    if isinstance(content, str) and len(content) > 50:
                        # Summarize long content
                        summary = content[:500] + "..." if len(content) > 500 else content
                        relevant_data.append(f"Content: {summary}")
        
        if relevant_data:
            return "\n".join(relevant_data[:3])  # Limit to top 3 most relevant pieces
        else:
            return "No relevant data found in previous results"

    def _format_results(self, task_description, plan, results):
        """
        Universal results formatting that adapts to any task type.
        """
        logger.info("Starting adaptive results formatting")
        
        # Analyze the task to understand what type of answer is expected
        task_analysis = self._analyze_task_for_answer_type(task_description)
        
        # Synthesize the direct answer from collected data
        final_answer = self._synthesize_final_answer(task_description, task_analysis, results)
        
        # Add execution context if there were issues
        execution_summary = self._generate_execution_context(results)
        if execution_summary:
            final_answer += execution_summary
        
        return final_answer

    def _generate_execution_context(self, results):
        """Generate execution context only when needed"""
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        if error_count > len(results) * 0.3:  # More than 30% errors
            context = f"\n\n## Research Notes\n\n"
            context += f"Research completed with {error_count} of {len(results)} steps encountering issues. "
            context += "Some information may be incomplete.\n"
            return context
        
        return ""

    def _analyze_task_for_answer_type(self, task_description):
        """
        Dynamically analyze any task to determine expected answer structure.
        Uses pattern recognition and semantic analysis instead of hardcoded rules.
        """
        task_analysis = {
            "primary_intent": self._extract_primary_intent(task_description),
            "expected_output_structure": self._infer_output_structure(task_description),
            "key_information_targets": self._identify_information_targets(task_description),
            "success_indicators": self._define_success_indicators(task_description),
            "synthesis_strategy": self._determine_synthesis_strategy(task_description)
        }
        
        return task_analysis

    def _extract_primary_intent(self, task_description):
        """
        Extract the core intent from any task description using semantic patterns.
        """
        # Intent mapping based on action verbs and question patterns
        intent_patterns = {
            "find_specific": [r"find\s+(the\s+)?name", r"who\s+is", r"what\s+is\s+the\s+name", r"identify\s+the"],
            "compile_list": [r"compile\s+.*list", r"list\s+of", r"find\s+.*companies", r"gather"],
            "extract_content": [r"extract.*statements", r"get\s+quotes", r"find\s+what.*said"],
            "calculate_value": [r"calculate", r"by\s+what\s+percentage", r"determine.*ratio"],
            "compare_analyze": [r"compare", r"analyze.*difference", r"versus"],
            "explain_describe": [r"explain", r"describe", r"how", r"why"],
            "download_process": [r"download", r"extract.*from.*dataset", r"process.*data"]
        }
        
        task_lower = task_description.lower()
        for intent, patterns in intent_patterns.items():
            if any(re.search(pattern, task_lower) for pattern in patterns):
                return intent
        
        return "general_research"

    def _infer_output_structure(self, task_description):
        """
        Infer what the final answer should look like based on the task.
        """
        task_lower = task_description.lower()
        
        # Structure inference based on linguistic cues
        if any(word in task_lower for word in ["list", "compile", "companies", "items"]):
            return "structured_list"
        elif any(word in task_lower for word in ["name", "who", "what is"]):
            return "specific_answer"
        elif any(word in task_lower for word in ["percentage", "ratio", "calculate"]):
            return "numerical_result"
        elif any(word in task_lower for word in ["statements", "quotes", "said"]):
            return "content_collection"
        elif any(word in task_lower for word in ["timeline", "over time", "series"]):
            return "temporal_sequence"
        else:
            return "comprehensive_report"

    def _identify_information_targets(self, task_description):
        """
        Identify what specific information needs to be extracted.
        Uses NER-like approach to find key targets dynamically.
        """
        targets = []
        
        # Extract quoted criteria or specific requirements
        quoted_criteria = re.findall(r'"([^"]*)"', task_description)
        targets.extend(quoted_criteria)
        
        # Extract entities mentioned in the task
        entities = self.comprehension.extract_entities(task_description)
        for entity_type, entity_list in entities.items():
            targets.extend([str(e) for e in entity_list])
        
        # Extract numerical targets
        numerical_targets = re.findall(r'(\d+(?:\.\d+)?)\s*([%€$£¥]|\w+)', task_description)
        targets.extend([f"{num} {unit}" for num, unit in numerical_targets])
        
        # Extract temporal targets
        temporal_targets = re.findall(r'(20\d{2}|19\d{2})', task_description)
        targets.extend(temporal_targets)
        
        return list(set(targets))  # Remove duplicates

    def _define_success_indicators(self, task_description):
        """
        Define what constitutes a successful answer for any task.
        """
        indicators = []
        
        # Extract quantitative requirements
        numbers = re.findall(r'(\d+)', task_description)
        if numbers:
            indicators.append(f"minimum_{numbers[0]}_items")
        
        # Extract qualitative requirements
        if "unique" in task_description.lower():
            indicators.append("uniqueness_verified")
        if "source" in task_description.lower():
            indicators.append("sources_provided")
        if "criteria" in task_description.lower():
            indicators.append("criteria_met")
        
        return indicators

    def _determine_synthesis_strategy(self, task_description):
        """
        Determine how to synthesize collected information into a final answer.
        """
        primary_intent = self._extract_primary_intent(task_description)
        
        strategy_map = {
            "find_specific": "extract_and_verify",
            "compile_list": "aggregate_and_filter", 
            "extract_content": "collect_and_organize",
            "calculate_value": "compute_and_explain",
            "compare_analyze": "contrast_and_synthesize",
            "explain_describe": "research_and_elaborate",
            "download_process": "acquire_and_transform"
        }
        
        return strategy_map.get(primary_intent, "comprehensive_synthesis")

    def _synthesize_final_answer(self, task_description, task_analysis, results):
        """
        Universal answer synthesis engine that adapts to any task type.
        """
        logger.info(f"Synthesizing answer using {task_analysis['synthesis_strategy']} strategy")
        
        # Extract all available data
        collected_data = self._extract_comprehensive_data(results)
        
        # Apply appropriate synthesis strategy
        synthesis_method = getattr(self, f"_synthesize_{task_analysis['synthesis_strategy']}", 
                                  self._synthesize_comprehensive_synthesis)
        
        return synthesis_method(task_description, task_analysis, collected_data)

    def _extract_comprehensive_data(self, results):
        """
        Extract all types of data from results in a unified structure.
        """
        data = {
            "search_results": [],
            "web_content": [],
            "entities": {},
            "numerical_data": [],
            "temporal_data": [],
            "text_content": [],
            "urls": [],
            "structured_data": []
        }
        
        for result in results:
            if result.get("status") == "success" and "output" in result:
                output = result["output"]
                
                # Extract search results
                if isinstance(output, dict) and "search_results" in output:
                    data["search_results"].extend(output["search_results"] or [])
                
                # Extract web content
                elif isinstance(output, dict) and "content" in output:
                    content_item = {
                        "url": output.get("url", "unknown"),
                        "title": output.get("title", ""),
                        "content": output["content"],
                        "extract_type": output.get("extract_type", "web")
                    }
                    data["web_content"].append(content_item)
                    data["text_content"].append(output["content"])
                
                # Extract other data types
                if isinstance(output, dict):
                    # URLs
                    if "url" in output:
                        data["urls"].append(output["url"])
                    
                    # Any structured data
                    if any(key in output for key in ["data", "results", "items", "entries"]):
                        data["structured_data"].append(output)
    
        # Extract entities from memory
        if hasattr(self.memory, 'extracted_entities') and self.memory.extracted_entities:
            data["entities"] = self.memory.extracted_entities
        
        # Extract numerical and temporal data from all text
        all_text = " ".join(data["text_content"])
        data["numerical_data"] = self._extract_numerical_patterns(all_text)
        data["temporal_data"] = self._extract_temporal_patterns(all_text)
        
        return data

    def _extract_numerical_patterns(self, text):
        """Extract numerical information patterns from text."""
        patterns = {
            "percentages": re.findall(r'(\d+(?:\.\d+)?)\s*%', text),
            "monetary": re.findall(r'[€$£¥]\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([bmk]?)', text, re.IGNORECASE),
            "years": re.findall(r'(20\d{2}|19\d{2})', text),
            "quantities": re.findall(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s+(\w+)', text)
        }
        return patterns

    def _extract_temporal_patterns(self, text):
        """Extract temporal information from text."""
        patterns = {
            "dates": re.findall(r'(\w+\s+\d{1,2},?\s+20\d{2})', text),
            "years": re.findall(r'(20\d{2})', text),
            "periods": re.findall(r'(from\s+\d{4}\s+to\s+\d{4})', text),
            "recent": re.findall(r'(last\s+\w+|recent|latest)', text, re.IGNORECASE)
        }
        return patterns

    # Synthesis strategies - each handles different types of tasks
    def _synthesize_extract_and_verify(self, task_description, task_analysis, collected_data):
        """For tasks that need to find specific information (names, facts, etc.)"""
        answer = f"# {task_description}\n\n"
        
        # Look for the specific information being requested
        targets = task_analysis["key_information_targets"]
        findings = {}
        
        # Search through all content for targets
        for target in targets:
            findings[target] = self._search_for_target(target, collected_data)
        
        # Extract the most likely answer
        primary_finding = self._identify_primary_finding(findings, task_description)
        
        if primary_finding:
            answer += f"## Answer\n\n{primary_finding}\n\n"
            answer += f"## Source Verification\n\n"
            answer += self._format_source_verification(primary_finding, collected_data)
        else:
            answer += "## Research Results\n\n"
            answer += "The specific information requested could not be definitively identified from available sources.\n\n"
            answer += self._format_available_findings(findings)
        
        return answer

    def _synthesize_aggregate_and_filter(self, task_description, task_analysis, collected_data):
        """For tasks that need to compile lists with criteria"""
        answer = f"# {task_description}\n\n"
        
        # Extract potential list items
        candidates = self._extract_list_candidates(collected_data, task_analysis)
        
        # Apply filtering based on task criteria
        filtered_items = self._apply_dynamic_filters(candidates, task_description)
        
        # Format as appropriate list
        if filtered_items:
            answer += self._format_dynamic_list(filtered_items, task_analysis)
        else:
            answer += "## Research Results\n\n"
            answer += "No items meeting all specified criteria could be identified from the available research.\n\n"
            answer += self._format_research_summary(collected_data)
        
        return answer

    def _synthesize_collect_and_organize(self, task_description, task_analysis, collected_data):
        """For tasks that need to extract and organize content (quotes, statements, etc.)"""
        answer = f"# {task_description}\n\n"
        
        # Extract content items
        content_items = self._extract_content_items(collected_data, task_analysis)
        
        # Organize and format
        if content_items:
            answer += self._format_content_collection(content_items, task_analysis)
        else:
            answer += "## Research Results\n\n"
            answer += "The requested content could not be extracted from available sources.\n\n"
            answer += self._format_alternative_findings(collected_data)
        
        return answer

    def _synthesize_comprehensive_synthesis(self, task_description, task_analysis, collected_data):
        """Default synthesis for complex or unclear tasks"""
        answer = f"# {task_description}\n\n"
        
        # Provide comprehensive findings organized by relevance
        answer += "## Research Findings\n\n"
        
        # Organize findings by information type
        if collected_data["entities"]:
            answer += self._format_entity_findings(collected_data["entities"])
        
        if collected_data["numerical_data"]:
            answer += self._format_numerical_findings(collected_data["numerical_data"])
        
        if collected_data["web_content"]:
            answer += self._format_content_findings(collected_data["web_content"][:3])  # Top 3
        
        answer += f"\n## Research Summary\n\n"
        answer += self._generate_research_summary(collected_data, task_analysis)
        
        return answer

    # Helper methods for dynamic processing
    def _search_for_target(self, target, collected_data):
        """Search for a specific target across all collected data"""
        findings = []
        
        # Search in web content
        for content_item in collected_data["web_content"]:
            content = content_item["content"].lower()
            if target.lower() in content:
                # Extract context around the target
                context = self._extract_context(content, target.lower())
                findings.append({
                    "target": target,
                    "context": context,
                    "source": content_item["url"],
                    "type": "web_content"
                })
        
        # Search in search results
        for result in collected_data["search_results"]:
            snippet = result.get("snippet", "").lower()
            title = result.get("title", "").lower()
            if target.lower() in snippet or target.lower() in title:
                findings.append({
                    "target": target,
                    "context": result.get("snippet", ""),
                    "source": result.get("link", ""),
                    "type": "search_result"
                })
        
        return findings

    def _extract_context(self, text, target, window=100):
        """Extract context around a target in text"""
        pos = text.find(target.lower())
        if pos == -1:
            return ""
        
        start = max(0, pos - window)
        end = min(len(text), pos + len(target) + window)
        
        return text[start:end].strip()

    def _identify_primary_finding(self, findings, task_description):
        """Identify the most relevant finding for the task"""
        all_findings = []
        for target, target_findings in findings.items():
            all_findings.extend(target_findings)
        
        if not all_findings:
            return None
        
        # Score findings based on relevance
        scored_findings = []
        for finding in all_findings:
            score = self._score_finding_relevance(finding, task_description)
            scored_findings.append((score, finding))
        
        # Return the highest scored finding
        scored_findings.sort(key=lambda x: x[0], reverse=True)
        return scored_findings[0][1]["context"] if scored_findings else None

    def _score_finding_relevance(self, finding, task_description):
        """Score a finding's relevance to the task"""
        score = 0
        
        # Higher score for web content vs search snippets
        if finding["type"] == "web_content":
            score += 5
        
        # Score based on context quality
        context_length = len(finding["context"])
        if 50 < context_length < 500:  # Optimal length
            score += 3
        
        # Score based on source quality
        source = finding["source"].lower()
        if any(domain in source for domain in [".gov", ".edu", "official"]):
            score += 4
        elif any(domain in source for domain in ["wikipedia", "reuters", "bbc"]):
            score += 2
        
        return score

    def _extract_list_candidates(self, collected_data, task_analysis):
        """Extract potential list items from collected data"""
        candidates = set()
        
        # From entities
        for entity_type, entities in collected_data["entities"].items():
            for entity in entities:
                candidates.add(str(entity))
        
        # From structured patterns in text
        all_text = " ".join(collected_data["text_content"])
        
        # Extract list-like patterns
        list_patterns = [
            r'(?:^|\n)\s*[-•*]\s*([^\n]+)',  # Bullet points
            r'(?:^|\n)\s*\d+\.\s*([^\n]+)',  # Numbered lists
            r'([A-Z][a-zA-Z\s&]+(?:Group|AG|SE|Ltd|Inc|Corporation|Company))',  # Company names
        ]
        
        for pattern in list_patterns:
            matches = re.findall(pattern, all_text, re.MULTILINE)
            candidates.update(matches)
        
        return list(candidates)

    def _apply_dynamic_filters(self, candidates, task_description):
        """Apply filters based on task description"""
        filtered = []
        
        # Extract filter criteria from task description
        filters = self._extract_filter_criteria(task_description)
        
        for candidate in candidates:
            if self._meets_criteria(candidate, filters):
                filtered.append(candidate)
        
        return filtered

    def _extract_filter_criteria(self, task_description):
        """Extract filtering criteria from task description"""
        criteria = {}
        
        # Geographic filters
        if "eu" in task_description.lower():
            criteria["geography"] = "eu"
        
        # Industry filters
        if "motor vehicle" in task_description.lower():
            criteria["industry"] = "automotive"
        
        # Size filters
        revenue_match = re.search(r'€(\d+)([bm])', task_description.lower())
        if revenue_match:
            amount = int(revenue_match.group(1))
            unit = revenue_match.group(2)
            criteria["revenue"] = f"{amount}{unit}"
        
        # Time filters
        years = re.findall(r'(20\d{2})', task_description)
        if years:
            criteria["years"] = years
        
        return criteria

    def _meets_criteria(self, candidate, filters):
        """Check if a candidate meets the filter criteria"""
        # Basic implementation - can be enhanced
        return True  # For now, accept all candidates

    # Formatting methods
    def _format_dynamic_list(self, items, task_analysis):
        """Format items as an appropriate list structure"""
        output = "## Results\n\n"
        
        if task_analysis["expected_output_structure"] == "structured_list":
            output += "| Item | Details | Status |\n"
            output += "|------|---------|--------|\n"
            for item in items[:20]:  # Limit to 20
                output += f"| {item} | Found in research | Requires verification |\n"
        else:
            for i, item in enumerate(items[:20], 1):
                output += f"{i}. {item}\n"
        
        output += f"\n**Total found:** {len(items)}\n\n"
        return output

    def _format_content_collection(self, content_items, task_analysis):
        """Format collected content items"""
        output = "## Collected Content\n\n"
        
        for i, item in enumerate(content_items, 1):
            output += f"### Item {i}\n\n"
            output += f"**Content:** {item['content']}\n\n"
            output += f"**Source:** {item['source']}\n\n"
        
        return output

    def _format_source_verification(self, primary_finding, collected_data):
        """Format source verification for findings"""
        output = "Sources that support this finding:\n\n"
        
        # Look for sources that mention the finding
        for content_item in collected_data["web_content"]:
            if primary_finding.lower() in content_item["content"].lower():
                output += f"- {content_item['url']} ({content_item.get('title', 'Web Content')})\n"
        
        for result in collected_data["search_results"]:
            if primary_finding.lower() in result.get("snippet", "").lower():
                output += f"- {result.get('link', '')} ({result.get('title', 'Search Result')})\n"
        
        return output

    def _format_available_findings(self, findings):
        """Format available findings when primary finding is not found"""
        output = "Available information found:\n\n"
        
        for target, target_findings in findings.items():
            if target_findings:
                output += f"**{target}:**\n"
                for finding in target_findings[:3]:  # Top 3
                    output += f"- {finding['context'][:100]}... (Source: {finding['source']})\n"
                output += "\n"
        
        return output

    def _format_research_summary(self, collected_data):
        """Format a summary of research conducted"""
        output = "Research conducted:\n\n"
        output += f"- Analyzed {len(collected_data['search_results'])} search results\n"
        output += f"- Extracted content from {len(collected_data['web_content'])} web pages\n"
        output += f"- Identified {sum(len(entities) for entities in collected_data['entities'].values())} entities\n"
        
        return output

    def _extract_content_items(self, collected_data, task_analysis):
        """Extract specific content items based on task analysis"""
        content_items = []
        
        # Extract based on the task's information targets
        targets = task_analysis.get("key_information_targets", [])
        
        # Look for content in web pages
        for content_item in collected_data["web_content"]:
            content = content_item["content"]
            
            # Look for quotes or statements
            quote_patterns = [
                r'"([^"]{20,300})"',  # Quoted text
                r'said[^.]*"([^"]{20,300})"',  # Said + quote
                r'stated[^.]*"([^"]{20,300})"',  # Stated + quote
            ]
            
            for pattern in quote_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if it's relevant to our targets
                    match_lower = match.lower()
                    if any(target.lower() in match_lower for target in targets) or not targets:
                        content_items.append({
                            "content": match.strip(),
                            "source": content_item["url"],
                            "type": "quote"
                        })
        
        # Look for statements in search results
        for result in collected_data["search_results"]:
            snippet = result.get("snippet", "")
            if len(snippet) > 50:
                content_items.append({
                    "content": snippet,
                    "source": result.get("link", ""),
                    "type": "snippet"
                })
        
        return content_items[:10]  # Limit to 10 items

    def _format_alternative_findings(self, collected_data):
        """Format alternative findings when requested content isn't found"""
        output = "Related information found:\n\n"
        
        # Show entities that were found
        if collected_data["entities"]:
            output += "**Entities identified:**\n"
            for entity_type, entities in collected_data["entities"].items():
                if entities:
                    output += f"- {entity_type.title()}: {', '.join(str(e) for e in entities[:5])}\n"
            output += "\n"
        
        # Show numerical data if any
        if collected_data["numerical_data"]:
            output += "**Numerical data found:**\n"
            for data_type, values in collected_data["numerical_data"].items():
                if values:
                    output += f"- {data_type.title()}: {', '.join(values[:5])}\n"
            output += "\n"
        
        return output

    def _format_entity_findings(self, entities):
        """Format entity findings"""
        output = "### Entities Identified\n\n"
        
        for entity_type, entity_list in entities.items():
            if entity_list:
                output += f"**{entity_type.title()}:** {', '.join(str(e) for e in entity_list[:10])}\n"
        
        output += "\n"
        return output

    def _format_numerical_findings(self, numerical_data):
        """Format numerical findings"""
        output = "### Numerical Data\n\n"
        
        for data_type, values in numerical_data.items():
            if values:
                # Convert tuples to strings if needed
                formatted_values = []
                for value in values[:10]:
                    if isinstance(value, tuple):
                        # Handle different tuple structures
                        if len(value) == 2:
                            formatted_values.append(f"{value[0]} {value[1]}")
                        else:
                            formatted_values.append(" ".join(str(v) for v in value))
                    else:
                        formatted_values.append(str(value))
                
                output += f"**{data_type.title()}:** {', '.join(formatted_values)}\n"
        
        output += "\n"
        return output

    def _format_content_findings(self, web_content):
        """Format content findings"""
        output = "### Key Content\n\n"
        
        for i, content_item in enumerate(web_content, 1):
            content = content_item["content"]
            # Truncate long content
            summary = content[:300] + "..." if len(content) > 300 else content
            output += f"**Source {i}:** {content_item['url']}\n"
            output += f"{summary}\n\n"
        
        return output

    def _generate_research_summary(self, collected_data, task_analysis):
        """Generate a summary of the research conducted"""
        summary = f"Research completed using {task_analysis['synthesis_strategy']} strategy.\n\n"
        
        # Count what was found
        search_count = len(collected_data["search_results"])
        content_count = len(collected_data["web_content"])
        entity_count = sum(len(entities) for entities in collected_data["entities"].values())
        
        summary += f"**Research scope:**\n"
        summary += f"- {search_count} search results analyzed\n"
        summary += f"- {content_count} web pages processed\n"
        summary += f"- {entity_count} entities identified\n\n"
        
        # Add success indicators
        success_indicators = task_analysis.get("success_indicators", [])
        if success_indicators:
            summary += f"**Success criteria:** {', '.join(success_indicators)}\n"
        
        return summary

    # Enhanced parameter resolution methods
    def _get_search_result_url(self, index, previous_results):
        """
        Enhanced URL retrieval with comprehensive fallback strategies.
        """
        logger.debug(f"Attempting to get URL at index {index}")
        
        # Strategy 1: Check memory's stored search results
        if hasattr(self.memory, 'search_results') and self.memory.search_results:
            search_results = self.memory.search_results
            if isinstance(search_results, list) and index < len(search_results):
                result = search_results[index]
                if isinstance(result, dict) and 'link' in result:
                    url = result['link']
                    if self._is_valid_url(url):
                        logger.debug(f"Found URL in memory at index {index}: {url}")
                        return url
        
        # Strategy 2: Search in previous results for search_results data
        for result in reversed(previous_results):
            if result.get("status") == "success" and "output" in result:
                output = result["output"]
                if isinstance(output, dict) and "search_results" in output:
                    search_results = output["search_results"]
                    if isinstance(search_results, list) and index < len(search_results):
                        search_result = search_results[index]
                        if isinstance(search_result, dict) and "link" in search_result:
                            url = search_result["link"]
                            if self._is_valid_url(url):
                                logger.debug(f"Found URL in previous results at index {index}: {url}")
                                return url
        
        # Strategy 3: Get any valid URL from search results (ignore index)
        all_urls = self._extract_all_urls_from_results(previous_results)
        if all_urls:
            # Use modulo to safely get a URL even if index is out of range
            safe_index = index % len(all_urls)
            url = all_urls[safe_index]
            logger.info(f"Using URL at safe index {safe_index} instead of {index}: {url}")
            return url
        
        # Strategy 4: Return a safe placeholder that tools can handle gracefully
        placeholder_url = "https://example.com/search-result-not-found"
        logger.warning(f"No valid URLs found, returning placeholder: {placeholder_url}")
        return placeholder_url

    def _is_valid_url(self, url):
        """Check if a URL is valid and not a placeholder."""
        if not isinstance(url, str) or not url.strip():
            return False
        
        # Check for valid URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return False
        
        # Reject common placeholder patterns
        placeholder_patterns = [
            r'example\.com',
            r'placeholder',
            r'from\s+previous\s+step',
            r'from\s+.+\s+results?',
            r'insert\s+url',
            r'website\s+urls?'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True

    def _extract_all_urls_from_results(self, previous_results):
        """Extract all valid URLs from previous results."""
        all_urls = []
        
        for result in previous_results:
            if result.get("status") == "success" and "output" in result:
                output = result["output"]
                
                # Extract from search results
                if isinstance(output, dict) and "search_results" in output:
                    search_results = output["search_results"]
                    if isinstance(search_results, list):
                        for search_result in search_results:
                            if isinstance(search_result, dict) and "link" in search_result:
                                url = search_result["link"]
                                if self._is_valid_url(url):
                                    all_urls.append(url)
            
            # Extract URLs from content using regex
            elif isinstance(output, dict) and "content" in output:
                content = output["content"]
                if isinstance(content, str):
                    urls = re.findall(r'https?://[^\s<>"]+', content)
                    for url in urls:
                        if self._is_valid_url(url):
                            all_urls.append(url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls

    def _can_execute_step(self, step_index, previous_results):
        """Check if a step can be executed based on previous results."""
        # Always allow first step
        if step_index == 0:
            return True, "First step"
        
        # Check if any critical previous steps failed
        critical_failures = 0
        for i, result in enumerate(previous_results):
            if result.get("status") == "error":
                critical_failures += 1
        
        # Allow execution if not too many failures
        if critical_failures < len(previous_results) * 0.7:  # Allow if less than 70% failed
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
        
        # Extract entities using comprehension module
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
        
        return True, "Step completed"  # Default to success for now

    def _refine_query_with_entities(self, original_query, entities):
        """Refine a search query using discovered entities."""
        if not entities:
            return original_query
        
        # Add relevant entities to query
        additional_terms = []
        for entity_type, entity_list in entities.items():
            if entity_type in ["organization", "person", "location"] and entity_list:
                # Add the first few entities
                for entity in entity_list[:2]:
                    entity_str = str(entity).strip()
                    if entity_str and entity_str not in original_query:
                        additional_terms.append(f'"{entity_str}"')
        
        if additional_terms:
            refined_query = f"{original_query} {' '.join(additional_terms)}"
            return refined_query
        
        return original_query

    def _display_step_result(self, step_number, description, status, output):
        """Display the result of a step execution."""
        # This method handles displaying step results
        # For now, just log the results
        logger.info(f"Step {step_number} ({description}): {status}")
        if isinstance(output, dict) and "results" in output:
            result_count = len(output["results"]) if output["results"] else 0
            logger.info(f"  Found {result_count} search results")
        elif isinstance(output, dict) and "content" in output:
            content_length = len(str(output["content"])) if output["content"] else 0
            logger.info(f"  Extracted {content_length} characters of content")