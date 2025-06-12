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
from utils.logger import get_logger, set_log_level
from agent.agent import WebResearchAgent
from config.config import get_config, init_config
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Import the new parser
from utils.task_parser import parse_tasks_from_file

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
│  [bold green]Your Daily Research Tool - Practical Web Research & Analysis[/bold green]  │
╰──────────────────────────────────────────────────────────────╯[/bold blue]
"""

def display_banner():
    """Display the ASCII art banner."""
    console.print(BANNER)
    console.print("\n[dim]Version 1.1.10 - Type 'help' for commands[/dim]\n")
    console.print("[dim]Chef's kiss [bold magenta]Ashioya Jotham Victor[/bold magenta] - lock in, build and accelerate, loser![/dim]\n")

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
@click.option('--no-config', is_flag=True, help="Skip API key checks (commands requiring API keys will fail)")
def cli(verbose, no_config):
    """Web Research Agent - An intelligent tool for web-based research tasks."""
    # Set log level based on verbose flag
    import logging
    
    if verbose:
        set_log_level(logging.INFO)  # Using the non-relative import
    
    # Store no_config flag in a global context so it can be accessed by other commands
    from click import get_current_context
    ctx = get_current_context()
    ctx.obj = ctx.obj or {}
    ctx.obj['no_config'] = no_config
        
    # We'll keep the banner display only for the main CLI, but skip it for subcommands
    if len(sys.argv) == 1 or sys.argv[1] not in ['shell', 'search', 'batch', 'config']:
        display_banner()

def _check_required_keys(agent_initialization=False):
    """
    Check if required API keys are available and prompt for them if needed.
    
    Args:
        agent_initialization (bool): Whether this check is happening during agent initialization
            
    Returns:
        bool: True if all required keys are available (or were just added) or if --no-config was used
    """
    # Check if --no-config flag was set
    from click import get_current_context
    ctx = get_current_context()
    if ctx.obj and ctx.obj.get('no_config', False):
        if agent_initialization:
            console.print("[yellow]Warning: Running in no-config mode. API calls will fail.[/yellow]")
        return True
    
    config = get_config()
    keyring_available = False
    
    try:
        import keyring
        keyring_available = True
    except ImportError:
        keyring_available = False
        # Inform user about keyring if we're in interactive mode
        if agent_initialization:
            console.print(Panel(
                "[bold yellow]Secure Credential Storage Recommended[/bold yellow]\n\n"
                "For secure API key storage, install the keyring package:\n"
                "[bold]pip install keyring[/bold]\n\n"
                "This will store your API keys in your system's secure credential store\n"
                "instead of in plain text files.",
                title="Security Recommendation",
                border_style="yellow"
            ))
    
    required_keys = {
        'gemini_api_key': 'Gemini API key',
        'serper_api_key': 'Serper API key'
    }
    
    missing_keys = [key for key in required_keys if not config.get(key)]
    if not missing_keys:
        return True
    
    if agent_initialization:
        console.print(Panel(
            "[bold yellow]API Keys Required[/bold yellow]\n\n"
            "To use the Web Research Agent, you need to provide API keys.\n"
            "You'll be prompted to enter them now.",
            title="Configuration Needed",
            border_style="yellow"
        ))
    
    # Check which keys can be stored securely - safely handle different config types
    secure_storage_available = keyring_available
    secure_status = {}
    
    # Only try to call securely_stored_keys if the config object might have this method
    if hasattr(config, 'securely_stored_keys') and callable(getattr(config, 'securely_stored_keys', None)):
        try:
            secure_status = config.securely_stored_keys()
        except Exception:
            # Fall back to assuming no secure storage if method fails
            secure_status = {}
    else:
        # This is likely an old version or different implementation
        secure_storage_available = False
    
    for key, display_name in required_keys.items():
        if key not in missing_keys:
            continue
            
        prompt_text = f"{display_name} is required"
        if secure_storage_available:
            choice = click.confirm(
                f"{prompt_text}. Store securely in system keyring?",
                default=True
            )
            
            if not choice:
                console.print("[yellow]Note: API key will be stored in .env file instead.[/yellow]")
        
        value = click.prompt(f"Enter your {display_name}", hide_input=True)
        
        if secure_storage_available and choice:
            success = config.update(key, value, store_in_keyring=True)
            if success:
                console.print(f"[green]✓[/green] {display_name} saved securely in system keyring")
            else:
                console.print(f"[yellow]⚠[/yellow] Could not save to keyring, storing in .env file")
                _save_to_env_file(key, value)
        else:
            config.update(key, value, store_in_keyring=False)
            _save_to_env_file(key, value)
    
    return True

def _save_to_env_file(key, value):
    """Save a key-value pair to the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # Convert config key to environment variable name
    env_var = None
    config = get_config()
    
    # Try different ways to access ENV_MAPPING based on the config object type
    if hasattr(config, 'ENV_MAPPING'):
        # Direct access to ENV_MAPPING attribute
        env_mapping = config.ENV_MAPPING
    elif hasattr(config, '__class__') and hasattr(config.__class__, 'ENV_MAPPING'):
        # Class-level attribute
        env_mapping = config.__class__.ENV_MAPPING
    else:
        # Hard-coded fallback mapping
        env_mapping = {
            "GEMINI_API_KEY": "gemini_api_key",
            "SERPER_API_KEY": "serper_api_key"
        }
    
    # Get the environment variable from the mapping
    for env_name, config_key in env_mapping.items():
        if config_key == key:
            env_var = env_name
            break
    
    # Check if .env file exists and if the key is already in it
    lines = []
    key_found = False
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as file:
            lines = file.readlines()
        
        # Check if key already exists
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}="):
                lines[i] = f"{env_var}='{value}'\n"
                key_found = True
                break
    
    # If key not found, add it
    if not key_found:
        lines.append(f"{env_var}='{value}'\n")
    
    # Write back to .env file
    with open(env_path, 'w') as file:
        file.writelines(lines)
    
    console.print(f"[green]✓[/green] Saved {env_var} to .env file")

@cli.command()
@click.argument('query', required=True)
@click.option('--output', '-o', default="results", help="Output directory for results")
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'html']), default="markdown", 
              help="Output format for results")
def search(query, output, format):
    """Execute a single research task with the given query."""
    # Check if keys are configured before doing anything else
    if not _check_required_keys(agent_initialization=True):
        return
        
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
    
    # Use our new task parser
    tasks = parse_tasks_from_file(file)
    
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
                progress.update(research_task, completed=(j * 10))
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
@click.option('--use-keyring/--no-keyring', default=None, help="Whether to use system keyring for secure storage")
@click.option('--show', is_flag=True, help="Show current configuration")
def config(api_key, serper_key, timeout, format, use_keyring, show):
    """Configure the Web Research Agent."""
    config = get_config()
    secure_storage = False
    
    try:
        import keyring
        secure_storage = True
    except ImportError:
        secure_storage = False
        console.print(Panel(
            "[bold yellow]Security Recommendation[/bold yellow]\n\n"
            "For secure credential storage, install the keyring package:\n"
            "[bold]pip install keyring[/bold]\n\n"
            "Without keyring, API keys will be stored in a .env file.",
            border_style="yellow"
        ))
    
    if show:
        click.echo("Current configuration:")
        
        # Safely handle different config types
        secure_keys = {}
        if hasattr(config, 'securely_stored_keys') and callable(getattr(config, 'securely_stored_keys', None)):
            try:
                secure_keys = config.securely_stored_keys() 
            except Exception:
                secure_keys = {}
        
        for key, value in (config.items() if hasattr(config, 'items') else config.get_all().items()):
            if key.endswith('_api_key') and value:
                value = f"{value[:4]}...{value[-4:]}"
                storage_info = " [stored in system keyring]" if secure_keys.get(key, False) else ""
                click.echo(f"  {key}: {value}{storage_info}")
            else:
                click.echo(f"  {key}: {value}")
        return
    
    # Set keyring preference if specified
    if use_keyring is not None:
        if use_keyring and not secure_storage:
            console.print("[yellow]Warning: System keyring support not available. Install the 'keyring' package.[/yellow]")
        config.update('use_keyring', use_keyring and secure_storage)
        console.print(f"{'✅' if use_keyring else '❌'} {'Enabled' if use_keyring else 'Disabled'} secure credential storage")
    
    # Update API keys with secure storage if possible
    if api_key:
        stored_securely = config.update('gemini_api_key', api_key, store_in_keyring=True) if secure_storage else False
        console.print(f"✅ Updated Gemini API key{' (stored securely)' if stored_securely else ''}")
        if not stored_securely:
            _save_to_env_file('gemini_api_key', api_key)
    
    if serper_key:
        stored_securely = config.update('serper_api_key', serper_key, store_in_keyring=True) if secure_storage else False
        console.print(f"✅ Updated Serper API key{' (stored securely)' if stored_securely else ''}")
        if not stored_securely:
            _save_to_env_file('serper_api_key', serper_key)
    
    # Other config updates
    if timeout:
        config.update('timeout', timeout)
        console.print(f"✅ Updated request timeout to {timeout} seconds")
    
    if format:
        config.update('output_format', format)
        console.print(f"✅ Updated default output format to {format}")
    
    # If use_keyring is explicitly set to True but keyring isn't available
    if use_keyring is True and not secure_storage:
        console.print("[yellow]Warning: System keyring support not available. Install the 'keyring' package.[/yellow]")
        console.print("[bold]pip install keyring[/bold]")
        config.update('use_keyring', False)
        console.print("[yellow]❌ Keyring storage disabled - unavailable on this system[/yellow]")
    
    # Only check for missing keys if no specific updates were provided
    if not any([api_key, serper_key, timeout, format, use_keyring is not None]):
        _check_required_keys()

@cli.command()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging")
def shell(verbose):
    """Start an interactive shell for research tasks."""
    # Check if keys are configured before doing anything else
    if not _check_required_keys(agent_initialization=True):
        return
        
    # Set log level based on verbose flag
    import logging
    
    if verbose:
        set_log_level(logging.INFO)  # Using the non-relative import
    
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.styles import Style
    
    # Import direct answer extraction functionality
    from utils.formatters import extract_direct_answer
    
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
                        
                        progress.update(task, completed=(i * 10))
                        if i < 9:
                            time.sleep(0.2)  # Just for visual feedback
                    
                    # Complete the progress
                    if result:
                        progress.update(task, completed=(100))
                
                # Only proceed if we got results
                if result:
                    # Save result to file in results directory
                    os.makedirs("results", exist_ok=True)
                    filename = f"results/result_{_sanitize_filename(filename_query)}.md"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result)
                    
                    # NEW: Extract and show a direct answer if possible
                    direct_answer = extract_direct_answer(query, agent.memory.get_results(), agent.memory)
                    if direct_answer:
                        console.print("\n[bold green]Answer:[/bold green]", style="bold")
                        console.print(Panel(direct_answer, border_style="green", expand=False))
                    
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
