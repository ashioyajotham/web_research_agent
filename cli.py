"""
Interactive CLI for Web Research Agent.
Provides a beautiful terminal interface with ASCII art and configuration management.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import logging
import random
import time

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown

    console = Console()
except ImportError:
    # Fallback if rich not installed
    console = None

    def rprint(*args, **kwargs):
        print(*args, **kwargs)


# ASCII Art with gradient effect - BIG AND BOLD
ASCII_ART = r"""
██╗    ██╗███████╗██████╗     ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
██║    ██║██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
██║ █╗ ██║█████╗  ██████╔╝    ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║
██║███╗██║██╔══╝  ██╔══██╗    ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
╚███╔███╔╝███████╗██████╔╝    ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
 ╚══╝╚══╝ ╚══════╝╚═════╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
"""

VERSION = "1.2.0"
TAGLINE = "lock in, anon"

# Spicy loading messages
LOADING_MESSAGES = [
    "Summoning the AI overlords...",
    "Teaching robots to google...",
    "Consulting the digital oracle...",
    "Bribing search engines...",
    "Downloading the internet...",
    "Asking ChatGPT's cool cousin...",
    "Hacking the mainframe...",
    "Reading the Matrix...",
    "Brewing digital coffee...",
    "Waking up the neurons...",
    "Compiling knowledge...",
    "Unleashing the agents...",
    "Charging the flux capacitor...",
    "Spinning up the hamster wheel...",
    "Consulting the elders of the internet...",
]

# Disable logging output to console by default
logging.getLogger().setLevel(logging.WARNING)


def print_banner():
    """Print the beautiful ASCII banner with gradient colors."""
    if console:
        # Rich version with gradient
        lines = ASCII_ART.strip().split("\n")

        # Blue gradient colors
        colors = [
            "bright_blue",
            "blue",
            "dodger_blue2",
            "deep_sky_blue1",
            "blue",
            "bright_blue",
        ]

        console.print()
        for i, line in enumerate(lines):
            color = colors[i % len(colors)]
            console.print(line, style=f"bold {color}")

        # Version and tagline
        version_text = Text()
        version_text.append(f"v{VERSION}", style="bold yellow")
        console.print(version_text, justify="center")

        tagline_text = Text(TAGLINE, style="italic cyan")
        console.print(tagline_text, justify="center")

        console.print("═" * 100, style="bright_blue")
        console.print()
    else:
        # Fallback for no rich
        print("\n" + ASCII_ART)
        print(f"v{VERSION}")
        print(TAGLINE)
        print("=" * 100 + "\n")


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    # Store config in user's home directory
    config_dir = Path.home() / ".webresearch"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.env"


def load_config() -> dict:
    """Load configuration from file."""
    config_path = get_config_path()
    config = {}

    if config_path.exists():
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

    return config


def save_config(config: dict):
    """Save configuration to file."""
    config_path = get_config_path()

    with open(config_path, "w") as f:
        f.write("# Web Research Agent Configuration\n")
        f.write("# This file is automatically generated\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")

    if console:
        console.print(f"✓ Configuration saved to {config_path}", style="bold green")
    else:
        print(f"✓ Configuration saved to {config_path}")


def setup_api_keys() -> dict:
    """Interactive setup for API keys."""
    if console:
        console.print(
            Panel.fit(
                "🔧 [bold cyan]First-time Setup[/bold cyan]\nLet's configure your API keys.",
                border_style="cyan",
            )
        )
        console.print()

        config = {}

        # Gemini API Key
        console.print("[bold yellow]1. Gemini API Key[/bold yellow]")
        console.print(
            "   Get yours at: [link=https://makersuite.google.com/app/apikey]https://makersuite.google.com/app/apikey[/link]"
        )
        gemini_key = Prompt.ask("   [green]Enter Gemini API key[/green]").strip()

        if not gemini_key:
            console.print("[bold red]✗ Gemini API key is required![/bold red]")
            sys.exit(1)

        config["GEMINI_API_KEY"] = gemini_key

        # Serper API Key
        console.print("\n[bold yellow]2. Serper API Key[/bold yellow]")
        console.print(
            "   Get yours at: [link=https://serper.dev]https://serper.dev[/link]"
        )
        console.print("   [dim](Free tier: 2,500 searches/month)[/dim]")
        serper_key = Prompt.ask("   [green]Enter Serper API key[/green]").strip()

        if not serper_key:
            console.print("[bold red]✗ Serper API key is required![/bold red]")
            sys.exit(1)

        config["SERPER_API_KEY"] = serper_key

        # Optional settings with defaults
        console.print(
            "\n[bold yellow]3. Optional Settings[/bold yellow] [dim](press Enter for defaults)[/dim]"
        )

        max_iterations = Prompt.ask("   [green]Max iterations[/green]", default="15")
        config["MAX_ITERATIONS"] = max_iterations

        temperature = Prompt.ask("   [green]Temperature[/green]", default="0.1")
        config["TEMPERATURE"] = temperature

        config["MAX_TOOL_OUTPUT_LENGTH"] = "5000"
        config["MODEL_NAME"] = "gemini-2.0-flash-exp"
        config["WEB_REQUEST_TIMEOUT"] = "30"
        config["CODE_EXECUTION_TIMEOUT"] = "60"

        console.print()
        save_config(config)
        console.print()

        return config
    else:
        # Fallback for no rich
        print("First-time Setup")
        print("Let's configure your API keys.\n")

        config = {}
        gemini_key = input("Enter Gemini API key: ").strip()
        if not gemini_key:
            print("✗ Gemini API key is required!")
            sys.exit(1)
        config["GEMINI_API_KEY"] = gemini_key

        serper_key = input("Enter Serper API key: ").strip()
        if not serper_key:
            print("✗ Serper API key is required!")
            sys.exit(1)
        config["SERPER_API_KEY"] = serper_key

        config["MAX_ITERATIONS"] = "15"
        config["TEMPERATURE"] = "0.1"
        config["MAX_TOOL_OUTPUT_LENGTH"] = "5000"
        config["MODEL_NAME"] = "gemini-2.0-flash-exp"
        config["WEB_REQUEST_TIMEOUT"] = "30"
        config["CODE_EXECUTION_TIMEOUT"] = "60"

        save_config(config)
        return config


def check_config() -> dict:
    """Check if configuration exists, prompt for setup if needed."""
    # First check if .env file exists in current directory (development mode)
    if os.path.exists(".env"):
        from dotenv import load_dotenv

        load_dotenv()
        config = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "SERPER_API_KEY": os.getenv("SERPER_API_KEY", ""),
            "MAX_ITERATIONS": os.getenv("MAX_ITERATIONS", "15"),
            "TEMPERATURE": os.getenv("TEMPERATURE", "0.1"),
            "MAX_TOOL_OUTPUT_LENGTH": os.getenv("MAX_TOOL_OUTPUT_LENGTH", "5000"),
            "MODEL_NAME": os.getenv("MODEL_NAME", "gemini-2.0-flash-exp"),
            "WEB_REQUEST_TIMEOUT": os.getenv("WEB_REQUEST_TIMEOUT", "30"),
            "CODE_EXECUTION_TIMEOUT": os.getenv("CODE_EXECUTION_TIMEOUT", "60"),
        }

        if config["GEMINI_API_KEY"] and config["SERPER_API_KEY"]:
            if console:
                console.print(
                    "✓ Using configuration from .env file", style="bold green"
                )
            else:
                print("✓ Using configuration from .env file")
            return config

    # Otherwise check user's home directory config
    config = load_config()

    # Check if essential keys exist
    if "GEMINI_API_KEY" not in config or "SERPER_API_KEY" not in config:
        if console:
            console.print(
                "⚠ Configuration not found or incomplete.\n", style="bold yellow"
            )
        else:
            print("⚠ Configuration not found or incomplete.\n")
        config = setup_api_keys()

    return config


def apply_config_to_env(config: dict):
    """Apply configuration to environment variables."""
    for key, value in config.items():
        os.environ[key] = value


def show_menu():
    """Display the main menu."""
    if console:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold")
        table.add_column(style="white")

        table.add_row("1.", "[green]🔍 Run a research query[/green]")
        table.add_row("2.", "[yellow]📁 Process tasks from file[/yellow]")
        table.add_row("3.", "[blue]📋 View recent logs[/blue]")
        table.add_row("4.", "[magenta]🔧 Reconfigure API keys[/magenta]")
        table.add_row("5.", "[red]👋 Exit[/red]")

        console.print(
            Panel(
                table,
                title="[bold cyan]What would you like to do?[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()
    else:
        print("What would you like to do?")
        print("1. Run a research query")
        print("2. Process tasks from file")
        print("3. View recent logs")
        print("4. Reconfigure API keys")
        print("5. Exit")
        print()


def view_logs():
    """View recent log files."""
    logs_dir = Path("logs")

    if not logs_dir.exists() or not list(logs_dir.glob("*.log")):
        if console:
            console.print("⚠ No log files found.", style="bold yellow")
        else:
            print("⚠ No log files found.")
        return

    log_files = sorted(
        logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
    )

    if console:
        from datetime import datetime

        console.print(
            Panel.fit("📋 [bold cyan]Recent Log Files[/bold cyan]", border_style="cyan")
        )
        console.print()

        table = Table(show_header=True, box=None)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Filename", style="green")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Modified", style="white")

        for i, log_file in enumerate(log_files[:5], 1):
            size = log_file.stat().st_size / 1024  # KB
            mtime = log_file.stat().st_mtime
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row(str(i), log_file.name, f"{size:.1f} KB", time_str)

        console.print(table)
        console.print()

        choice = Prompt.ask(
            "[green]Enter number to view[/green] (or press Enter to skip)", default=""
        )
    else:
        from datetime import datetime

        print("Recent Log Files:")
        for i, log_file in enumerate(log_files[:5], 1):
            size = log_file.stat().st_size / 1024  # KB
            mtime = log_file.stat().st_mtime
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i}. {log_file.name} ({size:.1f} KB) - {time_str}")

        print()
        choice = input("Enter number to view (or press Enter to skip): ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(log_files[:5]):
        log_file = log_files[int(choice) - 1]

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

            if console:
                console.print()
                console.rule(
                    f"[bold cyan]Log: {log_file.name}[/bold cyan]", style="cyan"
                )
                console.print()

                if len(lines) > 100:
                    console.print("[yellow][Showing last 100 lines...][/yellow]\n")
                    lines = lines[-100:]

                for line in lines:
                    if "ERROR" in line:
                        console.print(line, style="bold red")
                    elif "WARNING" in line:
                        console.print(line, style="bold yellow")
                    elif "INFO" in line:
                        console.print(line, style="white")
                    else:
                        console.print(line)

                console.print()
                console.rule(style="cyan")
                console.print()
            else:
                print(f"\n{'=' * 80}")
                print(f"Log: {log_file.name}")
                print(f"{'=' * 80}\n")

                if len(lines) > 100:
                    print("[Showing last 100 lines...]\n")
                    lines = lines[-100:]

                for line in lines:
                    print(line)

                print(f"\n{'=' * 80}\n")


def run_interactive_query():
    """Run a single interactive research query."""
    if console:
        console.print(
            Panel.fit(
                "🔍 [bold cyan]Research Query Mode[/bold cyan]", border_style="cyan"
            )
        )
        console.print()
        query = Prompt.ask(
            "[green]❯[/green] Enter your research question (or type 'back' to return)"
        )
    else:
        print("Research Query Mode")
        print("Enter your research question (or type 'back' to return):\n")
        query = input("❯ ").strip()

    if query.lower() == "back" or not query:
        return

    # Show a random spicy loading message
    loading_msg = random.choice(LOADING_MESSAGES)

    # Import here to avoid circular imports
    from datetime import datetime
    import sys
    import os

    # Add current directory to path to find webresearch package
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from webresearch.config import config
    from webresearch.llm import LLMInterface
    from webresearch.tools import (
        ToolManager,
        SearchTool,
        ScrapeTool,
        CodeExecutorTool,
        FileOpsTool,
    )
    from webresearch.agent import ReActAgent

    def initialize_agent(verbose=False):
        """Initialize the agent with all components."""
        config.validate()

        llm = LLMInterface(
            api_key=config.gemini_api_key,
            model_name=config.model_name,
            temperature=config.temperature,
        )

        tool_manager = ToolManager()
        tool_manager.register_tool(SearchTool(config.serper_api_key))
        tool_manager.register_tool(ScrapeTool())
        tool_manager.register_tool(CodeExecutorTool())
        tool_manager.register_tool(FileOpsTool())

        return ReActAgent(
            llm=llm,
            tool_manager=tool_manager,
            max_iterations=config.max_iterations,
        )

    # Initialize agent
    try:
        agent = initialize_agent(verbose=False)
    except Exception as e:
        print(f"{Fore.RED}✗ Error initializing agent: {str(e)}")
        print(f"{Fore.YELLOW}Tip: Check your API keys with option 4.")
        return

    # Run the query
    start_time = datetime.now()

    try:
        if console:
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold cyan]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(loading_msg, total=None)
                answer = agent.run(query)
                progress.stop()
        else:
            print("Agent is thinking...\n")
            answer = agent.run(query)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Display result
        if console:
            console.print()
            console.rule("[bold green]RESULT[/bold green]", style="green")
            console.print()
            console.print(Panel(answer, border_style="green", padding=(1, 2)))
            console.print()
            console.print(
                f"⏱  [yellow]Completed in {execution_time:.2f} seconds[/yellow]"
            )
            console.print()
        else:
            print(f"\n{'=' * 80}")
            print("RESULT")
            print(f"{'=' * 80}\n")
            print(answer)
            print(f"\n{'─' * 80}")
            print(f"⏱ Completed in {execution_time:.2f} seconds")
            print(f"{'=' * 80}\n")

        # Offer to save
        if console:
            save = Confirm.ask("Save result to file?")
        else:
            save = input("Save result to file? (y/n): ").strip().lower() == "y"

        if save:
            if console:
                filename = Prompt.ask("Filename", default="result.txt")
            else:
                filename = input("Filename [result.txt]: ").strip() or "result.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Query: {query}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(answer)
                f.write(f"\n\n{'─' * 80}\n")
                f.write(f"Execution time: {execution_time:.2f} seconds\n")

            if console:
                console.print(f"✓ Saved to [cyan]{filename}[/cyan]", style="bold green")
            else:
                print(f"✓ Saved to {filename}\n")

    except KeyboardInterrupt:
        if console:
            console.print("\n⚠ Research interrupted by user.", style="bold yellow")
        else:
            print("\n⚠ Research interrupted by user.\n")
    except Exception as e:
        if console:
            console.print(f"✗ Error during research: {str(e)}", style="bold red")
            console.print("Check logs for more details (option 3).", style="yellow")
        else:
            print(f"✗ Error during research: {str(e)}")
            print("Check logs for more details (option 3).\n")


def run_tasks_from_file():
    """Run tasks from a file."""
    print(f"{Style.BRIGHT}{Fore.CYAN}Process Tasks from File")
    print(f"{Fore.WHITE}Enter the path to your tasks file:\n")

    filepath = input(f"{Fore.GREEN}❯ {Fore.WHITE}").strip()

    if not filepath or filepath.lower() == "back":
        return

    if not os.path.exists(filepath):
        print(f"{Fore.RED}✗ File not found: {filepath}\n")
        return

    output_file = input(
        f"{Fore.GREEN}Output file [{Fore.WHITE}results.txt{Fore.GREEN}]: {Fore.WHITE}"
    ).strip()
    if not output_file:
        output_file = "results.txt"

    print(f"\n{Fore.YELLOW}🔍 Processing tasks from: {Fore.WHITE}{filepath}")
    print(f"{Fore.YELLOW}📝 Results will be saved to: {Fore.WHITE}{output_file}")
    print(f"{Fore.CYAN}{'─' * 80}\n")

    # Import and run
    from datetime import datetime
    import sys
    import os

    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    def read_tasks(task_file):
        """Read tasks from file."""
        with open(task_file, "r", encoding="utf-8") as f:
            tasks = []
            current_task = []
            for line in f:
                line = line.rstrip()
                if not line:
                    if current_task:
                        tasks.append("\n".join(current_task))
                        current_task = []
                else:
                    current_task.append(line)
            if current_task:
                tasks.append("\n".join(current_task))
        return tasks

    def write_results(output_file, results):
        """Write results to file."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("WEB RESEARCH AGENT RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")

            for i, result in enumerate(results, 1):
                f.write(f"\n{'=' * 100}\n")
                f.write(f"TASK {i}\n")
                f.write(f"{'=' * 100}\n\n")
                f.write(f"TASK DESCRIPTION:\n{result['task']}\n\n")
                f.write(f"{'-' * 100}\n\n")
                f.write(f"ANSWER:\n{result['answer']}\n\n")
                if result.get("error"):
                    f.write(f"ERROR: {result['error']}\n\n")
                f.write(
                    f"Execution time: {result.get('execution_time', 'N/A')} seconds\n"
                )
                f.write(f"Number of steps: {result.get('num_steps', 'N/A')}\n")

    try:
        tasks = read_tasks(filepath)
        agent = initialize_agent(verbose=False)

        results = []
        for i, task in enumerate(tasks, 1):
            print(f"{Fore.CYAN}[Task {i}/{len(tasks)}] {Fore.WHITE}{task[:60]}...")

            start_time = datetime.now()
            try:
                answer = agent.run(task)
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()

                result = {
                    "task": task,
                    "answer": answer,
                    "execution_time": execution_time,
                    "num_steps": len(agent.get_execution_trace()),
                    "trace": agent.get_execution_trace(),
                }

                results.append(result)
                print(f"{Fore.GREEN}✓ Completed in {execution_time:.2f}s\n")

            except Exception as e:
                print(f"{Fore.RED}✗ Error: {str(e)}\n")
                result = {
                    "task": task,
                    "answer": "Error occurred during processing",
                    "error": str(e),
                }
                results.append(result)

        write_results(output_file, results)
        print(f"{Fore.GREEN}✓ All tasks completed! Results saved to {output_file}\n")

    except Exception as e:
        print(f"{Fore.RED}✗ Error: {str(e)}\n")


def main():
    """Main CLI entry point."""
    # Print banner
    print_banner()

    # Check and load configuration
    config = check_config()
    apply_config_to_env(config)

    if console:
        console.print("✓ Configuration loaded", style="bold green")
        console.print()
    else:
        print("✓ Configuration loaded")
        print()

    # Main loop
    while True:
        show_menu()

        if console:
            choice = Prompt.ask(
                "[green]❯[/green] Choose an option", choices=["1", "2", "3", "4", "5"]
            )
        else:
            choice = input("❯ ").strip()

        console.print() if console else print()

        if choice == "1":
            run_interactive_query()
        elif choice == "2":
            run_tasks_from_file()
        elif choice == "3":
            view_logs()
        elif choice == "4":
            config = setup_api_keys()
            apply_config_to_env(config)
        elif choice == "5":
            if console:
                console.print(
                    Panel.fit(
                        "👋 [bold cyan]Thanks for using Web Research Agent![/bold cyan]\nStay curious, anon.",
                        border_style="cyan",
                    )
                )
            else:
                print("Thanks for using Web Research Agent! 👋\n")
            sys.exit(0)
        else:
            if console:
                console.print("Invalid choice. Please try again.", style="bold red")
            else:
                print("Invalid choice. Please try again.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if console:
            console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]\n")
        else:
            print("\nGoodbye! 👋\n")
        sys.exit(0)
