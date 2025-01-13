import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import Agent, AgentConfig, AgentLogger
from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool

from dotenv import load_dotenv
load_dotenv()

async def run_sustainability_analysis():
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool()
    }
    
    agent = Agent(tools)
    task_file = os.path.join(os.path.dirname(__file__), "tasks/environmental_data.txt")
    
    with open(task_file, 'r') as f:
        tasks = f.readlines()
        
    for task in tasks:
        result = await agent.process_task(task.strip())
        print(f"\nSustainability Analysis Task: {task.strip()}")
        print(f"Environmental Data: {result.get('findings', 'No data available')}")
        print(f"Status: {result.get('status', 'Unknown')}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run_sustainability_analysis())
