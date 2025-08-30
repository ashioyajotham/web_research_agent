from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
import logging
from typing import List, Dict, Any, Optional
import json
from typing import Any
from tools.tool_registry import BaseTool
from utils.logger import get_logger

# Create a global console object
console = Console()
logger = get_logger(__name__)

class RichHandler(logging.Handler):
    """Custom logging handler that uses Rich formatting."""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.console = console
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level_name = record.levelname
            
            if record.levelno >= logging.ERROR:
                style = "bold red"
            elif record.levelno >= logging.WARNING:
                style = "yellow"
            elif record.levelno >= logging.INFO:
                style = "green"
            else:
                style = "blue"
            
            self.console.print(f"[{style}]{level_name}:[/] {msg}")
        except Exception:
            self.handleError(record)

def configure_logging():
    """Configure logging to use Rich formatting."""
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # Set up the Rich handler
    handler = RichHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Also configure specific loggers
    for logger_name in ["agent.agent", "tools.search", "tools.browser", "tools.code_generator"]:
        logger = logging.getLogger(logger_name)
        for h in list(logger.handlers):
            logger.removeHandler(h)
        logger.propagate = True  # Make sure it uses the root logger's handler

def display_title(title: str):
    """Display a title with decorative formatting."""
    console.print(Panel(f"[bold blue]{title}[/]", border_style="blue"))

def display_task_header(task_number: int, total_tasks: int, task_description: str):
    """Display a header for a task."""
    console.print("\n")
    console.rule(f"[bold yellow]Task {task_number}/{total_tasks}[/]")
    console.print(Panel(task_description, title="Current Task", border_style="yellow"))
    console.print("\n")

def create_progress_context():
    """Create a progress context with multiple status indicators."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[bold green]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console
    )

def display_plan(plan_steps: List[Dict[str, Any]]):
    """Display the plan steps in a table."""
    table = Table(title="Execution Plan", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Step Description")
    table.add_column("Tool")
    
    for i, step in enumerate(plan_steps, 1):
        table.add_row(
            str(i),
            step["description"],
            step["tool"]
        )
    
    console.print(table)
    console.print("\n")

def _to_jsonable(obj: Any):
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        if isinstance(obj, dict):
            return {str(k): _to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [_to_jsonable(x) for x in obj]
        if hasattr(obj, "__dict__"):
            return {k: _to_jsonable(v) for k, v in vars(obj).items()}
        return str(obj)

def display_result(step_number, description, status, output):
    console.print(f"\nStep {step_number}: {description}")
    console.print(f"Status: {status.upper()}")
    try:
        compact = output
        if isinstance(output, dict):
            preview = {}
            for k in ("title", "url", "query"):
                if k in output and output[k]:
                    preview[k] = output[k]
            if "results" in output and isinstance(output["results"], list):
                preview["results"] = len(output["results"])
            if "extracted_text" in output and isinstance(output["extracted_text"], str):
                preview["text_chars"] = len(output["extracted_text"])
            if "_binary" in output:
                preview["binary"] = bool(output["_binary"])
            if preview:
                compact = preview
        console.print_json(json.dumps(_to_jsonable(compact)))
    except Exception:
        try:
            console.print_json(json.dumps(_to_jsonable(output)))
        except Exception:
            console.print(str(output)[:500])

def display_completion_message(task_description: str, output_file: str):
    """Display a message indicating task completion."""
    console.print(Panel(
        f"[bold green]Task completed successfully![/]\n\n"
        f"Results for: {task_description}\n\n"
        f"Saved to: {output_file}",
        title="Task Complete",
        border_style="green"
    ))

class PresentationTool(BaseTool):
    """Tool for organizing and presenting information without writing code."""
    
    def __init__(self):
        super().__init__(name="present", description="Format and present results")

    def execute(self, parameters: Dict[str, Any], memory: Any) -> Dict[str, Any]:
        params = parameters or {}
        title = params.get("title", "Results")
        prompt = params.get("prompt", "")
        data = params.get("data")
        suppress_debug = bool(params.get("suppress_debug", False))

        if prompt:
            prompt = self._replace_placeholders(prompt, memory)

        # Minimal deterministic output: prefer explicit content if provided
        if isinstance(data, str) and data.strip():
            content = data.strip()
        else:
            content = prompt.strip() or "No data available for presentation"

        if suppress_debug:
            return {"status": "success", "output": {"final_text": content}}
        return {"status": "success", "output": {"title": title, "content": content}}

    def _replace_placeholders(self, text: str, memory: Any) -> str:
        return (text or "").replace("{coo_name}", getattr(memory, "coo_name", "{coo_name}"))

    # Stubs kept for future richer formatting
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
