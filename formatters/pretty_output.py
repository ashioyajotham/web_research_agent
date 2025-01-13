from typing import Dict, Any
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

    def format_task_result(self, task: str, result: Dict[str, Any]):
        """Format a task result with better error handling and display"""
        # Create main panel
        task_panel = Panel(
            Text(task, style="bold blue"),
            title="Task",
            border_style="blue"
        )
        self.console.print(task_panel)

        # Status section with more detail
        status = "✅ Success" if result.get("success") else "❌ Failed"
        status_color = "green" if result.get("success") else "red"
        self.console.print(f"\n[{status_color}]Status: {status}[/{status_color}]")

        # Error handling with more context
        if error := result.get("error"):
            error_detail = error
            if "execution_time" in result:
                error_detail += f"\nExecution time: {result['execution_time']:.3f}s"
            if "confidence" in result:
                error_detail += f"\nConfidence: {result['confidence']:.2f}"
                
            error_panel = Panel(
                Text(error_detail, style="red"),
                title="Error Details",
                border_style="red"
            )
            self.console.print(error_panel)
            
            # Suggest possible solutions
            if "timeout" in error.lower():
                self.console.print("[yellow]Suggestion: Try increasing the timeout value or breaking down the task[/yellow]")
            elif "tool not found" in error.lower():
                self.console.print("[yellow]Suggestion: Verify tool configuration and dependencies[/yellow]")
            
            return

        # Metrics
        metrics_table = Table(title="Execution Metrics", show_header=True, header_style="bold cyan")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="white")
        
        metrics_table.add_row("Confidence", f"{result.get('confidence', 0.0):.2f}")
        metrics_table.add_row("Execution Time", f"{result.get('execution_time', 0.0):.3f}s")
        
        if steps_taken := result.get("steps_taken"):
            metrics_table.add_row("Steps Taken", str(steps_taken))
            
        self.console.print(metrics_table)

        # Output handling
        output = result.get("output", {})
        if output:
            if direct_answer := output.get("direct_answer"):
                self.console.print("\n[bold green]Answer:[/bold green]", direct_answer)
                if metadata := output.get("metadata"):
                    self.console.print("\n[dim]Additional Information:[/dim]")
                    for key, value in metadata.items():
                        self.console.print(f"[dim]{key}:[/dim] {value}")
            else:
                # First show specific answer if available
                if specific_answer := output.get("specific_answer"):
                    answer_panel = Panel(
                        Text(f"Answer: {specific_answer['value']}\n\n" +
                             f"Confidence: {specific_answer['confidence']:.2f}\n" +
                             (f"Source: {specific_answer['source']}\n" if specific_answer['source'] else "") +
                             (f"Context: {specific_answer['context']}" if specific_answer['context'] else ""),
                             style="green"),
                        title="Extracted Answer",
                        border_style="green"
                    )
                    self.console.print(answer_panel)
                    
                # Handle different output types
                if isinstance(output, dict) and "code" in output:
                    # Direct code object
                    code = output["code"]
                    if isinstance(code, dict):
                        code = code.get("code", "")  # Extract code from nested structure
                    if isinstance(code, str):
                        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                        self.console.print(Panel(syntax, title="Generated Code", border_style="green"))
                
                elif "code" in output:
                    # Code output
                    code = output["code"]
                    if isinstance(code, str):
                        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                        self.console.print(Panel(syntax, title="Generated Code", border_style="green"))
                
                elif "data" in output:
                    # Data analysis output
                    data_panel = Panel(
                        Text(str(output["data"]), style="white"),
                        title="Data Analysis Results",
                        border_style="cyan"
                    )
                    self.console.print(data_panel)
                
                elif "results" in output:
                    # Search/research results
                    if output["results"]:
                        results_table = Table(show_header=True, header_style="bold magenta")
                        results_table.add_column("Result", style="white", width=80)
                        results_table.add_column("Source", style="dim blue")
                        
                        for item in output["results"]:
                            if isinstance(item, dict):
                                title = item.get("title", "No Title")
                                link = item.get("link", "No Source")
                                snippet = item.get("snippet", "No Content")
                                results_table.add_row(f"{title}\n{snippet}", link)
                            else:
                                results_table.add_row(str(item), "N/A")
                                
                        self.console.print(results_table)
                    else:
                        self.console.print("[yellow]No results found[/yellow]")
                
                # Additional metadata if present
                if metadata := output.get("metadata"):
                    self.console.print("\n[bold cyan]Metadata:[/bold cyan]")
                    for key, value in metadata.items():
                        self.console.print(f"[dim]{key}:[/dim] {value}")

        # Execution metrics if present
        if metrics := result.get("execution_metrics"):
            self.console.print("\n[bold cyan]Execution Details:[/bold cyan]")
            for key, value in metrics.items():
                if key != "error":  # Skip error messages here as they're shown above
                    self.console.print(f"[dim]{key}:[/dim] {value}")
