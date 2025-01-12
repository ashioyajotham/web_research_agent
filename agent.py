import os
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv
import nltk
from rich.console import Console
from enum import Enum

from agent.core import Agent, AgentConfig
from tools.base import BaseTool
from formatters.pretty_output import PrettyFormatter
from utils.logger import AgentLogger

# Load environment variables
load_dotenv()

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def initialize_nltk():
    # ...existing NLTK initialization code...
    pass

async def process_tasks(agent: Agent, tasks: List[str]) -> List[Dict]:
    """Process multiple tasks using the agent"""
    return await asyncio.gather(*[agent.process_task(task) for task in tasks])

def main(task_file_path: str, output_file_path: str):
    # Verify environment variables are loaded
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("GOOGLE_CSE_ID"):
        print("\nEnvironment Variable Check:")
        print(f"GOOGLE_API_KEY: {'✓ Set' if os.getenv('GOOGLE_API_KEY') else '✗ Missing'}")
        print(f"GOOGLE_CSE_ID: {'✓ Set' if os.getenv('GOOGLE_CSE_ID') else '✗ Missing'}")
        print("\nPlease ensure your .env file contains the required variables")
        sys.exit(1)

    # Initialize NLTK silently
    initialize_nltk()
    
    # Import and initialize tools
    from tools.google_search import GoogleSearchTool
    from tools.web_scraper import WebScraperTool
    from tools.code_tools import CodeGeneratorTool, CodeAnalysisTool
    from tools.dataset_tool import DatasetTool
    
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool(),
        "code_generator": CodeGeneratorTool(),
        "dataset": DatasetTool()
    }
    
    # Initialize agent with updated config parameters
    config = AgentConfig(
        max_steps=10,
        min_confidence=0.7,
        timeout=300,
        learning_enabled=True,  # Changed from enable_reflection
        memory_path="agent_memory.db",
        parallel_execution=True,
        planning_enabled=True,
        pattern_learning_enabled=True
    )
    
    agent = Agent(tools=tools, config=config)
    
    # Read tasks
    with open(task_file_path, 'r') as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
    
    # Process tasks and format results
    results = asyncio.run(process_tasks(agent, tasks))
    
    # Output formatting
    console = Console()
    formatter = PrettyFormatter()
    
    console.print("\n[bold]🤖 Web Research Agent Results[/bold]\n")
    for task, result in zip(tasks, results):
        formatter.format_task_result(task, result)
        console.print("\n" + "-" * 80 + "\n")
    
    # Save results
    with open(output_file_path, 'w') as f:
        json.dump(results, f, indent=2, cls=EnhancedJSONEncoder)
    
    console.print(f"\n[dim]Full results saved to: {output_file_path}[/dim]")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python agent.py <task_file_path> <output_file_path>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])