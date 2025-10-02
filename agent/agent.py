import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .memory import Memory
from .planner import Planner
from .comprehension import Comprehension
from tools.tool_registry import ToolRegistry
from tools.search import SearchTool
from tools.browser import BrowserTool
from tools.presentation_tool import PresentationTool
from utils.formatters import format_results
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class EvaluationResult:
    """Results of evaluating a research step or phase."""
    confidence: float  # 0.0 to 1.0
    completeness: float  # 0.0 to 1.0
    relevance: float  # 0.0 to 1.0
    overall_score: float  # 0.0 to 1.0
    missing_entities: List[str]
    quality_issues: List[str]
    suggested_actions: List[str]
    should_replan: bool

class WebResearchAgent:
    """Main agent class to coordinate the research process with adaptive evaluation."""
    
    def __init__(self, config_path=None):
        self.memory = Memory()
        self.planner = Planner()
        self.comprehension = Comprehension()
        self.registry = ToolRegistry()
        # Back-compat alias
        self.tool_registry = self.registry
        
        # Result evaluation state
        self.evaluation_history = []
        self.execution_metadata = {
            "step_results": [],
            "discovered_entities": {},
            "quality_scores": []
        }

        # Explicitly register tools with their designated names for clarity and correctness.
        self.tool_registry.register_tool("search", SearchTool())
        self.tool_registry.register_tool("browser", BrowserTool())
        self.tool_registry.register_tool("present", PresentationTool())

    def evaluate_step_result(self, step_result: Dict[str, Any], 
                           expected_entities: List[str],
                           research_objective: str) -> EvaluationResult:
        """Evaluate the result of a single research step."""
        # Extract content from step result
        content = self._extract_content_from_result(step_result)
        
        # Evaluate different dimensions
        confidence = self._assess_confidence(content, step_result)
        completeness = self._assess_completeness(content, expected_entities, research_objective)
        relevance = self._assess_relevance(content, research_objective)
        
        # Overall score is weighted average
        overall_score = (confidence * 0.3 + completeness * 0.4 + relevance * 0.3)
        
        # Identify issues and suggestions
        missing_entities = self._identify_missing_entities(content, expected_entities)
        quality_issues = self._identify_quality_issues(content, step_result)
        suggested_actions = self._generate_action_suggestions(
            overall_score, missing_entities, quality_issues, research_objective
        )
        
        # Decide if replanning is needed
        should_replan = overall_score < 0.6 or len(missing_entities) > len(expected_entities) / 2
        
        result = EvaluationResult(
            confidence=confidence,
            completeness=completeness,
            relevance=relevance,
            overall_score=overall_score,
            missing_entities=missing_entities,
            quality_issues=quality_issues,
            suggested_actions=suggested_actions,
            should_replan=should_replan
        )
        
        # Store for learning
        self.evaluation_history.append({
            "timestamp": f"{len(self.evaluation_history)}",
            "objective": research_objective,
            "result": result,
            "content_length": len(content) if content else 0
        })
        
        return result
    
    def _extract_content_from_result(self, result: Dict[str, Any]) -> str:
        """Extract text content from various result formats."""
        if not result:
            return ""
        
        # Handle different result structures
        if "output" in result:
            output = result["output"]
            if isinstance(output, dict):
                return output.get("extracted_text", "") or output.get("content", "") or str(output)
            elif isinstance(output, str):
                return output
        
        if "extracted_text" in result:
            return result["extracted_text"]
        
        if "content" in result:
            return result["content"]
        
        return str(result)
    
    def _assess_confidence(self, content: str, result: Dict[str, Any]) -> float:
        """Assess confidence in the result quality."""
        if not content:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Content length indicates substance
        if len(content) > 500:
            confidence += 0.2
        elif len(content) > 200:
            confidence += 0.1
        
        # Check for error indicators
        error_indicators = ["error", "not found", "access denied", "404", "blocked"]
        if any(indicator in content.lower() for indicator in error_indicators):
            confidence -= 0.3
        
        # Check for quality indicators
        quality_indicators = ["published", "source", "date", "author", "official"]
        quality_score = sum(1 for indicator in quality_indicators if indicator in content.lower())
        confidence += min(quality_score * 0.05, 0.2)
        
        # Check result status
        if result.get("status") == "success":
            confidence += 0.1
        elif result.get("status") == "error":
            confidence -= 0.4
        
        return max(0.0, min(1.0, confidence))
    
    def _assess_completeness(self, content: str, expected_entities: List[str], objective: str) -> float:
        """Assess how completely the content addresses the research objective."""
        if not content:
            return 0.0
        
        content_lower = content.lower()
        objective_lower = objective.lower()
        
        # Check for expected entities
        entity_coverage = 0.0
        if expected_entities:
            found_entities = sum(1 for entity in expected_entities 
                               if entity.lower() in content_lower)
            entity_coverage = found_entities / len(expected_entities)
        
        # Check for objective keywords
        objective_words = [word for word in objective_lower.split() 
                          if len(word) > 3 and word not in ["find", "identify", "locate"]]
        if objective_words:
            keyword_coverage = sum(1 for word in objective_words 
                                 if word in content_lower) / len(objective_words)
        else:
            keyword_coverage = 0.5
        
        # Weighted average
        completeness = entity_coverage * 0.6 + keyword_coverage * 0.4
        
        return max(0.0, min(1.0, completeness))
    
    def _assess_relevance(self, content: str, objective: str) -> float:
        """Assess how relevant the content is to the research objective."""
        if not content:
            return 0.0
        
        content_lower = content.lower()
        objective_lower = objective.lower()
        
        # Simple relevance based on keyword overlap
        objective_keywords = set(word for word in objective_lower.split() if len(word) > 3)
        content_words = set(word for word in content_lower.split() if len(word) > 3)
        
        if not objective_keywords:
            return 0.5
        
        overlap = len(objective_keywords.intersection(content_words))
        relevance = overlap / len(objective_keywords)
        
        # Boost for exact phrase matches
        if any(phrase in content_lower for phrase in objective_lower.split()):
            relevance += 0.2
        
        return max(0.0, min(1.0, relevance))
    
    def _identify_missing_entities(self, content: str, expected_entities: List[str]) -> List[str]:
        """Identify which expected entities are missing from the content."""
        if not content:
            return expected_entities.copy()
        
        content_lower = content.lower()
        missing = []
        
        for entity in expected_entities:
            entity_lower = entity.lower()
            # Check for entity or related terms
            if entity_lower not in content_lower:
                # Check for variations
                if entity_lower == "person" and not any(term in content_lower for term in ["ceo", "president", "director", "manager"]):
                    missing.append(entity)
                elif entity_lower == "organization" and not any(term in content_lower for term in ["company", "corporation", "firm"]):
                    missing.append(entity)
                elif entity_lower not in ["person", "organization"]:
                    missing.append(entity)
        
        return missing
    
    def _identify_quality_issues(self, content: str, result: Dict[str, Any]) -> List[str]:
        """Identify quality issues with the content."""
        issues = []
        
        if not content:
            issues.append("No content extracted")
            return issues
        
        # Check for various quality issues
        if len(content) < 100:
            issues.append("Content too short")
        
        if "error" in content.lower():
            issues.append("Contains error messages")
        
        if content.count(".") < 3:  # Very few sentences
            issues.append("Insufficient detail")
        
        # Check for blocked/denied content
        blocked_indicators = ["access denied", "blocked", "403", "401", "subscription required"]
        if any(indicator in content.lower() for indicator in blocked_indicators):
            issues.append("Access restrictions")
        
        return issues
    
    def _generate_action_suggestions(self, score: float, missing_entities: List[str], 
                                   issues: List[str], objective: str) -> List[str]:
        """Generate specific action suggestions based on evaluation."""
        suggestions = []
        
        if score < 0.4:
            suggestions.append("Consider changing search strategy entirely")
        elif score < 0.7:
            suggestions.append("Refine search terms for better results")
        
        if missing_entities:
            suggestions.append(f"Add entity-focused search for: {', '.join(missing_entities)}")
        
        if "Content too short" in issues:
            suggestions.append("Try alternative sources or expand search scope")
        
        if "Access restrictions" in issues:
            suggestions.append("Find alternative sources without access restrictions")
        
        return suggestions

    def _substitute_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute placeholders in tool parameters with values from memory.
        """
        substituted_params = {}
        if not parameters:
            return {}

        for key, value in parameters.items():
            if isinstance(value, str):
                # This regex now correctly looks for single-brace placeholders like {search_result_0_url}
                match = re.search(r"\{search_result_(\d+)_url\}", value)
                if match:
                    try:
                        index = int(match.group(1))
                        if self.memory.search_results and len(self.memory.search_results) > index:
                            url = self.memory.search_results[index].get("link")
                            if url:
                                substituted_params[key] = url
                                logger.info(f"Substituted placeholder with URL: {url}")
                            else:
                                substituted_params[key] = None
                                logger.warning(f"Search result {index} found but has no 'link' key.")
                        else:
                            substituted_params[key] = None
                            logger.warning(f"Could not find search result with index {index} in memory.")
                    except (ValueError, IndexError) as e:
                        logger.error(f"Failed to substitute parameter for value {value}: {e}")
                        substituted_params[key] = None
                else:
                    # If no placeholder is found, use the original value
                    substituted_params[key] = value
            else:
                # If the value is not a string, use it as is
                substituted_params[key] = value
        
        return substituted_params

    async def run(self, task_description: str):
        """Main execution loop for the agent."""
        logger.info(f"Starting research task: {task_description}")

        # 1. Comprehension: Analyze the task
        analysis = self.comprehension.analyze_task(task_description)
        logger.info(f"Task analysis complete. Synthesis strategy: {analysis['synthesis_strategy']}")

        # 2. Planning: Create a plan - pass the entire analysis dict
        plan = self.planner.create_plan(task_description, analysis)
        logger.info("Execution plan created.")
        
        # 3. Execution: Run the plan steps
        execution_results = []
        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                logger.error(f"Tool '{step.tool_name}' not found in registry.")
                execution_results.append({"step": i+1, "description": step.description, "status": "error", "output": f"Tool '{step.tool_name}' not found."})
                continue

            # Substitute placeholders like {search_result_0_url} with actual values from memory
            params = self._substitute_parameters(step.parameters)
            
            # For the final presentation step, pass all previous results
            if step.tool_name == "present":
                params['results'] = execution_results

            try:
                output = tool.execute(params, self.memory)
                status = "success"
                # Store search results in memory for later steps
                if step.tool_name == "search" and isinstance(output, dict):
                    self.memory.search_results = output.get("results", [])
            except Exception as e:
                output = f"Error executing tool {step.tool_name}: {e}"
                status = "error"
                logger.error(output)

            result_data = {"step": i + 1, "description": step.description, "status": status, "output": output}
            execution_results.append(result_data)

            # New: Process content for synthesis after each relevant step
            if step.tool_name == "browser" and status == "success":
                content = self._extract_content_from_result(result_data)
                url = output.get("url", "")
                if content:
                    logger.info(f"Processing content from {url} for synthesis.")
                    self.comprehension.process_content(content, url)

        # 4. Synthesis: Generate the final answer
        logger.info("Synthesizing final answer from processed content.")
        synthesized_answer = self.comprehension.synthesize_final_answer(task_description)
        logger.info(f"Synthesized answer: {synthesized_answer}")

        # 5. Check for failure
        if not synthesized_answer or not synthesized_answer.get("statements"):
            logger.error("Task failed: Could not synthesize a final answer.")
            synthesized_answer["answer"] = "Could not synthesize a direct answer from the available information."

        # 6. Formatting: Generate the final report
        final_output = self._format_results(task_description, plan, execution_results, synthesized_answer)
        return self._clean_present_output(final_output)

    def _resolve_url_from_search_results(self, previous_results):
        """Pick a URL from latest successful search results."""
        # Prefer memory if set during main loop
        if getattr(self.memory, "search_results", None):
            for item in self.memory.search_results:
                link = item.get("link") or item.get("url")
                if self._is_valid_url(link):
                    return link
        # Fallback: scan previous tool outputs
        for r in reversed(previous_results or []):
            out = r.get("output")
            if isinstance(out, dict):
                results = out.get("results") or out.get("search_results") or []
                for item in results:
                    link = item.get("link") or item.get("url")
                    if self._is_valid_url(link):
                        return link
        return None

    def _is_valid_url(self, url):
        try:
            if not url:
                return False
            u = urlparse(url)
            return u.scheme in ("http", "https") and bool(u.netloc)
        except Exception:
            return False

    def _is_placeholder_url(self, url):
        if not isinstance(url, str):
            return False
        t = url.strip().lower()
        return (t in ("{from_search}", "from_search", "${from_search}")
                or ("${" in t and "}" in t))

    def _display_step_result(self, step_number, description, status, output):
        """Safe, compact console output (not used by main UI but kept for completeness)."""
        print(f"\nStep {step_number}: {description}")
        print(f"Status: {status.upper()}")
        try:
            if isinstance(output, dict):
                title = output.get("title") or ""
                url = output.get("url") or ""
                text = output.get("extracted_text") or output.get("content") or ""
                items = output.get("results") or output.get("items") or []
                binary = output.get("_binary", False)
                text_len = len(text) if isinstance(text, str) else 0
                if title:
                    print(f'title: {title[:120]}...')
                if url:
                    print(f'url: {url}')
                if items:
                    print(f'items: {len(items)}')
                if text_len:
                    print(f'text_chars: {text_len}')
                if binary:
                    print('note: binary content omitted')
            elif isinstance(output, str):
                preview = output.replace("\n", " ")[:400]
                ellipsis = "..." if len(output) > 400 else ""
                print(f'text_preview: {preview}{ellipsis}')
            else:
                print(f'output_type: {type(output).__name__}')
        except Exception as e:
            print(f"display_error: {e}")

    def _format_results(self, task_description, plan, results, synthesized_answer=None):
        """Delegate to unified formatter for consistent, task-agnostic outputs."""
        try:
            return format_results(task_description, plan, results, synthesized_answer)
        except Exception as e:
            logger.error(f"Formatting failed: {e}")
            # Minimal fallback with sources if available
            lines = [f"## Result for: {task_description}\n"]
            for r in results or []:
                if isinstance(r.get("output"), dict):
                    url = r["output"].get("url")
                    title = r["output"].get("title")
                    if url or title:
                        lines.append(f"- {title or ''} {url or ''}".strip())
            return "\n".join(lines) or "No result."

    def _clean_present_output(self, text: str) -> str:
        return (text or "").strip()

    def _synthesize_comprehensive_synthesis(self, task_description, results):
        # Kept for future use; current flow uses utils.formatters
        pass