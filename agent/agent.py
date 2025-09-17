import re
from urllib.parse import urlparse
from typing import Dict, Any

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

class WebResearchAgent:
    """Main agent class to coordinate the research process."""
    
    def __init__(self, config_path=None):
        self.memory = Memory()
        self.planner = Planner()
        self.comprehension = Comprehension()
        self.registry = ToolRegistry()
        # Back-compat alias
        self.tool_registry = self.registry

        # Explicitly register tools with their designated names for clarity and correctness.
        self.tool_registry.register_tool("search", SearchTool())
        self.tool_registry.register_tool("browser", BrowserTool())
        self.tool_registry.register_tool("present", PresentationTool())

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
        logger.info(f"Task analysis complete. Synthesis strategy: {analysis.synthesis_strategy}")

        # 2. Planning: Create a plan
        plan = self.planner.create_plan(task_description, analysis.synthesis_strategy, analysis.information_targets)
        logger.info("Execution plan created.")
        
        # 3. Execution: Run the plan steps
        execution_results = []
        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")
            tool = self.tool_registry.get_tool(step.tool)
            if not tool:
                logger.error(f"Tool '{step.tool}' not found in registry.")
                execution_results.append({"step": i+1, "status": "error", "output": f"Tool '{step.tool}' not found."})
                continue

            # Substitute placeholders like {search_result_0_url} with actual values from memory
            params = self._substitute_parameters(step.parameters)
            
            # For the final presentation step, pass all previous results
            if step.tool == "present":
                params['results'] = execution_results

            try:
                output = await tool.execute(**params)
                status = "success"
                # Store search results in memory for later steps
                if step.tool == "search" and isinstance(output, dict):
                    self.memory.search_results = output.get("results", [])
            except Exception as e:
                output = f"Error executing tool {step.tool}: {e}"
                status = "error"
                logger.error(output)

            execution_results.append({"step": i+1, "description": step.description, "status": status, "output": output})

        # 4. Formatting: Generate the final report
        final_output = self._format_results(task_description, plan, execution_results)
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

    def _format_results(self, task_description, plan, results):
        """Delegate to unified formatter for consistent, task-agnostic outputs."""
        try:
            return format_results(task_description, plan, results)
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