from typing import Dict, Any, List, Optional
from .tool_registry import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)

class PresentationTool(BaseTool):
    """Tool for organizing and presenting information without writing code."""

    def __init__(self):
        super().__init__(name="present", description="Format and present results")

    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        params = parameters or {}
        title = params.get("title", "Results")
        prompt = params.get("prompt", "") or ""
        data = params.get("data")
        suppress_debug = bool(params.get("suppress_debug", False))

        # Basic placeholder replacement
        if prompt:
            prompt = self._replace_placeholders(prompt, memory)

        # Choose deterministic content
        if isinstance(data, str) and data.strip():
            content = data.strip()
        elif isinstance(data, dict) and "content" in data and isinstance(data["content"], str):
            content = data["content"].strip()
        else:
            content = prompt.strip() or "No data available for presentation"

        if suppress_debug:
            return {"status": "success", "output": {"final_text": content}}
        else:
            return {"status": "success", "output": {"title": title, "content": content}}

    def _replace_placeholders(self, text: str, memory: Any) -> str:
        # Minimal example; extend as needed
        text = (text or "")
        coo = getattr(memory, "coo_name", None)
        if coo:
            text = text.replace("{coo_name}", str(coo))
        return text

    # Stubs for future extension
    def _infer_entity_type(self, placeholder_text: str) -> str:
        return "generic"

    def _find_matching_entity(self, placeholder_text: str, entity_type: Optional[str], memory: Any) -> Optional[str]:
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        return []

    def _format_as_table(self, title: str, prompt: str, data: Any) -> str:
        return f"# {title}\n\n{prompt}"

# Back-compat alias for older imports
PresentTool = PresentationTool
