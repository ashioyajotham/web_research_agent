import os
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv
import nltk
from enum import Enum
from agent.core import Agent, AgentConfig
from tools.base import BaseTool

# Load environment variables
load_dotenv()

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def initialize_nltk():
    """Initialize NLTK with required data"""
    try:
        # Check if required data exists first
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('taggers/averaged_perceptron_tagger')
        nltk.data.find('corpora/stopwords')
        return True
    except LookupError:
        # Only download if not found
        try:
            nltk.download(['punkt', 'averaged_perceptron_tagger', 'stopwords'], quiet=True)
            return True
        except Exception as e:
            print(f"Note: NLTK data not automatically downloaded: {e}")
            print("If needed, manually download using: nltk.download()")
            return True  # Continue anyway since files might be manually installed

def extract_direct_answer(task: str, results: List[Dict]) -> Dict[str, str]:
    """Extract a direct answer from search results for direct questions"""
    answer = "Could not find a definitive answer"
    source = ""
    
    # Extract potential answer and source based on the search results
    if results and len(results) > 0:
        top_result = results[0]
        snippet = top_result.get('snippet', '')
        link = top_result.get('link', '')
        
        # Basic answer extraction - this could be enhanced with more sophisticated NLP
        if snippet:
            answer = snippet.split('.')[0]  # Take first sentence
            source = link
    
    return {
        "answer": answer,
        "source": source
    }

def is_direct_question(task: str) -> bool:
    """Check if task is a direct question requiring a single answer"""
    direct_question_starters = [
        "find the", "what is", "who is", "when did", "where is",
        "how many", "how much", "by what percentage"
    ]
    return any(task.lower().startswith(q) for q in direct_question_starters)

async def process_tasks(agent: Agent, tasks: List[str]) -> List[Dict]:
    """Process multiple tasks using the agent"""
    results = []
    for task in tasks:
        result = await agent.process_task(task)
        if is_direct_question(task):
            # For direct questions, extract and format a clear answer
            direct_answer = extract_direct_answer(task, result["output"]["results"])
            result["formatted_answer"] = direct_answer
        results.append(result)
    return results

def main(task_file_path: str, output_file_path: str):
    # Initialize NLTK silently
    initialize_nltk()
    
    # Import tools here to avoid circular imports
    from tools.google_search import GoogleSearchTool
    from tools.web_scraper import WebScraperTool
    from tools.code_tools import CodeGeneratorTool, CodeAnalysisTool
    
    # Initialize tools
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool(),
        "code_generator": CodeGeneratorTool()
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
    
    # Write results with custom encoder
    with open(output_file_path, 'w') as f:
        json.dump(results, f, indent=2, cls=EnhancedJSONEncoder)
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python agent.py <task_file_path> <output_file_path>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])
