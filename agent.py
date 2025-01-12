import os
import json
import asyncio
from typing import List, Dict
from dotenv import load_dotenv
import nltk
import datetime
import time
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
    context = ""
    
    if not results:
        return {"answer": answer, "source": source, "context": context}
    
    # Enhance pattern matching for specific question types
    task_lower = task.lower()
    if "coo" in task_lower or "chief operating officer" in task_lower:
        # Look for executive names and titles
        for result in results:
            snippet = result.get('snippet', '')
            if any(term in snippet.lower() for term in ['coo', 'chief operating', 'executive', 'leader']):
                answer = snippet
                source = result.get('link', '')
                context = f"From {result.get('title', '')}"
                break
                
    elif "percentage" in task_lower or "reduce" in task_lower:
        # Look for percentage changes and numerical values
        for result in results:
            snippet = result.get('snippet', '')
            if any(term in snippet.lower() for term in ['%', 'percent', 'reduction', 'decreased by']):
                answer = snippet
                source = result.get('link', '')
                context = f"From {result.get('title', '')}"
                break
    
    else:
        # Default extraction for other questions
        top_result = results[0]
        answer = top_result.get('snippet', '').split('.')[0]
        source = top_result.get('link', '')
        context = f"From {top_result.get('title', '')}"
    
    return {
        "answer": answer,
        "source": source,
        "context": context
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
        try:
            result = await agent.process_task(task)
            if is_direct_question(task) and result.get("success", False):
                # For direct questions, extract and format a clear answer
                direct_answer = extract_direct_answer(task, result.get("output", {}).get("results", []))
                result["formatted_answer"] = direct_answer
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "output": {"results": []},
                "task": task
            })
    return results

class Agent:
    def __init__(self, tools: Dict[str, BaseTool], config: AgentConfig):
        self.tools = tools
        self.config = config
        self.logger = AgentLogger()
        
    async def process_task(self, task: str) -> Dict:
        self.logger.task_start(task)
        start_time = time.time()
        
        try:
            task_lower = task.lower()
            if "implement" in task_lower or "create" in task_lower or "write" in task_lower:
                if any(term in task_lower for term in ["algorithm", "function", "class", "code"]):
                    result = await self._handle_code_task(task)
                else:
                    result = await self._process_task(task)
            elif "download" in task_lower and "dataset" in task_lower:
                result = await self._handle_dataset_task(task)
            else:
                result = await self._process_task(task)
                
            time_taken = time.time() - start_time
            self.logger.task_complete(task, time_taken)
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(error_msg, context=f"Task: {task[:50]}...")
            return {
                "success": False,
                "error": error_msg,
                "output": {"results": []}  # Ensure output.results exists even on error
            }

    async def _handle_dataset_task(self, task: str) -> Dict:
        """Handle tasks involving dataset downloads and processing"""
        try:
            # Use execute() instead of search()
            search_results = await self.tools["google_search"].execute(query=task)
            
            if not search_results.get("success", False):
                return {"success": False, "error": "Search failed"}
                
            results = search_results.get("results", [])
            dataset_url = self._extract_dataset_url(results)
            
            if not dataset_url:
                return {"success": False, "error": "Could not find dataset URL"}
                
            # Download and process dataset
            df = await self.tools["dataset"].download_dataset(dataset_url)
            
            # Determine analysis type and parameters from task
            analysis_params = self._extract_analysis_params(task)
            
            # Process the dataset
            result = await self.tools["dataset"].process_dataset(
                df, 
                analysis_params["type"],
                analysis_params["params"]
            )
            
            return {
                "success": True,
                "output": result
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_task(self, task: str) -> Dict:
        """Process a regular (non-dataset) task"""
        try:
            # Use Google Search as default tool for general tasks
            search_results = await self.tools["google_search"].execute(query=task)
            
            if search_results.get("success", False):
                return {
                    "success": True,
                    "output": {
                        "results": search_results.get("results", []),
                        "knowledge_graph": search_results.get("knowledge_graph", {}),
                        "related_searches": search_results.get("related_searches", [])
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Search failed",
                    "output": {"results": []}
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {"results": []}
            }

    async def _handle_code_task(self, task: str) -> Dict:
        """Handle tasks requiring code implementation"""
        try:
            # Extract key requirements and constraints from task
            requirements = self._extract_code_requirements(task)
            
            # Generate code using the code generator tool
            code_result = await self.tools["code_generator"].execute(
                prompt=f"""Implement the following with detailed code:
                Task: {task}
                Requirements: {requirements}
                Include:
                - Comprehensive error handling
                - Clear documentation
                - Type hints where applicable
                - Example usage
                """
            )
            
            if code_result.get("code"):
                # Analyze generated code for quality
                analysis = await self.tools["code_analysis"].execute(
                    code=code_result["code"],
                    context=task
                )
                
                return {
                    "success": True,
                    "output": {
                        "code": code_result["code"],
                        "language": code_result.get("language", "python"),
                        "analysis": analysis
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Code generation failed",
                    "output": {"results": []}
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_code_requirements(self, task: str) -> str:
        """Extract key requirements from coding task"""
        requirements = []
        task_lower = task.lower()
        
        # Algorithm type requirements
        if "mcts" in task_lower or "monte carlo tree search" in task_lower:
            requirements.extend([
                "Implement Monte Carlo Tree Search with selection, expansion, simulation, and backpropagation phases",
                "Include node class with visit counts and value statistics",
                "Support customizable simulation count and exploration parameter"
            ])
        elif "minimax" in task_lower:
            requirements.extend([
                "Implement Minimax algorithm with alpha-beta pruning",
                "Support customizable search depth",
                "Include evaluation function"
            ])
            
        # Game/problem specific requirements
        if "tic-tac-toe" in task_lower:
            requirements.extend([
                "Implement game state representation",
                "Include move validation",
                "Support both human and AI players",
                "Provide win condition checking"
            ])
            
        # General coding requirements
        requirements.extend([
            "Use object-oriented design where appropriate",
            "Include comprehensive error handling",
            "Add type hints and documentation"
        ])
        
        return "\n".join(f"- {req}" for req in requirements)

    def _extract_dataset_url(self, results: List[Dict]) -> str:
        """Extract dataset URL from search results"""
        dataset_keywords = ['dataset', 'data', 'csv', 'json', 'api']
        file_extensions = ['.csv', '.json', '.xlsx', '.zip', '.tar.gz']
        
        for result in results:
            url = result.get('link', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            # Check if URL directly points to a dataset file
            if any(url.endswith(ext) for ext in file_extensions):
                return url
                
            # Check if title/snippet suggests this is a dataset
            if any(keyword in title or keyword in snippet for keyword in dataset_keywords):
                return url
                
        return ''

    def _extract_analysis_params(self, task: str) -> Dict:
        """Extract analysis parameters from task description"""
        params = {
            "type": "time_series",  # Default analysis type
            "params": {}
        }
        
        task_lower = task.lower()
        
        # Detect time series analysis
        if any(term in task_lower for term in ['over time', 'trend', 'changes']):
            params["type"] = "time_series"
            
        # Detect statistical analysis
        elif any(term in task_lower for term in ['average', 'mean', 'median', 'correlation']):
            params["type"] = "statistical"
            
        # Detect comparative analysis
        elif any(term in task_lower for term in ['compare', 'difference', 'versus']):
            params["type"] = "comparative"
            
        # Extract specific parameters based on task
        if 'maximum' in task_lower or 'max' in task_lower:
            params["params"]["aggregate"] = "max"
        elif 'minimum' in task_lower or 'min' in task_lower:
            params["params"]["aggregate"] = "min"
            
        return params

def main(task_file_path: str, output_file_path: str):
    # Initialize NLTK silently
    initialize_nltk()
    
    # Import tools here to avoid circular imports
    from tools.google_search import GoogleSearchTool
    from tools.web_scraper import WebScraperTool
    from tools.code_tools import CodeGeneratorTool, CodeAnalysisTool
    from tools.dataset_tool import DatasetTool
    
    # Initialize tools
    tools = {
        "google_search": GoogleSearchTool(),
        "web_scraper": WebScraperTool(),
        "code_analysis": CodeAnalysisTool(),
        "code_generator": CodeGeneratorTool(),
        "dataset": DatasetTool()  # Add the dataset tool
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
    agent.logger.log('INFO', "Agent initialized with tools and config", "Startup")
    
    # Read tasks
    with open(task_file_path, 'r') as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
    agent.logger.log('INFO', f"Loaded {len(tasks)} tasks from {task_file_path}", "Startup")
    
    # Initialize pretty formatter
    formatter = PrettyFormatter()
    
    # Process tasks and collect results
    results = asyncio.run(process_tasks(agent, tasks))
    
    # Pretty print results
    console = Console()
    console.print("\n[bold]🤖 Web Research Agent Results[/bold]\n")
    
    for task, result in zip(tasks, results):
        formatter.format_task_result(task, result)
        console.print("\n" + "-" * 80 + "\n")
    
    # Also save JSON results for programmatic access
    with open(output_file_path, 'w') as f:
        json.dump(results, f, indent=2, cls=EnhancedJSONEncoder)
    
    console.print(f"\n[dim]Full results saved to: {output_file_path}[/dim]")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python agent.py <task_file_path> <output_file_path>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])
