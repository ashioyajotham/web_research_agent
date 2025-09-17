import argparse
import os
import asyncio
from agent.agent import WebResearchAgent
from utils.console_ui import (
    console, configure_logging, display_title, display_task_header,
    create_progress_context, display_plan, display_result, display_completion_message
)
from utils.logger import get_logger
from utils.task_parser import parse_tasks_from_file

# Initialize the logger 
logger = get_logger(__name__)

async def process_tasks(task_file_path):
    """Process tasks from a file and save results."""
    
    # Initialize the agent
    agent = WebResearchAgent()
    
    # Read tasks from file
    with open(task_file_path, 'r', encoding='utf-8') as file:
        tasks = [line.strip() for line in file if line.strip()]
    
    # Process each task
    for i, task in enumerate(tasks, 1):
        if not task:
            continue
            
        logger.info(f"Processing task {i}: {task}")
        
        try:
            # Use the agent's run method instead of manual orchestration
            result = await agent.run(task)
            
            # Save the result
            result_filename = os.path.join("results", f"task_{i}_result.md")
            os.makedirs("results", exist_ok=True)
            
            with open(result_filename, 'w', encoding='utf-8') as result_file:
                result_file.write(result)
            
            logger.info(f"Task {i} completed. Result saved to {result_filename}")
            
        except Exception as e:
            logger.error(f"Error processing task {i}: {e}")
            # Save error result
            error_result = f"# Task {i} - Error\n\nAn error occurred while processing this task:\n\n```\n{str(e)}\n```"
            result_filename = os.path.join("results", f"task_{i}_result.md")
            os.makedirs("results", exist_ok=True)
            
            with open(result_filename, 'w', encoding='utf-8') as result_file:
                result_file.write(error_result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Research Agent")
    parser.add_argument("task_file", help="Path to text file containing tasks")
    parser.add_argument("--output", default="results", help="Output directory for results")
    args = parser.parse_args()
    
    asyncio.run(process_tasks(args.task_file, args.output))
