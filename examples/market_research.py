import os
import sys
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
import re
from collections import Counter

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

from tools.google_search import GoogleSearchTool
from tools.web_scraper import WebScraperTool
from agent.core import Agent, AgentConfig
from formatters.pretty_output import PrettyFormatter

def extract_answer(query: str, results: List[Dict[str, str]]) -> str:
    """Extract specific answer from search results by analyzing patterns"""
    # Combine all snippets for analysis
    all_text = " ".join(r.get("snippet", "") for r in results)
    
    # Common patterns for numerical answers
    number_pattern = r'\d+(?:\.\d+)?'
    percentage_pattern = f'{number_pattern}%'
    money_pattern = f'\${number_pattern}(?:\s*(?:billion|million|trillion))?'
    
    # Find the most relevant sentence
    sentences = [s.strip() for s in all_text.split('.') if query.lower() in s.lower()]
    if not sentences:
        return "Could not find a specific answer."
        
    most_relevant = sentences[0]
    
    # Extract based on question type
    if 'market share' in query.lower():
        matches = re.findall(percentage_pattern, most_relevant)
        return matches[0] if matches else "No specific percentage found"
        
    elif 'market size' in query.lower():
        matches = re.findall(money_pattern, most_relevant)
        return matches[0] if matches else "No specific amount found"
        
    else:
        return most_relevant.strip()

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
        
        if result.get("success") and "results" in result.get("output", {}):
            answer = extract_answer(task, result["output"]["results"])
            print(f"\nTask: {task}")
            print(f"Answer: {answer}")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run_market_research())
