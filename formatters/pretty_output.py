from typing import Dict, List
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

class PrettyFormatter:
    def __init__(self):
        self.console = Console()

    def format_task_result(self, task: str, result: Dict) -> None:
        """Format a single task result"""
        self.console.print(Panel(f"[bold blue]Task:[/bold blue] {task}\n", title="📋 Task Details"))
        
        if not result.get("success", False):
            self.console.print("[red]❌ Task Failed[/red]")
            self.console.print(f"Error: {result.get('error', 'Unknown error')}")
            return

        # Handle different types of results
        output = result.get("output", {})
        
        if "data" in output and output.get("type") == "time_series":
            self._format_time_series(output["data"])
        elif "formatted_answer" in result:
            self._format_direct_answer(result["formatted_answer"])
        elif isinstance(output.get("results"), list):
            self._format_search_results(output["results"])
        
        if "execution_time" in result:
            self.console.print(f"\n⏱️ [dim]Execution time: {result['execution_time']:.2f} seconds[/dim]")

    def _format_time_series(self, data: List[Dict]) -> None:
        """Format time series data in a table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date")
        table.add_column("Value")
        
        for entry in data:
            table.add_row(
                str(entry.get("date", "")),
                str(entry.get("value", ""))
            )
        
        self.console.print(Panel(table, title="📈 Time Series Data"))

    def _format_direct_answer(self, answer: Dict) -> None:
        """Format a direct answer with its source"""
        self.console.print(Panel(
            f"[bold green]Answer:[/bold green] {answer['answer']}\n"
            f"[dim]Source: {answer['source']}[/dim]",
            title="💡 Direct Answer"
        ))

    def _format_search_results(self, results: List[Dict]) -> None:
        """Format search results in a readable way"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Title")
        table.add_column("Summary")
        table.add_column("URL", style="dim")
        
        for result in results[:5]:  # Show top 5 results
            table.add_row(
                result.get("title", ""),
                result.get("snippet", "")[:100] + "...",
                result.get("link", "")
            )
        
        self.console.print(Panel(table, title="🔍 Search Results"))
