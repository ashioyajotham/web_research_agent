import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool
from agent.core import Agent, AgentConfig
from formatters.pretty_output import PrettyFormatter

async def run_market_research():
    # Initialize specialized tools for market research
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
    }
    
    config = AgentConfig(
        max_steps=5,
        min_confidence=0.7,
        timeout=300
    )
    
    agent = Agent(tools=tools, config=config)
    formatter = PrettyFormatter()
    
    # Process market research tasks
    task_file = os.path.join(os.path.dirname(__file__), "tasks/market_research.txt")
    
    with open(task_file, 'r') as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
        
    for task in tasks:
        result = await agent.process_task(task)
        formatter.format_task_result(task, result)
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run_market_research())
