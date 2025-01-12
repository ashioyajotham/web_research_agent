import os
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv
from agent.core import Agent, AgentConfig
from tools.base import BaseTool

# Load environment variables
load_dotenv()

async def process_tasks(agent: Agent, tasks: List[str]) -> List[Dict]:
    """Process multiple tasks using the agent"""
    return await agent.process_tasks(tasks)

def main(task_file_path: str, output_file_path: str):
    # Import tools here to avoid circular imports
    from tools.google_search import GoogleSearchTool
    from tools.web_scraper import WebScraperTool
    from tools.code_tools import CodeAnalysisTool
    
    # Initialize tools
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool()
    }
    
    # Initialize agent with default config
    config = AgentConfig(
        max_steps=10,
        min_confidence=0.7,
        timeout=300,
        enable_reflection=True,
        memory_path="agent_memory.json",
        parallel_execution=True
    )
    
    agent = Agent(tools=tools, config=config)
    
    # Read tasks
    with open(task_file_path, 'r') as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
    
    # Process tasks and collect results
    results = asyncio.run(process_tasks(agent, tasks))
    
    # Write results
    with open(output_file_path, 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python agent.py <task_file_path> <output_file_path>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])
