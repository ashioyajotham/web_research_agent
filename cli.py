#!/usr/bin/env python3
import os
import sys
import re
import click
from pathlib import Path
import time

# Add the parent directory to sys.path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now we can import from our modules using absolute imports
from utils.logger import get_logger, set_log_level  # Changed from relative import
from agent.agent import WebResearchAgent
from config.config import get_config, init_config
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

logger = get_logger(__name__)
console = Console()

# ASCII Art Banner
BANNER = """
[bold blue]╭──────────────────────────────────────────────────────────────╮
│       [bold cyan]██╗    ██╗███████╗██████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/bold cyan]       │
│       [bold cyan]██║    ██║██╔════╝██╔══██╗   ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/bold cyan]       │
│       [bold cyan]██║ █╗ ██║█████╗  ██████╔╝   ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   [/bold cyan]       │
│       [bold cyan]██║███╗██║██╔══╝  ██╔══██╗   ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   [/bold cyan]       │
│       [bold cyan]╚███╔███╔╝███████╗██████╔╝   ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   [/bold cyan]       │
│       [bold cyan] ╚══╝╚══╝ ╚══════╝╚═════╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   [/bold cyan]       │
[bold blue]│                                                            │
│  [bold green]Research Assistant AI - Navigating the web for answers[/bold green]  │
╰──────────────────────────────────────────────────────────────╯[/bold blue]
"""

def display_banner():
    """Display the ASCII art banner."""
    console.print(BANNER)
    console.print("\n[dim]Version 1.0.4 - Type 'help' for commands[/dim]\n")
    console.print("[dim]Built by [bold magenta]Ashioya Jotham Victor[/bold magenta][/dim]\n")

def display_intro():
    """Display introduction info."""
    table = Table(box=box.ROUNDED, show_header=False, border_style="blue")
    table.add_column(justify="center", style="bold cyan")
    table.add_row("[bold green]Available commands:[/bold green]")
    table.add_row("search [query] - Research a topic")
    table.add_row("batch [file] - Process multiple tasks from a file")
    table.add_row("config - Configure API keys and settings")
    table.add_row("shell - Start interactive mode")
    
    console.print(Panel(table, border_style="blue", title="Web Research Agent"))

def _sanitize_filename(query):
    """Sanitize a query string to create a valid filename."""
    # First, strip surrounding quotes if present
    if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
        query = query[1:-1]
    
    # Remove quotes and other invalid filename characters more aggressively
    invalid_chars = '"\'\\/:*?<>|'
    sanitized = ''.join(c for c in query if c not in invalid_chars)
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Normalize multiple underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    
    # Limit length and trim whitespace
    sanitized = sanitized.strip()[:30]
    
    # Don't return an empty string
    if not sanitized:
        sanitized = "research_result"
        
    return sanitized

def _extract_preview_sections(content, max_length=2000):
    """Extract key sections from research results for preview."""
    # Get the plan section
    plan_match = re.search(r'(?i)## Plan\s+(.*?)(?:##|$)', content, re.DOTALL)
    plan = plan_match.group(1).strip() if plan_match else ""
    
    # Get the results/findings section (might be called Results, Findings, or Summary)
    results_match = re.search(r'(?i)## (?:Results|Findings|Summary)\s+(.*?)(?:##|$)', content, re.DOTALL)
    results = results_match.group(1).strip() if results_match else ""
    
    # If we don't find a specific section, try to find any content after the plan
    if not results:
        # Look for any section after the plan
        after_plan_match = re.search(r'(?i)## Plan.*?(?:##\s+(.*?)(?:##|$))', content, re.DOTALL)
        if after_plan_match:
            results = after_plan_match.group(1).strip()
    
    # Create preview with both plan and results (if found)
    preview = "## Plan\n\n" + plan[:max_length//3]  # 1/3 of space for plan
    
    if results:
        preview += "\n\n## Results\n\n" + results[:max_length*2//3]  # 2/3 of space for results
    else:
        # If no results section found, use more of the full content
        preview += "\n\n## Content\n\n" + content[len(plan)+100:max_length*2//3] if len(content) > len(plan)+100 else ""
    
    # Add ellipsis if we had to trim content
    if len(preview) < len(content):
        preview += "\n\n..."
        
    return preview

@click.group()
@click.version_option(version="1.0.1")
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging")
def cli(verbose):
    """Web Research Agent - An intelligent tool for web-based research tasks."""
    # Set log level based on verbose flag
    import logging
    
    if verbose:
        set_log_level(logging.INFO)  # Using the non-relative import
        
    # We'll keep the banner display only for the main CLI, but skip it for subcommands
    if len(sys.argv) == 1 or sys.argv[1] not in ['shell', 'search', 'batch', 'config']:
        display_banner()

@cli.command()
@click.argument('query', required=True)
@click.option('--output', '-o', default="results", help="Output directory for results")
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'html']), default="markdown", 
              help="Output format for results")
def search(query, output, format):
    """Execute a single research task with the given query."""
    os.makedirs(output, exist_ok=True)
    
    console.print(Panel(f"[bold cyan]Researching:[/bold cyan] {query}", border_style="blue"))
    
    # Set output format in config
    config = get_config()
    config.update('output_format', format)
    
    # Initialize agent and execute task
    agent = WebResearchAgent()
    
    # Create rich progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Researching...", total=100)
        
        # We don't have granular progress info, so use time-based updates
        for i in range(10):
            # Execute the research task on the first iteration
            if i == 0:
                result = agent.execute_task(query)
            progress.update(task, completed=i * 10)
            if i < 9:  # Don't sleep on the last iteration
                time.sleep(0.2)  # Just for visual effect
        
        # Complete the progress
        progress.update(task, completed=100)
    
    # Save result to file with sanitized filename
    filename = f"{output}/result_{_sanitize_filename(query)}.{_get_file_extension(format)}"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
    
    console.print(Panel(f"[bold green]✓[/bold green] Research complete! Results saved to [bold cyan]{filename}[/bold cyan]", 
                        border_style="green"))
    
    # Show a preview of the results
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if format == 'markdown':
                # Use our smart preview extraction
                preview = _extract_preview_sections(content)
                console.print(Panel(Markdown(preview), 
                             title="Research Results Preview", border_style="cyan"))
            else:
                # Use the default syntax highlighting for non-markdown formats
                syntax = Syntax(content[:1000] + "..." if len(content) > 1000 else content, 
                                format, theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Results Preview", border_style="cyan"))
    except Exception as e:
        console.print(f"[yellow]Could not display preview: {str(e)}[/yellow]")

@cli.command()
@click.argument('file', type=click.Path(exists=True), required=True)
@click.option('--output', '-o', default="results", help="Output directory for results")
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'html']), default="markdown",
              help="Output format for results")
def batch(file, output, format):
    """Execute multiple research tasks from a file (one task per line)."""
    os.makedirs(output, exist_ok=True)
    
    # Set output format in config
    config = get_config()
    config.update('output_format', format)
    
    # Read tasks from file
    with open(file, 'r', encoding='utf-8') as f:
        tasks = [line.strip() for line in f if line.strip()]
    
    # Initialize agent
    agent = WebResearchAgent()
    
    console.print(Panel(f"[bold cyan]Processing {len(tasks)} research tasks from {file}[/bold cyan]", border_style="blue"))
    
    # Create table for results summary
    results_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    results_table.add_column("#", style="dim")
    results_table.add_column("Task", style="cyan")
    results_table.add_column("Status", style="green")
    results_table.add_column("Output File")
    
    # Process each task with a progress display
    for i, task in enumerate(tasks):
        console.print(f"\n[bold blue]Task {i+1}/{len(tasks)}:[/bold blue] {task[:80]}...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            research_task = progress.add_task(f"[cyan]Researching task {i+1}/{len(tasks)}...", total=100)
            
            # Execute the task
            for j in range(10):
                if j == 0:
                    try:
                        result = agent.execute_task(task)
                        status = "✓ Complete"
                    except Exception as e:
                        console.print(f"[bold red]Error:[/bold red] {str(e)}")
                        result = f"Error: {str(e)}"
                        status = "✗ Failed"
                progress.update(research_task, completed=j * 10)
                if j < 9:
                    time.sleep(0.1)  # Just for visual effect
            
            progress.update(research_task, completed=100)
        
        # Save result to file
        task_filename = f"task_{i+1}_{task[:20].replace(' ', '_').replace('?', '').lower()}.{_get_file_extension(format)}"
        output_path = os.path.join(output, task_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        
        # Add to results table
        results_table.add_row(
            str(i+1), 
            task[:50] + "..." if len(task) > 50 else task,
            status,
            output_path
        )
    
    console.print("\n[bold green]✓ All tasks completed![/bold green]")
    console.print(results_table)

@cli.command()
@click.option('--api-key', '-k', help="Set Gemini API key")
@click.option('--serper-key', '-s', help="Set Serper API key")
@click.option('--timeout', '-t', type=int, help="Set request timeout in seconds")
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'html']), help="Set default output format")
@click.option('--show', is_flag=True, help="Show current configuration")
def config(api_key, serper_key, timeout, format, show):
    """Configure the Web Research Agent."""
    config = get_config()
    
    if show:
        click.echo("Current configuration:")
        for key, value in config.items():
            if key.endswith('_api_key') and value:
                value = f"{value[:4]}...{value[-4:]}"
            click.echo(f"  {key}: {value}")
        return
    
    # Prompt for missing API keys interactively
    if not api_key and not config.get("gemini_api_key"):
        api_key = click.prompt("Gemini API key is missing, please enter it", hide_input=True)
        config.update('gemini_api_key', api_key)
        click.echo("✅ Updated Gemini API key")
    elif api_key:
        config.update('gemini_api_key', api_key)
        click.echo("✅ Updated Gemini API key")
    
    if not serper_key and not config.get("serper_api_key"):
        serper_key = click.prompt("Serper API key is missing, please enter it", hide_input=True)
        config.update('serper_api_key', serper_key)
        click.echo("✅ Updated Serper API key")
    elif serper_key:
        config.update('serper_api_key', serper_key)
        click.echo("✅ Updated Serper API key")
    
    if timeout:
        config.update('timeout', timeout)
        click.echo(f"✅ Updated request timeout to {timeout} seconds")
    
    if format:
        config.update('output_format', format)
        click.echo(f"✅ Updated default output format to {format}")
    
    # Verify required configuration again after interactive prompts
    required_keys = ['gemini_api_key', 'serper_api_key']
    missing_keys = [key for key in required_keys if not config.get(key)]
    if missing_keys:
        click.echo(f"⚠️  Still missing: {', '.join(missing_keys)}")
        click.echo("Please set these with 'web-research config --api-key=\"...\" --serper-key=\"...\"'")

@cli.command()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging")
def shell(verbose):
    """Start an interactive shell for research tasks."""
    # Set log level based on verbose flag
    import logging
    
    if verbose:
        set_log_level(logging.INFO)  # Using the non-relative import
    
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.styles import Style
    
    # Create history file path
    history_file = Path.home() / ".web_research_history"
    
    # Create command completer with context-aware suggestions
    commands = WordCompleter([
        'search', 'exit', 'help', 'config', 'clear', 'version',
        'search "What is machine learning"',
        'search "Latest advances in AI"',
        'search "How to implement neural networks"'
    ], ignore_case=True)
    
    # Set up proper styling for prompt
    style = Style.from_dict({
        'prompt': 'ansicyan bold',
    })
    
    # Initialize session with proper styling
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=commands,
        style=style,
        message="web-research> "  # Plain text prompt, styling applied via style dict
    )
    
    # Initialize agent
    agent = WebResearchAgent()
    
    # Display banner (we'll keep this since shell can be called directly)
    display_banner()
    
    console.print("\n[bold cyan]Interactive Shell Started[/bold cyan]")
    console.print("[dim]Type commands to interact with the agent. Try 'help' for assistance.[/dim]\n")
    
    while True:
        try:
            user_input = session.prompt("web-research> ")
            
            if not user_input.strip():
                continue
            
            if user_input.lower() in ('exit', 'quit'):
                console.print("[yellow]Exiting Web Research Agent...[/yellow]")
                break
            
            if user_input.lower() == 'clear':
                console.clear()
                display_banner()
                continue
                
            if user_input.lower() == 'version':
                console.print("[cyan]Web Research Agent v1.0.1[/cyan]")
                continue
            
            if user_input.lower() == 'help':
                help_table = Table(box=box.ROUNDED)
                help_table.add_column("Command", style="cyan")
                help_table.add_column("Description", style="green")
                
                help_table.add_row("search <query>", "Research a topic")
                help_table.add_row("config", "Show/modify configuration")
                help_table.add_row("clear", "Clear the screen")
                help_table.add_row("version", "Show version")
                help_table.add_row("exit/quit", "Exit the shell")
                
                console.print(Panel(help_table, title="Help", border_style="blue"))
                continue
            
            if user_input.lower() == 'config':
                # Show configuration
                config = get_config()
                config_table = Table(box=box.ROUNDED)
                config_table.add_column("Setting", style="cyan")
                config_table.add_column("Value", style="green")
                
                for key, value in config.items():
                    if key.endswith('_api_key') and value:
                        masked_value = f"{value[:4]}...{value[-4:]}"
                        config_table.add_row(key, masked_value)
                    else:
                        config_table.add_row(key, str(value))
                
                console.print(Panel(config_table, title="Configuration", border_style="blue"))
                continue
            
            # Default to search if no command specified
            if not user_input.lower().startswith('search '):
                query = user_input
            else:
                query = user_input[7:]
            
            # Strip surrounding quotes from the query
            if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
                # Only strip quotes for filename, leave original query for searching
                filename_query = query[1:-1]
            else:
                filename_query = query

            if query:
                console.print(Panel(f"[bold cyan]Researching:[/bold cyan] {query}", border_style="blue"))
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Researching...", total=100)
                    
                    # We don't have granular progress info, so fake it
                    result = None
                    for i in range(10):
                        if i == 0:  # Actually do the work on the first iteration
                            try:
                                result = agent.execute_task(query)
                            except Exception as e:
                                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                                break
                        
                        progress.update(task, completed=i * 10)
                        if i < 9:
                            time.sleep(0.2)  # Just for visual feedback
                    
                    # Complete the progress
                    if result:
                        progress.update(task, completed=100)
                
                # Only proceed if we got results
                if result:
                    # Save result to file in results directory
                    os.makedirs("results", exist_ok=True)
                    filename = f"results/result_{_sanitize_filename(filename_query)}.md"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result)
                    
                    console.print(f"[bold green]✓[/bold green] Research complete! Results saved to [cyan]{filename}[/cyan]")

                    
                    # Show a preview of the results
                    try:
                        preview = _extract_preview_sections(result)
                        console.print(Panel(Markdown(preview), title="Results Preview", border_style="cyan"))
                    except Exception as e:
                        console.print(f"[yellow]Could not display preview: {str(e)}[/yellow]")
                else:
                    console.print("[bold red]✗[/bold red] Research failed. Please try again.")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled. Press Ctrl+D or type 'exit' to quit.[/yellow]")
            continue
        except EOFError:
            console.print("\n[yellow]Exiting Web Research Agent...[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    console.print("[bold green]Goodbye![/bold green]")

def _get_file_extension(format):
    """Get file extension based on output format."""
    if format == 'json':
        return 'json'
    elif format == 'html':
        return 'html'
    else:
        return 'md'

def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")

if __name__ == '__main__':
    main()
