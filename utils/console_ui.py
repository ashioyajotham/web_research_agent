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

# Create a global console object
console = Console()

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

def display_result(step_number: int, step_description: str, status: str, output: Any):
    """Display a result from a step in a formatted way."""
    if status == "success":
        header_style = "green"
        status_display = "[bold green]SUCCESS[/]"
    else:
        header_style = "red"
        status_display = "[bold red]ERROR[/]"
    
    console.print(f"\n[bold {header_style}]Step {step_number}: {step_description}[/]")
    console.print(f"Status: {status_display}")
    
    if status == "error":
        console.print(Panel(str(output), title="Error", border_style="red"))
        return
    
    if isinstance(output, dict):
        if "error" in output:
            console.print(Panel(output["error"], title="Error", border_style="red"))
        elif "content" in output:  # Browser results
            console.print(f"[bold]Source:[/] {output.get('title', 'Web content')} ({output.get('url', 'unknown URL')})")
            md = Markdown(output['content'][:500] + ("..." if len(output['content']) > 500 else ""))
            console.print(md)
        elif "results" in output:  # Search results
            console.print(f"[bold]Search Query:[/] {output.get('query', 'Unknown query')}")
            console.print(f"[bold]Found:[/] {output.get('result_count', 0)} results")
            
            results_table = Table(show_header=True)
            results_table.add_column("#", style="dim")
            results_table.add_column("Title")
            results_table.add_column("Link", style="blue")
            
            for i, result in enumerate(output.get('results', []), 1):
                results_table.add_row(
                    str(i),
                    result.get('title', 'No title'),
                    result.get('link', '#')
                )
            
            console.print(results_table)
        else:
            # Generic dictionary output
            console.print_json(json.dumps(output))
    elif isinstance(output, str):
        if output.startswith("```"):
            # This is a code block, try to extract the language
            import re
            lang_match = re.match(r"```(\w+)", output)
            language = lang_match.group(1) if lang_match else "text"
            code = re.sub(r"```\w*\n", "", output).replace("```", "")
            console.print(Syntax(code, language, theme="monokai"))
        else:
            console.print(output)
    else:
        console.print(str(output))

def display_completion_message(task_description: str, output_file: str):
    """Display a message indicating task completion."""
    console.print(Panel(
        f"[bold green]Task completed successfully![/]\n\n"
        f"Results for: {task_description}\n\n"
        f"Saved to: {output_file}",
        title="Task Complete",
        border_style="green"
    ))
