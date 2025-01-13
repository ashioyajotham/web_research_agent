import sys
import os
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agent.core import Agent, AgentConfig
from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool
from tools.code_tools import CodeAnalysisTool

from dotenv import load_dotenv
load_dotenv()

async def run_tech_analysis():
    # Initialize tools
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool()
    }
    
    agent = Agent(tools)
    task_file = Path(__file__).parent / "tasks" / "tech_analysis.txt"
    
    try:
        with open(task_file, 'r') as f:
            tasks = [task.strip() for task in f.readlines() if task.strip()]
        
        results = []
        for task in tasks:
            result = await agent.process_task(task)
            results.append(result)
            
        return results
            
    except FileNotFoundError:
        print(f"Error: Task file not found at {task_file}")
        return []
    except Exception as e:
        print(f"Error during analysis: {e}")
        return []

if __name__ == "__main__":
    results = asyncio.run(run_tech_analysis())
    
    for result in results:
        print("\nTask Analysis:")
        print("-" * 50)
        print(f"Task: {result.get('task', 'Unknown')}")
        print(f"Status: {result.get('status', 'Error')}")
        if 'findings' in result:
            print(f"Findings: {result['findings']}")
        if 'error' in result:
            print(f"Error: {result['error']}")
