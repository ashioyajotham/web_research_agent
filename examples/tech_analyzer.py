import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import Agent
from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool
from tools.code_tools import CodeAnalysisTool

def run_tech_analysis():
    # Initialize tools with focus on technical analysis
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool()
    }
    
    agent = Agent(tools)
    task_file = os.path.join(os.path.dirname(__file__), "tasks/tech_analysis.txt")
    
    with open(task_file, 'r') as f:
        tasks = f.readlines()
        
    for task in tasks:
        result = agent.process_task(task.strip())
        print(f"\nTechnology Analysis Task: {task.strip()}")
        print(f"Findings: {result.result}")
        print(f"Confidence: {result.confidence}")
        print("-" * 80)

if __name__ == "__main__":
    run_tech_analysis()
