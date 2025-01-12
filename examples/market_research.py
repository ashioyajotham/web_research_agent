import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import Agent
from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool

def run_market_research():
    # Initialize specialized tools for market research
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
    }
    
    agent = Agent(tools)
    
    # Process market research tasks
    task_file = os.path.join(os.path.dirname(__file__), "tasks/market_research.txt")
    results_file = "market_research_results.json"
    
    with open(task_file, 'r') as f:
        tasks = f.readlines()
        
    for task in tasks:
        result = agent.process_task(task.strip())
        print(f"\nTask: {task.strip()}")
        print(f"Result: {result.result}")
        print(f"Confidence: {result.confidence}")
        print("-" * 80)

if __name__ == "__main__":
    run_market_research()
