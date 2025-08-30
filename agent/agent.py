import re
from urllib.parse import urlparse

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
    """Main agent class for web research."""
    
    def __init__(self):
        self.memory = Memory()
        self.planner = Planner()
        self.comprehension = Comprehension()
        self.registry = ToolRegistry()
        self.tool_registry = self.registry  # back-compat
        self.registry.register(SearchTool())
        self.registry.register(BrowserTool())
        self.registry.register(PresentationTool())

    def execute_task(self, task_description):
        # ...existing or planned logic...
        pass

    def _substitute_parameters(self, parameters, previous_results):
        params = dict(parameters or {})
        url = params.get("url")
        if isinstance(url, str):
            m = re.fullmatch(r"\{\{\s*search_result_(\d+)_url\s*\}\}", url.strip(), flags=re.I)
            if m:
                idx = int(m.group(1))
                results = getattr(self.memory, "search_results", None) or []
                if 0 <= idx < len(results):
                    params["url"] = results[idx].get("link") or results[idx].get("url")
                    return params
        if url and self._is_placeholder_url(url):
            resolved = self._resolve_url_from_search_results(previous_results)
            if resolved:
                params["url"] = resolved
        return params

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