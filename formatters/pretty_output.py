from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.syntax import Syntax

class PrettyFormatter:
    def __init__(self):
        self.console = Console()

    def format_task_result(self, task: str, result: Dict[str, Any]) -> None:
        """Format and display task results with improved readability"""
        # Show task header
        self.console.print(f"\n[bold cyan]Task:[/bold cyan] {task}")
        
        if not result.get("success"):
            self.console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")
            return

        output = result.get("output", {})
        
        # Handle different output types
        if "direct_answer" in output:
            self._format_direct_answer(output)
        elif "chronological_summary" in output:
            self._format_research_timeline(output)
        elif "code" in output:
            self._format_code_output(output)
        elif "content" in output:
            self._format_blog_content(output)
        
        # Show confidence
        confidence = result.get("confidence", 0)
        color = "green" if confidence > 0.8 else "yellow" if confidence > 0.5 else "red"
        self.console.print(f"\n[{color}]Confidence: {confidence:.0%}[/{color}]")

    def _format_direct_answer(self, output: Dict[str, Any]) -> None:
        """Format direct answers with supporting info"""
        if output.get("direct_answer"):
            self.console.print(Panel(
                f"[bold green]{output['direct_answer']}[/bold green]",
                title="Answer",
                border_style="green"
            ))
        
        if "results" in output and output["results"]:
            self._show_sources(output["results"][:3])

    def _format_research_timeline(self, output: Dict[str, Any]) -> None:
        """Format research results as a timeline"""
        # Show latest developments first
        if output.get("latest_developments"):
            table = Table(title="Latest Developments", show_header=True)
            table.add_column("Date", style="cyan")
            table.add_column("Development", style="white")
            
            for event in output["latest_developments"]:
                table.add_row(
                    event.get("date", "N/A"),
                    event.get("event", "").strip()
                )
            self.console.print(table)
        
        # Show major milestones
        if output.get("major_milestones"):
            self.console.print("\n[bold]Major Milestones:[/bold]")
            for milestone in output["major_milestones"]:
                self.console.print(f"• {milestone.get('event', '')}")
        
        # Show sources
        if output.get("sources"):
            self._show_sources(output["sources"])

    def _format_code_output(self, output: Dict[str, Any]) -> None:
        """Format code output with syntax highlighting"""
        if output.get("code"):
            # Show code with syntax highlighting
            self.console.print("\n[bold]Implementation:[/bold]")
            syntax = Syntax(
                output["code"],
                "python",
                theme="monokai",
                line_numbers=True
            )
            self.console.print(syntax)
            
            # Show explanation if available
            if output.get("explanation"):
                self.console.print("\n[bold]Explanation:[/bold]")
                self.console.print(Markdown(output["explanation"]))

    def _format_blog_content(self, output: Dict[str, Any]) -> None:
        """Format blog/article content with Markdown"""
        if output.get("content"):
            content = output["content"]
            if isinstance(content, dict):
                content = content.get("content", "")
            self.console.print(Markdown(content))

    def _show_sources(self, sources: List[Dict[str, Any]]) -> None:
        """Display reference sources"""
        self.console.print("\n[bold]Sources:[/bold]")
        for i, source in enumerate(sources, 1):
            if isinstance(source, dict):
                title = source.get("title", source.get("source", "Unknown"))
                url = source.get("link", source.get("url", ""))
                self.console.print(f"{i}. {title}")
                if url:
                    self.console.print(f"   [dim]{url}[/dim]")
            elif isinstance(source, (list, tuple)) and len(source) == 2:
                title, url = source
                self.console.print(f"{i}. {title}")
                self.console.print(f"   [dim]{url}[/dim]")
